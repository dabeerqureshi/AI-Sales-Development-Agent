from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.email import EmailDraft
from app.schemas.gmail import (
    EmailMessageResponse,
    GmailAuthStatusResponse,
    GmailAuthUrlResponse,
    GmailCodeExchangeRequest,
    GmailDraftCreateResponse,
    GmailSendResponse,
)
from app.services.gmail_service import gmail_service

router = APIRouter()


@router.get("/gmail/status", response_model=GmailAuthStatusResponse)
def get_gmail_status(
    db: Session = Depends(get_db),
) -> GmailAuthStatusResponse:
    """Check current Gmail OAuth connection status and mode (live vs simulator)."""
    data = gmail_service.get_connection_status(db=db)
    return GmailAuthStatusResponse(**data)


@router.get("/gmail/auth-url", response_model=GmailAuthUrlResponse)
def get_gmail_auth_url() -> GmailAuthUrlResponse:
    """Retrieve Google OAuth 2.0 authorization URL."""
    return GmailAuthUrlResponse(auth_url=gmail_service.get_auth_url())


@router.post("/gmail/exchange")
async def exchange_gmail_code(
    payload: GmailCodeExchangeRequest,
    db: Session = Depends(get_db),
):
    """Exchange authorization code for Gmail access tokens."""
    try:
        tokens = await gmail_service.exchange_code(code=payload.code, db=db)
        return {
            "status": "connected",
            "email": tokens.get("email"),
            "mode": tokens.get("mode"),
            "message": "Gmail OAuth successfully authorized.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/drafts/{draft_id}/gmail-draft", response_model=GmailDraftCreateResponse)
async def push_draft_to_gmail(
    draft_id: int,
    db: Session = Depends(get_db),
) -> GmailDraftCreateResponse:
    """Create a remote draft in the operator's Gmail inbox for this outreach message."""
    try:
        res = await gmail_service.create_remote_draft(draft_id=draft_id, db=db)
        return GmailDraftCreateResponse(**res)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/drafts/{draft_id}/send", response_model=GmailSendResponse)
async def dispatch_approved_email(
    draft_id: int,
    db: Session = Depends(get_db),
) -> GmailSendResponse:
    """
    Human-in-the-Loop Send Endpoint:
    Dispatches an approved outreach email via Gmail API.
    Enforces human approval, suppression checks, and duplicate prevention.
    """
    try:
        message = await gmail_service.send_approved_email(draft_id=draft_id, db=db)
        return GmailSendResponse(
            message_id=message.id,
            gmail_message_id=message.gmail_message_id,
            gmail_thread_id=message.gmail_thread_id,
            recipient_email=message.recipient_email,
            subject=message.subject,
            status="sent",
            dispatched_at=message.received_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/messages", response_model=List[EmailMessageResponse])
def get_sent_messages_audit(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[EmailMessageResponse]:
    """Retrieve chronological audit trail of sent email messages."""
    messages = gmail_service.list_sent_messages(db=db, limit=limit)
    return [EmailMessageResponse.model_validate(m) for m in messages]
