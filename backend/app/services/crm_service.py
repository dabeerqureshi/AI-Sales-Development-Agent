import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.models.lead import Lead
from app.models.contact import Contact
from app.models.research import ResearchRecord
from app.models.score import LeadScore
from app.models.email import EmailDraft
from app.models.crm import SuppressionEntry, ActivityLog
from app.schemas.crm import PipelineLeadCard, PipelineResponse

logger = logging.getLogger("crm_service")

VALID_STAGES = [
    "discovered",
    "researched",
    "draft_ready",
    "approved",
    "contacted",
    "replied",
    "suppressed",
]


class CRMService:
    @staticmethod
    def extract_domain(url_or_email: Optional[str]) -> Optional[str]:
        if not url_or_email:
            return None
        val = url_or_email.strip().lower()
        if "@" in val:
            return val.split("@")[-1].strip()
        if val.startswith(("http://", "https://")):
            parsed = urlparse(val)
            netloc = parsed.netloc or ""
            return netloc.replace("www.", "").strip()
        return val.replace("www.", "").lstrip("@").strip()

    def check_suppression(
        self,
        email: Optional[str],
        domain: Optional[str],
        db: Session,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Safety Hard Gate:
        Checks whether an email address or its domain matches an active suppression entry.
        Returns: (is_suppressed, matched_by, reason, details)
        """
        clean_email = email.strip().lower() if email else None
        clean_domain = self.extract_domain(domain) or (self.extract_domain(clean_email) if clean_email else None)

        if not clean_email and not clean_domain:
            return False, None, None, None

        # 1. Direct Email Match
        if clean_email:
            entry = db.query(SuppressionEntry).filter(SuppressionEntry.email == clean_email).first()
            if entry:
                return True, "email", entry.reason, f"Direct email block: {clean_email}"

        # 2. Domain Match
        if clean_domain:
            entry = (
                db.query(SuppressionEntry)
                .filter(SuppressionEntry.domain == clean_domain)
                .first()
            )
            if entry:
                return True, "domain", entry.reason, f"Domain block: {clean_domain}"

        return False, None, None, None

    def add_suppression(
        self,
        email: Optional[str] = None,
        domain: Optional[str] = None,
        reason: str = "unsubscribed",
        db: Session = None,
    ) -> SuppressionEntry:
        if db is None:
            raise ValueError("Database session required.")
        clean_email = email.strip().lower() if email else None
        clean_domain = self.extract_domain(domain)

        if not clean_email and not clean_domain:
            raise ValueError("Must provide either a valid email or domain to suppress.")

        # Check existing entry
        entry = None
        if clean_email:
            entry = db.query(SuppressionEntry).filter(SuppressionEntry.email == clean_email).first()
        elif clean_domain:
            entry = db.query(SuppressionEntry).filter(SuppressionEntry.domain == clean_domain).first()

        if entry:
            entry.reason = reason
            entry.added_at = datetime.now(timezone.utc)
        else:
            entry = SuppressionEntry(
                email=clean_email,
                domain=clean_domain,
                reason=reason,
                added_at=datetime.now(timezone.utc),
            )
            db.add(entry)

        db.commit()
        db.refresh(entry)

        # Log Activity
        self.log_activity(
            entity_type="suppression",
            entity_id=entry.id,
            action="suppression_added",
            details={
                "email": clean_email,
                "domain": clean_domain,
                "reason": reason,
            },
            db=db,
        )

        return entry

    def remove_suppression(self, entry_id: int, db: Session):
        entry = db.get(SuppressionEntry, entry_id)
        if not entry:
            raise ValueError(f"Suppression entry {entry_id} not found.")

        details = {"email": entry.email, "domain": entry.domain, "reason": entry.reason}
        db.delete(entry)
        db.commit()

        self.log_activity(
            entity_type="suppression",
            entity_id=entry_id,
            action="suppression_removed",
            details=details,
            db=db,
        )

    def list_suppression(
        self,
        db: Session,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[SuppressionEntry]:
        stmt = select(SuppressionEntry)
        if search:
            s = f"%{search.strip().lower()}%"
            stmt = stmt.where(or_(SuppressionEntry.email.ilike(s), SuppressionEntry.domain.ilike(s)))
        stmt = stmt.order_by(SuppressionEntry.added_at.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def log_activity(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        details: Dict[str, Any],
        db: Session,
    ) -> ActivityLog:
        log = ActivityLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def get_recent_activities(self, db: Session, limit: int = 50) -> List[ActivityLog]:
        stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def update_lead_stage(
        self,
        lead_id: int,
        target_stage: str,
        notes: Optional[str],
        db: Session,
    ) -> Lead:
        stage_clean = target_stage.strip().lower()
        if stage_clean not in VALID_STAGES:
            raise ValueError(f"Invalid stage '{target_stage}'. Valid stages are: {', '.join(VALID_STAGES)}")

        lead = db.get(Lead, lead_id)
        if not lead:
            raise ValueError(f"Lead with id {lead_id} not found.")

        # Safety Hard Gate for Approved or Contacted
        if stage_clean in ("approved", "contacted"):
            # Check domain
            lead_domain = self.extract_domain(lead.website)
            is_supp, match, reason, details = self.check_suppression(None, lead_domain, db)
            if is_supp:
                raise ValueError(
                    f"Compliance Safety Gate: Cannot move lead to '{stage_clean}'. "
                    f"Domain '{lead_domain}' is blocked ({reason})."
                )

            # Check contacts
            contacts = db.query(Contact).filter(Contact.lead_id == lead_id).all()
            for c in contacts:
                if c.email:
                    is_supp, match, reason, details = self.check_suppression(c.email, None, db)
                    if is_supp:
                        raise ValueError(
                            f"Compliance Safety Gate: Cannot move lead to '{stage_clean}'. "
                            f"Contact email '{c.email}' is suppressed ({reason})."
                        )

        prev_stage = lead.status
        lead.status = stage_clean
        lead.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(lead)

        self.log_activity(
            entity_type="lead",
            entity_id=lead_id,
            action="stage_change",
            details={
                "from_stage": prev_stage,
                "to_stage": stage_clean,
                "notes": notes,
                "business_name": lead.business_name,
            },
            db=db,
        )

        return lead

    def get_pipeline(self, campaign_id: int, db: Session) -> PipelineResponse:
        leads = (
            db.query(Lead)
            .filter(Lead.campaign_id == campaign_id)
            .all()
        )

        # Preload scores, contacts, drafts
        lead_ids = [l.id for l in leads]
        scores = {s.lead_id: s for s in db.query(LeadScore).filter(LeadScore.lead_id.in_(lead_ids)).all()}
        all_contacts = db.query(Contact).filter(Contact.lead_id.in_(lead_ids)).all()
        contacts_by_lead: Dict[int, List[Contact]] = {}
        for c in all_contacts:
            contacts_by_lead.setdefault(c.lead_id, []).append(c)

        all_drafts = db.query(EmailDraft).filter(EmailDraft.lead_id.in_(lead_ids)).all()
        drafts_by_lead: Dict[int, EmailDraft] = {}
        for d in all_drafts:
            drafts_by_lead[d.lead_id] = d

        stages_map: Dict[str, List[PipelineLeadCard]] = {
            "discovered": [],
            "researched": [],
            "draft_ready": [],
            "approved": [],
            "contacted": [],
            "replied": [],
        }

        for lead in leads:
            score_rec = scores.get(lead.id)
            lead_contacts = contacts_by_lead.get(lead.id, [])
            draft = drafts_by_lead.get(lead.id)

            primary_contact = next((c for c in lead_contacts if c.is_primary), None)
            if not primary_contact:
                primary_contact = next((c for c in lead_contacts if c.email), None) or (lead_contacts[0] if lead_contacts else None)

            # Check suppression
            lead_domain = self.extract_domain(lead.website)
            lead_email = primary_contact.email if primary_contact else None
            is_supp, _, _, _ = self.check_suppression(lead_email, lead_domain, db)

            card = PipelineLeadCard(
                id=lead.id,
                campaign_id=lead.campaign_id,
                business_name=lead.business_name,
                industry=lead.industry,
                website=lead.website,
                phone=lead.phone,
                address=lead.address,
                status=lead.status,
                score=score_rec.overall_score if score_rec else None,
                primary_contact_name=primary_contact.full_name if primary_contact else None,
                primary_contact_email=primary_contact.email if primary_contact else None,
                has_draft=draft is not None,
                draft_status=draft.status if draft else None,
                is_suppressed=is_supp,
            )

            # Assign to pipeline column
            stage_key = lead.status.lower()
            if stage_key == "qualified":
                # If qualified, place in draft_ready if draft exists else researched
                stage_key = "draft_ready" if draft else "researched"
            elif stage_key not in stages_map:
                stage_key = "discovered"

            # If draft was approved and lead is still marked draft_ready, advance visual column
            if draft and draft.status == "approved" and stage_key == "draft_ready":
                stage_key = "approved"

            stages_map[stage_key].append(card)

        stage_counts = {k: len(v) for k, v in stages_map.items()}

        return PipelineResponse(
            campaign_id=campaign_id,
            stages=stages_map,
            stage_counts=stage_counts,
        )


crm_service = CRMService()
