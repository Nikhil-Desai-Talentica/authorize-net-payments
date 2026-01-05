"""Payment model"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Payment(Base):
    """Payment model"""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(String, nullable=False, index=True)
    payment_method_token = Column(String, nullable=True)  # Encrypted if stored
    billing_address = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    transactions = relationship("Transaction", back_populates="payment")

