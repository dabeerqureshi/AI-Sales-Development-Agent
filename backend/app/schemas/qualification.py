from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class LeadScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    overall_score: int
    rule_breakdown: Dict[str, Any]
    verified_facts: List[str]
    potential_opportunity: Optional[str] = None
    unknowns: Optional[str] = None
    recommended_angle: Optional[str] = None
    scored_at: datetime


class BatchQualificationStats(BaseModel):
    total_candidates: int
    qualified_count: int
    skipped_count: int
    average_score: float
    execution_time_seconds: float


class BatchQualificationResponse(BaseModel):
    campaign_id: int
    status: str
    stats: BatchQualificationStats
    scores: List[LeadScoreResponse]
