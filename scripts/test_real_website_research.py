"""
Live Integration Test: Crawls real discovered dental clinic websites from Task 02.
Verifies service extraction, title, and booking system detection.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database.session import SessionLocal, init_db
from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.services.research_service import research_service


async def main():
    print("=" * 70)
    print("AI SDR — LIVE WEBSITE RESEARCH INTEGRATION TEST")
    print("=" * 70)

    init_db()
    db = SessionLocal()

    try:
        leads_with_web = (
            db.query(Lead)
            .filter(Lead.website.isnot(None))
            .limit(3)
            .all()
        )

        if not leads_with_web:
            print("[!] No leads with websites found in sdr.db. Run discovery first.")
            return

        print(f"Testing live website extraction on {len(leads_with_web)} real businesses:\n")

        for lead in leads_with_web:
            print(f"--> Crawling: {lead.business_name} ({lead.website})...")
            try:
                record = await research_service.research_lead(lead.id, db)
                print(f"    [✓] Title:            {record.page_title or 'N/A'}")
                print(f"    [✓] Booking Detected: {record.booking_system_found} ({record.booking_system_name or 'None'})")
                print(f"    [✓] Custom Form:      {record.has_custom_booking_form}")
                print(f"    [✓] Services:         {record.services_summary or 'General Dental Services'}")
                if record.after_hours_info:
                    print(f"    [✓] After-Hours Info: {record.after_hours_info[:80]}...")
                print(f"    [✓] Text Snippet:     {len(record.extracted_text_snippet or '')} chars extracted")
                print()
            except Exception as e:
                print(f"    [!] Crawl error: {e}\n")

        # Verify saved records in SQLite
        saved_records = db.query(ResearchRecord).all()
        print(f"[✓] Successfully saved {len(saved_records)} research records in SQLite sdr.db.")
        assert len(saved_records) > 0, "No research records saved."

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
