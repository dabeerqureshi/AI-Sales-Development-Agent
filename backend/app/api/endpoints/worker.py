from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.lead import Lead
from app.schemas.worker import (
    FollowupTaskCreate,
    FollowupTaskResponse,
    JobResponse,
    SimulateReplyRequest,
    WorkerCycleResponse,
)
from app.services.worker_service import worker_service

router = APIRouter()


@router.post("/leads/{lead_id}/followup", response_model=FollowupTaskResponse)
def schedule_lead_followup(
    lead_id: int,
    payload: FollowupTaskCreate = FollowupTaskCreate(),
    db: Session = Depends(get_db),
) -> FollowupTaskResponse:
    """Schedule an automated follow-up task for a lead."""
    try:
        task = worker_service.schedule_followup(
            lead_id=lead_id,
            delay_days=payload.delay_days,
            sequence_step=payload.sequence_step,
            db=db,
        )
        lead = db.get(Lead, lead_id)
        return FollowupTaskResponse(
            id=task.id,
            lead_id=task.lead_id,
            sequence_step=task.sequence_step,
            scheduled_date=task.scheduled_date,
            status=task.status,
            cancellation_reason=task.cancellation_reason,
            created_at=task.created_at,
            business_name=lead.business_name if lead else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/followups", response_model=List[FollowupTaskResponse])
def list_scheduled_followups(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[FollowupTaskResponse]:
    """Retrieve all follow-up tasks with optional status filter."""
    items = worker_service.list_followups(db=db, status_filter=status_filter, limit=limit)
    return [FollowupTaskResponse(**item) for item in items]


@router.post("/followups/{task_id}/cancel", response_model=FollowupTaskResponse)
def cancel_scheduled_followup(
    task_id: int,
    reason: str = Query("manual_cancel"),
    db: Session = Depends(get_db),
) -> FollowupTaskResponse:
    """Cancel a pending follow-up task."""
    try:
        task = worker_service.cancel_followup(task_id=task_id, reason=reason, db=db)
        lead = db.get(Lead, task.lead_id)
        return FollowupTaskResponse(
            id=task.id,
            lead_id=task.lead_id,
            sequence_step=task.sequence_step,
            scheduled_date=task.scheduled_date,
            status=task.status,
            cancellation_reason=task.cancellation_reason,
            created_at=task.created_at,
            business_name=lead.business_name if lead else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/leads/{lead_id}/simulate-reply")
def simulate_lead_reply(
    lead_id: int,
    payload: SimulateReplyRequest = SimulateReplyRequest(),
    db: Session = Depends(get_db),
):
    """
    Simulate an inbound email reply from a prospect.
    Enforces the STOP SEQUENCE RULE: Cancels all pending follow-up tasks
    and transitions lead stage to 'replied'.
    """
    try:
        result = worker_service.process_inbound_reply(
            lead_id=lead_id,
            snippet=payload.snippet,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/worker/run-cycle", response_model=WorkerCycleResponse)
async def run_worker_cycle_endpoint(
    campaign_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> WorkerCycleResponse:
    """Trigger background worker cycle to poll due follow-ups and verify suppression."""
    res = await worker_service.execute_worker_cycle(campaign_id=campaign_id, db=db)
    return WorkerCycleResponse(**res)


@router.get("/jobs", response_model=List[JobResponse])
def get_background_jobs_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[JobResponse]:
    """Retrieve history of background execution jobs."""
    jobs = worker_service.list_jobs(db=db, limit=limit)
    return [JobResponse.model_validate(j) for j in jobs]
