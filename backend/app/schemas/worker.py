from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class FollowupTaskCreate(BaseModel):
    delay_days: int = 3
    sequence_step: int = 2


class FollowupTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    sequence_step: int
    scheduled_date: datetime
    status: str
    cancellation_reason: Optional[str] = None
    created_at: datetime
    business_name: Optional[str] = None
    recipient_email: Optional[str] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: Optional[int] = None
    job_type: str
    status: str
    progress_pct: int
    error_details: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class WorkerCycleResponse(BaseModel):
    job_id: int
    status: str
    replies_detected: int
    tasks_processed: int
    tasks_cancelled: int
    execution_time_seconds: float


class SimulateReplyRequest(BaseModel):
    snippet: str = "Hi, thanks for reaching out. We would be open to a quick demo call."
