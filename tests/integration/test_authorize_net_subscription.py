"""Integration test for Authorize.Net subscription creation (ARB) against sandbox"""
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.adapters.authorize_net.client import AuthorizeNetClient
from app.adapters.authorize_net.models import (
    SubscriptionRequest,
    SubscriptionSchedule,
    CreditCard,
    CustomerAddress,
)


@pytest.mark.integration
def test_create_subscription_succeeds_with_sandbox_credentials():
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

    schedule = SubscriptionSchedule(
        interval_length=7,
        interval_unit="days",
        start_date=date.today() + timedelta(days=1),
        total_occurrences=12,
        trial_occurrences=1,
        trial_amount=Decimal("0.00"),
    )

    subscription_request = SubscriptionRequest(
        name=f"Sandbox Sub {uuid.uuid4().hex[:6]}",
        amount=Decimal("2.00"),
        credit_card=CreditCard(
            card_number="4111111111111111",
            expiration_date="2035-12",
            card_code="123",
        ),
        customer_address=CustomerAddress(
            first_name="John",
            last_name="Smith",
            address="14 Main Street",
            city="Pecan Springs",
            state="TX",
            zip="44628",
            country="USA",
        ),
        schedule=schedule,
        ref_id="sub-int-test",
    )

    response = client.create_subscription(subscription_request)

    assert response.success is True, f"Subscription failed: {response.error_text}"
    assert response.subscription_id
    assert response.result_code == "Ok"
