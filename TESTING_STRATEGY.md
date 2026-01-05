# Testing Strategy

This document outlines how to validate the payment service across unit, integration, and end-to-end layers, with guidance for Authorize.Net sandbox dependencies and idempotency/correlation concerns.

## Layers
- **Unit tests**: Pure logic and helpers (e.g., webhook signature verification, model conversions). Run fast and offline.
- **Integration tests**: Hit live external services (Authorize.Net sandbox) and real components (DB, Redis). Marked with `@pytest.mark.integration` and gated by env.
- **End-to-end (optional)**: Through the HTTP API against a running stack (compose) with stubbed/mocked upstreams for repeatability; can add contract tests later.

## Current coverage
- `tests/unit`: core models, utils, and adapters (example: `test_webhook_utils.py` for signature validation).
- `tests/integration` (sandbox-gated):
  - `test_authorize_net_purchase.py` — purchase (auth+capture).
  - `test_authorize_net_authorize_capture.py` — auth then capture.
  - `test_authorize_net_void.py` — auth then void.
  - `test_authorize_net_refund.py` — purchase then refund (skips if unsettled).
  - `test_authorize_net_subscription.py` — ARB subscription creation.

## Running tests
- Unit-only (fast, offline): `uv run -m pytest tests/unit -vv`
- All integration (requires sandbox creds + gate):  
  ```bash
  set -a; source .env; set +a
  export RUN_AUTHORIZE_NET_SANDBOX_TESTS=1
  uv run -m pytest -m integration -vv
  ```
- Single integration test: `uv run -m pytest -m integration tests/integration/test_authorize_net_purchase.py -vv`

## Sandbox prerequisites
- Env vars: `AUTHORIZE_NET_API_LOGIN_ID`, `AUTHORIZE_NET_TRANSACTION_KEY`, `AUTHORIZE_NET_ENVIRONMENT=sandbox`, `AUTHORIZE_NET_WEBHOOK_SECRET` (for webhook tests when added).
- Gate: `RUN_AUTHORIZE_NET_SANDBOX_TESTS=1` to avoid accidental live calls.
- Note: Refunds require settled transactions; test will skip on Authorize.Net error 54 if unsettled.

## Idempotency & correlation in tests
- Use distinct `X-Idempotency-Key` per logical test case when exercising API endpoints to assert caching/duplicate handling.
- Assert `X-Correlation-ID` is present on responses; optionally set a custom value to confirm passthrough.

## Webhooks & queue
- Unit: verify signature logic and that invalid signatures are rejected.
- Integration (future): spin up Redis + RQ worker (via docker-compose) and post signed webhook payloads to assert DB status transitions and event processing.

## Database & migrations
- Tests use the configured `DATABASE_URL`. For isolation, point to a test DB or ephemeral schema. Use fixtures to set up/tear down if you add API-level integration tests that write the DB.

## CI recommendations
- Split jobs:
  - `unit` (no network): `uv run -m pytest tests/unit`
  - `integration` (opt-in via env): require sandbox secrets, enable gate.
- Fail fast on lint/format (ruff/black) if added to the pipeline.

## Extending coverage
- Add API-level tests for idempotency behavior (same `X-Idempotency-Key` + body → cached response; mismatched body → 409).
- Add webhook processing integration when a test webhook payload is available; assert DB transaction status updates.
- Add subscription lifecycle tests (pause/cancel) if implemented later.
