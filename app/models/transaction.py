"""Transaction model"""
from datetime import datetime
from uuid import uuid4
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class TransactionType(str, PyEnum):
    """Transaction type enum"""

    PURCHASE = "purchase"
    AUTHORIZE = "authorize"
    CAPTURE = "capture"
    REFUND = "refund"
    VOID = "void"


class TransactionStatus(str, PyEnum):
    """Transaction status enum"""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    VOIDED = "voided"
    FAILED = "failed"


class Transaction(Base):
    """Transaction model"""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    transaction_type = Column(
        SQLEnum(TransactionType), nullable=False, index=True
    )
    status = Column(SQLEnum(TransactionStatus), nullable=False, index=True)
    authorize_net_transaction_id = Column(String, nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    customer_id = Column(String, nullable=True, index=True)
    customer_email = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True, index=True)
    extra_data = Column("metadata", JSONB, nullable=True)  # Database column named 'metadata', Python attribute 'extra_data'
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    payment = relationship("Payment", back_populates="transactions")

