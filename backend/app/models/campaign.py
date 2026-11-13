from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False)
    max_leads = Column(Integer, default=50)
    website_required = Column(Boolean, default=False)
    phone_required = Column(Boolean, default=False)
    status = Column(String(50), default="draft")  # draft, running, completed, paused
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    leads = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="campaign", cascade="all, delete-orphan")
