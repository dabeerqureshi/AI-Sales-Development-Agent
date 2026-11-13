from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.database.session import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.schemas.lead import DiscoveryResponse, LeadResponse
from app.services.discovery_service import discovery_service

router = APIRouter()


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign_in: CampaignCreate,
    db: Session = Depends(get_db),
) -> CampaignResponse:
    """Create a new prospecting campaign."""
    campaign = Campaign(
        name=campaign_in.name,
        industry=campaign_in.industry,
        country=campaign_in.country,
        region=campaign_in.region,
        city=campaign_in.city,
        max_leads=campaign_in.max_leads,
        website_required=campaign_in.website_required,
        phone_required=campaign_in.phone_required,
        status="draft",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    resp = CampaignResponse.model_validate(campaign)
    resp.lead_count = 0
    return resp


@router.get("/campaigns", response_model=List[CampaignResponse])
def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[CampaignResponse]:
    """List all campaigns with active lead counts."""
    # Query campaigns and annotate with lead counts
    stmt = (
        select(Campaign, func.count(Lead.id).label("lead_count"))
        .outerjoin(Lead, Campaign.id == Lead.campaign_id)
        .group_by(Campaign.id)
        .order_by(Campaign.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    results = db.execute(stmt).all()

    response_list = []
    for campaign, count in results:
        camp_resp = CampaignResponse.model_validate(campaign)
        camp_resp.lead_count = count
        response_list.append(camp_resp)

    return response_list


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
) -> CampaignResponse:
    """Get single campaign details."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    count_stmt = select(func.count(Lead.id)).where(Lead.campaign_id == campaign_id)
    lead_count = db.scalar(count_stmt) or 0

    resp = CampaignResponse.model_validate(campaign)
    resp.lead_count = lead_count
    return resp


@router.post("/campaigns/{campaign_id}/discover", response_model=DiscoveryResponse)
async def discover_leads_for_campaign(
    campaign_id: int,
    limit: Optional[int] = Query(None, ge=1, le=500),
    db: Session = Depends(get_db),
) -> DiscoveryResponse:
    """Trigger MCP OpenStreetMap business discovery for the specified campaign."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    try:
        return await discovery_service.run_discovery_for_campaign(
            campaign_id=campaign_id,
            db=db,
            override_limit=limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Business discovery failed: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/leads", response_model=List[LeadResponse])
def get_campaign_leads(
    campaign_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    has_website: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> List[LeadResponse]:
    """Retrieve discovered leads for a specific campaign."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    stmt = select(Lead).where(Lead.campaign_id == campaign_id)
    if has_website is True:
        stmt = stmt.where(Lead.website.isnot(None))
    elif has_website is False:
        stmt = stmt.where(Lead.website.is_(None))

    stmt = stmt.order_by(Lead.created_at.desc()).offset(skip).limit(limit)
    leads = db.scalars(stmt).all()
    return [LeadResponse.model_validate(l) for l in leads]


@router.get("/leads/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
) -> LeadResponse:
    """Retrieve a single lead with source attributions."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )
    return LeadResponse.model_validate(lead)
