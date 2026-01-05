"""Integration test for Authorize.Net refund flow against sandbox"""
import os
import uuid
from decimal import Decimal

import pytest

from app.adapters.authorize_net.client import AuthorizeNetClient
from app.adapters.authorize_net.models import (
    PurchaseRequest,
    CreditCard,
    CustomerAddress,
    CustomerData,
    RefundRequest,
)


@pytest.mark.integration
def test_capture_then_refund_succeeds_with_sandbox_credentials():
    """
    Runs against Authorize.Net sandbox. Skips unless RUN_AUTHORIZE_NET_SANDBOX_TESTS=1 and
    required credentials are present in the environment (.env loaded by settings).
    """
    required_env = [
        "AUTHORIZE_NET_API_LOGIN_ID",
        "AUTHORIZE_NET_TRANSACTION_KEY",
    ]
    missing = [name for name in required_env if not os.getenv(name)]
    if missing:
        pytest.skip(f"Missing required env vars for Authorize.Net sandbox: {', '.join(missing)}")

    if os.getenv("RUN_AUTHORIZE_NET_SANDBOX_TESTS") != "1":
        pytest.skip("Set RUN_AUTHORIZE_NET_SANDBOX_TESTS=1 to run live Authorize.Net sandbox test")

    client = AuthorizeNetClient()

    amount = Decimal("2.30")
    purchase_request = PurchaseRequest(
        amount=amount,
        credit_card=CreditCard(
            card_number="4111111111111111",
            expiration_date="2035-12",
            card_code="123",
        ),
        customer_address=CustomerAddress(
            first_name="Sandbox",
            last_name="Tester",
            company=None,
            address="14 Main Street",
            city="Pecan Springs",
            state="TX",
            zip="44628",
            country="USA",
        ),
        customer_data=CustomerData(
            customer_id="sandbox-customer",
            email="sandbox@example.com",
        ),
        invoice_number=f"refund-{uuid.uuid4().hex[:10]}",
        description="Integration test purchase then refund",
        line_items=None,
        ref_id="refund-int-purch",
    )

    # Purchase (auth + capture)
    purchase_response = client.purchase(purchase_request)
    assert purchase_response.success is True, f"Purchase failed: {purchase_response.error_text}"
    assert purchase_response.transaction_id
    assert purchase_response.response_code == "1"

    # Refund captured transaction (full amount)
    refund_request = RefundRequest(
        amount=amount,
        transaction_id=purchase_response.transaction_id,
        card_number_last4="1111",
        ref_id="refund-int",
    )
    refund_response = client.refund(refund_request)

    if not refund_response.success and refund_response.error_code == "54":
        pytest.skip("Transaction not yet settled for refund; retry after settlement window")

    assert refund_response.success is True, f"Refund failed: {refund_response.error_text}"
    assert refund_response.transaction_id
    assert refund_response.response_code == "1"
    assert refund_response.result_code == "Ok"
