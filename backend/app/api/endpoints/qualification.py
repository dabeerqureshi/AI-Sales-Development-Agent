from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.session import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.score import LeadScore
from app.schemas.qualification import BatchQualificationResponse, LeadScoreResponse
from app.services.qualification_service import qualification_service

router = APIRouter()


@router.post("/leads/{lead_id}/qualify", response_model=LeadScoreResponse)
async def qualify_single_lead(
    lead_id: int,
    db: Session = Depends(get_db),
) -> LeadScoreResponse:
    """Execute dual-layer qualification (deterministic scoring + 4-quadrant report) for a single lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )

    try:
        score_record = await qualification_service.qualify_lead(lead_id=lead.id, db=db)
        return LeadScoreResponse.model_validate(score_record)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to qualify lead: {str(e)}",
        )


@router.get("/leads/{lead_id}/score", response_model=LeadScoreResponse)
def get_lead_score(
    lead_id: int,
    db: Session = Depends(get_db),
) -> LeadScoreResponse:
    """Retrieve saved qualification score and 4-quadrant report for a lead."""
    stmt = select(LeadScore).where(LeadScore.lead_id == lead_id)
    score_record = db.execute(stmt).scalar_one_or_none()
    if not score_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No qualification score found for lead ID {lead_id}. Run qualification first.",
        )
    return LeadScoreResponse.model_validate(score_record)


@router.post("/campaigns/{campaign_id}/qualify", response_model=BatchQualificationResponse)
async def qualify_campaign_leads(
    campaign_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> BatchQualificationResponse:
    """Batch qualify leads for a campaign."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    result = await qualification_service.batch_qualify_campaign(
        campaign_id=campaign_id,
        db=db,
        limit=limit,
    )
    return BatchQualificationResponse.model_validate(result)


@router.get("/campaigns/{campaign_id}/scores", response_model=List[LeadScoreResponse])
def get_campaign_scores(
    campaign_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[LeadScoreResponse]:
    """Retrieve all qualification scores for leads within a campaign."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    stmt = (
        select(LeadScore)
        .join(Lead, Lead.id == LeadScore.lead_id)
        .where(Lead.campaign_id == campaign_id)
        .order_by(LeadScore.overall_score.desc())
        .limit(limit)
    )
    scores = db.execute(stmt).scalars().all()
    return [LeadScoreResponse.model_validate(s) for s in scores]
