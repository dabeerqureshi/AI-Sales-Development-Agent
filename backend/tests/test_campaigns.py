from fastapi.testclient import TestClient


def test_create_campaign_success(client: TestClient):
    payload = {
        "name": "Texas Dental Automation",
        "industry": "Dentist",
        "country": "United States",
        "region": "Texas",
        "city": "Austin",
        "max_leads": 25,
        "website_required": True,
        "phone_required": False,
    }
    response = client.post("/api/campaigns", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Texas Dental Automation"
    assert data["city"] == "Austin"
    assert data["max_leads"] == 25
    assert data["status"] == "draft"
    assert data["lead_count"] == 0
    assert "id" in data


def test_create_campaign_validation_error(client: TestClient):
    # Empty name and city should fail validation
    payload = {
        "name": "",
        "industry": "Dentist",
        "country": "United States",
        "city": "",
    }
    response = client.post("/api/campaigns", json=payload)
    assert response.status_code == 422


def test_list_and_get_campaign(client: TestClient):
    # Create campaign
    create_resp = client.post(
        "/api/campaigns",
        json={
            "name": "Miami Clinics",
            "industry": "Clinic",
            "country": "United States",
            "city": "Miami",
            "max_leads": 10,
        },
    )
    assert create_resp.status_code == 201
    campaign_id = create_resp.json()["id"]

    # List campaigns
    list_resp = client.get("/api/campaigns")
    assert list_resp.status_code == 200
    campaigns = list_resp.json()
    assert len(campaigns) >= 1
    found = any(c["id"] == campaign_id for c in campaigns)
    assert found is True

    # Get single campaign
    get_resp = client.get(f"/api/campaigns/{campaign_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Miami Clinics"

    # Get non-existent campaign
    not_found_resp = client.get("/api/campaigns/999999")
    assert not_found_resp.status_code == 404
