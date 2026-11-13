from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("email_drafts.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    gmail_message_id = Column(String(255), nullable=False, index=True)
    gmail_thread_id = Column(String(255), nullable=True, index=True)
    direction = Column(String(50), default="outbound")  # outbound, inbound
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    snippet = Column(Text, nullable=True)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="messages")
    draft = relationship("EmailDraft", back_populates="messages")
