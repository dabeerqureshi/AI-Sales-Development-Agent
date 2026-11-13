from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class SuppressionCreate(BaseModel):
    email: Optional[str] = None
    domain: Optional[str] = None
    reason: str = "unsubscribed"


class SuppressionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: Optional[str] = None
    domain: Optional[str] = None
    reason: str
    added_at: datetime


class SuppressionCheckResponse(BaseModel):
    is_suppressed: bool
    matched_by: Optional[str] = None  # "email", "domain", None
    reason: Optional[str] = None
    details: Optional[str] = None


class LeadStageUpdate(BaseModel):
    stage: str
    notes: Optional[str] = None


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: str
    details: Dict[str, Any] = {}
    created_at: datetime


class PipelineLeadCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    business_name: str
    industry: str
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    status: str
    score: Optional[int] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    has_draft: bool = False
    draft_status: Optional[str] = None
    is_suppressed: bool = False


class PipelineResponse(BaseModel):
    campaign_id: int
    stages: Dict[str, List[PipelineLeadCard]]
    stage_counts: Dict[str, int]
