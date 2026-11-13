from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.schemas.crm import (
    ActivityLogResponse,
    LeadStageUpdate,
    PipelineResponse,
    SuppressionCheckResponse,
    SuppressionCreate,
    SuppressionResponse,
)
from app.services.crm_service import crm_service

router = APIRouter()


@router.get("/crm/pipeline", response_model=PipelineResponse)
def get_crm_pipeline(
    campaign_id: int = Query(...),
    db: Session = Depends(get_db),
) -> PipelineResponse:
    """Retrieve leads for a campaign categorized into visual Kanban pipeline stages."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    return crm_service.get_pipeline(campaign_id=campaign_id, db=db)


@router.post("/leads/{lead_id}/stage")
def update_lead_pipeline_stage(
    lead_id: int,
    payload: LeadStageUpdate,
    db: Session = Depends(get_db),
):
    """
    Update lead pipeline stage with safety checks.
    Blocks transitions to 'approved' or 'contacted' if email/domain is on the suppression list.
    """
    try:
        updated_lead = crm_service.update_lead_stage(
            lead_id=lead_id,
            target_stage=payload.stage,
            notes=payload.notes,
            db=db,
        )
        return {
            "lead_id": updated_lead.id,
            "status": updated_lead.status,
            "message": f"Lead moved to stage '{updated_lead.status}'",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/suppression", response_model=List[SuppressionResponse])
def list_suppression_entries(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[SuppressionResponse]:
    """Retrieve global suppression rules (emails and domains)."""
    entries = crm_service.list_suppression(db=db, search=search, limit=limit)
    return [SuppressionResponse.model_validate(e) for e in entries]


@router.post("/suppression", response_model=SuppressionResponse)
def add_suppression_entry(
    payload: SuppressionCreate,
    db: Session = Depends(get_db),
) -> SuppressionResponse:
    """Add an email or whole domain to the global suppression list."""
    try:
        entry = crm_service.add_suppression(
            email=payload.email,
            domain=payload.domain,
            reason=payload.reason,
            db=db,
        )
        return SuppressionResponse.model_validate(entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/suppression/{entry_id}")
def remove_suppression_entry(
    entry_id: int,
    db: Session = Depends(get_db),
):
    """Remove a rule from the global suppression list."""
    try:
        crm_service.remove_suppression(entry_id=entry_id, db=db)
        return {"status": "success", "message": f"Suppression entry {entry_id} removed."}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/suppression/check", response_model=SuppressionCheckResponse)
def check_suppression_endpoint(
    email: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> SuppressionCheckResponse:
    """Verify whether an email address or domain is blocked before taking any action."""
    is_supp, matched_by, reason, details = crm_service.check_suppression(
        email=email,
        domain=domain,
        db=db,
    )
    return SuppressionCheckResponse(
        is_suppressed=is_supp,
        matched_by=matched_by,
        reason=reason,
        details=details,
    )


@router.get("/activities", response_model=List[ActivityLogResponse])
def get_activity_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[ActivityLogResponse]:
    """Retrieve chronological audit trail of all SDR operator and agent actions."""
    logs = crm_service.get_recent_activities(db=db, limit=limit)
    return [ActivityLogResponse.model_validate(l) for l in logs]
