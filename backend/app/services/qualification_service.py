import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.models.contact import Contact
from app.models.score import LeadScore

logger = logging.getLogger(__name__)


class DeterministicScorer:
    """
    Transparent, auditable rule-based lead scorer.
    Score ranges from 0 to 100 based strictly on verified evidence.
    """

    POINTS_WEBSITE = 25
    POINTS_EMAIL = 25
    POINTS_PHONE = 15
    POINTS_PRACTITIONER = 15
    POINTS_OPPORTUNITY = 20

    @classmethod
    def calculate_score(
        cls,
        lead: Lead,
        research: Optional[ResearchRecord],
        contacts: List[Contact],
    ) -> Tuple[int, Dict[str, Any]]:
        breakdown = {}
        total_score = 0

        # 1. Verified Website (25 pts)
        has_website = bool(lead.website and lead.website.strip().startswith(("http://", "https://")))
        pts_website = cls.POINTS_WEBSITE if has_website else 0
        total_score += pts_website
        breakdown["website"] = {
            "name": "Verified Website",
            "points": pts_website,
            "max": cls.POINTS_WEBSITE,
            "passed": has_website,
            "details": f"Website URL: {lead.website}" if has_website else "No valid website found",
        }

        # 2. Direct Contact Email (25 pts)
        email_contacts = [c for c in contacts if c.email and c.email.strip()]
        has_email = len(email_contacts) > 0
        pts_email = cls.POINTS_EMAIL if has_email else 0
        total_score += pts_email
        breakdown["email"] = {
            "name": "Direct Contact Email",
            "points": pts_email,
            "max": cls.POINTS_EMAIL,
            "passed": has_email,
            "details": f"Direct email: {email_contacts[0].email}" if has_email else "No verified email discovered",
        }

        # 3. Verified Phone Number (15 pts)
        has_lead_phone = bool(lead.phone and lead.phone.strip())
        phone_contacts = [c for c in contacts if c.phone and c.phone.strip()]
        has_phone = has_lead_phone or len(phone_contacts) > 0
        phone_val = lead.phone or (phone_contacts[0].phone if phone_contacts else None)
        pts_phone = cls.POINTS_PHONE if has_phone else 0
        total_score += pts_phone
        breakdown["phone"] = {
            "name": "Verified Phone",
            "points": pts_phone,
            "max": cls.POINTS_PHONE,
            "passed": has_phone,
            "details": f"Phone number: {phone_val}" if has_phone else "No telephone number listed",
        }

        # 4. Identified Named Practitioner / Decision-Maker (15 pts)
        # Check if full_name is a specific named practitioner (e.g. Dr. ... or has DDS/DMD title)
        practitioner_contacts = [
            c for c in contacts
            if c.full_name and c.full_name not in ("Main Office / Reception", "Front Desk / Reception")
            and ("Dr." in c.full_name or any(deg in (c.title or "") for deg in ["DDS", "DMD", "Doctor", "Dentist", "Director", "Owner"]))
        ]
        has_practitioner = len(practitioner_contacts) > 0
        pts_practitioner = cls.POINTS_PRACTITIONER if has_practitioner else 0
        total_score += pts_practitioner
        breakdown["practitioner"] = {
            "name": "Named Practitioner / Doctor",
            "points": pts_practitioner,
            "max": cls.POINTS_PRACTITIONER,
            "passed": has_practitioner,
            "details": f"Practitioner: {practitioner_contacts[0].full_name} ({practitioner_contacts[0].title or 'Practitioner'})" if has_practitioner else "No named practitioner detected",
        }

        # 5. Opportunity Fit (20 pts)
        # Evaluates automation need: does clinic lack modern automated self-booking or rely on manual requests?
        pts_opportunity = 0
        opp_details = "Not yet researched"
        opp_passed = False

        if research:
            if not research.booking_system_found:
                # Prime opportunity: relies entirely on phone or static custom form
                pts_opportunity = cls.POINTS_OPPORTUNITY
                opp_passed = True
                if research.has_custom_booking_form:
                    opp_details = "Uses basic static request form without real-time booking; prime candidate for automated scheduling."
                else:
                    opp_details = "No online self-scheduling found; all intake requires manual phone calls during business hours."
            else:
                # Already has modern booking (e.g. Modento, Calendly, NexHealth)
                pts_opportunity = 5
                opp_passed = True
                opp_details = f"Modern booking tool detected ({research.booking_system_name or 'widget'}); opportunity limited to 24/7 after-hours voice triage."
        elif has_website:
            pts_opportunity = 10
            opp_passed = True
            opp_details = "Website exists but in-depth page research pending."

        total_score += pts_opportunity
        breakdown["opportunity_fit"] = {
            "name": "Automation Opportunity Fit",
            "points": pts_opportunity,
            "max": cls.POINTS_OPPORTUNITY,
            "passed": opp_passed,
            "details": opp_details,
        }

        return total_score, breakdown


class OpportunitySynthesizer:
    """
    Synthesizes evidence into a 4-quadrant qualification report:
    1. Verified Facts
    2. Potential Opportunity
    3. Unknowns (What cannot be assumed)
    4. Recommended Hook / Angle
    """

    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def build_rule_based_synthesis(
        self,
        lead: Lead,
        research: Optional[ResearchRecord],
        contacts: List[Contact],
    ) -> Dict[str, Any]:
        """Deterministic, grounded 4-quadrant report when Ollama is offline or unavailable."""
        verified_facts: List[str] = [
            f"Business: {lead.business_name} ({lead.industry}) located at {lead.address or 'Austin, TX'}",
        ]
        if lead.website:
            verified_facts.append(f"Official website: {lead.website}")
        if research and research.page_title:
            verified_facts.append(f"Website title: {research.page_title}")
        if research and research.services_summary:
            verified_facts.append(f"Services offered: {research.services_summary[:200]}")

        for c in contacts:
            if c.full_name and c.full_name not in ("Main Office / Reception", "Front Desk / Reception"):
                verified_facts.append(f"Identified practitioner: {c.full_name} ({c.title or 'Staff'})")
            if c.email:
                verified_facts.append(f"Verified direct email: {c.email}")
            if c.phone:
                verified_facts.append(f"Listed telephone: {c.phone}")

        # Potential Opportunity
        if research:
            if not research.booking_system_found and research.has_custom_booking_form:
                potential_opportunity = (
                    f"{lead.business_name} currently relies on a static web contact/appointment request form. "
                    "Prospective patients submitting inquiries in the evening must wait until the front desk opens to confirm slots, "
                    "creating an ideal fit for an AI receptionist to confirm appointments in real time."
                )
            elif not research.booking_system_found:
                potential_opportunity = (
                    f"{lead.business_name} has no automated online booking tool detected. All patient bookings appear to be routed "
                    "through traditional telephone lines during clinic hours. An AI voice/chat receptionist could capture after-hours booking demand."
                )
            else:
                potential_opportunity = (
                    f"{lead.business_name} utilizes {research.booking_system_name or 'an online scheduling tool'}. "
                    "The primary automation opportunity is after-hours call routing and inbound phone triage rather than basic web forms."
                )
        else:
            potential_opportunity = (
                f"{lead.business_name} operates in {lead.industry}. Automating customer inquiries and after-hours triage represents a valuable operational improvement."
            )

        # Honest Unknowns
        unknowns = (
            "1. Inbound call volume and after-hours inquiry frequency are unconfirmed from public data.\n"
            "2. Front desk staffing levels and current appointment cancellation rates cannot be determined without direct discussion.\n"
            "3. Internal practice management software compatibility is unverified."
        )

        # Recommended Angle
        practitioners = [
            c.full_name for c in contacts
            if c.full_name and c.full_name not in ("Main Office / Reception", "Front Desk / Reception")
        ]
        target_name = practitioners[0] if practitioners else "the Practice Director"
        if research and not research.booking_system_found:
            recommended_angle = (
                f"Introduce an AI receptionist tailored for {lead.industry} to {target_name}. "
                "Highlight eliminating delayed booking confirmations from web inquiries and capturing after-hours patient calls without expanding front desk headcount."
            )
        else:
            recommended_angle = (
                f"Present {target_name} with an after-hours voice triage solution that integrates with their existing schedule, "
                "ensuring no high-value dental inquiries are missed outside standard office hours."
            )

        return {
            "verified_facts": verified_facts,
            "potential_opportunity": potential_opportunity,
            "unknowns": unknowns,
            "recommended_angle": recommended_angle,
        }

    async def synthesize(
        self,
        lead: Lead,
        research: Optional[ResearchRecord],
        contacts: List[Contact],
    ) -> Dict[str, Any]:
        """
        Attempts synthesis via local Ollama (qwen3:4b).
        Falls back automatically to deterministic synthesis if Ollama is offline or times out.
        """
        # Prepare context data
        facts = [
            f"Business Name: {lead.business_name}",
            f"Industry: {lead.industry}",
            f"Location: {lead.address or 'Texas'}",
            f"Website: {lead.website or 'None'}",
        ]
        if research:
            facts.append(f"Page Title: {research.page_title or 'N/A'}")
            facts.append(f"Services: {research.services_summary or 'N/A'}")
            facts.append(f"Booking System Detected: {research.booking_system_found} ({research.booking_system_name or 'None'})")
            facts.append(f"Has Custom Form: {research.has_custom_booking_form}")
            if research.after_hours_info:
                facts.append(f"After Hours Info: {research.after_hours_info}")

        contact_facts = []
        for c in contacts:
            details = []
            if c.full_name:
                details.append(f"Name: {c.full_name}")
            if c.title:
                details.append(f"Title: {c.title}")
            if c.email:
                details.append(f"Email: {c.email}")
            if c.phone:
                details.append(f"Phone: {c.phone}")
            contact_facts.append(" | ".join(details))

        if contact_facts:
            facts.append("Discovered Contacts: " + "; ".join(contact_facts))
        if contact_facts:
            facts.append("Discovered Contacts: " + ", ".join(contact_facts))

        evidence_str = "\n".join(facts)

        prompt = f"""You are an objective B2B Sales Research Assistant.
Analyze the following verified business evidence and produce a structured qualification assessment.

STRICT ACCURACY RULES:
1. 'verified_facts': List ONLY statements strictly proven by the evidence below. Never invent services or details.
2. 'potential_opportunity': Explain how an AI Receptionist / Automated Booking system could assist them based on their actual intake setup.
3. 'unknowns': State clearly what cannot be known from public data (e.g. call drop rates, staffing stress).
4. 'recommended_angle': Recommend an evidence-backed hook for reaching out.
5. You MUST return ONLY a JSON object matching this schema:
{{
  "verified_facts": ["fact 1", "fact 2"],
  "potential_opportunity": "description",
  "unknowns": "description of unverified facts",
  "recommended_angle": "suggested outreach angle"
}}

VERIFIED BUSINESS EVIDENCE:
{evidence_str}
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
                            "temperature": 0.1,
                            "num_ctx": settings.OLLAMA_NUM_CTX,
                        },
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    response_text = data.get("response", "{}")
                    parsed = json.loads(response_text)
                    if (
                        "verified_facts" in parsed
                        and "potential_opportunity" in parsed
                        and "unknowns" in parsed
                        and "recommended_angle" in parsed
                    ):
                        logger.info(f"Ollama qualification synthesis successful for lead {lead.id}")
                        return parsed
        except Exception as e:
            logger.info(f"Ollama synthesis unavailable or failed ({e}); falling back to deterministic synthesis.")

        return self.build_rule_based_synthesis(lead, research, contacts)


class QualificationService:
    def __init__(self):
        self.synthesizer = OpportunitySynthesizer()

    async def qualify_lead(self, lead_id: int, db: Session) -> LeadScore:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead with id {lead_id} not found")

        research = db.query(ResearchRecord).filter(ResearchRecord.lead_id == lead_id).first()
        contacts = db.query(Contact).filter(Contact.lead_id == lead_id).all()

        # 1. Deterministic score computation
        overall_score, rule_breakdown = DeterministicScorer.calculate_score(lead, research, contacts)

        # 2. 4-quadrant report synthesis
        report = await self.synthesizer.synthesize(lead, research, contacts)

        # 3. Store or update LeadScore
        lead_score = db.query(LeadScore).filter(LeadScore.lead_id == lead_id).first()
        if not lead_score:
            lead_score = LeadScore(
                lead_id=lead_id,
                overall_score=overall_score,
                rule_breakdown=rule_breakdown,
                verified_facts=report.get("verified_facts", []),
                potential_opportunity=report.get("potential_opportunity", ""),
                unknowns=report.get("unknowns", ""),
                recommended_angle=report.get("recommended_angle", ""),
                scored_at=datetime.now(timezone.utc),
            )
            db.add(lead_score)
        else:
            lead_score.overall_score = overall_score
            lead_score.rule_breakdown = rule_breakdown
            lead_score.verified_facts = report.get("verified_facts", [])
            lead_score.potential_opportunity = report.get("potential_opportunity", "")
            lead_score.unknowns = report.get("unknowns", "")
            lead_score.recommended_angle = report.get("recommended_angle", "")
            lead_score.scored_at = datetime.now(timezone.utc)

        # Update lead status
        lead.status = "qualified"
        db.commit()
        db.refresh(lead_score)
        return lead_score

    async def batch_qualify_campaign(self, campaign_id: int, db: Session, limit: int = 50) -> Dict[str, Any]:
        start_time = time.time()
        leads = (
            db.query(Lead)
            .filter(Lead.campaign_id == campaign_id)
            .limit(limit)
            .all()
        )

        qualified_scores: List[LeadScore] = []
        skipped_count = 0

        for lead in leads:
            try:
                score = await self.qualify_lead(lead.id, db)
                qualified_scores.append(score)
            except Exception as e:
                logger.error(f"Error qualifying lead {lead.id}: {e}")
                skipped_count += 1

        elapsed = round(time.time() - start_time, 2)
        avg_score = (
            round(sum(s.overall_score for s in qualified_scores) / len(qualified_scores), 1)
            if qualified_scores
            else 0.0
        )

        return {
            "campaign_id": campaign_id,
            "status": "completed",
            "stats": {
                "total_candidates": len(leads),
                "qualified_count": len(qualified_scores),
                "skipped_count": skipped_count,
                "average_score": avg_score,
                "execution_time_seconds": elapsed,
            },
            "scores": qualified_scores,
        }


qualification_service = QualificationService()
