from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class ResearchRecord(Base):
    __tablename__ = "research_records"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    crawled_url = Column(Text, nullable=False)
    page_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    services_summary = Column(Text, nullable=True)
    booking_system_found = Column(Boolean, default=False)
    booking_system_name = Column(String(100), nullable=True)
    has_custom_booking_form = Column(Boolean, default=False)
    after_hours_info = Column(Text, nullable=True)
    extracted_text_snippet = Column(Text, nullable=True)
    raw_metadata = Column(JSON, default=dict)
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="research")
