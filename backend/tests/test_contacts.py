from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.services.contact_service import ContactService

MOCK_HTML_CONTACT = """
<!DOCTYPE html>
<html>
<head>
    <title>Austin Family Dental - Meet The Team</title>
</head>
<body>
    <h1>Our Dental Team</h1>
    <p>Led by Dr. Marcus Vance, DDS, our practice has been serving Austin for 15 years.</p>
    <p>Associate practitioner Dr. Emily Thorne, DMD specializes in pediatric care.</p>

    <div class="contact-info">
        <h3>Contact Us</h3>
        <p>Call our office: <a href="tel:5125550144">(512) 555-0144</a></p>
        <p>Email appointments: <a href="mailto:appointments@austinfamilydental.com">appointments@austinfamilydental.com</a></p>
        <p>General inquiries: info@austinfamilydental.com</p>
    </div>

    <!-- Honeypot and image assets to be filtered out -->
    <img src="/assets/doctor@2x.png" alt="Doctor" />
    <script src="https://sentry.io/api/123/bundle.min.js"></script>
    <p>Developer: support@sentry.io</p>
    <p>Sample: yourname@example.com</p>
</body>
</html>
"""


def test_is_valid_email():
    assert ContactService.is_valid_email("appointments@austinfamilydental.com") is True
    assert ContactService.is_valid_email("dr.vance@dentalcare.org") is True

    # Image asset strings
    assert ContactService.is_valid_email("doctor@2x.png") is False
    assert ContactService.is_valid_email("logo@1x.jpg") is False

    # Disallowed domains / honeypots
    assert ContactService.is_valid_email("sample@example.com") is False
    assert ContactService.is_valid_email("support@sentry.io") is False
    assert ContactService.is_valid_email("test@domain.com") is False

    # Placeholders
    assert ContactService.is_valid_email("yourname@dentist.com") is False
    assert ContactService.is_valid_email("name@dentist.com") is False


def test_normalize_phone():
    assert ContactService.normalize_phone("5125550144") == "+1 (512) 555-0144"
    assert ContactService.normalize_phone("(512) 555-0144") == "+1 (512) 555-0144"
    assert ContactService.normalize_phone("+1-512-555-0144") == "+1 (512) 555-0144"


def test_extract_from_html():
    results = ContactService.extract_from_html(MOCK_HTML_CONTACT, "https://austinfamilydental.com/team")
    assert len(results) >= 2

    # Practitioner extraction
    practitioners = [r for r in results if r["full_name"] and "Dr." in r["full_name"]]
    assert len(practitioners) >= 1
    assert any("Dr. Marcus Vance, DDS" in p["full_name"] for p in practitioners)
    assert any("Dentist (DDS)" in p["title"] for p in practitioners)

    # Email verification
    emails = [r["email"] for r in results if r["email"]]
    assert "appointments@austinfamilydental.com" in emails

    # Filtered out asset/honeypot emails
    assert "doctor@2x.png" not in emails
    assert "support@sentry.io" not in emails
    assert "yourname@example.com" not in emails

    # Check phone
    phones = [r["phone"] for r in results if r["phone"]]
    assert "+1 (512) 555-0144" in phones


@patch("httpx.AsyncClient.get")
def test_extract_contacts_for_lead_endpoint(mock_get, client: TestClient):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = MOCK_HTML_CONTACT
    mock_resp.url = "https://austinfamilydental.com"
    mock_get.return_value = mock_resp

    # 1. Create a campaign and discover a lead
    camp_resp = client.post(
        "/api/campaigns",
        json={"name": "Contact Extraction Camp", "industry": "Dentist", "city": "Austin", "country": "USA"},
    )
    camp_id = camp_resp.json()["id"]

    with patch("app.mcp.manager.search_businesses", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "business_name": "Austin Family Dental",
                "industry": "dentist",
                "website": "https://austinfamilydental.com",
                "phone": "+1-512-555-0144",
                "address": "400 Dental Way, Austin, TX",
                "latitude": 30.26,
                "longitude": -97.74,
                "external_id": "node/881",
                "source_url": "https://www.openstreetmap.org/node/881",
                "source_name": "OpenStreetMap",
                "raw_tags": {},
            }
        ]
        disc_resp = client.post(f"/api/campaigns/{camp_id}/discover")
        lead_id = disc_resp.json()["leads"][0]["id"]

    # 2. Extract contacts
    ext_resp = client.post(f"/api/leads/{lead_id}/contacts/extract")
    assert ext_resp.status_code == 200
    contacts = ext_resp.json()
    assert len(contacts) >= 1

    first = contacts[0]
    assert first["lead_id"] == lead_id
    assert first["business_name"] == "Austin Family Dental"
    assert first["is_primary"] is True
    assert len(first["sources"]) >= 1

    # 3. Retrieve contacts
    list_resp = client.get(f"/api/leads/{lead_id}/contacts")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == len(contacts)

    # 4. Set primary contact
    if len(contacts) > 1:
        second_id = contacts[1]["id"]
        primary_resp = client.post(f"/api/contacts/{second_id}/primary")
        assert primary_resp.status_code == 200
        assert primary_resp.json()["is_primary"] is True


@patch("httpx.AsyncClient.get")
def test_batch_extract_contacts(mock_get, client: TestClient):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = MOCK_HTML_CONTACT
    mock_resp.url = "https://batchdental.com"
    mock_get.return_value = mock_resp

    camp_resp = client.post(
        "/api/campaigns",
        json={"name": "Batch Contact Camp", "industry": "Dentist", "city": "Austin", "country": "USA"},
    )
    camp_id = camp_resp.json()["id"]

    with patch("app.mcp.manager.search_businesses", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "business_name": "Batch Dental Office",
                "industry": "dentist",
                "website": "https://batchdental.com",
                "phone": "+1-512-555-0155",
                "address": "500 Dental Way, Austin, TX",
                "latitude": 30.26,
                "longitude": -97.74,
                "external_id": "node/882",
                "source_url": "https://www.openstreetmap.org/node/882",
                "source_name": "OpenStreetMap",
                "raw_tags": {},
            }
        ]
        client.post(f"/api/campaigns/{camp_id}/discover")

    batch_resp = client.post(f"/api/campaigns/{camp_id}/contacts/extract")
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["campaign_id"] == camp_id
    assert batch_data["stats"]["contacts_found"] >= 1
    assert len(batch_data["contacts"]) >= 1
