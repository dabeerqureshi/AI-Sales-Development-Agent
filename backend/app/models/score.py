from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    overall_score = Column(Integer, nullable=False)
    rule_breakdown = Column(JSON, nullable=False, default=dict)
    verified_facts = Column(JSON, nullable=False, default=list)
    potential_opportunity = Column(Text, nullable=True)
    unknowns = Column(Text, nullable=True)
    recommended_angle = Column(Text, nullable=True)
    scored_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="score")
