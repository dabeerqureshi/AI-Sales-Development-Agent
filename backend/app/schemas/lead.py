from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class LeadSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_name: str
    source_url: str
    external_id: Optional[str] = None
    retrieved_at: datetime


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    business_name: str
    industry: str
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: str
    external_id: str
    status: str
    created_at: datetime
    sources: List[LeadSourceResponse] = []


class DiscoveryStats(BaseModel):
    total_found: int
    new_leads_saved: int
    duplicates_skipped: int
    filtered_out: int
    execution_time_seconds: float


class DiscoveryResponse(BaseModel):
    campaign_id: int
    status: str
    stats: DiscoveryStats
    leads: List[LeadResponse]
