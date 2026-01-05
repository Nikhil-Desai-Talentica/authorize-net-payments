"""Unit tests for database models"""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models.payment import Payment
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.idempotency import IdempotencyKey
from app.models.webhook_event import WebhookEvent


def test_transaction_type_enum():
    """Test TransactionType enum values"""
    assert TransactionType.PURCHASE == "purchase"
    assert TransactionType.AUTHORIZE == "authorize"
    assert TransactionType.CAPTURE == "capture"
    assert TransactionType.REFUND == "refund"
    assert TransactionType.VOID == "void"


def test_transaction_status_enum():
    """Test TransactionStatus enum values"""
    assert TransactionStatus.PENDING == "pending"
    assert TransactionStatus.AUTHORIZED == "authorized"
    assert TransactionStatus.CAPTURED == "captured"
    assert TransactionStatus.REFUNDED == "refunded"
    assert TransactionStatus.VOIDED == "voided"
    assert TransactionStatus.FAILED == "failed"


def test_idempotency_key_expires_at():
    """Test IdempotencyKey expiration calculation"""
    expires_at = IdempotencyKey.create_expires_at(hours=24)
    assert isinstance(expires_at, datetime)
    assert expires_at > datetime.utcnow()


def test_payment_model_structure():
    """Test Payment model has expected attributes"""
    assert hasattr(Payment, "id")
    assert hasattr(Payment, "customer_id")
    assert hasattr(Payment, "payment_method_token")
    assert hasattr(Payment, "billing_address")
    assert hasattr(Payment, "created_at")
    assert hasattr(Payment, "updated_at")


def test_transaction_model_structure():
    """Test Transaction model has expected attributes"""
    assert hasattr(Transaction, "id")
    assert hasattr(Transaction, "payment_id")
    assert hasattr(Transaction, "transaction_type")
    assert hasattr(Transaction, "status")
    assert hasattr(Transaction, "amount")
    assert hasattr(Transaction, "currency")
    assert hasattr(Transaction, "correlation_id")
    assert hasattr(Transaction, "extra_data")  # Note: Python attribute name
    assert hasattr(Transaction, "created_at")
    assert hasattr(Transaction, "updated_at")


def test_webhook_event_model_structure():
    """Test WebhookEvent model has expected attributes"""
    assert hasattr(WebhookEvent, "id")
    assert hasattr(WebhookEvent, "event_type")
    assert hasattr(WebhookEvent, "authorize_net_transaction_id")
    assert hasattr(WebhookEvent, "raw_payload")
    assert hasattr(WebhookEvent, "processed")
    assert hasattr(WebhookEvent, "correlation_id")
    assert hasattr(WebhookEvent, "created_at")

