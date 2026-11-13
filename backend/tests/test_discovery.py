from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.mcp.servers.openstreetmap import normalize_osm_element


def test_normalize_osm_element():
    # Valid node
    raw_node = {
        "type": "node",
        "id": 123456,
        "lat": 30.2672,
        "lon": -97.7431,
        "tags": {
            "name": "Austin Gentle Dental",
            "amenity": "dentist",
            "website": "http://austingentledental.com",
            "phone": "+1-512-555-0199",
            "addr:street": "Congress Ave",
            "addr:housenumber": "500",
            "addr:city": "Austin",
            "addr:state": "TX",
        },
    }
    result = normalize_osm_element(raw_node, "dentist")
    assert result is not None
    assert result["business_name"] == "Austin Gentle Dental"
    assert result["industry"] == "dentist"
    assert result["website"] == "http://austingentledental.com"
    assert result["phone"] == "+1-512-555-0199"
    assert result["address"] == "500, Congress Ave, Austin, TX"
    assert result["external_id"] == "node/123456"
    assert "openstreetmap.org/node/123456" in result["source_url"]

    # Unnamed element must be discarded
    unnamed_node = {"type": "node", "id": 789, "tags": {"amenity": "dentist"}}
    assert normalize_osm_element(unnamed_node, "dentist") is None


MOCK_DISCOVERED_BUSINESSES = [
    {
        "business_name": "Austin Smiles Dentistry",
        "industry": "dentist",
        "website": "https://austinsmiles.example.com",
        "phone": "+1-512-555-0101",
        "address": "100 Main St, Austin, TX",
        "latitude": 30.26,
        "longitude": -97.74,
        "external_id": "node/101",
        "source_url": "https://www.openstreetmap.org/node/101",
        "source_name": "OpenStreetMap/Overpass",
        "raw_tags": {},
    },
    {
        "business_name": "Capitol Dental Care",
        "industry": "dentist",
        "website": None,  # no website
        "phone": "+1-512-555-0102",
        "address": "200 Lavaca St, Austin, TX",
        "latitude": 30.27,
        "longitude": -97.75,
        "external_id": "node/102",
        "source_url": "https://www.openstreetmap.org/node/102",
        "source_name": "OpenStreetMap/Overpass",
        "raw_tags": {},
    },
]


@patch("app.mcp.manager.search_businesses", new_callable=AsyncMock)
def test_discovery_workflow_and_deduplication(mock_search, client: TestClient):
    mock_search.return_value = MOCK_DISCOVERED_BUSINESSES

    # 1. Create campaign requiring websites
    create_resp = client.post(
        "/api/campaigns",
        json={
            "name": "Austin Dental Test",
            "industry": "Dentist",
            "country": "United States",
            "city": "Austin",
            "max_leads": 10,
            "website_required": True,
            "phone_required": False,
        },
    )
    assert create_resp.status_code == 201
    campaign_id = create_resp.json()["id"]

    # 2. Trigger discovery
    discover_resp = client.post(f"/api/campaigns/{campaign_id}/discover")
    assert discover_resp.status_code == 200
    data = discover_resp.json()
    assert data["status"] == "completed"
    stats = data["stats"]
    assert stats["total_found"] == 2
    assert stats["new_leads_saved"] == 1  # only 1 had a website
    assert stats["filtered_out"] == 1     # 1 had no website and was filtered out

    # Verify saved lead has source attribution
    saved_lead = data["leads"][0]
    assert saved_lead["business_name"] == "Austin Smiles Dentistry"
    assert saved_lead["external_id"] == "node/101"
    assert len(saved_lead["sources"]) == 1
    assert saved_lead["sources"][0]["source_name"] == "OpenStreetMap/Overpass"

    # 3. Trigger discovery a second time: duplicate detection must skip already saved lead
    discover_resp_2 = client.post(f"/api/campaigns/{campaign_id}/discover")
    assert discover_resp_2.status_code == 200
    stats_2 = discover_resp_2.json()["stats"]
    assert stats_2["duplicates_skipped"] == 1
    assert stats_2["new_leads_saved"] == 0

    # 4. Verify campaign lead count updated
    leads_resp = client.get(f"/api/campaigns/{campaign_id}/leads")
    assert leads_resp.status_code == 200
    assert len(leads_resp.json()) == 1


@patch("app.mcp.manager.search_businesses", new_callable=AsyncMock)
def test_discovery_failure_handling(mock_search, client: TestClient):
    mock_search.side_effect = RuntimeError("Overpass rate limit exceeded (HTTP 429)")

    camp_resp = client.post(
        "/api/campaigns",
        json={
            "name": "Failing Campaign",
            "industry": "Dentist",
            "country": "United States",
            "city": "Dallas",
        },
    )
    campaign_id = camp_resp.json()["id"]

    discover_resp = client.post(f"/api/campaigns/{campaign_id}/discover")
    assert discover_resp.status_code == 502
    assert "rate limit exceeded" in discover_resp.json()["detail"]

    # Verify campaign status is marked as failed
    check_camp = client.get(f"/api/campaigns/{campaign_id}")
    assert check_camp.json()["status"] == "failed"
