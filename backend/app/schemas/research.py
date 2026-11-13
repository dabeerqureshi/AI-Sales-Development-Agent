from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ResearchRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    crawled_url: str
    page_title: Optional[str] = None
    meta_description: Optional[str] = None
    services_summary: Optional[str] = None
    booking_system_found: bool = False
    booking_system_name: Optional[str] = None
    has_custom_booking_form: bool = False
    after_hours_info: Optional[str] = None
    extracted_text_snippet: Optional[str] = None
    raw_metadata: Dict[str, Any] = {}
    crawled_at: datetime


class BatchResearchStats(BaseModel):
    total_leads: int
    successfully_researched: int
    booking_systems_detected: int
    failed_or_unreachable: int
    duration_seconds: float


class BatchResearchResponse(BaseModel):
    campaign_id: int
    stats: BatchResearchStats
    results: List[ResearchRecordResponse]
