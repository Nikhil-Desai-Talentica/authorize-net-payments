"""Integration test for Authorize.Net purchase flow using sandbox credentials"""
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
)


@pytest.mark.integration
def test_purchase_succeeds_with_sandbox_credentials():
    """
    Requires valid sandbox credentials in environment (.env is loaded by settings)
    and RUN_AUTHORIZE_NET_SANDBOX_TESTS=1 to run.
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

    adapter_request = PurchaseRequest(
        amount=Decimal("2.00"),
        credit_card=CreditCard(
            card_number="4111111111111111",  # Authorize.Net sandbox card
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
        invoice_number=f"test-{uuid.uuid4().hex[:12]}",
        description="Integration test purchase",
        line_items=None,
        ref_id="integration-test",
    )

    response = client.purchase(adapter_request)

    assert response.success is True, f"Authorize.Net purchase failed: {response.error_text}"
    assert response.transaction_id
    assert response.result_code == "Ok"
    assert response.response_code == "1"
    assert response.message_code
