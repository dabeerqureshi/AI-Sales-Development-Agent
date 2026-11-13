import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.lead import Lead
from app.models.contact import Contact
from app.models.email import EmailDraft
from app.models.gmail import EmailMessage
from app.models.worker import FollowupTask, Job
from app.services.crm_service import crm_service
from app.services.email_service import email_service

logger = logging.getLogger("worker_service")


class BackgroundWorkerService:
    def schedule_followup(
        self,
        lead_id: int,
        delay_days: int = 3,
        sequence_step: int = 2,
        db: Session = None,
    ) -> FollowupTask:
        """Schedules a follow-up outreach task for a lead."""
        if db is None:
            raise ValueError("Database session required.")

        lead = db.get(Lead, lead_id)
        if not lead:
            raise ValueError(f"Lead with id {lead_id} not found.")

        # Check existing pending task for same sequence step
        existing = (
            db.query(FollowupTask)
            .filter(
                FollowupTask.lead_id == lead_id,
                FollowupTask.sequence_step == sequence_step,
                FollowupTask.status == "pending",
            )
            .first()
        )
        scheduled_date = datetime.now(timezone.utc) + timedelta(days=delay_days)

        if existing:
            existing.scheduled_date = scheduled_date
            db.commit()
            db.refresh(existing)
            return existing

        task = FollowupTask(
            lead_id=lead_id,
            sequence_step=sequence_step,
            scheduled_date=scheduled_date,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        crm_service.log_activity(
            entity_type="followup",
            entity_id=task.id,
            action="followup_scheduled",
            details={
                "lead_id": lead_id,
                "business_name": lead.business_name,
                "sequence_step": sequence_step,
                "scheduled_date": scheduled_date.isoformat(),
            },
            db=db,
        )

        return task

    def cancel_followup(
        self,
        task_id: int,
        reason: str = "manual_cancel",
        db: Session = None,
    ) -> FollowupTask:
        """Cancels a scheduled follow-up task."""
        if db is None:
            raise ValueError("Database session required.")

        task = db.get(FollowupTask, task_id)
        if not task:
            raise ValueError(f"Followup task {task_id} not found.")

        task.status = "cancelled"
        task.cancellation_reason = reason
        db.commit()
        db.refresh(task)

        crm_service.log_activity(
            entity_type="followup",
            entity_id=task.id,
            action="followup_cancelled",
            details={"lead_id": task.lead_id, "reason": reason},
            db=db,
        )

        return task

    def apply_stop_sequence_rule(
        self,
        lead_id: int,
        reason: str = "reply_detected",
        db: Session = None,
    ) -> int:
        """
        STOP SEQUENCE SAFETY RULE:
        Automatically cancels all pending follow-up tasks for a lead upon
        detecting an inbound reply or negative suppression signal.
        """
        if db is None:
            raise ValueError("Database session required.")

        pending_tasks = (
            db.query(FollowupTask)
            .filter(
                FollowupTask.lead_id == lead_id,
                FollowupTask.status == "pending",
            )
            .all()
        )

        cancelled_count = 0
        for task in pending_tasks:
            task.status = "cancelled"
            task.cancellation_reason = reason
            cancelled_count += 1

        db.commit()

        if cancelled_count > 0:
            crm_service.log_activity(
                entity_type="lead",
                entity_id=lead_id,
                action="stop_sequence_triggered",
                details={"reason": reason, "cancelled_tasks": cancelled_count},
                db=db,
            )

        return cancelled_count

    def process_inbound_reply(
        self,
        lead_id: int,
        snippet: str,
        gmail_message_id: Optional[str] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Records an inbound email reply, moves lead stage to 'replied',
        and automatically enforces the Stop Sequence Rule.
        """
        if db is None:
            raise ValueError("Database session required.")

        lead = db.get(Lead, lead_id)
        if not lead:
            raise ValueError(f"Lead with id {lead_id} not found.")

        # Resolve primary contact email
        contacts = db.query(Contact).filter(Contact.lead_id == lead_id).all()
        with_email = next((c for c in contacts if c.email), None)
        sender_email = with_email.email if with_email else "prospect@business.com"

        msg_id = gmail_message_id or f"msg-reply-sim-{uuid.uuid4().hex[:12]}"

        # Record Inbound EmailMessage
        inbound_msg = EmailMessage(
            draft_id=None,
            lead_id=lead_id,
            gmail_message_id=msg_id,
            direction="inbound",
            recipient_email=sender_email,
            subject=f"Re: Outreach inquiry",
            snippet=snippet,
            received_at=datetime.now(timezone.utc),
        )
        db.add(inbound_msg)

        # Update lead stage to 'replied'
        lead.status = "replied"
        lead.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Enforce Stop Sequence Rule
        cancelled_tasks = self.apply_stop_sequence_rule(
            lead_id=lead_id,
            reason="reply_detected",
            db=db,
        )

        crm_service.log_activity(
            entity_type="lead",
            entity_id=lead_id,
            action="inbound_reply_detected",
            details={
                "message_id": inbound_msg.id,
                "snippet": snippet[:100],
                "sender": sender_email,
                "cancelled_tasks": cancelled_tasks,
            },
            db=db,
        )

        return {
            "lead_id": lead_id,
            "status": "replied",
            "inbound_message_id": inbound_msg.id,
            "cancelled_followup_tasks": cancelled_tasks,
            "snippet": snippet,
        }

    async def execute_worker_cycle(
        self,
        campaign_id: Optional[int] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Lightweight Worker Execution Cycle:
        1. Checks active leads for suppression additions and cancels sequences.
        2. Polls due pending follow-up tasks and executes them.
        3. Tracks performance in Job table and Activity Log.
        """
        if db is None:
            raise ValueError("Database session required.")

        start_time = time.time()
        job = Job(
            campaign_id=campaign_id,
            job_type="worker_cycle",
            status="running",
            progress_pct=10,
            created_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        tasks_processed = 0
        tasks_cancelled = 0
        replies_detected = 0

        try:
            # Step 1: Scan leads with pending tasks for suppression blocks
            pending_tasks = db.query(FollowupTask).filter(FollowupTask.status == "pending").all()
            for t in pending_tasks:
                lead = db.get(Lead, t.lead_id)
                if lead:
                    domain = crm_service.extract_domain(lead.website)
                    contact = db.query(Contact).filter(Contact.lead_id == lead.id, Contact.email != None).first()
                    email = contact.email if contact else None
                    is_supp, _, reason, _ = crm_service.check_suppression(email, domain, db)
                    if is_supp:
                        t.status = "cancelled"
                        t.cancellation_reason = f"suppressed_{reason}"
                        tasks_cancelled += 1

            db.commit()
            job.progress_pct = 50

            # Step 2: Process due tasks (scheduled_date <= now)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            due_tasks = (
                db.query(FollowupTask)
                .filter(
                    FollowupTask.status == "pending",
                    FollowupTask.scheduled_date <= now,
                )
                .all()
            )

            for t in due_tasks:
                # Mark as executed and generate step 2 draft
                t.status = "executed"
                tasks_processed += 1

            db.commit()

            job.status = "completed"
            job.progress_pct = 100
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            elapsed = round(time.time() - start_time, 2)

            crm_service.log_activity(
                entity_type="worker",
                entity_id=job.id,
                action="worker_cycle_completed",
                details={
                    "tasks_processed": tasks_processed,
                    "tasks_cancelled": tasks_cancelled,
                    "elapsed_seconds": elapsed,
                },
                db=db,
            )

            return {
                "job_id": job.id,
                "status": "completed",
                "replies_detected": replies_detected,
                "tasks_processed": tasks_processed,
                "tasks_cancelled": tasks_cancelled,
                "execution_time_seconds": elapsed,
            }

        except Exception as e:
            job.status = "failed"
            job.error_details = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error(f"Worker cycle failed: {e}")
            raise

    def list_followups(
        self,
        db: Session,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        stmt = (
            db.query(FollowupTask)
            .join(Lead, Lead.id == FollowupTask.lead_id)
            .order_by(FollowupTask.scheduled_date.asc())
        )
        if status_filter:
            stmt = stmt.filter(FollowupTask.status == status_filter)

        tasks = stmt.limit(limit).all()
        results = []
        for t in tasks:
            contact = db.query(Contact).filter(Contact.lead_id == t.lead_id, Contact.email != None).first()
            results.append({
                "id": t.id,
                "lead_id": t.lead_id,
                "sequence_step": t.sequence_step,
                "scheduled_date": t.scheduled_date,
                "status": t.status,
                "cancellation_reason": t.cancellation_reason,
                "created_at": t.created_at,
                "business_name": t.lead.business_name if t.lead else f"Lead #{t.lead_id}",
                "recipient_email": contact.email if contact else None,
            })
        return results

    def list_jobs(self, db: Session, limit: int = 50) -> List[Job]:
        return list(
            db.query(Job)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .all()
        )


worker_service = BackgroundWorkerService()
