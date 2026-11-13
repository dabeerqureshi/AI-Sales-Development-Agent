import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lead import Lead
from app.models.contact import Contact
from app.models.email import EmailDraft
from app.models.gmail import EmailMessage
from app.models.setting import SystemSetting
from app.services.crm_service import crm_service

logger = logging.getLogger("gmail_service")

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GmailService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI

    def is_credentials_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_auth_url(self) -> str:
        """Generates Google OAuth 2.0 authorization URL."""
        if not self.is_credentials_configured():
            # Return demo/simulator auth instructions URL
            params = {
                "client_id": self.client_id or "configured-in-env",
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(GMAIL_SCOPES),
                "access_type": "offline",
                "prompt": "consent",
            }
            return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def get_stored_tokens(self, db: Session) -> Optional[Dict[str, Any]]:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "gmail_oauth_tokens").first()
        if setting and setting.value:
            try:
                return json.loads(setting.value)
            except Exception:
                return None
        return None

    def save_tokens(self, tokens: Dict[str, Any], db: Session):
        setting = db.query(SystemSetting).filter(SystemSetting.key == "gmail_oauth_tokens").first()
        if not setting:
            setting = SystemSetting(key="gmail_oauth_tokens", value=json.dumps(tokens))
            db.add(setting)
        else:
            setting.value = json.dumps(tokens)
            setting.updated_at = datetime.now(timezone.utc)
        db.commit()

    async def exchange_code(self, code: str, db: Session) -> Dict[str, Any]:
        """Exchanges authorization code for Google access and refresh tokens."""
        if not self.is_credentials_configured():
            # In simulator/dev mode without external credentials
            simulated_tokens = {
                "access_token": f"sim-access-{uuid.uuid4().hex[:16]}",
                "refresh_token": f"sim-refresh-{uuid.uuid4().hex[:16]}",
                "email": "operator-sdr@agency.internal",
                "scopes": GMAIL_SCOPES,
                "mode": "simulator",
            }
            self.save_tokens(simulated_tokens, db)
            crm_service.log_activity(
                entity_type="gmail",
                entity_id=0,
                action="oauth_connected",
                details={"mode": "simulator", "email": simulated_tokens["email"]},
                db=db,
            )
            return simulated_tokens

        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data=data)
            if resp.status_code == 200:
                token_data = resp.json()
                # Fetch user email profile
                user_email = None
                headers = {"Authorization": f"Bearer {token_data.get('access_token')}"}
                profile_resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)
                if profile_resp.status_code == 200:
                    user_email = profile_resp.json().get("email")

                token_data["email"] = user_email
                token_data["scopes"] = GMAIL_SCOPES
                token_data["mode"] = "live"
                self.save_tokens(token_data, db)
                crm_service.log_activity(
                    entity_type="gmail",
                    entity_id=0,
                    action="oauth_connected",
                    details={"mode": "live", "email": user_email},
                    db=db,
                )
                return token_data
            else:
                raise ValueError(f"Google token exchange failed: {resp.text}")

    def get_connection_status(self, db: Session) -> Dict[str, Any]:
        tokens = self.get_stored_tokens(db)
        if tokens:
            return {
                "is_connected": True,
                "mode": tokens.get("mode", "simulator" if not self.is_credentials_configured() else "live"),
                "authorized_email": tokens.get("email", "operator@example.com"),
                "scopes": tokens.get("scopes", GMAIL_SCOPES),
            }
        return {
            "is_connected": False,
            "mode": "live" if self.is_credentials_configured() else "simulator",
            "authorized_email": None,
            "scopes": [],
        }

    @staticmethod
    def create_mime_message(to: str, subject: str, body: str, from_email: Optional[str] = None) -> str:
        """Constructs an RFC 2822 base64url encoded MIME message."""
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        if from_email:
            msg["From"] = from_email
        raw_bytes = msg.as_bytes()
        return base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

    def resolve_recipient_email(self, draft: EmailDraft, db: Session) -> str:
        """Resolves target recipient email for draft."""
        if draft.contact and draft.contact.email:
            return draft.contact.email.strip()

        contacts = db.query(Contact).filter(Contact.lead_id == draft.lead_id).all()
        primary = next((c for c in contacts if c.is_primary and c.email), None)
        with_email = next((c for c in contacts if c.email), None)
        target = primary or with_email

        if not target or not target.email:
            raise ValueError(f"Lead #{draft.lead_id} does not have a verified email address for outreach.")
        return target.email.strip()

    async def create_remote_draft(self, draft_id: int, db: Session) -> Dict[str, Any]:
        """Creates a remote draft in the user's Gmail inbox."""
        draft = db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError(f"Draft with id {draft_id} not found.")

        recipient_email = self.resolve_recipient_email(draft, db)
        tokens = self.get_stored_tokens(db)
        raw_msg = self.create_mime_message(
            to=recipient_email,
            subject=draft.subject,
            body=draft.body_text,
            from_email=tokens.get("email") if tokens else None,
        )

        if tokens and tokens.get("mode") == "live" and tokens.get("access_token"):
            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json",
            }
            payload = {"message": {"raw": raw_msg}}
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post("https://gmail.googleapis.com/gmail/v1/users/me/drafts", headers=headers, json=payload)
                if res.status_code == 200:
                    remote_data = res.json()
                    crm_service.log_activity(
                        entity_type="draft",
                        entity_id=draft.id,
                        action="gmail_draft_created",
                        details={"gmail_draft_id": remote_data.get("id"), "recipient": recipient_email},
                        db=db,
                    )
                    return {
                        "draft_id": draft.id,
                        "gmail_draft_id": remote_data.get("id", ""),
                        "message": "Gmail draft successfully created in live inbox.",
                    }
                else:
                    logger.warning(f"Live Gmail API draft error: {res.text}. Falling back to simulation.")

        # Simulator Mode
        sim_id = f"draft-sim-{uuid.uuid4().hex[:12]}"
        crm_service.log_activity(
            entity_type="draft",
            entity_id=draft.id,
            action="gmail_draft_created",
            details={"gmail_draft_id": sim_id, "mode": "simulator", "recipient": recipient_email},
            db=db,
        )
        return {
            "draft_id": draft.id,
            "gmail_draft_id": sim_id,
            "message": "Gmail draft created successfully (Simulator Mode).",
        }

    async def send_approved_email(self, draft_id: int, db: Session) -> EmailMessage:
        """
        Human-in-the-Loop Send Gate:
        Dispatches an approved outreach email via Gmail API.
        Strictly verifies:
        1. Human approval (draft.status == 'approved')
        2. Recipient suppression status (email & domain)
        3. Duplicate send prevention
        """
        draft = db.get(EmailDraft, draft_id)
        if not draft:
            raise ValueError(f"Draft with id {draft_id} not found.")

        # Safety Gate 1: Human Approval Required
        if draft.status != "approved":
            raise ValueError(
                f"Human Safety Gate: Email draft #{draft.id} is currently '{draft.status}'. "
                "Only human-reviewed drafts with status 'approved' may be sent."
            )

        lead = db.get(Lead, draft.lead_id)
        if not lead:
            raise ValueError(f"Lead with id {draft.lead_id} not found.")

        recipient_email = self.resolve_recipient_email(draft, db)

        # Safety Gate 2: Suppression Check (Email & Domain)
        lead_domain = crm_service.extract_domain(lead.website)
        is_supp, match, reason, details = crm_service.check_suppression(recipient_email, lead_domain, db)
        if is_supp:
            raise ValueError(
                f"Compliance Safety Gate: Recipient '{recipient_email}' is on the suppression list ({reason}). "
                f"Dispatch rejected: {details}."
            )

        # Safety Gate 3: Duplicate Send Prevention
        existing_sent = (
            db.query(EmailMessage)
            .filter(EmailMessage.lead_id == lead.id, EmailMessage.direction == "outbound")
            .first()
        )
        if existing_sent:
            raise ValueError(
                f"Duplicate Send Prevention: Lead '{lead.business_name}' already received outbound message #{existing_sent.id} "
                f"(Gmail ID: {existing_sent.gmail_message_id}) on {existing_sent.received_at.strftime('%Y-%m-%d %H:%M UTC')}."
            )

        tokens = self.get_stored_tokens(db)
        raw_msg = self.create_mime_message(
            to=recipient_email,
            subject=draft.subject,
            body=draft.body_text,
            from_email=tokens.get("email") if tokens else None,
        )

        gmail_msg_id = ""
        gmail_th_id = ""

        # Dispatch via live Gmail if connected
        if tokens and tokens.get("mode") == "live" and tokens.get("access_token"):
            headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", headers=headers, json={"raw": raw_msg})
                if res.status_code == 200:
                    send_data = res.json()
                    gmail_msg_id = send_data.get("id", "")
                    gmail_th_id = send_data.get("threadId", "")
                else:
                    logger.warning(f"Live Gmail send failed ({res.text}); falling back to simulator.")

        if not gmail_msg_id:
            # Simulator Mode
            gmail_msg_id = f"msg-sim-{uuid.uuid4().hex[:16]}"
            gmail_th_id = f"th-sim-{uuid.uuid4().hex[:16]}"

        # Persist Sent Email Message Audit Record
        message = EmailMessage(
            draft_id=draft.id,
            lead_id=lead.id,
            gmail_message_id=gmail_msg_id,
            gmail_thread_id=gmail_th_id,
            direction="outbound",
            recipient_email=recipient_email,
            subject=draft.subject,
            snippet=draft.body_text[:200],
            received_at=datetime.now(timezone.utc),
        )
        db.add(message)

        # Transition Draft & Lead States
        draft.status = "sent"
        draft.updated_at = datetime.now(timezone.utc)
        lead.status = "contacted"
        lead.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(message)

        # Record Activity Log
        crm_service.log_activity(
            entity_type="email",
            entity_id=draft.id,
            action="email_dispatched",
            details={
                "message_id": message.id,
                "gmail_message_id": gmail_msg_id,
                "recipient": recipient_email,
                "lead_id": lead.id,
                "business_name": lead.business_name,
            },
            db=db,
        )

        return message

    def list_sent_messages(self, db: Session, limit: int = 50) -> List[EmailMessage]:
        stmt = (
            db.query(EmailMessage)
            .order_by(EmailMessage.received_at.desc())
            .limit(limit)
            .all()
        )
        return list(stmt)


gmail_service = GmailService()
