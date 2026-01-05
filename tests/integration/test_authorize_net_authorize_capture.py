"""Integration test for Authorize.Net authorize then capture flow (sandbox)"""
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
    CaptureRequest,
)


@pytest.mark.integration
def test_authorize_then_capture_succeeds_with_sandbox_credentials():
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

    amount = Decimal("2.50")
    adapter_request = PurchaseRequest(
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
        invoice_number=f"auth-{uuid.uuid4().hex[:10]}",
        description="Integration test auth only",
        line_items=None,
        ref_id="auth-int-test",
    )

    auth_response = client.authorize(adapter_request)

    assert auth_response.success is True, f"Authorize failed: {auth_response.error_text}"
    assert auth_response.transaction_id
    assert auth_response.result_code == "Ok"
    assert auth_response.response_code == "1"

    capture_request = CaptureRequest(
        amount=amount,
        transaction_id=auth_response.transaction_id,
        ref_id="integration-test-capture",
    )

    capture_response = client.capture(capture_request)

    assert capture_response.success is True, f"Capture failed: {capture_response.error_text}"
    assert capture_response.transaction_id
    assert capture_response.result_code == "Ok"
    assert capture_response.response_code == "1"
