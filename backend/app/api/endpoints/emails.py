from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.session import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.email import EmailDraft
from app.schemas.email import (
    BatchDraftGenerationResponse,
    DraftReviewRequest,
    EmailDraftResponse,
    EmailDraftUpdate,
)
from app.services.email_service import email_service

router = APIRouter()


@router.post("/leads/{lead_id}/drafts/generate", response_model=EmailDraftResponse)
async def generate_lead_draft(
    lead_id: int,
    contact_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> EmailDraftResponse:
    """Generate or regenerate an evidence-grounded cold outreach email draft for a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )

    try:
        draft = await email_service.generate_or_update_draft(
            lead_id=lead_id,
            contact_id=contact_id,
            db=db,
        )
        return EmailDraftResponse.model_validate(draft)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate draft: {str(e)}",
        )


@router.get("/leads/{lead_id}/drafts", response_model=List[EmailDraftResponse])
def get_lead_drafts(
    lead_id: int,
    db: Session = Depends(get_db),
) -> List[EmailDraftResponse]:
    """Retrieve all drafts generated for a lead."""
    stmt = (
        select(EmailDraft)
        .where(EmailDraft.lead_id == lead_id)
        .order_by(EmailDraft.version.desc())
    )
    drafts = db.execute(stmt).scalars().all()
    return [EmailDraftResponse.model_validate(d) for d in drafts]


@router.get("/drafts/{draft_id}", response_model=EmailDraftResponse)
def get_draft_by_id(
    draft_id: int,
    db: Session = Depends(get_db),
) -> EmailDraftResponse:
    """Retrieve an email draft by its ID."""
    draft = db.get(EmailDraft, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email draft with ID {draft_id} not found",
        )
    return EmailDraftResponse.model_validate(draft)


@router.put("/drafts/{draft_id}", response_model=EmailDraftResponse)
def update_draft_content(
    draft_id: int,
    payload: EmailDraftUpdate,
    db: Session = Depends(get_db),
) -> EmailDraftResponse:
    """Manually edit subject or body of an outreach draft."""
    try:
        updated = email_service.update_draft(
            draft_id=draft_id,
            subject=payload.subject,
            body_text=payload.body_text,
            db=db,
        )
        return EmailDraftResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/drafts/{draft_id}/approve", response_model=EmailDraftResponse)
def approve_draft_endpoint(
    draft_id: int,
    payload: DraftReviewRequest = DraftReviewRequest(),
    db: Session = Depends(get_db),
) -> EmailDraftResponse:
    """Approve draft for outreach review."""
    try:
        approved = email_service.approve_draft(
            draft_id=draft_id,
            reviewer_notes=payload.notes,
            db=db,
        )
        return EmailDraftResponse.model_validate(approved)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/drafts/{draft_id}/reject", response_model=EmailDraftResponse)
def reject_draft_endpoint(
    draft_id: int,
    payload: DraftReviewRequest = DraftReviewRequest(),
    db: Session = Depends(get_db),
) -> EmailDraftResponse:
    """Reject draft with reviewer feedback."""
    try:
        rejected = email_service.reject_draft(
            draft_id=draft_id,
            reviewer_notes=payload.notes,
            db=db,
        )
        return EmailDraftResponse.model_validate(rejected)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/campaigns/{campaign_id}/drafts/generate", response_model=BatchDraftGenerationResponse)
async def batch_generate_campaign_drafts(
    campaign_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> BatchDraftGenerationResponse:
    """Batch generate evidence-grounded cold outreach email drafts across a campaign."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    result = await email_service.batch_generate_campaign_drafts(
        campaign_id=campaign_id,
        db=db,
        limit=limit,
    )
    return BatchDraftGenerationResponse.model_validate(result)


@router.get("/campaigns/{campaign_id}/drafts", response_model=List[EmailDraftResponse])
def get_campaign_drafts(
    campaign_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[EmailDraftResponse]:
    """Retrieve all email drafts for a campaign with optional status filtering."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    stmt = (
        select(EmailDraft)
        .join(Lead, Lead.id == EmailDraft.lead_id)
        .where(Lead.campaign_id == campaign_id)
    )
    if status_filter:
        stmt = stmt.where(EmailDraft.status == status_filter)

    stmt = stmt.order_by(EmailDraft.updated_at.desc()).limit(limit)
    drafts = db.execute(stmt).scalars().all()
    return [EmailDraftResponse.model_validate(d) for d in drafts]
