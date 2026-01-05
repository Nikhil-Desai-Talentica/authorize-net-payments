"""Webhook event model"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class WebhookEvent(Base):
    """Webhook event model for storing Authorize.Net webhook events"""

    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String, nullable=False, index=True)
    authorize_net_transaction_id = Column(String, nullable=True, index=True)
    raw_payload = Column(JSONB, nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

