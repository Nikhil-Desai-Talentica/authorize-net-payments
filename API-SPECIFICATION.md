# API Specification (v1)

Base prefix: `/api/v1`
Auth: Bearer JWT required for payment endpoints. Webhook endpoint is unsigned except for Authorize.Net HMAC check.
Headers: `X-Correlation-ID` optional in request; always returned in responses. Idempotency: `X-Idempotency-Key` supported on payment endpoints.

## Health
- `GET /health` → `200 {"status":"healthy"}` plus `X-Correlation-ID`.

## Payments
### Purchase (auth + capture)
- `POST /payments/purchase`
- Body: `{ amount, credit_card{card_number, expiration_date, card_code?}, customer_address{first_name,last_name,address,city,state,zip,country?,company?}, customer_id, customer_email, invoice_number?, description?, line_items?[{item_id,name,description,quantity,unit_price}] }`
- Response: `{ transaction_id, status:"captured", amount, currency, authorize_net_transaction_id?, message?, correlation_id }`

### Authorize (hold only)
- `POST /payments/authorize`
- Body: same as Purchase.
- Response: `{ transaction_id, status:"authorized", ... }`

### Capture (after authorize)
- `POST /payments/capture/{transaction_id}`
- Body: `{ amount? }` (defaults to authorized amount)
- Response: `{ transaction_id, status:"captured", amount, currency, authorize_net_transaction_id?, message?, correlation_id }`

### Void (cancel before settlement)
- `POST /payments/cancel/{transaction_id}`
- Body: none
- Response: `{ transaction_id, status:"voided", amount, currency, authorize_net_transaction_id?, message?, correlation_id }`

### Refund (settled captures)
- `POST /payments/refund/{transaction_id}`
- Body: `{ amount?, card_number_last4 }` (amount defaults to captured amount)
- Response: `{ transaction_id, status:"refunded", amount, currency, authorize_net_transaction_id?, message?, correlation_id }`

### Subscriptions (ARB)
- `POST /payments/subscriptions`
- Body: `{ name, amount, credit_card{...}, customer_address{...}, schedule{interval_length, interval_unit:"days"|"months", start_date, total_occurrences, trial_occurrences?, trial_amount?} }`
- Response: `{ subscription_id, status:"active", message_code?, message_text?, correlation_id }`

## Webhooks
- `POST /webhooks/authorize-net`
- Headers: `X-ANET-SIGNATURE` (or `X-Authorize-Net-Signature`) with `SHA512=<hmac>` using `AUTHORIZE_NET_WEBHOOK_SECRET`.
- Body: Authorize.Net event payload.
- Behavior: verifies signature, stores event, enqueues async processing; returns `{"status":"ok"}` with `X-Correlation-ID` (from `refId` if provided).

## Idempotency & Correlation
- `X-Idempotency-Key`: caches request/response per body; reused key with different body returns 409.
- `refId` to Authorize.Net uses idempotency key or correlation ID to avoid duplicate upstream charges within duplicate window.
- `X-Correlation-ID`: pass through for tracing; generated if absent. Included on all responses and bound into logs, including webhooks when `refId` exists.
