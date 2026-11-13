import pytest
from unittest.mock import patch, AsyncMock
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.models.contact import Contact
from app.models.score import LeadScore
from app.services.qualification_service import DeterministicScorer, OpportunitySynthesizer


def test_deterministic_scorer_full_points():
    lead = Lead(
        id=1,
        campaign_id=1,
        business_name="Austin Smiles Dental",
        industry="Dental clinics",
        website="https://austinsmilesdental.com",
        phone="512-555-0100",
        address="123 Congress Ave, Austin, TX",
        external_id="osm-1",
    )
    research = ResearchRecord(
        lead_id=1,
        crawled_url="https://austinsmilesdental.com",
        page_title="Austin Smiles Dental Clinic",
        services_summary="General Dentistry, Cleanings, Implants",
        booking_system_found=False,
        has_custom_booking_form=True,
    )
    contacts = [
        Contact(
            lead_id=1,
            full_name="Dr. Jane Doe, DDS",
            title="Lead Dentist",
            email="office@austinsmilesdental.com",
            phone="512-555-0100",
            confidence_score=0.95,
        ),
    ]

    score, breakdown = DeterministicScorer.calculate_score(lead, research, contacts)
    assert score == 100
    assert breakdown["website"]["points"] == 25
    assert breakdown["email"]["points"] == 25
    assert breakdown["phone"]["points"] == 15
    assert breakdown["practitioner"]["points"] == 15
    assert breakdown["opportunity_fit"]["points"] == 20
    assert breakdown["opportunity_fit"]["passed"] is True


def test_deterministic_scorer_partial_points():
    # Only website and phone, modern booking tool present
    lead = Lead(
        id=2,
        campaign_id=1,
        business_name="Modern Dental Hub",
        industry="Dental clinics",
        website="https://moderndental.com",
        phone="512-555-0200",
        external_id="osm-2",
    )
    research = ResearchRecord(
        lead_id=2,
        crawled_url="https://moderndental.com",
        booking_system_found=True,
        booking_system_name="Modento",
        has_custom_booking_form=False,
    )
    contacts = [
        Contact(
            lead_id=2,
            full_name="Main Office / Reception",
            title="General Inquiries",
            email=None,
            phone="512-555-0200",
            confidence_score=0.85,
        ),
    ]

    score, breakdown = DeterministicScorer.calculate_score(lead, research, contacts)
    # Website: 25, Email: 0, Phone: 15, Practitioner: 0, Opportunity: 5
    assert score == 45
    assert breakdown["website"]["passed"] is True
    assert breakdown["email"]["passed"] is False
    assert breakdown["phone"]["passed"] is True
    assert breakdown["practitioner"]["passed"] is False
    assert breakdown["opportunity_fit"]["points"] == 5


def test_opportunity_synthesizer_rule_based_fallback():
    lead = Lead(
        id=3,
        campaign_id=1,
        business_name="Downtown Austin Dental",
        industry="Dental clinics",
        website="https://downtownaustindental.com",
        address="Austin, TX",
        external_id="osm-3",
    )
    research = ResearchRecord(
        lead_id=3,
        crawled_url="https://downtownaustindental.com",
        page_title="Downtown Austin Dental Practice",
        services_summary="Emergency care, Whitening, Crowns",
        booking_system_found=False,
        has_custom_booking_form=True,
    )
    contacts = [
        Contact(
            lead_id=3,
            full_name="Dr. Robert Smith, DDS",
            title="Owner & Dentist",
            email="info@downtownaustindental.com",
            phone="512-555-0300",
            confidence_score=0.95,
        ),
    ]

    synth = OpportunitySynthesizer()
    report = synth.build_rule_based_synthesis(lead, research, contacts)

    assert "verified_facts" in report
    assert any("Downtown Austin Dental" in f for f in report["verified_facts"])
    assert any("Dr. Robert Smith" in f for f in report["verified_facts"])
    assert "potential_opportunity" in report
    assert "unknowns" in report
    assert "recommended_angle" in report
    assert "Dr. Robert Smith" in report["recommended_angle"]


@pytest.mark.asyncio
async def test_opportunity_synthesizer_ollama_mock():
    lead = Lead(
        id=4,
        campaign_id=1,
        business_name="Apex Dental Care",
        industry="Dental clinics",
        website="https://apexdentalcare.com",
        external_id="osm-4",
    )
    synth = OpportunitySynthesizer()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "response": '{"verified_facts": ["Operates in Austin"], "potential_opportunity": "Automate after-hours patient intake.", "unknowns": "Staff availability is unverified.", "recommended_angle": "Discuss after-hours answering service."}'
            },
        )
        report = await synth.synthesize(lead, None, [])
        assert "verified_facts" in report
        assert report["potential_opportunity"] == "Automate after-hours patient intake."


def test_qualify_api_endpoints(client, db_session):
    # 1. Setup test campaign and lead
    campaign = Campaign(
        name="Texas Dental Outreach",
        industry="Dental clinics",
        country="United States",
        city="Austin",
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    lead = Lead(
        campaign_id=campaign.id,
        business_name="Lone Star Dentistry",
        industry="Dental clinics",
        website="https://lonestardentistry.com",
        phone="512-555-9999",
        external_id="osm-lead-10",
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    contact = Contact(
        lead_id=lead.id,
        full_name="Dr. Sarah Johnson, DDS",
        title="Dentist",
        email="contact@lonestardentistry.com",
        phone="512-555-9999",
        confidence_score=0.95,
    )
    db_session.add(contact)
    db_session.commit()

    # 2. Qualify single lead
    response = client.post(f"/api/leads/{lead.id}/qualify")
    assert response.status_code == 200
    data = response.json()
    assert data["lead_id"] == lead.id
    assert data["overall_score"] > 0
    assert "website" in data["rule_breakdown"]
    assert "email" in data["rule_breakdown"]
    assert len(data["verified_facts"]) > 0

    # 3. Retrieve score via GET
    get_res = client.get(f"/api/leads/{lead.id}/score")
    assert get_res.status_code == 200
    score_data = get_res.json()
    assert score_data["overall_score"] == data["overall_score"]

    # 4. Batch qualify campaign
    batch_res = client.post(f"/api/campaigns/{campaign.id}/qualify")
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["campaign_id"] == campaign.id
    assert batch_data["stats"]["qualified_count"] >= 1

    # 5. Get campaign scores
    camp_scores_res = client.get(f"/api/campaigns/{campaign.id}/scores")
    assert camp_scores_res.status_code == 200
    scores_list = camp_scores_res.json()
    assert len(scores_list) >= 1
