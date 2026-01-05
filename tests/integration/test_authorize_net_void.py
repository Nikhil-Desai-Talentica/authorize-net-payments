"""Integration test for Authorize.Net void (cancel) flow against sandbox"""
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
    VoidRequest,
)


@pytest.mark.integration
def test_authorize_then_void_succeeds_with_sandbox_credentials():
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

    amount = Decimal("2.40")
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
        invoice_number=f"void-{uuid.uuid4().hex[:10]}",
        description="Integration test auth then void",
        line_items=None,
        ref_id="void-int-test",
    )

    auth_response = client.authorize(adapter_request)

    assert auth_response.success is True, f"Authorize failed: {auth_response.error_text}"
    assert auth_response.transaction_id
    assert auth_response.result_code == "Ok"
    assert auth_response.response_code == "1"

    void_request = VoidRequest(
        transaction_id=auth_response.transaction_id,
        ref_id="void-int-test-2",
    )

    void_response = client.void(void_request)

    assert void_response.success is True, f"Void failed: {void_response.error_text}"
    assert void_response.transaction_id
    assert void_response.result_code == "Ok"
    assert void_response.response_code == "1"
