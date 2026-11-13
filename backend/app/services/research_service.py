import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
import trafilatura
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.schemas.research import BatchResearchResponse, BatchResearchStats, ResearchRecordResponse

logger = logging.getLogger("research_service")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (AISalesDevelopmentAgent/1.0; +http://local.sdr)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

BOOKING_PROVIDERS = [
    ("nexhealth", "NexHealth"),
    ("calendly.com", "Calendly"),
    ("zocdoc.com", "ZocDoc"),
    ("opentable.com", "OpenTable"),
    ("janeapp.com", "JaneApp"),
    ("jane.app", "JaneApp"),
    ("acuityscheduling.com", "Acuity Scheduling"),
    ("squareup.com/appointments", "Square Appointments"),
    ("square.site", "Square Appointments"),
    ("solutionreach.com", "Solutionreach"),
    ("dentrix.com", "Dentrix"),
    ("localmed.com", "LocalMed"),
    ("modento.io", "Modento"),
    ("phorest.com", "Phorest"),
]

CUSTOM_BOOKING_PHRASES = [
    "request an appointment",
    "book an appointment",
    "schedule an appointment",
    "schedule appointment",
    "book appointment",
    "book online",
    "appointment request",
    "schedule consultation",
    "request appointment",
]


class ResearchService:
    @staticmethod
    async def fetch_html(url: str, timeout: float = 10.0) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fetch HTML safely with redirects and timeouts.
        Returns: (html_content, final_url, error_message)
        """
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                follow_redirects=True,
                verify=False,  # tolerate local or expired corporate certificates
            ) as client:
                resp = await client.get(url)
                if resp.status_code < 400:
                    return resp.text, str(resp.url), None
                else:
                    return None, str(resp.url), f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            return None, url, "Connection timed out"
        except httpx.ConnectError:
            # If https fails, try http fallback
            if url.startswith("https://"):
                try:
                    fallback_url = "http://" + url[8:]
                    async with httpx.AsyncClient(
                        headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True, verify=False
                    ) as client:
                        resp = await client.get(fallback_url)
                        if resp.status_code < 400:
                            return resp.text, str(resp.url), None
                except Exception:
                    pass
            return None, url, "Could not resolve or connect to server"
        except Exception as e:
            return None, url, str(e)

    @staticmethod
    def detect_booking_system(soup: BeautifulSoup, html: str) -> Tuple[bool, Optional[str], bool]:
        """
        Detect third-party widgets and custom appointment request forms.
        Returns: (booking_found, provider_name, has_custom_form)
        """
        html_lower = html.lower()

        # 1. Search for known third-party widget domains in links, iframes, and scripts
        for pattern, provider_name in BOOKING_PROVIDERS:
            if pattern in html_lower:
                return True, provider_name, False

        # Check iframe src and a href specifically
        for tag in soup.find_all(["iframe", "a", "script"]):
            src_or_href = (tag.get("src") or tag.get("href") or "").lower()
            for pattern, provider_name in BOOKING_PROVIDERS:
                if pattern in src_or_href:
                    return True, provider_name, False

        # 2. Check for custom booking forms or scheduling buttons
        has_custom_form = False
        for form in soup.find_all("form"):
            form_text = form.get_text(" ", strip=True).lower()
            action = (form.get("action") or "").lower()
            if any(p in form_text or p in action for p in CUSTOM_BOOKING_PHRASES):
                has_custom_form = True
                break

        # Check button/link texts if not in form
        if not has_custom_form:
            for elem in soup.find_all(["button", "a"]):
                elem_text = elem.get_text(" ", strip=True).lower()
                if any(p == elem_text or f" {p} " in f" {elem_text} " for p in CUSTOM_BOOKING_PHRASES):
                    has_custom_form = True
                    break

        if has_custom_form:
            return True, "Custom Online Booking Form", True

        return False, None, False

    @staticmethod
    def extract_services_summary(soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract key business services mentioned on the page."""
        services = []
        
        # Look for headers mentioning services or procedures
        headers = soup.find_all(["h1", "h2", "h3", "h4"])
        service_sections = []
        for h in headers:
            h_text = h.get_text(" ", strip=True)
            if re.search(r"\b(services|treatments|procedures|what we offer|specialties|care)\b", h_text, re.I):
                service_sections.append(h)

        for s_header in service_sections[:3]:
            # Extract subsequent siblings (ul/ol or p)
            parent = s_header.parent
            if parent:
                for li in parent.find_all("li")[:10]:
                    item_text = li.get_text(" ", strip=True)
                    if 3 < len(item_text) < 80:
                        services.append(item_text)

        # Fallback keyword scanning if structure is not standard
        if not services:
            common_keywords = [
                "General Dentistry", "Cosmetic Dentistry", "Teeth Whitening", "Dental Implants",
                "Orthodontics", "Invisalign", "Root Canal", "Emergency Dental Care",
                "Pediatric Dentistry", "Preventive Care", "Crowns & Bridges", "Periodontics",
                "Dentures", "Oral Surgery", "Sedation Dentistry"
            ]
            for kw in common_keywords:
                if re.search(rf"\b{re.escape(kw)}\b", text, re.I):
                    services.append(kw)

        if services:
            unique_services = list(dict.fromkeys(services))[:8]
            return ", ".join(unique_services)
        return None

    @staticmethod
    def extract_after_hours_info(text: str) -> Optional[str]:
        """Scan text for emergency or after-hours call handling policies."""
        patterns = [
            r"([^.?!;\n]*?\b(?:after[\s-]hours|emergency care|emergencies|24/7|on-call|same[\s-]day emergency)[^.?!;\n]*?[.?!])",
        ]
        matches = []
        for pat in patterns:
            found = re.findall(pat, text, flags=re.I)
            for m in found:
                cleaned = m.strip()
                if 20 < len(cleaned) < 200:
                    matches.append(cleaned)

        if matches:
            return matches[0]
        return None

    @classmethod
    async def analyze_website(cls, url: str) -> Dict[str, Any]:
        """
        Crawl homepage and (if applicable) Contact/Booking subpage to extract evidence.
        """
        html, final_url, err = await cls.fetch_html(url)
        if err or not html:
            return {
                "crawled_url": url,
                "error": err or "Failed to retrieve webpage",
                "booking_system_found": False,
                "booking_system_name": None,
                "has_custom_booking_form": False,
                "services_summary": None,
                "after_hours_info": None,
                "extracted_text_snippet": None,
                "page_title": None,
                "meta_description": None,
                "raw_metadata": {"error": err},
            }

        soup = BeautifulSoup(html, "html.parser")

        # 1. Page Title & Meta Description
        page_title = soup.title.get_text(" ", strip=True) if soup.title else None
        meta_desc = None
        desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)}) or \
                   soup.find("meta", attrs={"property": re.compile(r"description", re.I)})
        if desc_tag:
            meta_desc = desc_tag.get("content", "").strip()

        # 2. Main content extraction via Trafilatura
        main_text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        if not main_text or len(main_text) < 100:
            # Fallback to BeautifulSoup text
            main_text = " ".join([p.get_text(" ", strip=True) for p in soup.find_all(["p", "h1", "h2", "h3"])])

        # 3. Detect booking systems on Homepage
        booking_found, booking_name, has_custom_form = cls.detect_booking_system(soup, html)

        # 4. Extract services & after-hours evidence
        services = cls.extract_services_summary(soup, main_text)
        after_hours = cls.extract_after_hours_info(main_text)

        # 5. Check subpages (Contact or Book) if booking wasn't detected on homepage
        contact_subpage_url = None
        if not booking_found:
            for link in soup.find_all("a", href=True):
                href = link["href"].strip()
                full_link = urljoin(final_url, href)
                # Ensure it belongs to the same domain
                if urlparse(full_link).netloc == urlparse(final_url).netloc:
                    if re.search(r"/(contact|appointment|book|schedule)", full_link, re.I):
                        contact_subpage_url = full_link
                        break

            if contact_subpage_url:
                sub_html, _, _ = await cls.fetch_html(contact_subpage_url, timeout=6.0)
                if sub_html:
                    sub_soup = BeautifulSoup(sub_html, "html.parser")
                    sub_booking, sub_name, sub_form = cls.detect_booking_system(sub_soup, sub_html)
                    if sub_booking:
                        booking_found = True
                        booking_name = sub_name
                        has_custom_form = sub_form

        # Clean preview snippet
        clean_snippet = re.sub(r"\s+", " ", main_text).strip()[:1000] if main_text else None

        return {
            "crawled_url": final_url,
            "page_title": page_title[:255] if page_title else None,
            "meta_description": meta_desc[:500] if meta_desc else None,
            "services_summary": services,
            "booking_system_found": booking_found,
            "booking_system_name": booking_name,
            "has_custom_booking_form": has_custom_form,
            "after_hours_info": after_hours,
            "extracted_text_snippet": clean_snippet,
            "raw_metadata": {
                "subpage_checked": contact_subpage_url,
                "character_count": len(main_text) if main_text else 0,
            },
        }

    @classmethod
    async def research_lead(cls, lead_id: int, db: Session) -> ResearchRecord:
        """Execute website research for a single lead and persist evidence."""
        lead = db.get(Lead, lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found.")

        if not lead.website:
            raise ValueError(f"Lead '{lead.business_name}' does not have a website.")

        evidence = await cls.analyze_website(lead.website)

        # Check existing record or create new
        record_stmt = select(ResearchRecord).where(ResearchRecord.lead_id == lead.id)
        record = db.scalar(record_stmt)

        if not record:
            record = ResearchRecord(
                lead_id=lead.id,
                crawled_url=evidence["crawled_url"],
                page_title=evidence.get("page_title"),
                meta_description=evidence.get("meta_description"),
                services_summary=evidence.get("services_summary"),
                booking_system_found=evidence.get("booking_system_found", False),
                booking_system_name=evidence.get("booking_system_name"),
                has_custom_booking_form=evidence.get("has_custom_booking_form", False),
                after_hours_info=evidence.get("after_hours_info"),
                extracted_text_snippet=evidence.get("extracted_text_snippet"),
                raw_metadata=evidence.get("raw_metadata", {}),
            )
            db.add(record)
        else:
            record.crawled_url = evidence["crawled_url"]
            record.page_title = evidence.get("page_title")
            record.meta_description = evidence.get("meta_description")
            record.services_summary = evidence.get("services_summary")
            record.booking_system_found = evidence.get("booking_system_found", False)
            record.booking_system_name = evidence.get("booking_system_name")
            record.has_custom_booking_form = evidence.get("has_custom_booking_form", False)
            record.after_hours_info = evidence.get("after_hours_info")
            record.extracted_text_snippet = evidence.get("extracted_text_snippet")
            record.raw_metadata = evidence.get("raw_metadata", {})

        lead.status = "researched"
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    async def research_campaign(
        cls,
        campaign_id: int,
        db: Session,
        limit: int = 20,
    ) -> BatchResearchResponse:
        """Batch research all discovered leads in a campaign with a website."""
        start_time = time.time()
        leads_stmt = (
            select(Lead)
            .where(Lead.campaign_id == campaign_id, Lead.website.isnot(None))
            .limit(limit)
        )
        leads = list(db.scalars(leads_stmt).all())

        researched_records: List[ResearchRecord] = []
        booking_detected_count = 0
        failed_count = 0

        for lead in leads:
            try:
                rec = await cls.research_lead(lead.id, db)
                researched_records.append(rec)
                if rec.booking_system_found:
                    booking_detected_count += 1
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to research lead {lead.id}: {e}")

        duration = round(time.time() - start_time, 2)
        stats = BatchResearchStats(
            total_leads=len(leads),
            successfully_researched=len(researched_records),
            booking_systems_detected=booking_detected_count,
            failed_or_unreachable=failed_count,
            duration_seconds=duration,
        )

        return BatchResearchResponse(
            campaign_id=campaign_id,
            stats=stats,
            results=[ResearchRecordResponse.model_validate(r) for r in researched_records],
        )


research_service = ResearchService()
