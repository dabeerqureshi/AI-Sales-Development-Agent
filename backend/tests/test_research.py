from unittest.mock import patch, AsyncMock
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.services.research_service import ResearchService

MOCK_HTML_NEXHEALTH = """
<!DOCTYPE html>
<html>
<head>
    <title>Austin Smiles Dentistry | Premier Dental Care</title>
    <meta name="description" content="Compassionate dental care in Austin. Book your appointment online today." />
</head>
<body>
    <h1>Welcome to Austin Smiles Dentistry</h1>
    <p>We provide compassionate dental care for the whole family in Austin, Texas.</p>
    
    <h2>Our Dental Services</h2>
    <ul>
        <li>General Dentistry</li>
        <li>Teeth Whitening</li>
        <li>Dental Implants</li>
        <li>Invisalign Clear Aligners</li>
    </ul>

    <p>Call us for emergency care! We provide 24/7 emergency care for acute toothaches and trauma.</p>

    <iframe src="https://nexhealth.com/widgets/austin-smiles"></iframe>
</body>
</html>
"""

MOCK_HTML_CUSTOM_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Capitol Dental Studio</title>
</head>
<body>
    <h1>Capitol Dental Studio</h1>
    <p>Comprehensive oral healthcare in downtown Austin.</p>
    
    <h2>Treatments</h2>
    <p>Specializing in Cosmetic Dentistry and Periodontics.</p>

    <form action="/submit-appointment">
        <label>Your Name</label>
        <input type="text" name="name" />
        <button type="submit">Request an Appointment</button>
    </form>
</body>
</html>
"""


def test_detect_booking_system_nexhealth():
    soup = BeautifulSoup(MOCK_HTML_NEXHEALTH, "html.parser")
    found, name, is_custom = ResearchService.detect_booking_system(soup, MOCK_HTML_NEXHEALTH)
    assert found is True
    assert name == "NexHealth"
    assert is_custom is False


def test_detect_custom_booking_form():
    soup = BeautifulSoup(MOCK_HTML_CUSTOM_FORM, "html.parser")
    found, name, is_custom = ResearchService.detect_booking_system(soup, MOCK_HTML_CUSTOM_FORM)
    assert found is True
    assert name == "Custom Online Booking Form"
    assert is_custom is True


def test_extract_services_and_after_hours():
    soup = BeautifulSoup(MOCK_HTML_NEXHEALTH, "html.parser")
    text = soup.get_text()
    services = ResearchService.extract_services_summary(soup, text)
    assert services is not None
    assert "General Dentistry" in services
    assert "Teeth Whitening" in services

    after_hours = ResearchService.extract_after_hours_info(text)
    assert after_hours is not None
    assert "emergency care" in after_hours.lower()


@patch("app.services.research_service.ResearchService.fetch_html", new_callable=AsyncMock)
def test_research_single_lead_endpoint(mock_fetch, client: TestClient):
    mock_fetch.return_value = (MOCK_HTML_NEXHEALTH, "https://austinsmiles.example.com", None)

    # 1. Create a campaign and discover a lead
    camp_resp = client.post(
        "/api/campaigns",
        json={"name": "Research Test Camp", "industry": "Dentist", "city": "Austin", "country": "USA"},
    )
    camp_id = camp_resp.json()["id"]

    # Directly mock discovery to inject a lead with a website
    with patch("app.mcp.manager.search_businesses", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "business_name": "Austin Smiles Dentistry",
                "industry": "dentist",
                "website": "https://austinsmiles.example.com",
                "phone": "+1-512-555-0101",
                "address": "100 Main St, Austin, TX",
                "latitude": 30.26,
                "longitude": -97.74,
                "external_id": "node/991",
                "source_url": "https://www.openstreetmap.org/node/991",
                "source_name": "OpenStreetMap",
                "raw_tags": {},
            }
        ]
        disc_resp = client.post(f"/api/campaigns/{camp_id}/discover")
        lead_id = disc_resp.json()["leads"][0]["id"]

    # 2. Trigger research on this lead
    res_resp = client.post(f"/api/leads/{lead_id}/research")
    assert res_resp.status_code == 200
    data = res_resp.json()
    assert data["lead_id"] == lead_id
    assert data["booking_system_found"] is True
    assert data["booking_system_name"] == "NexHealth"
    assert "Austin Smiles" in data["page_title"]
    assert "General Dentistry" in data["services_summary"]

    # 3. Fetch saved research
    get_res = client.get(f"/api/leads/{lead_id}/research")
    assert get_res.status_code == 200
    assert get_res.json()["booking_system_name"] == "NexHealth"

    # 4. Verify lead status updated to researched
    lead_check = client.get(f"/api/leads/{lead_id}")
    assert lead_check.json()["status"] == "researched"


def test_research_lead_no_website(client: TestClient):
    camp_resp = client.post(
        "/api/campaigns",
        json={"name": "No Web Camp", "industry": "Dentist", "city": "Austin", "country": "USA"},
    )
    camp_id = camp_resp.json()["id"]

    with patch("app.mcp.manager.search_businesses", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "business_name": "No Website Dental",
                "industry": "dentist",
                "website": None,
                "phone": "+1-512-555-0102",
                "address": "200 St, Austin, TX",
                "latitude": 30.26,
                "longitude": -97.74,
                "external_id": "node/992",
                "source_url": "https://www.openstreetmap.org/node/992",
                "source_name": "OpenStreetMap",
                "raw_tags": {},
            }
        ]
        disc_resp = client.post(f"/api/campaigns/{camp_id}/discover")
        lead_id = disc_resp.json()["leads"][0]["id"]

    res_resp = client.post(f"/api/leads/{lead_id}/research")
    assert res_resp.status_code == 400
    assert "does not have a website" in res_resp.json()["detail"]


@patch("app.services.research_service.ResearchService.fetch_html", new_callable=AsyncMock)
def test_batch_campaign_research(mock_fetch, client: TestClient):
    mock_fetch.return_value = (MOCK_HTML_CUSTOM_FORM, "https://capitol.example.com", None)

    camp_resp = client.post(
        "/api/campaigns",
        json={"name": "Batch Camp", "industry": "Dentist", "city": "Austin", "country": "USA"},
    )
    camp_id = camp_resp.json()["id"]

    with patch("app.mcp.manager.search_businesses", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "business_name": "Capitol Dental",
                "industry": "dentist",
                "website": "https://capitol.example.com",
                "phone": "+1-512-555-0103",
                "address": "300 St, Austin, TX",
                "latitude": 30.26,
                "longitude": -97.74,
                "external_id": "node/993",
                "source_url": "https://www.openstreetmap.org/node/993",
                "source_name": "OpenStreetMap",
                "raw_tags": {},
            }
        ]
        client.post(f"/api/campaigns/{camp_id}/discover")

    batch_resp = client.post(f"/api/campaigns/{camp_id}/research?limit=10")
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["campaign_id"] == camp_id
    assert batch_data["stats"]["successfully_researched"] == 1
    assert batch_data["stats"]["booking_systems_detected"] == 1
    assert len(batch_data["results"]) == 1
    assert batch_data["results"][0]["has_custom_booking_form"] is True
