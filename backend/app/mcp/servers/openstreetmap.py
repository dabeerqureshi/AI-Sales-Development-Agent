import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_openstreetmap")

mcp = FastMCP("openstreetmap")

DEFAULT_HEADERS = {
    "User-Agent": "AISalesDevelopmentAgent/1.0 (local-sdr-project; contact: dev@local.sdr)",
    "Accept": "application/json",
}

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"

INDUSTRY_TAG_MAP = {
    "dentist": [('amenity', 'dentist'), ('healthcare', 'dentist')],
    "dental": [('amenity', 'dentist'), ('healthcare', 'dentist')],
    "dental clinic": [('amenity', 'dentist'), ('healthcare', 'dentist')],
    "doctor": [('amenity', 'doctors'), ('healthcare', 'doctor')],
    "clinic": [('amenity', 'clinic'), ('healthcare', 'clinic')],
    "pharmacy": [('amenity', 'pharmacy'), ('healthcare', 'pharmacy')],
    "hospital": [('amenity', 'hospital'), ('healthcare', 'hospital')],
    "veterinary": [('amenity', 'veterinary'), ('healthcare', 'veterinarian')],
    "restaurant": [('amenity', 'restaurant')],
    "cafe": [('amenity', 'cafe')],
}


def build_overpass_query(
    industry: str,
    city: str,
    country: str,
    state_or_region: Optional[str] = None,
    limit: int = 50,
) -> str:
    """Build optimized Overpass QL query."""
    normalized_ind = industry.strip().lower()
    tag_filters = INDUSTRY_TAG_MAP.get(normalized_ind, [('amenity', normalized_ind)])
    clean_city = re.sub(r'[^a-zA-Z0-9\s\.\-]', '', city).strip()
    
    filter_clauses = ""
    for key, val in tag_filters:
        filter_clauses += f'node["{key}"="{val}"](area.searchArea);\n'
        filter_clauses += f'way["{key}"="{val}"](area.searchArea);\n'

    return f"""[out:json][timeout:15];
area["name"="{clean_city}"]->.searchArea;
(
{filter_clauses}
);
out center {limit};
"""


def normalize_osm_element(elem: Dict[str, Any], requested_industry: str) -> Optional[Dict[str, Any]]:
    """Transform raw Overpass element into structured business discovery record."""
    tags = elem.get("tags", {})
    name = tags.get("name")
    if not name:
        return None

    elem_type = elem.get("type", "node")
    elem_id = elem.get("id")
    external_id = f"{elem_type}/{elem_id}"
    source_url = f"https://www.openstreetmap.org/{elem_type}/{elem_id}"

    lat = elem.get("lat") or (elem.get("center", {}).get("lat") if "center" in elem else None)
    lon = elem.get("lon") or (elem.get("center", {}).get("lon") if "center" in elem else None)

    website = (
        tags.get("contact:website")
        or tags.get("website")
        or tags.get("url")
        or tags.get("contact:facebook")
    )
    if website and not website.startswith("http"):
        website = f"https://{website}"

    phone = (
        tags.get("contact:phone")
        or tags.get("phone")
        or tags.get("contact:mobile")
    )

    addr_parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    address = ", ".join([p for p in addr_parts if p]) if any(addr_parts) else None
    category = tags.get("amenity") or tags.get("healthcare") or requested_industry

    return {
        "business_name": name,
        "industry": category,
        "website": website,
        "phone": phone,
        "address": address,
        "latitude": lat,
        "longitude": lon,
        "external_id": external_id,
        "source_url": source_url,
        "source_name": "OpenStreetMap/Overpass",
        "raw_tags": tags,
    }


def normalize_nominatim_element(item: Dict[str, Any], requested_industry: str) -> Optional[Dict[str, Any]]:
    """Transform raw Nominatim item into structured business discovery record."""
    raw_name = item.get("name") or (item.get("display_name", "").split(",")[0] if item.get("display_name") else None)
    if not raw_name:
        return None

    osm_type = item.get("osm_type", "node")
    osm_id = item.get("osm_id")
    external_id = f"{osm_type}/{osm_id}"
    source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

    try:
        lat = float(item["lat"]) if "lat" in item else None
        lon = float(item["lon"]) if "lon" in item else None
    except (ValueError, TypeError):
        lat, lon = None, None

    tags = item.get("extratags", {})
    website = tags.get("website") or tags.get("contact:website") or tags.get("url")
    if website and not website.startswith("http"):
        website = f"https://{website}"

    phone = tags.get("phone") or tags.get("contact:phone")
    address = item.get("display_name")

    return {
        "business_name": raw_name.strip(),
        "industry": requested_industry,
        "website": website,
        "phone": phone,
        "address": address,
        "latitude": lat,
        "longitude": lon,
        "external_id": external_id,
        "source_url": source_url,
        "source_name": "OpenStreetMap/Nominatim",
        "raw_tags": tags,
    }


@mcp.tool()
async def search_businesses(
    industry: str,
    city: str,
    country: str,
    state_or_region: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search real businesses from OpenStreetMap via Overpass API with Nominatim resilience fallback.
    """
    logger.info(f"Executing OpenStreetMap business discovery: industry='{industry}', city='{city}', country='{country}'")

    # 1. Try Overpass API mirrors
    query = build_overpass_query(industry, city, country, state_or_region, limit=limit)
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=8.0) as client:
                response = await client.post(endpoint, data={"data": query})
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get("elements", [])
                    results = []
                    for el in elements:
                        norm = normalize_osm_element(el, industry)
                        if norm:
                            results.append(norm)
                            if len(results) >= limit:
                                break
                    if results:
                        logger.info(f"Overpass endpoint {endpoint} returned {len(results)} businesses.")
                        return results
        except Exception as e:
            logger.warning(f"Overpass endpoint {endpoint} failed or timed out: {e}")

    # 2. Resilient fallback: Query OpenStreetMap Nominatim search
    logger.info("Falling back to OpenStreetMap Nominatim provider...")
    location_str = f"{city}"
    if state_or_region:
        location_str += f" {state_or_region}"
    if country:
        location_str += f" {country}"

    search_query = f"{industry} {location_str}"
    try:
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=12.0) as client:
            resp = await client.get(
                NOMINATIM_ENDPOINT,
                params={
                    "q": search_query,
                    "format": "json",
                    "addressdetails": 1,
                    "extratags": 1,
                    "limit": limit,
                },
            )
            if resp.status_code == 200:
                items = resp.json()
                results = []
                for item in items:
                    norm = normalize_nominatim_element(item, industry)
                    if norm:
                        results.append(norm)
                        if len(results) >= limit:
                            break
                if results:
                    logger.info(f"Nominatim returned {len(results)} verified OpenStreetMap businesses.")
                    return results
    except Exception as e:
        logger.error(f"Nominatim fallback failed: {e}")

    raise RuntimeError(f"Could not discover businesses for '{industry}' in '{city}'. Both Overpass and Nominatim services failed or returned no matches.")


if __name__ == "__main__":
    mcp.run()
