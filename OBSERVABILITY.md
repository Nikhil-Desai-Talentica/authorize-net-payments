# Observability

This project traces requests end-to-end, logs structured events with correlation IDs, and is ready to expose metrics. Below is the recommended setup and key signals to capture.

## Logging & Tracing
- **Correlation ID**: `X-Correlation-ID` is accepted on incoming requests and returned on all responses (including webhooks). Middleware binds it to `structlog` contextvars. Webhooks also bind `refId` as correlation ID when provided.
- **Structured logs**: All logs use `structlog`; include `correlation_id`, `transaction_id`, `authorize_net_transaction_id` where relevant. Adapter/service layers log successes and failures for each flow (purchase, authorize, capture, void, refund, subscription, webhook).
- **Upstream refId**: Authorize.Net `refId` uses idempotency key (if provided) or correlation ID to make retries traceable and reduce duplicates.
- **Recommended tracing backend**: Wrap `structlog` with an exporter to your APM (e.g., OpenTelemetry + OTLP). Propagate `X-Correlation-ID` as trace/span attribute.

## Metrics (suggested)
- **API**:
  - `http_requests_total{path,method,status}` / latency histogram `http_request_duration_seconds{path,method}`.
  - `http_requests_idempotent_hits_total` for cached idempotent responses.
- **Payments (Authorize.Net)**:
  - `payments_requests_total{flow=purchase|authorize|capture|void|refund|subscription, outcome=success|fail}`.
  - `payments_duration_seconds{flow,...}` (histogram).
  - `payments_upstream_failures_total{flow,error_code}` capturing Authorize.Net error codes.
- **DB**:
  - `db_txn_status_total{status}` counts of transaction state transitions (pending/authorized/captured/voided/refunded/failed).
- **Queue/Worker (RQ)**:
  - `webhook_jobs_enqueued_total`.
  - `webhook_jobs_processed_total{outcome=success|fail}` and `webhook_job_duration_seconds`.
  - `webhook_jobs_retried_total`.
- **Webhooks**:
  - `webhook_events_total{event_type,outcome=processed|skipped|invalid_signature}`.
  - `webhook_signature_failures_total`.
  - `webhook_missing_txn_total` when no matching local transaction is found.
- **Subscriptions**:
  - `subscriptions_created_total{outcome=success|fail}`.

## Where to hook metrics
- Add a metrics middleware (e.g., Prometheus FastAPI instrumentor) to expose `/metrics`.
- Instrument service methods for each payment flow and webhook processing. Use decorators or context managers to time operations and increment counters.
- RQ worker: wrap `process_webhook_event` task to emit counters and durations.

## Alerting ideas
- High rate of upstream failures (`payments_upstream_failures_total`).
- Webhook signature failures spike.
- Job queue lag increasing (depth of `webhooks` queue).
- Database errors or frequent transaction rollbacks.

## Log fields to include
- `correlation_id`, `transaction_id` (internal UUID), `authorize_net_transaction_id` (external), `flow` (purchase/authorize/capture/void/refund/subscription/webhook), `event_type` (for webhooks), `status`, `error_code`, `error_text`, `idempotency_key` (when present).
