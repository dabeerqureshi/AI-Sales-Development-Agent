from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.models.base import Base


class SuppressionEntry(Base):
    __tablename__ = "suppression_list"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    domain = Column(String(255), nullable=True, index=True)
    reason = Column(String(100), default="unsubscribed")  # unsubscribed, bounced, manual_block, competitor
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False)  # lead, campaign, draft, suppression
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(100), nullable=False)  # stage_change, approved, suppressed, researched, draft_created
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
