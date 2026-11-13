from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class GmailAuthStatusResponse(BaseModel):
    is_connected: bool
    mode: str  # "live" | "simulator"
    authorized_email: Optional[str] = None
    scopes: List[str] = []


class GmailAuthUrlResponse(BaseModel):
    auth_url: str


class GmailCodeExchangeRequest(BaseModel):
    code: str


class GmailDraftCreateResponse(BaseModel):
    draft_id: int
    gmail_draft_id: str
    message: str


class GmailSendResponse(BaseModel):
    message_id: int
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    recipient_email: str
    subject: str
    status: str
    dispatched_at: datetime


class EmailMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    draft_id: Optional[int] = None
    lead_id: int
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    direction: str
    recipient_email: str
    subject: str
    snippet: Optional[str] = None
    received_at: datetime
