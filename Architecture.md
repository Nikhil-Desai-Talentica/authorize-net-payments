# Architecture Overview

## Components
- **FastAPI API** (`app/main.py` + `app/api/v1/routes`) — exposes payment flows and webhooks.
- **Service layer** (`app/services/`) — orchestrates business logic, validation, persistence, and calls to adapters.
- **Authorize.Net adapter** (`app/adapters/authorize_net/`) — wraps Authorize.Net SDK for purchase, authorize, capture, void, refund, and ARB subscription creation. Normalizes responses and enforces refId truncation.
- **Persistence**:
  - PostgreSQL (via SQLAlchemy async) for payments, transactions, webhook events, idempotency keys.
  - Repositories encapsulate reads/writes (`app/repositories/`).
- **Queue/worker**:
  - Redis + RQ queue for webhook processing.
  - Worker entrypoint at `scripts/rq_worker.py`; tasks in `app/tasks/webhook_tasks.py`; processing logic in `app/services/webhook_service.py`.
- **Middleware**:
  - Correlation ID middleware adds/propagates `X-Correlation-ID` and binds to logs.
  - Error handling middleware (existing) for consistent responses.
- **Utilities**:
  - Webhook signature verification (`app/utils/authorize_net_webhook.py`).

## Data flow (happy-path examples)
- **Purchase (auth + capture)**:
  1. API `/payments/purchase` → service `process_purchase`.
  2. DB: create payment + pending transaction.
  3. Adapter `purchase` → Authorize.Net `authCaptureTransaction`.
  4. DB: update transaction to `captured`; return response with correlation ID and Authorize.Net transaction ID.
  5. Idempotency: request cached/validated via `IdempotencyService`; refId uses idempotency key or correlation ID to avoid duplicates upstream.

- **Authorize → Capture**:
  1. `/payments/authorize` → create payment + pending auth transaction → adapter `authOnlyTransaction`.
  2. `/payments/capture/{transaction_id}` → validate auth state → adapter `priorAuthCaptureTransaction` → update to `captured`.

- **Void (cancel before settlement)**:
  - `/payments/cancel/{transaction_id}` → validate state → adapter `voidTransaction` → update to `voided`.

- **Refund (settled captures)**:
  - `/payments/refund/{transaction_id}` (needs amount and last4) → adapter `refundTransaction` → update to `refunded`. Skips or errors if unsettled (Authorize.Net 54).

- **Subscriptions (ARB)**:
  - `/payments/subscriptions` → adapter `create_subscription` using schedule/payment/billing details → returns subscription ID.

- **Webhooks**:
  1. Authorize.Net posts to `/webhooks/authorize-net` with HMAC-SHA512 signature.
  2. Route verifies signature, stores event, enqueues RQ job.
  3. Worker fetches event, updates matching transaction status based on event type (`authorized`, `captured`, `voided`, `refunded`), marks event processed.

## Observability & Idempotency
- `X-Correlation-ID` propagated on all responses and bound in logs; webhook processing also binds `refId` if present.
- Idempotency keys supported on payment endpoints; cached responses via DB; upstream refId set to idempotency key (or correlation ID) to prevent double charges within Authorize.Net duplicate window.

## Local stack
- `docker-compose.yml` brings up API, worker, Postgres, and Redis. API and worker share the same image and code volume. Redis backs RQ queue; Postgres stores domain data and webhook events.
