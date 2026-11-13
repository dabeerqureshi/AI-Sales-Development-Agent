import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.models.contact import Contact, ContactSource
from app.schemas.contact import BatchContactExtractionResponse, BatchContactExtractionStats, ContactResponse
from app.services.research_service import DEFAULT_HEADERS

logger = logging.getLogger("contact_service")

# Blacklisted extensions often mistaken for emails in web bundles (e.g., image@2x.png)
IMAGE_AND_ASSET_EXTS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "tiff",
    "css", "js", "woff", "woff2", "ttf", "eot", "mp4", "mp3"
}

# Blacklisted placeholder and honeypot domains
DISALLOWED_DOMAINS = {
    "example.com", "yourdomain.com", "domain.com", "email.com",
    "sentry.io", "wixpress.com", "cloudflare.com", "gravatar.com",
    "schema.org", "w3.org", "googleapis.com", "google.com", "facebook.com",
    "instagram.com", "twitter.com", "linkedin.com", "youtube.com"
}

EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_REGEX = re.compile(
    r"(?:\+?1[-.\s]?)?\(?([2-9]\d{2})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b"
)

PRACTITIONER_REGEX = re.compile(
    r"\b(?:Dr\.\s+[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:,\s*(?:DDS|DMD|MD|MS|FAGD|MAGD))?|[A-Z][a-z]+\s+[A-Z][a-z]+,\s*(?:DDS|DMD))\b"
)


class ContactService:
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format and filter honeypots, assets, and placeholders."""
        if not email or "@" not in email:
            return False

        email_clean = email.strip().lower()
        parts = email_clean.split("@")
        if len(parts) != 2:
            return False

        local_part, domain_part = parts

        # Check for asset files like user@2x.png
        if any(local_part.endswith(f".{ext}") or domain_part.endswith(f".{ext}") for ext in IMAGE_AND_ASSET_EXTS):
            return False

        # Check domain against disallowed list
        if any(d in domain_part for d in DISALLOWED_DOMAINS):
            return False

        # Reject common template placeholders
        if local_part in ["name", "yourname", "user", "username", "test", "demo", "sample"]:
            return False

        return True

    @staticmethod
    def normalize_phone(raw_phone: str) -> Optional[str]:
        """Normalize phone string into standard US/International format."""
        match = PHONE_REGEX.search(raw_phone)
        if match:
            area, prefix, line = match.groups()
            return f"+1 ({area}) {prefix}-{line}"
        return None

    @classmethod
    def extract_from_html(
        cls,
        html: str,
        source_url: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract verified emails, phone numbers, and practitioners with confidence scoring.
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        is_contact_page = bool(re.search(r"/(contact|about|team|staff|our-doctors)", source_url, re.I))
        extracted_contacts: List[Dict[str, Any]] = []

        seen_emails: Set[str] = set()
        seen_phones: Set[str] = set()

        # 1. High confidence: mailto links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.lower().startswith("mailto:"):
                raw_mail = href[7:].split("?")[0].strip()
                if cls.is_valid_email(raw_mail) and raw_mail.lower() not in seen_emails:
                    seen_emails.add(raw_mail.lower())
                    confidence = 1.0 if is_contact_page else 0.95
                    parent_text = a_tag.parent.get_text(" ", strip=True)[:150] if a_tag.parent else ""
                    extracted_contacts.append({
                        "email": raw_mail,
                        "phone": None,
                        "full_name": None,
                        "title": None,
                        "confidence_score": confidence,
                        "source_url": source_url,
                        "snippet": parent_text or f"Direct mailto link: {raw_mail}",
                    })

        # 2. Text regex emails
        for match in EMAIL_REGEX.finditer(text):
            found_mail = match.group(0).strip()
            if cls.is_valid_email(found_mail) and found_mail.lower() not in seen_emails:
                seen_emails.add(found_mail.lower())
                # Calculate confidence based on proximity to contact keywords
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 60)
                context_snippet = text[start:end].strip()

                confidence = 0.9 if is_contact_page else 0.8
                if re.search(r"\b(email|contact|appointment|reach us)\b", context_snippet, re.I):
                    confidence = min(0.95, confidence + 0.05)

                extracted_contacts.append({
                    "email": found_mail,
                    "phone": None,
                    "full_name": None,
                    "title": None,
                    "confidence_score": confidence,
                    "source_url": source_url,
                    "snippet": context_snippet,
                })

        # 3. High confidence: tel: links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.lower().startswith("tel:"):
                raw_phone = href[4:].split("?")[0].strip()
                norm_phone = cls.normalize_phone(raw_phone)
                if norm_phone and norm_phone not in seen_phones:
                    seen_phones.add(norm_phone)
                    parent_text = a_tag.parent.get_text(" ", strip=True)[:150] if a_tag.parent else ""
                    extracted_contacts.append({
                        "email": None,
                        "phone": norm_phone,
                        "full_name": None,
                        "title": None,
                        "confidence_score": 0.95,
                        "source_url": source_url,
                        "snippet": parent_text or f"Direct tel link: {norm_phone}",
                    })

        # 4. Text regex phones
        for match in PHONE_REGEX.finditer(text):
            norm_phone = cls.normalize_phone(match.group(0))
            if norm_phone and norm_phone not in seen_phones:
                seen_phones.add(norm_phone)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context_snippet = text[start:end].strip()
                extracted_contacts.append({
                    "email": None,
                    "phone": norm_phone,
                    "full_name": None,
                    "title": None,
                    "confidence_score": 0.85,
                    "source_url": source_url,
                    "snippet": context_snippet,
                })

        # 5. Extract practitioner / owner names
        practitioners = []
        for match in PRACTITIONER_REGEX.finditer(text):
            raw_practitioner = match.group(0).strip()
            # Clean titles
            title = "Doctor / Practitioner"
            if "DDS" in raw_practitioner:
                title = "Dentist (DDS)"
            elif "DMD" in raw_practitioner:
                title = "Dentist (DMD)"
            elif "MD" in raw_practitioner:
                title = "Physician (MD)"

            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            context_snippet = text[start:end].strip()

            practitioners.append({
                "full_name": raw_practitioner,
                "title": title,
                "confidence_score": 0.9 if is_contact_page else 0.85,
                "source_url": source_url,
                "snippet": context_snippet,
            })

        # 6. Pair practitioner names with primary contact points if available
        combined_results: List[Dict[str, Any]] = []

        if practitioners:
            for p in practitioners[:3]:  # up to 3 lead practitioners
                # Pair with best available email and phone
                assigned_email = next((c["email"] for c in extracted_contacts if c["email"]), None)
                assigned_phone = next((c["phone"] for c in extracted_contacts if c["phone"]), None)

                combined_results.append({
                    "full_name": p["full_name"],
                    "title": p["title"],
                    "email": assigned_email,
                    "phone": assigned_phone,
                    "confidence_score": p["confidence_score"],
                    "source_url": p["source_url"],
                    "snippet": p["snippet"],
                })

        # Add remaining distinct emails
        assigned_emails = {c["email"] for c in combined_results if c.get("email")}
        for c in extracted_contacts:
            if c["email"] and c["email"] not in assigned_emails:
                combined_results.append({
                    "full_name": "Main Office / Reception",
                    "title": "General Inquiries",
                    "email": c["email"],
                    "phone": c["phone"] or next((p["phone"] for p in extracted_contacts if p["phone"]), None),
                    "confidence_score": c["confidence_score"],
                    "source_url": c["source_url"],
                    "snippet": c["snippet"],
                })
                assigned_emails.add(c["email"])

        # If still no results but phones exist, add general office phone
        if not combined_results and seen_phones:
            first_phone = next(iter(seen_phones))
            combined_results.append({
                "full_name": "Front Desk / Reception",
                "title": "Business Contact",
                "email": None,
                "phone": first_phone,
                "confidence_score": 0.85,
                "source_url": source_url,
                "snippet": f"Phone contact: {first_phone}",
            })

        return combined_results

    @classmethod
    async def extract_contacts_for_lead(cls, lead_id: int, db: Session) -> List[Contact]:
        """
        Extract and persist public contacts for a specific lead.
        """
        lead = db.get(Lead, lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found.")

        # Check existing contacts to prevent duplicates
        existing_contacts_stmt = select(Contact).where(Contact.lead_id == lead.id)
        existing_contacts = list(db.scalars(existing_contacts_stmt).all())
        existing_emails = {c.email.lower() for c in existing_contacts if c.email}
        existing_phones = {c.phone for c in existing_contacts if c.phone}

        crawled_items: List[Dict[str, Any]] = []

        # 1. If research record exists, extract from research snippet
        research_stmt = select(ResearchRecord).where(ResearchRecord.lead_id == lead.id)
        research = db.scalar(research_stmt)

        if research and research.crawled_url:
            # Re-fetch live homepage and contact page to ensure DOM-level mailto extraction
            try:
                async with httpx.AsyncClient(
                    headers=DEFAULT_HEADERS, timeout=8.0, follow_redirects=True, verify=False
                ) as client:
                    resp = await client.get(research.crawled_url)
                    if resp.status_code == 200:
                        crawled_items.extend(cls.extract_from_html(resp.text, str(resp.url)))

                        # Check contact subpage link
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for a in soup.find_all("a", href=True):
                            href = a["href"].strip()
                            if re.search(r"/(contact|about|team)", href, re.I):
                                sub_url = resp.url.join(href)
                                sub_resp = await client.get(sub_url)
                                if sub_resp.status_code == 200:
                                    crawled_items.extend(cls.extract_from_html(sub_resp.text, str(sub_resp.url)))
                                break
            except Exception as e:
                logger.warning(f"Could not fetch live pages for lead {lead.id}: {e}")
                # Fallback to research record text snippet
                if research.extracted_text_snippet:
                    crawled_items.extend(
                        cls.extract_from_html(f"<html><body>{research.extracted_text_snippet}</body></html>", research.crawled_url)
                    )

        # 2. If OpenStreetMap phone was discovered and not in existing contacts, add as fallback
        if lead.phone and lead.phone not in existing_phones and not any(c.get("phone") == lead.phone for c in crawled_items):
            crawled_items.append({
                "full_name": "Main Office",
                "title": "Business Listing",
                "email": None,
                "phone": lead.phone,
                "confidence_score": 0.8,
                "source_url": f"https://www.openstreetmap.org/{lead.external_id}",
                "snippet": f"OpenStreetMap verified business listing: {lead.phone}",
            })

        new_contacts: List[Contact] = []
        is_first = len(existing_contacts) == 0

        for item in crawled_items:
            item_mail = item.get("email")
            item_phone = item.get("phone")

            if item_mail and item_mail.lower() in existing_emails:
                continue
            if item_phone and item_phone in existing_phones and not item_mail:
                continue

            contact = Contact(
                lead_id=lead.id,
                full_name=item.get("full_name"),
                title=item.get("title"),
                email=item_mail,
                phone=item_phone,
                confidence_score=item.get("confidence_score", 0.8),
                is_primary=is_first,  # mark the first identified contact as primary
            )
            db.add(contact)
            db.flush()

            source = ContactSource(
                contact_id=contact.id,
                source_url=item.get("source_url", lead.website or "web"),
                snippet=item.get("snippet"),
            )
            db.add(source)

            if item_mail:
                existing_emails.add(item_mail.lower())
            if item_phone:
                existing_phones.add(item_phone)

            new_contacts.append(contact)
            is_first = False

        db.commit()
        for c in new_contacts:
            db.refresh(c)
        return new_contacts

    @classmethod
    async def batch_extract_contacts(
        cls,
        campaign_id: int,
        db: Session,
        limit: int = 25,
    ) -> BatchContactExtractionResponse:
        """
        Batch extract contacts for leads in a campaign.
        """
        start_time = time.time()
        leads_stmt = (
            select(Lead)
            .where(Lead.campaign_id == campaign_id)
            .limit(limit)
        )
        leads = list(db.scalars(leads_stmt).all())

        all_extracted: List[Contact] = []
        emails_count = 0
        practitioners_count = 0

        for lead in leads:
            try:
                extracted = await cls.extract_contacts_for_lead(lead.id, db)
                for c in extracted:
                    all_extracted.append(c)
                    if c.email:
                        emails_count += 1
                    if c.full_name and "Dr." in c.full_name:
                        practitioners_count += 1
            except Exception as e:
                logger.warning(f"Failed contact extraction for lead {lead.id}: {e}")

        duration = round(time.time() - start_time, 2)
        stats = BatchContactExtractionStats(
            total_leads=len(leads),
            contacts_found=len(all_extracted),
            emails_found=emails_count,
            practitioners_identified=practitioners_count,
            duration_seconds=duration,
        )

        pydantic_contacts = []
        for c in all_extracted:
            lead = db.get(Lead, c.lead_id)
            c_resp = ContactResponse.model_validate(c)
            c_resp.business_name = lead.business_name if lead else None
            pydantic_contacts.append(c_resp)

        return BatchContactExtractionResponse(
            campaign_id=campaign_id,
            stats=stats,
            contacts=pydantic_contacts,
        )


contact_service = ContactService()
