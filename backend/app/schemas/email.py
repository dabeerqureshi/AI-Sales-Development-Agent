from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class EmailApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    draft_id: int
    reviewer_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None


class EmailDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    contact_id: Optional[int] = None
    subject: str
    body_text: str
    evidence_citations: List[str] = []
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
    approval: Optional[EmailApprovalResponse] = None


class EmailDraftUpdate(BaseModel):
    subject: Optional[str] = None
    body_text: Optional[str] = None


class DraftReviewRequest(BaseModel):
    notes: Optional[str] = None


class BatchDraftGenerationStats(BaseModel):
    total_candidates: int
    drafts_generated: int
    skipped_count: int
    execution_time_seconds: float


class BatchDraftGenerationResponse(BaseModel):
    campaign_id: int
    status: str
    stats: BatchDraftGenerationStats
    drafts: List[EmailDraftResponse]
