"""Authorize.Net adapter models"""
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import date


@dataclass
class CreditCard:
    """Credit card information"""
    card_number: str
    expiration_date: str  # Format: "YYYY-MM" or "MM/YY"
    card_code: Optional[str] = None  # CVV


@dataclass
class CustomerAddress:
    """Customer billing address"""
    first_name: str
    last_name: str
    address: str
    city: str
    state: str
    zip: str
    country: str = "USA"
    company: Optional[str] = None


@dataclass
class CustomerData:
    """Customer identifying information"""
    customer_id: str
    email: str
    customer_type: str = "individual"


@dataclass
class LineItem:
    """Line item for transaction"""
    item_id: str
    name: str
    description: str
    quantity: str
    unit_price: str


@dataclass
class PurchaseRequest:
    """Purchase transaction request"""
    amount: Decimal
    credit_card: CreditCard
    customer_address: CustomerAddress
    customer_data: CustomerData
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    line_items: Optional[list[LineItem]] = None
    duplicate_window: int = 600  # seconds
    ref_id: Optional[str] = None


@dataclass
class CaptureRequest:
    """Capture (prior auth) transaction request"""
    amount: Decimal
    transaction_id: str
    ref_id: Optional[str] = None


@dataclass
class VoidRequest:
    """Void (cancel) transaction request for unsettled auth"""
    transaction_id: str
    ref_id: Optional[str] = None


@dataclass
class RefundRequest:
    """Refund transaction request"""
    amount: Decimal
    transaction_id: str
    card_number_last4: str
    ref_id: Optional[str] = None


@dataclass
class SubscriptionSchedule:
    """Subscription schedule details"""
    interval_length: int
    interval_unit: str  # "days" or "months"
    start_date: date
    total_occurrences: int
    trial_occurrences: int = 0
    trial_amount: Decimal = Decimal("0.00")


@dataclass
class SubscriptionRequest:
    """Subscription creation request"""
    name: str
    amount: Decimal
    credit_card: CreditCard
    customer_address: CustomerAddress
    schedule: SubscriptionSchedule
    ref_id: Optional[str] = None


@dataclass
class SubscriptionResponse:
    """Subscription creation response"""
    subscription_id: Optional[str] = None
    result_code: Optional[str] = None
    message_code: Optional[str] = None
    message_text: Optional[str] = None
    error_code: Optional[str] = None
    error_text: Optional[str] = None
    success: bool = False


@dataclass
class TransactionResponse:
    """Transaction response from Authorize.Net"""
    transaction_id: Optional[str] = None
    response_code: Optional[str] = None
    message_code: Optional[str] = None
    message_description: Optional[str] = None
    error_code: Optional[str] = None
    error_text: Optional[str] = None
    result_code: Optional[str] = None
    success: bool = False
