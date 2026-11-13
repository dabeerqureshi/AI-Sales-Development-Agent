from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.session import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.contact import Contact
from app.schemas.contact import BatchContactExtractionResponse, ContactResponse
from app.services.contact_service import contact_service

router = APIRouter()


@router.post("/leads/{lead_id}/contacts/extract", response_model=List[ContactResponse])
async def extract_contacts_for_lead(
    lead_id: int,
    db: Session = Depends(get_db),
) -> List[ContactResponse]:
    """Extract public contacts from crawled records and website for a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )

    try:
        contacts = await contact_service.extract_contacts_for_lead(lead_id=lead.id, db=db)
        results = []
        for c in contacts:
            c_resp = ContactResponse.model_validate(c)
            c_resp.business_name = lead.business_name
            results.append(c_resp)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contact extraction failed: {str(e)}",
        )


@router.get("/leads/{lead_id}/contacts", response_model=List[ContactResponse])
def get_lead_contacts(
    lead_id: int,
    db: Session = Depends(get_db),
) -> List[ContactResponse]:
    """Retrieve all contacts associated with a specific lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found",
        )

    stmt = select(Contact).where(Contact.lead_id == lead_id).order_by(Contact.is_primary.desc())
    contacts = db.scalars(stmt).all()
    results = []
    for c in contacts:
        c_resp = ContactResponse.model_validate(c)
        c_resp.business_name = lead.business_name
        results.append(c_resp)
    return results


@router.post("/campaigns/{campaign_id}/contacts/extract", response_model=BatchContactExtractionResponse)
async def batch_extract_contacts(
    campaign_id: int,
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> BatchContactExtractionResponse:
    """Batch extract contacts for all discovered leads in a campaign."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with ID {campaign_id} not found",
        )

    try:
        return await contact_service.batch_extract_contacts(
            campaign_id=campaign_id,
            db=db,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch contact extraction failed: {str(e)}",
        )


@router.get("/contacts", response_model=List[ContactResponse])
def list_contacts(
    campaign_id: Optional[int] = None,
    has_email: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[ContactResponse]:
    """List discovered contacts with optional campaign and email filters."""
    stmt = select(Contact).join(Lead, Contact.lead_id == Lead.id)

    if campaign_id:
        stmt = stmt.where(Lead.campaign_id == campaign_id)
    if has_email is True:
        stmt = stmt.where(Contact.email.isnot(None))
    elif has_email is False:
        stmt = stmt.where(Contact.email.is_(None))

    stmt = stmt.order_by(Contact.created_at.desc()).offset(skip).limit(limit)
    contacts = db.scalars(stmt).all()

    results = []
    for c in contacts:
        lead = db.get(Lead, c.lead_id)
        c_resp = ContactResponse.model_validate(c)
        c_resp.business_name = lead.business_name if lead else None
        results.append(c_resp)
    return results


@router.post("/contacts/{contact_id}/primary", response_model=ContactResponse)
def set_primary_contact(
    contact_id: int,
    db: Session = Depends(get_db),
) -> ContactResponse:
    """Designate this contact as the primary recipient for outreach."""
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found",
        )

    # Unmark other contacts for this lead
    other_contacts_stmt = select(Contact).where(Contact.lead_id == contact.lead_id)
    for c in db.scalars(other_contacts_stmt).all():
        c.is_primary = False

    contact.is_primary = True
    db.commit()
    db.refresh(contact)

    lead = db.get(Lead, contact.lead_id)
    resp = ContactResponse.model_validate(contact)
    resp.business_name = lead.business_name if lead else None
    return resp
