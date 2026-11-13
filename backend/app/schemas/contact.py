from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ContactSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contact_id: int
    source_url: str
    snippet: Optional[str] = None
    detected_at: datetime


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    full_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    confidence_score: float = 0.8
    is_primary: bool = False
    created_at: datetime
    sources: List[ContactSourceResponse] = []
    business_name: Optional[str] = None


class BatchContactExtractionStats(BaseModel):
    total_leads: int
    contacts_found: int
    emails_found: int
    practitioners_identified: int
    duration_seconds: float


class BatchContactExtractionResponse(BaseModel):
    campaign_id: int
    stats: BatchContactExtractionStats
    contacts: List[ContactResponse]
