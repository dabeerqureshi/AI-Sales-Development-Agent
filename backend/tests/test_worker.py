import pytest
from datetime import datetime, timezone, timedelta
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.contact import Contact
from app.models.worker import FollowupTask, Job
from app.models.gmail import EmailMessage
from app.services.crm_service import crm_service
from app.services.worker_service import worker_service


def test_schedule_and_cancel_followup(db_session):
    campaign = Campaign(name="Worker Camp", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(campaign_id=campaign.id, business_name="Followup Smiles", industry="Dental", external_id="osm-w1")
    db_session.add(lead)
    db_session.commit()

    # 1. Schedule follow-up
    task = worker_service.schedule_followup(lead_id=lead.id, delay_days=3, sequence_step=2, db=db_session)
    assert task.id is not None
    assert task.status == "pending"
    assert task.sequence_step == 2
    task_date = task.scheduled_date.replace(tzinfo=None) if task.scheduled_date.tzinfo else task.scheduled_date
    assert task_date > datetime.now(timezone.utc).replace(tzinfo=None)

    # 2. Cancel follow-up
    cancelled = worker_service.cancel_followup(task.id, reason="manual_cancel", db=db_session)
    assert cancelled.status == "cancelled"
    assert cancelled.cancellation_reason == "manual_cancel"


def test_stop_sequence_rule_on_inbound_reply(db_session):
    campaign = Campaign(name="Worker Camp 2", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(campaign_id=campaign.id, business_name="Responsive Dental", industry="Dental", external_id="osm-w2", status="contacted")
    db_session.add(lead)
    db_session.commit()

    contact = Contact(lead_id=lead.id, full_name="Dr. Responsive", email="responsive@dental.com")
    db_session.add(contact)
    db_session.commit()

    # Schedule step 2 and step 3 follow-ups
    task2 = worker_service.schedule_followup(lead_id=lead.id, delay_days=3, sequence_step=2, db=db_session)
    task3 = worker_service.schedule_followup(lead_id=lead.id, delay_days=7, sequence_step=3, db=db_session)
    assert task2.status == "pending"
    assert task3.status == "pending"

    # Prospect replies!
    res = worker_service.process_inbound_reply(
        lead_id=lead.id,
        snippet="Thanks for reaching out! Let's talk Tuesday at 2pm.",
        db=db_session,
    )

    assert res["status"] == "replied"
    assert res["cancelled_followup_tasks"] == 2
    assert lead.status == "replied"

    # STOP SEQUENCE RULE CHECK: Both follow-up tasks MUST be cancelled automatically
    db_session.refresh(task2)
    db_session.refresh(task3)
    assert task2.status == "cancelled"
    assert task2.cancellation_reason == "reply_detected"
    assert task3.status == "cancelled"
    assert task3.cancellation_reason == "reply_detected"

    # Inbound EmailMessage record exists
    inbound_msgs = db_session.query(EmailMessage).filter(EmailMessage.lead_id == lead.id, EmailMessage.direction == "inbound").all()
    assert len(inbound_msgs) == 1
    assert "Tuesday" in inbound_msgs[0].snippet


@pytest.mark.asyncio
async def test_worker_cycle_and_suppression_cleanup(db_session):
    campaign = Campaign(name="Worker Camp 3", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(
        campaign_id=campaign.id,
        business_name="Unsubscribed Clinic",
        industry="Dental",
        website="https://unsubclinic.com",
        external_id="osm-w3",
    )
    db_session.add(lead)
    db_session.commit()

    task = worker_service.schedule_followup(lead_id=lead.id, delay_days=3, sequence_step=2, db=db_session)
    assert task.status == "pending"

    # Add suppression rule
    crm_service.add_suppression(domain="unsubclinic.com", reason="unsubscribed", db=db_session)

    # Run worker cycle
    cycle_res = await worker_service.execute_worker_cycle(campaign_id=campaign.id, db=db_session)
    assert cycle_res["status"] == "completed"
    assert cycle_res["tasks_cancelled"] >= 1

    # Task should be auto-cancelled due to suppression
    db_session.refresh(task)
    assert task.status == "cancelled"
    assert "suppressed" in task.cancellation_reason

    # Job record exists
    job = db_session.get(Job, cycle_res["job_id"])
    assert job is not None
    assert job.status == "completed"
    assert job.progress_pct == 100


def test_worker_api_endpoints(client, db_session):
    campaign = Campaign(name="API Worker Camp", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(campaign_id=campaign.id, business_name="API Worker Dental", industry="Dental", external_id="osm-w4")
    db_session.add(lead)
    db_session.commit()

    # 1. Schedule Followup Endpoint
    sched_res = client.post(
        f"/api/leads/{lead.id}/followup",
        json={"delay_days": 2, "sequence_step": 2},
    )
    assert sched_res.status_code == 200
    task_data = sched_res.json()
    task_id = task_data["id"]
    assert task_data["status"] == "pending"

    # 2. List Followups Endpoint
    list_res = client.get("/api/followups?status=pending")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Simulate Inbound Reply Endpoint
    reply_res = client.post(
        f"/api/leads/{lead.id}/simulate-reply",
        json={"snippet": "I am interested. Call me tomorrow."},
    )
    assert reply_res.status_code == 200
    assert reply_res.json()["status"] == "replied"

    # 4. Run Worker Cycle Endpoint
    cycle_res = client.post("/api/worker/run-cycle")
    assert cycle_res.status_code == 200
    assert cycle_res.json()["status"] == "completed"

    # 5. List Background Jobs Endpoint
    jobs_res = client.get("/api/jobs")
    assert jobs_res.status_code == 200
    assert len(jobs_res.json()) >= 1
