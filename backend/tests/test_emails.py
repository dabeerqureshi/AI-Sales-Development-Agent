import pytest
from unittest.mock import patch, AsyncMock
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.models.contact import Contact
from app.models.score import LeadScore
from app.models.email import EmailDraft, EmailApproval
from app.services.email_service import email_service, EmailGeneratorService


def test_deterministic_email_generation():
    lead = Lead(
        id=1,
        campaign_id=1,
        business_name="Austin Smiles Dental",
        industry="Dental clinics",
        website="https://austinsmilesdental.com",
        address="Austin, TX",
        external_id="osm-1",
    )
    contact = Contact(
        id=1,
        lead_id=1,
        full_name="Dr. Jane Doe, DDS",
        title="Lead Dentist",
        email="jane@austinsmilesdental.com",
    )
    research = ResearchRecord(
        lead_id=1,
        crawled_url="https://austinsmilesdental.com",
        services_summary="General & Cosmetic Dentistry, Implants",
        booking_system_found=False,
        has_custom_booking_form=True,
    )
    score = LeadScore(
        lead_id=1,
        overall_score=85,
        verified_facts=["Location: Austin Smiles Dental in Austin, TX", "Services: General & Cosmetic Dentistry"],
    )

    gen = EmailGeneratorService()
    content = gen.build_deterministic_draft(lead, contact, research, score)

    assert "subject" in content
    assert "Austin Smiles Dental" in content["subject"]
    assert "body_text" in content
    assert "Dr. Jane Doe" in content["body_text"]
    assert "evidence_citations" in content
    assert len(content["evidence_citations"]) >= 2
    assert "P.S." in content["body_text"]


@pytest.mark.asyncio
async def test_ollama_email_mock():
    lead = Lead(
        id=2,
        campaign_id=1,
        business_name="Capital Dental",
        industry="Dental clinics",
        address="Austin, TX",
        external_id="osm-2",
    )
    gen = EmailGeneratorService()

    mock_json = {
        "subject": "Capital Dental / quick inquiry",
        "body_text": "Hi Capital Dental Team,\n\nI noticed you offer comprehensive dental care in Austin...\n\nBest,\nSDR",
        "evidence_citations": ["Offers comprehensive dental care in Austin"],
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "response": '{"subject": "Capital Dental / quick inquiry", "body_text": "Hi Capital Dental Team,\\n\\nI noticed you offer comprehensive dental care in Austin...\\n\\nBest,\\nSDR", "evidence_citations": ["Offers comprehensive dental care in Austin"]}'
            },
        )
        result = await gen.generate_draft_content(lead, None, None, None)
        assert result["subject"] == "Capital Dental / quick inquiry"
        assert len(result["evidence_citations"]) == 1


def test_email_endpoints_workflow(client, db_session):
    # Setup test campaign and lead
    campaign = Campaign(
        name="Texas Dental Campaign",
        industry="Dental clinics",
        country="United States",
        city="Austin",
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    lead = Lead(
        campaign_id=campaign.id,
        business_name="Austin Dental Excellence",
        industry="Dental clinics",
        website="https://austindexcellence.com",
        external_id="osm-lead-100",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    contact = Contact(
        lead_id=lead.id,
        full_name="Dr. Mark Miller, DDS",
        email="dr.miller@austindexcellence.com",
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)

    # 1. Generate Draft
    gen_res = client.post(f"/api/leads/{lead.id}/drafts/generate")
    assert gen_res.status_code == 200
    draft_data = gen_res.json()
    draft_id = draft_data["id"]
    assert draft_data["version"] == 1
    assert draft_data["status"] == "draft"
    assert "Austin Dental Excellence" in draft_data["subject"]
    assert len(draft_data["evidence_citations"]) > 0

    # 2. Get Draft by ID
    get_res = client.get(f"/api/drafts/{draft_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == draft_id

    # 3. Update Draft
    put_res = client.put(
        f"/api/drafts/{draft_id}",
        json={"subject": "Customized Subject Line", "body_text": "Customized email text."},
    )
    assert put_res.status_code == 200
    assert put_res.json()["subject"] == "Customized Subject Line"

    # 4. Approve Draft
    approve_res = client.post(
        f"/api/drafts/{draft_id}/approve",
        json={"notes": "Looks grounded and concise. Approved."},
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["status"] == "approved"
    assert approved_data["approval"]["reviewer_notes"] == "Looks grounded and concise. Approved."

    # 5. Regenerate Draft (bumps version)
    regen_res = client.post(f"/api/leads/{lead.id}/drafts/generate")
    assert regen_res.status_code == 200
    regen_data = regen_res.json()
    assert regen_data["version"] == 2
    assert regen_data["status"] == "draft"

    # 6. Reject Draft
    reject_res = client.post(
        f"/api/drafts/{draft_id}/reject",
        json={"notes": "Need to tweak angle for pediatric care."},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # 7. Batch generate campaign drafts
    batch_res = client.post(f"/api/campaigns/{campaign.id}/drafts/generate")
    assert batch_res.status_code == 200
    assert batch_res.json()["stats"]["drafts_generated"] >= 1

    # 8. List campaign drafts
    list_res = client.get(f"/api/campaigns/{campaign.id}/drafts")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
