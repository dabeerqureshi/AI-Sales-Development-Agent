import pytest
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.contact import Contact
from app.models.email import EmailDraft
from app.models.gmail import EmailMessage
from app.services.crm_service import crm_service
from app.services.gmail_service import gmail_service


def test_oauth_url_and_mime():
    auth_url = gmail_service.get_auth_url()
    assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
    assert "gmail.send" in auth_url

    raw_msg = gmail_service.create_mime_message(
        to="doctor@austindental.com",
        subject="AI Receptionist Opportunity",
        body="Hi Doctor,\n\nWe would love to connect.",
    )
    assert isinstance(raw_msg, str)
    assert len(raw_msg) > 20


@pytest.mark.asyncio
async def test_safety_gate_unapproved_draft_blocked(db_session):
    campaign = Campaign(name="Test Camp", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(campaign_id=campaign.id, business_name="Smiles", industry="Dental", external_id="osm-g1")
    db_session.add(lead)
    db_session.commit()

    contact = Contact(lead_id=lead.id, full_name="Dr. Smith", email="smith@smiles.com")
    db_session.add(contact)
    db_session.commit()

    draft = EmailDraft(
        lead_id=lead.id,
        contact_id=contact.id,
        subject="Hello",
        body_text="Test message",
        status="draft",  # NOT approved
    )
    db_session.add(draft)
    db_session.commit()

    # Attempting to send unapproved draft MUST raise safety error
    with pytest.raises(ValueError) as excinfo:
        await gmail_service.send_approved_email(draft.id, db_session)
    assert "Human Safety Gate" in str(excinfo.value)
    assert "approved" in str(excinfo.value)


@pytest.mark.asyncio
async def test_safety_gate_suppressed_recipient_blocked(db_session):
    campaign = Campaign(name="Test Camp 2", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(
        campaign_id=campaign.id,
        business_name="Blocked Smiles",
        industry="Dental",
        website="https://blockedsmiles.com",
        external_id="osm-g2",
    )
    db_session.add(lead)
    db_session.commit()

    contact = Contact(lead_id=lead.id, full_name="Dr. Blocked", email="blocked@blockedsmiles.com")
    db_session.add(contact)
    db_session.commit()

    draft = EmailDraft(
        lead_id=lead.id,
        contact_id=contact.id,
        subject="Hello",
        body_text="Test message",
        status="approved",
    )
    db_session.add(draft)
    db_session.commit()

    # Block email
    crm_service.add_suppression(email="blocked@blockedsmiles.com", reason="unsubscribed", db=db_session)

    # Attempting send MUST raise suppression safety error
    with pytest.raises(ValueError) as excinfo:
        await gmail_service.send_approved_email(draft.id, db_session)
    assert "Compliance Safety Gate" in str(excinfo.value)


@pytest.mark.asyncio
async def test_duplicate_send_prevention(db_session):
    campaign = Campaign(name="Test Camp 3", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(campaign_id=campaign.id, business_name="Single Send Dental", industry="Dental", external_id="osm-g3")
    db_session.add(lead)
    db_session.commit()

    contact = Contact(lead_id=lead.id, full_name="Dr. Taylor", email="taylor@singlesend.com")
    db_session.add(contact)
    db_session.commit()

    draft = EmailDraft(
        lead_id=lead.id,
        contact_id=contact.id,
        subject="Single Outreach",
        body_text="Test outreach text",
        status="approved",
    )
    db_session.add(draft)
    db_session.commit()

    # First send succeeds
    msg = await gmail_service.send_approved_email(draft.id, db_session)
    assert msg.id is not None
    assert msg.direction == "outbound"
    assert lead.status == "contacted"
    assert draft.status == "sent"

    # Second send attempt MUST be blocked by duplicate send prevention
    draft2 = EmailDraft(
        lead_id=lead.id,
        contact_id=contact.id,
        subject="Second Outreach Attempt",
        body_text="Test outreach 2",
        status="approved",
    )
    db_session.add(draft2)
    db_session.commit()

    with pytest.raises(ValueError) as excinfo:
        await gmail_service.send_approved_email(draft2.id, db_session)
    assert "Duplicate Send Prevention" in str(excinfo.value)


def test_gmail_api_endpoints(client, db_session):
    # 1. Check status & auth url
    status_res = client.get("/api/gmail/status")
    assert status_res.status_code == 200

    url_res = client.get("/api/gmail/auth-url")
    assert url_res.status_code == 200
    assert "https://accounts.google.com" in url_res.json()["auth_url"]

    # 2. Setup lead & approved draft
    campaign = Campaign(name="API Send Camp", industry="Dental", country="US", city="Austin")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(campaign_id=campaign.id, business_name="API Dental", industry="Dental", external_id="osm-g4")
    db_session.add(lead)
    db_session.commit()

    contact = Contact(lead_id=lead.id, full_name="Dr. Kelly", email="kelly@apidental.com")
    db_session.add(contact)
    db_session.commit()

    draft = EmailDraft(
        lead_id=lead.id,
        contact_id=contact.id,
        subject="Intro to AI Receptionist",
        body_text="Hi Dr. Kelly,\n\nWe offer AI front desk reception.",
        status="approved",
    )
    db_session.add(draft)
    db_session.commit()

    # 3. Create Gmail Draft Endpoint
    draft_res = client.post(f"/api/drafts/{draft.id}/gmail-draft")
    assert draft_res.status_code == 200
    assert "gmail_draft_id" in draft_res.json()

    # 4. Dispatch Email Endpoint
    send_res = client.post(f"/api/drafts/{draft.id}/send")
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["status"] == "sent"
    assert send_data["recipient_email"] == "kelly@apidental.com"

    # 5. List Sent Messages Audit Log
    msg_res = client.get("/api/messages")
    assert msg_res.status_code == 200
    assert len(msg_res.json()) >= 1
