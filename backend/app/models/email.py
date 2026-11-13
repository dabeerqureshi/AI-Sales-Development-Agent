from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=False)
    evidence_citations = Column(JSON, default=list)
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft")  # draft, approved, rejected, sent
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    lead = relationship("Lead", back_populates="email_drafts")
    contact = relationship("Contact")
    approval = relationship("EmailApproval", back_populates="draft", uselist=False, cascade="all, delete-orphan")
    messages = relationship("EmailMessage", back_populates="draft")


class EmailApproval(Base):
    __tablename__ = "email_approvals"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("email_drafts.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    reviewer_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    draft = relationship("EmailDraft", back_populates="approval")
