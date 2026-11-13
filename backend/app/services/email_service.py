import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.models.contact import Contact
from app.models.score import LeadScore
from app.models.email import EmailDraft, EmailApproval

logger = logging.getLogger("email_service")


class EmailGeneratorService:
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def build_deterministic_draft(
        self,
        lead: Lead,
        contact: Optional[Contact],
        research: Optional[ResearchRecord],
        score: Optional[LeadScore],
    ) -> Dict[str, Any]:
        """
        Grounded, professional cold outreach template citing strictly verified facts.
        Used as fallback when Ollama is offline or unavailable.
        """
        # Salutation
        if contact and contact.full_name and contact.full_name not in ("Main Office / Reception", "Front Desk / Reception"):
            salutation = f"Hi {contact.full_name.split(',')[0]},"
            recipient_label = contact.full_name.split(',')[0]
        else:
            salutation = f"Hi {lead.business_name} Team,"
            recipient_label = "your team"

        # Verified Citations
        citations: List[str] = []
        if lead.business_name:
            loc = f" in {lead.address}" if lead.address else ""
            citations.append(f"Business: {lead.business_name}{loc} ({lead.industry})")
        if lead.website:
            citations.append(f"Official Website: {lead.website}")
        if contact and contact.full_name:
            citations.append(f"Primary Contact: {contact.full_name}")
        if research and research.services_summary:
            citations.append(f"Services: {research.services_summary[:120]}")
        if score and score.verified_facts:
            for f in score.verified_facts[:2]:
                if f not in citations:
                    citations.append(f)

        # Hook based on booking system detection
        if research and not research.booking_system_found and research.has_custom_booking_form:
            booking_hook = (
                f"I noticed on your website that prospective patients request appointments via an online form. "
                f"When patients submit inquiries outside office hours, they often have to wait until the front desk opens the next day to confirm."
            )
            citations.append("Intake: Uses static request form without real-time booking")
        elif research and not research.booking_system_found:
            booking_hook = (
                f"I noticed {lead.business_name} handles patient intake primarily by telephone during clinic hours. "
                f"Many patients researching dental care in the evenings hesitate to leave voicemails and look for practices that offer instant confirmation."
            )
            citations.append("Intake: Relies on phone inquiries with no online booking tool")
        else:
            booking_tool_name = research.booking_system_name if research else "online scheduling"
            booking_hook = (
                f"I noticed {lead.business_name} already utilizes {booking_tool_name}. "
                f"We help busy Texas practices handle inbound phone inquiries and after-hours call triage that traditional web widgets don't capture."
            )
            if research and research.booking_system_name:
                citations.append(f"Booking: Detected existing tool {research.booking_system_name}")

        subject = f"{lead.business_name} / after-hours patient inquiries"

        body = (
            f"{salutation}\n\n"
            f"I came across {lead.business_name} while researching top dental practices in {lead.address or 'Texas'}.\n\n"
            f"{booking_hook}\n\n"
            f"We built an AI receptionist specifically for dental clinics that answers patient phone calls and web inquiries 24/7, "
            f"answers routine questions, and schedules appointments directly into your system—without burdening your front desk.\n\n"
            f"Would you be open to a quick 3-minute video showing how other Texas clinics use this to capture after-hours bookings?\n\n"
            f"Best regards,\n"
            f"Sales Development Team\n\n"
            f"P.S. If you're not the right person to discuss front-desk operations, please let me know and I won't follow up."
        )

        return {
            "subject": subject,
            "body_text": body,
            "evidence_citations": citations,
        }

    async def generate_draft_content(
        self,
        lead: Lead,
        contact: Optional[Contact],
        research: Optional[ResearchRecord],
        score: Optional[LeadScore],
    ) -> Dict[str, Any]:
        """
        Attempts generation with local Ollama (qwen3:4b).
        Falls back automatically to deterministic template if Ollama is unreachable.
        """
        recipient_name = (
            contact.full_name
            if contact and contact.full_name and contact.full_name not in ("Main Office / Reception", "Front Desk / Reception")
            else "Practice Director"
        )

        verified_facts = score.verified_facts if score and score.verified_facts else []
        if not verified_facts and lead.website:
            verified_facts.append(f"Website: {lead.website}")

        evidence_bullets = "\n".join([f"- {fact}" for fact in verified_facts])

        recommended_angle = score.recommended_angle if score and score.recommended_angle else "24/7 patient call triage"

        prompt = f"""You are a professional B2B Sales Assistant writing a highly personalized cold outreach email.

RECIPIENT:
- Contact Name: {recipient_name}
- Business: {lead.business_name}
- Industry: {lead.industry}
- Location: {lead.address or 'Texas'}

VERIFIED EVIDENCE (You may ONLY reference facts from this list):
{evidence_bullets}

RECOMMENDED SALES ANGLE:
{recommended_angle}

OUR PRODUCT:
AI Receptionist for dental clinics that handles after-hours patient calls and web inquiries, confirms appointments, and prevents missed patient opportunities.

STRICT WRITING RULES:
1. Subject line: Under 7 words, relevant, zero clickbait or spammy words.
2. Salutation: Appropriate for {recipient_name}.
3. Length: 100 to 150 words total (3 brief paragraphs).
4. Do NOT claim they are losing money, missing calls, or understaffed without evidence.
5. In 'evidence_citations', list the exact verified facts you referenced in the email.
6. Include a polite opt-out at the end.
7. Return ONLY a valid JSON object matching this schema:
{{
  "subject": "subject line",
  "body_text": "full email body with linebreaks",
  "evidence_citations": ["verified fact 1", "verified fact 2"]
}}
"""

        try:
            async with httpx.AsyncClient(timeout=float(settings.OLLAMA_TIMEOUT_SECONDS)) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.2,
                            "num_ctx": settings.OLLAMA_NUM_CTX,
                        },
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "{}")
                    parsed = json.loads(response_text)
                    if (
                        "subject" in parsed
                        and "body_text" in parsed
                        and "evidence_citations" in parsed
                        and parsed["body_text"].strip()
                    ):
                        logger.info(f"Ollama email generation successful for lead {lead.id}")
                        return parsed
        except Exception as e:
            logger.info(f"Ollama generation failed or unavailable ({e}); using deterministic fallback.")

        return self.build_deterministic_draft(lead, contact, research, score)

    async def generate_or_update_draft(
        self,
        lead_id: int,
        contact_id: Optional[int],
        db: Session,
    ) -> EmailDraft:
        lead = db.get(Lead, lead_id)
        if not lead:
            raise ValueError(f"Lead with id {lead_id} not found")

        # Select target contact
        contact = None
        if contact_id:
            contact = db.get(Contact, contact_id)
        if not contact:
            # Pick primary contact or first with an email
            contacts = db.query(Contact).filter(Contact.lead_id == lead_id).all()
            primary = next((c for c in contacts if c.is_primary), None)
            with_email = next((c for c in contacts if c.email), None)
            contact = primary or with_email or (contacts[0] if contacts else None)

        research = db.query(ResearchRecord).filter(ResearchRecord.lead_id == lead_id).first()
        score = db.query(LeadScore).filter(LeadScore.lead_id == lead_id).first()

        content = await self.generate_draft_content(lead, contact, research, score)

        # Check existing draft for this lead
        existing_draft = (
            db.query(EmailDraft)
            .filter(EmailDraft.lead_id == lead_id)
            .order_by(EmailDraft.version.desc())
            .first()
        )

        if existing_draft:
            # Bump version and update content
            existing_draft.version += 1
            existing_draft.contact_id = contact.id if contact else None
            existing_draft.subject = content["subject"]
            existing_draft.body_text = content["body_text"]
            existing_draft.evidence_citations = content.get("evidence_citations", [])
            existing_draft.status = "draft"
            existing_draft.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_draft)
            return existing_draft
        else:
            new_draft = EmailDraft(
                lead_id=lead_id,
                contact_id=contact.id if contact else None,
                subject=content["subject"],
                body_text=content["body_text"],
                evidence_citations=content.get("evidence_citations", []),
                version=1,
                status="draft",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(new_draft)
            db.commit()
            db.refresh(new_draft)
            return new_draft

    def update_draft(
        self,
        draft_id: int,
        subject: Optional[str],
        body_text: Optional[str],
        db: Session,
    ) -> EmailDraft:
        draft = db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError(f"Draft with id {draft_id} not found")

        if subject is not None:
            draft.subject = subject.strip()
        if body_text is not None:
            draft.body_text = body_text.strip()

        draft.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(draft)
        return draft

    def approve_draft(
        self,
        draft_id: int,
        reviewer_notes: Optional[str],
        db: Session,
    ) -> EmailDraft:
        draft = db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError(f"Draft with id {draft_id} not found")

        draft.status = "approved"
        draft.updated_at = datetime.now(timezone.utc)

        approval = db.query(EmailApproval).filter(EmailApproval.draft_id == draft_id).first()
        if not approval:
            approval = EmailApproval(
                draft_id=draft_id,
                reviewer_notes=reviewer_notes,
                approved_at=datetime.now(timezone.utc),
            )
            db.add(approval)
        else:
            approval.reviewer_notes = reviewer_notes
            approval.approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(draft)
        return draft

    def reject_draft(
        self,
        draft_id: int,
        reviewer_notes: Optional[str],
        db: Session,
    ) -> EmailDraft:
        draft = db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError(f"Draft with id {draft_id} not found")

        draft.status = "rejected"
        draft.updated_at = datetime.now(timezone.utc)

        approval = db.query(EmailApproval).filter(EmailApproval.draft_id == draft_id).first()
        if not approval:
            approval = EmailApproval(
                draft_id=draft_id,
                reviewer_notes=reviewer_notes,
            )
            db.add(approval)
        else:
            approval.reviewer_notes = reviewer_notes

        db.commit()
        db.refresh(draft)
        return draft

    async def batch_generate_campaign_drafts(
        self,
        campaign_id: int,
        db: Session,
        limit: int = 50,
    ) -> Dict[str, Any]:
        start_time = time.time()
        leads = (
            db.query(Lead)
            .filter(Lead.campaign_id == campaign_id)
            .limit(limit)
            .all()
        )

        generated_drafts: List[EmailDraft] = []
        skipped_count = 0

        for lead in leads:
            try:
                draft = await self.generate_or_update_draft(
                    lead_id=lead.id,
                    contact_id=None,
                    db=db,
                )
                generated_drafts.append(draft)
            except Exception as e:
                logger.error(f"Failed to generate draft for lead {lead.id}: {e}")
                skipped_count += 1

        elapsed = round(time.time() - start_time, 2)

        return {
            "campaign_id": campaign_id,
            "status": "completed",
            "stats": {
                "total_candidates": len(leads),
                "drafts_generated": len(generated_drafts),
                "skipped_count": skipped_count,
                "execution_time_seconds": elapsed,
            },
            "drafts": generated_drafts,
        }


email_service = EmailGeneratorService()
