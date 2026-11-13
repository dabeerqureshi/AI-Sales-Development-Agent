from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class FollowupTask(Base):
    __tablename__ = "followup_tasks"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_step = Column(Integer, default=2)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="pending")  # pending, executed, cancelled
    cancellation_reason = Column(String(255), nullable=True)  # reply_detected, suppressed, manual_cancel
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="followup_tasks")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    job_type = Column(String(50), nullable=False)  # discovery, research, scoring, draft_gen, worker_cycle
    status = Column(String(50), default="queued")  # queued, running, completed, failed
    progress_pct = Column(Integer, default=0)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    campaign = relationship("Campaign", back_populates="jobs")
