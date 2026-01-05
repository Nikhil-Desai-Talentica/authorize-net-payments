"""Payment request/response schemas"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from decimal import Decimal
from datetime import date


class CreditCardSchema(BaseModel):
    """Credit card information"""
    card_number: str = Field(..., description="Credit card number", min_length=13, max_length=19)
    expiration_date: str = Field(..., description="Expiration date in format YYYY-MM or MM/YY", pattern=r"^\d{4}-\d{2}$|^\d{2}/\d{2}$")
    card_code: Optional[str] = Field(None, description="CVV code", min_length=3, max_length=4)


class CustomerAddressSchema(BaseModel):
    """Customer billing address"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    company: Optional[str] = Field(None, max_length=50)
    address: str = Field(..., min_length=1, max_length=60)
    city: str = Field(..., min_length=1, max_length=40)
    state: str = Field(..., min_length=2, max_length=40)
    zip: str = Field(..., min_length=1, max_length=20)
    country: str = Field(default="USA", max_length=60)


class LineItemSchema(BaseModel):
    """Line item for transaction"""
    item_id: str = Field(..., max_length=31)
    name: str = Field(..., max_length=31)
    description: str = Field(..., max_length=255)
    quantity: str = Field(..., description="Quantity as string")
    unit_price: str = Field(..., description="Unit price as string")


class PurchaseRequestSchema(BaseModel):
    """Purchase transaction request"""
    amount: Decimal = Field(..., gt=0, description="Transaction amount")
    credit_card: CreditCardSchema
    customer_address: CustomerAddressSchema
    customer_id: str = Field(..., description="Customer identifier")
    customer_email: EmailStr
    invoice_number: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=255)
    line_items: Optional[list[LineItemSchema]] = None


class PurchaseResponseSchema(BaseModel):
    """Purchase transaction response"""
    transaction_id: str
    status: str
    amount: Decimal
    currency: str
    authorize_net_transaction_id: Optional[str] = None
    message: Optional[str] = None
    correlation_id: str


class AuthorizeRequestSchema(PurchaseRequestSchema):
    """Authorize transaction request (auth only)"""
    pass


class AuthorizeResponseSchema(PurchaseResponseSchema):
    """Authorize transaction response"""
    pass


class CaptureRequestSchema(BaseModel):
    """Capture transaction request"""
    amount: Optional[Decimal] = Field(None, gt=0, description="Capture amount (defaults to auth amount)")


class CaptureResponseSchema(PurchaseResponseSchema):
    """Capture transaction response"""
    pass


class VoidRequestSchema(BaseModel):
    """Void transaction request"""
    # Body optional; we use path transaction_id
    pass


class VoidResponseSchema(PurchaseResponseSchema):
    """Void transaction response"""
    pass


class RefundRequestSchema(BaseModel):
    """Refund transaction request"""
    amount: Optional[Decimal] = Field(None, gt=0, description="Refund amount (defaults to captured amount)")
    transaction_id: str = Field(..., description="Captured transaction ID (UUID from this service)")
    card_number_last4: str = Field(..., min_length=4, max_length=4, description="Last 4 digits of card used for payment")


class RefundResponseSchema(PurchaseResponseSchema):
    """Refund transaction response"""
    pass


class SubscriptionScheduleSchema(BaseModel):
    """Subscription schedule"""
    interval_length: int = Field(..., gt=0, description="Interval length (e.g., every 7 days)")
    interval_unit: str = Field(..., pattern="^(days|months)$", description="Interval unit: days or months")
    start_date: date = Field(..., description="Start date for the subscription")
    total_occurrences: int = Field(..., gt=0, description="Total billing occurrences")
    trial_occurrences: int = Field(0, ge=0, description="Trial occurrences")
    trial_amount: Decimal = Field(Decimal("0.00"), ge=0)


class SubscriptionRequestSchema(BaseModel):
    """Subscription creation request"""
    name: str = Field(..., max_length=50)
    amount: Decimal = Field(..., gt=0)
    credit_card: CreditCardSchema
    customer_address: CustomerAddressSchema
    schedule: SubscriptionScheduleSchema


class SubscriptionResponseSchema(BaseModel):
    """Subscription creation response"""
    subscription_id: str | None = None
    status: str
    message_code: str | None = None
    message_text: str | None = None
    error_code: str | None = None
    error_text: str | None = None
    correlation_id: str | None = None
