"""
Live Integration Test: Extracts public business contacts, phone lines, and practitioners
from real websites discovered in Task 02.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database.session import SessionLocal, init_db
from app.models.lead import Lead
from app.models.contact import Contact
from app.services.contact_service import contact_service


async def main():
    print("=" * 70)
    print("AI SDR — LIVE PUBLIC CONTACT DISCOVERY INTEGRATION TEST")
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

        print(f"Extracting verified public contacts for {len(leads_with_web)} real businesses:\n")

        for lead in leads_with_web:
            print(f"--> Scanning: {lead.business_name} ({lead.website})...")
            try:
                contacts = await contact_service.extract_contacts_for_lead(lead.id, db)
                print(f"    [✓] Contacts Discovered: {len(contacts)}")
                for c in contacts:
                    print(f"        * Name:       {c.full_name or 'N/A'}")
                    print(f"          Title:      {c.title or 'N/A'}")
                    print(f"          Email:      {c.email or 'N/A'}")
                    print(f"          Phone:      {c.phone or 'N/A'}")
                    print(f"          Confidence: {int(c.confidence_score * 100)}%")
                    print(f"          Primary:    {c.is_primary}")
                    if c.sources:
                        print(f"          Snippet:    {c.sources[0].snippet[:70]}...")
                print()
            except Exception as e:
                print(f"    [!] Contact extraction error: {e}\n")

        saved_contacts = db.query(Contact).all()
        print(f"[✓] Total contacts persisted in SQLite sdr.db: {len(saved_contacts)}")
        assert len(saved_contacts) > 0, "No contacts were saved."

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
