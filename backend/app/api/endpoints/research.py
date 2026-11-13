from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.session import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.research import ResearchRecord
from app.schemas.research import BatchResearchResponse, ResearchRecordResponse
from app.services.research_service import research_service

router = APIRouter()


@router.post("/leads/{lead_id}/research", response_model=ResearchRecordResponse)
async def research_single_lead(
    lead_id: int,
    db: Session = Depends(get_db),
) -> ResearchRecordResponse:
    """Execute website research for a single lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )
    if not lead.website:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lead '{lead.business_name}' does not have a website to research.",
        )

    try:
        record = await research_service.research_lead(lead_id=lead.id, db=db)
        return ResearchRecordResponse.model_validate(record)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to crawl and extract evidence: {str(e)}",
        )


@router.get("/leads/{lead_id}/research", response_model=ResearchRecordResponse)
def get_lead_research(
    lead_id: int,
    db: Session = Depends(get_db),
) -> ResearchRecordResponse:
    """Retrieve saved website research evidence for a lead."""
    stmt = select(ResearchRecord).where(ResearchRecord.lead_id == lead_id)
    record = db.scalar(stmt)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No research records found for lead ID {lead_id}",
        )
    return ResearchRecordResponse.model_validate(record)


@router.post("/campaigns/{campaign_id}/research", response_model=BatchResearchResponse)
async def batch_research_campaign(
    campaign_id: int,
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> BatchResearchResponse:
    """Batch crawl and research websites for all discovered leads in a campaign."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    try:
        return await research_service.research_campaign(
            campaign_id=campaign_id,
            db=db,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch research failed: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/research", response_model=List[ResearchRecordResponse])
def list_campaign_research_records(
    campaign_id: int,
    db: Session = Depends(get_db),
) -> List[ResearchRecordResponse]:
    """List all extracted research records for leads in a campaign."""
    stmt = (
        select(ResearchRecord)
        .join(Lead, ResearchRecord.lead_id == Lead.id)
        .where(Lead.campaign_id == campaign_id)
        .order_by(ResearchRecord.crawled_at.desc())
    )
    records = db.scalars(stmt).all()
    return [ResearchRecordResponse.model_validate(r) for r in records]
