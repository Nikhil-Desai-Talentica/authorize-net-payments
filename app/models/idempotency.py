"""Idempotency key model"""
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class IdempotencyKey(Base):
    """Idempotency key model for ensuring idempotent operations"""

    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    idempotency_key = Column(String, unique=True, nullable=False, index=True)
    request_hash = Column(String, nullable=False)
    response_body = Column(JSONB, nullable=True)
    status_code = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @classmethod
    def create_expires_at(cls, hours: int = 24) -> datetime:
        """Create expiration datetime"""
        return datetime.utcnow() + timedelta(hours=hours)

