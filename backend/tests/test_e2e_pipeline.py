import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.worker import FollowupTask


MOCK_HTML_CUSTOM_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Capital City Smiles Dental | Austin Cosmetic Care</title>
</head>
<body>
    <h1>Capital City Smiles Dental</h1>
    <p>We provide general dental cleanings, cosmetic porcelain veneers, and dental implants.</p>

    <form action="/submit-appointment">
        <label>Your Name</label>
        <input type="text" name="name" />
        <button type="submit">Request an Appointment</button>
    </form>
    
    <footer>
        <p>For urgent emergencies after 5 PM, please call our direct emergency triage.</p>
    </footer>
</body>
</html>
"""

MOCK_HTML_CONTACT = """
<!DOCTYPE html>
<html>
<head><title>Team | Capital City Smiles Dental</title></head>
<body>
    <h2>Meet Our Clinical Director</h2>
    <p>Dr. Elena Vance, DDS is our leading cosmetic dentist.</p>
    <p>Appointments: appointments@capcitysmiles.com</p>
    <p>Direct: dr.vance@capcitysmiles.com</p>
    <p>Office Phone: (512) 555-7890</p>
</body>
</html>
"""


def test_full_e2e_sdr_lifecycle(client: TestClient):
    """
    Comprehensive End-to-End Test covering the complete 10-stage AI SDR lifecycle:
    1. Health checks & configuration
    2. Campaign Creation
    3. Business Discovery (MCP)
    4. Autonomous Website Research
    5. Public Contact Discovery
    6. Qualification & Scoring (Deterministic + Synthesis)
    7. Email Studio (Generation, Citation, Human Approval)
    8. CRM Pipeline & Safety Gate (Suppression check + Human dispatch)
    9. Follow-up Engine (Task scheduling)
    10. Inbound Reply & Stop-Sequence Rule Enforcement
    """

    # --- STAGE 1: HEALTH CHECKS ---
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # --- STAGE 2: CAMPAIGN CREATION ---
    camp_payload = {
        "name": "E2E Austin Dental Pipeline",
        "industry": "Dentist",
        "country": "United States",
        "region": "Texas",
        "city": "Austin",
        "max_leads": 25,
        "website_required": True,
        "phone_required": False,
    }
    res_camp = client.post("/api/campaigns", json=camp_payload)
    assert res_camp.status_code == 201
    campaign = res_camp.json()
    camp_id = campaign["id"]
    assert campaign["name"] == "E2E Austin Dental Pipeline"

    # --- STAGE 3: BUSINESS DISCOVERY VIA MCP ---
    mock_discovered = [
        {
            "business_name": "Capital City Smiles Dental",
            "industry": "dentist",
            "website": "https://www.capcitysmiles.com",
            "phone": "+1-512-555-7890",
            "address": "1200 Congress Ave, Austin, TX",
            "latitude": 30.2747,
            "longitude": -97.7404,
            "external_id": "node/880011",
            "source_url": "https://www.openstreetmap.org/node/880011",
            "source_name": "OpenStreetMap/Overpass",
            "raw_tags": {},
        }
    ]

    with patch("app.mcp.manager.search_businesses", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_discovered
        res_disc = client.post(f"/api/campaigns/{camp_id}/discover")
        assert res_disc.status_code == 200
        disc_data = res_disc.json()
        assert disc_data["status"] == "completed"
        assert disc_data["stats"]["new_leads_saved"] >= 1
        leads = disc_data["leads"]
        lead = leads[0]
        lead_id = lead["id"]
        assert lead["business_name"] == "Capital City Smiles Dental"

    # --- STAGE 4: AUTONOMOUS WEBSITE RESEARCH ---
    with patch("app.services.research_service.ResearchService.fetch_html", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (MOCK_HTML_CUSTOM_FORM, "https://www.capcitysmiles.com", None)
        res_res = client.post(f"/api/leads/{lead_id}/research")
        assert res_res.status_code == 200
        research_data = res_res.json()
        assert research_data["lead_id"] == lead_id
        assert research_data["has_custom_booking_form"] is True
        assert research_data["booking_system_found"] is True
        assert research_data["booking_system_name"] == "Custom Online Booking Form"

    # --- STAGE 5: PUBLIC CONTACT DISCOVERY ---
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_HTML_CONTACT
        mock_response.url = "https://www.capcitysmiles.com/team"
        mock_get.return_value = mock_response

        res_contacts = client.post(f"/api/leads/{lead_id}/contacts/extract")
        assert res_contacts.status_code == 200
        contacts = res_contacts.json()
        assert len(contacts) >= 1
        with_email = [c for c in contacts if c.get("email")]
        assert len(with_email) >= 1

    # --- STAGE 6: QUALIFICATION & SCORING ---
    res_qual = client.post(f"/api/leads/{lead_id}/qualify")
    assert res_qual.status_code == 200
    score_data = res_qual.json()
    assert score_data["overall_score"] >= 70
    assert "opportunity_fit" in score_data["rule_breakdown"]
    assert len(score_data["verified_facts"]) >= 1

    # --- STAGE 7: AI EMAIL STUDIO (DRAFT GENERATION & CITATIONS) ---
    res_draft = client.post(f"/api/leads/{lead_id}/drafts/generate")
    assert res_draft.status_code == 200
    draft = res_draft.json()
    draft_id = draft["id"]
    assert draft["version"] == 1
    assert len(draft["evidence_citations"]) >= 1

    # Operator human edits draft
    res_edit = client.put(
        f"/api/drafts/{draft_id}",
        json={
            "subject": "Quick question regarding Capital City Smiles appointment requests",
            "body_text": draft["body_text"] + "\n\nP.S. Best regards from the Austin AI SDR team.",
        },
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["subject"] == "Quick question regarding Capital City Smiles appointment requests"

    # Human Approves draft
    res_appr = client.post(
        f"/api/drafts/{draft_id}/approve",
        json={"notes": "Looks grounded and concise. Approved."},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "approved"

    # --- STAGE 8: SUPPRESSION GATE & GMAIL DISPATCH ---
    # Test 8a: Verify suppression gate blocks outreach if domain suppressed
    res_supp = client.post(
        "/api/suppression",
        json={
            "domain": "capcitysmiles.com",
            "reason": "Test temporary block",
        },
    )
    assert res_supp.status_code == 200
    supp_id = res_supp.json()["id"]

    res_blocked_send = client.post(f"/api/drafts/{draft_id}/send")
    assert res_blocked_send.status_code == 400
    assert "suppression" in res_blocked_send.json()["detail"].lower()

    # Lift suppression for valid dispatch
    res_del_supp = client.delete(f"/api/suppression/{supp_id}")
    assert res_del_supp.status_code == 200

    # Test 8b: Successful Dispatch via Simulator Gate
    res_send = client.post(f"/api/drafts/{draft_id}/send")
    assert res_send.status_code == 200
    send_data = res_send.json()
    assert send_data["status"] == "sent"
    assert "msg-sim-" in send_data["gmail_message_id"]

    # Verify duplicate send is blocked
    res_dup = client.post(f"/api/drafts/{draft_id}/send")
    assert res_dup.status_code == 400
    assert "approved" in res_dup.json()["detail"].lower()

    # --- STAGE 9: FOLLOW-UP ENGINE ---
    res_followup = client.post(
        f"/api/leads/{lead_id}/followup",
        json={"delay_days": 3, "sequence_step": 2},
    )
    assert res_followup.status_code == 200
    task_id = res_followup.json()["id"]
    assert res_followup.json()["status"] == "pending"

    # Run background worker cycle
    res_cycle = client.post(
        "/api/worker/run-cycle",
        json={"campaign_id": camp_id},
    )
    assert res_cycle.status_code == 200
    cycle_res = res_cycle.json()
    assert cycle_res["status"] == "completed"

    # --- STAGE 10: INBOUND REPLY & STOP-SEQUENCE RULE ---
    res_reply = client.post(
        f"/api/leads/{lead_id}/simulate-reply",
        json={
            "snippet": "Thanks for your email. We would love to see how the automated triage works. Please share a video or calendar link.",
            "gmail_message_id": "sim-inbound-reply-vance-404",
        },
    )
    assert res_reply.status_code == 200
    reply_data = res_reply.json()
    assert reply_data["status"] == "replied"
    assert reply_data["cancelled_followup_tasks"] >= 1

    # Verify Follow-up task cancelled with 'reply_detected'
    res_tasks = client.get("/api/followups")
    assert res_tasks.status_code == 200
    our_task = next(t for t in res_tasks.json() if t["id"] == task_id)
    assert our_task["status"] == "cancelled"
    assert our_task["cancellation_reason"] == "reply_detected"

    # Final pipeline verification
    res_pipeline = client.get(f"/api/crm/pipeline?campaign_id={camp_id}")
    assert res_pipeline.status_code == 200
    stages = res_pipeline.json()["stages"]
    replied_leads = stages.get("replied", [])
    assert any(l["id"] == lead_id for l in replied_leads)
