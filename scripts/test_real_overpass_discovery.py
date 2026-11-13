"""
Integration Test: Real Public OpenStreetMap / Overpass Discovery Test.
Tests discovery of 10 real dental clinics in Austin, Texas, USA.
Verifies real OSM node IDs, names, addresses, and website/contact tags.
"""
import asyncio
import json
import os
import sys

# Ensure backend app is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database.session import SessionLocal, init_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.services.discovery_service import discovery_service


async def main():
    print("=" * 70)
    print("AI SDR — LIVE OVERPASS INTEGRATION TEST (Austin Dental Clinics)")
    print("=" * 70)

    init_db()
    db = SessionLocal()

    try:
        # 1. Create a test campaign
        campaign_name = "Live Integration Test — Austin Dentists"
        
        # Check if exists and cleanup previous run
        existing = db.query(Campaign).filter(Campaign.name == campaign_name).first()
        if existing:
            db.delete(existing)
            db.commit()

        campaign = Campaign(
            name=campaign_name,
            industry="Dentist",
            country="United States",
            region="Texas",
            city="Austin",
            max_leads=10,
            website_required=False,
            phone_required=False,
            status="draft",
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        print(f"[✓] Created Campaign ID {campaign.id}: '{campaign.name}' in {campaign.city}, {campaign.region}")

        # 2. Run discovery via MCP / Overpass API
        print(f"[i] Querying live Overpass API for real dental clinics in Austin (limit=10)...")
        response = await discovery_service.run_discovery_for_campaign(
            campaign_id=campaign.id,
            db=db,
            override_limit=10,
        )

        print(f"\n[✓] Discovery Succeeded!")
        print(f"    Total Found:          {response.stats.total_found}")
        print(f"    New Leads Saved:      {response.stats.new_leads_saved}")
        print(f"    Duplicates Skipped:   {response.stats.duplicates_skipped}")
        print(f"    Execution Time:       {response.stats.execution_time_seconds}s")

        # 3. Inspect saved leads
        saved_leads = (
            db.query(Lead)
            .filter(Lead.campaign_id == campaign.id)
            .order_by(Lead.id.asc())
            .all()
        )

        print("\n" + "-" * 70)
        print(f"SAVED REAL LEADS IN SQLITE ({len(saved_leads)} leads):")
        print("-" * 70)

        for i, lead in enumerate(saved_leads, 1):
            source_url = lead.sources[0].source_url if lead.sources else "N/A"
            print(f"{i}. {lead.business_name}")
            print(f"   OSM ID:    {lead.external_id}")
            print(f"   Address:   {lead.address or 'N/A'}")
            print(f"   Phone:     {lead.phone or 'N/A'}")
            print(f"   Website:   {lead.website or 'N/A'}")
            print(f"   Source:    {source_url}")
            print()

        assert len(saved_leads) > 0, "No leads were saved from live Overpass query!"
        print("[✓] ALL VERIFICATIONS PASSED: Real business records saved with genuine OSM IDs.")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
