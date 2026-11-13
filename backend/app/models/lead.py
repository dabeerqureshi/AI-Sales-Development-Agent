from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    business_name = Column(String(255), nullable=False, index=True)
    industry = Column(String(100), nullable=False)
    website = Column(String(500), nullable=True)
    phone = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    source = Column(String(100), default="OpenStreetMap/Overpass")
    external_id = Column(String(255), nullable=False, index=True)
    status = Column(String(50), default="discovered")  # discovered, researched, draft_ready, approved, contacted, replied, suppressed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    campaign = relationship("Campaign", back_populates="leads")
    sources = relationship("LeadSource", back_populates="lead", cascade="all, delete-orphan")
    research = relationship("ResearchRecord", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="lead", cascade="all, delete-orphan")
    score = relationship("LeadScore", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    email_drafts = relationship("EmailDraft", back_populates="lead", cascade="all, delete-orphan")
    messages = relationship("EmailMessage", back_populates="lead", cascade="all, delete-orphan")
    followup_tasks = relationship("FollowupTask", back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("campaign_id", "external_id", name="uq_campaign_external_id"),
    )


class LeadSource(Base):
    __tablename__ = "lead_sources"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name = Column(String(100), nullable=False)
    source_url = Column(Text, nullable=False)
    external_id = Column(String(255), nullable=True)
    retrieved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="sources")
