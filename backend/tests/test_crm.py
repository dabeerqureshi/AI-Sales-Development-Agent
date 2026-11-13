import pytest
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.contact import Contact
from app.models.crm import SuppressionEntry, ActivityLog
from app.services.crm_service import crm_service


def test_extract_domain():
    assert crm_service.extract_domain("https://www.austindentalcare.com/about") == "austindentalcare.com"
    assert crm_service.extract_domain("doctor@dentistry.com") == "dentistry.com"
    assert crm_service.extract_domain("@hospital.org") == "hospital.org"
    assert crm_service.extract_domain(None) is None


def test_suppression_matching(db_session):
    # Add email suppression
    crm_service.add_suppression(email="optout@competitor.com", domain=None, reason="unsubscribed", db=db_session)
    # Add domain suppression
    crm_service.add_suppression(email=None, domain="badleads.org", reason="competitor", db=db_session)

    # 1. Match direct email
    is_supp, matched_by, reason, details = crm_service.check_suppression("optout@competitor.com", None, db_session)
    assert is_supp is True
    assert matched_by == "email"
    assert reason == "unsubscribed"

    # 2. Match domain via email
    is_supp, matched_by, reason, details = crm_service.check_suppression("anyone@badleads.org", None, db_session)
    assert is_supp is True
    assert matched_by == "domain"
    assert reason == "competitor"

    # 3. Match domain directly
    is_supp, matched_by, reason, details = crm_service.check_suppression(None, "https://badleads.org/page", db_session)
    assert is_supp is True
    assert matched_by == "domain"

    # 4. Clean email
    is_supp, matched_by, _, _ = crm_service.check_suppression("hello@goodclinic.com", "goodclinic.com", db_session)
    assert is_supp is False
    assert matched_by is None


def test_safety_gate_blocks_suppressed_lead(db_session):
    campaign = Campaign(name="Safety Test", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(
        campaign_id=campaign.id,
        business_name="Blocked Clinic",
        industry="Dental",
        website="https://www.donotcall.com",
        external_id="osm-block-1",
        status="discovered",
    )
    db_session.add(lead)
    db_session.commit()

    # Block the domain
    crm_service.add_suppression(domain="donotcall.com", reason="manual_block", db=db_session)

    # Moving to 'researched' is fine
    updated = crm_service.update_lead_stage(lead.id, "researched", "Crawled successfully", db_session)
    assert updated.status == "researched"

    # Moving to 'approved' MUST be blocked by safety hard gate
    with pytest.raises(ValueError) as excinfo:
        crm_service.update_lead_stage(lead.id, "approved", "Human approval attempt", db_session)
    assert "Compliance Safety Gate" in str(excinfo.value)
    assert "donotcall.com" in str(excinfo.value)


def test_suppression_api_crud(client, db_session):
    # 1. Add suppression
    add_res = client.post(
        "/api/suppression",
        json={"email": "bounce@target.com", "domain": "target.com", "reason": "bounced"},
    )
    assert add_res.status_code == 200
    data = add_res.json()
    entry_id = data["id"]
    assert data["reason"] == "bounced"

    # 2. Check suppression API
    check_res = client.get("/api/suppression/check?email=bounce@target.com")
    assert check_res.status_code == 200
    assert check_res.json()["is_suppressed"] is True

    # 3. List suppression entries
    list_res = client.get("/api/suppression?search=target.com")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Delete suppression
    del_res = client.delete(f"/api/suppression/{entry_id}")
    assert del_res.status_code == 200

    # 5. Verify no longer suppressed
    recheck_res = client.get("/api/suppression/check?email=bounce@target.com")
    assert recheck_res.status_code == 200
    assert recheck_res.json()["is_suppressed"] is False


def test_crm_pipeline_and_activity_api(client, db_session):
    campaign = Campaign(name="Pipeline Test", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(
        campaign_id=campaign.id,
        business_name="Austin Smiles CRM",
        industry="Dental",
        website="https://austinsmilescrm.com",
        external_id="osm-pipeline-1",
        status="discovered",
    )
    db_session.add(lead)
    db_session.commit()

    # 1. Get Pipeline
    pipe_res = client.get(f"/api/crm/pipeline?campaign_id={campaign.id}")
    assert pipe_res.status_code == 200
    pipe_data = pipe_res.json()
    assert pipe_data["campaign_id"] == campaign.id
    assert "discovered" in pipe_data["stages"]
    assert len(pipe_data["stages"]["discovered"]) >= 1

    # 2. Advance Lead Stage
    stage_res = client.post(
        f"/api/leads/{lead.id}/stage",
        json={"stage": "researched", "notes": "Completed initial website analysis"},
    )
    assert stage_res.status_code == 200
    assert stage_res.json()["status"] == "researched"

    # 3. Verify Activity Logs
    act_res = client.get("/api/activities?limit=10")
    assert act_res.status_code == 200
    logs = act_res.json()
    assert len(logs) >= 1
    assert any(l["action"] == "stage_change" for l in logs)
