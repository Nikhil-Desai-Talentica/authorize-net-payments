# Authorize.Net Payment Service

A web service integrating with Authorize.Net payment service to implement core payment flows.

## Features

- Purchase, Authorize, Capture, Refund, Cancel payment flows
- JWT authentication
- Correlation ID tracing for end-to-end request tracking
- Webhook handlers for async payment events
- Idempotency support
- PostgreSQL storage

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Set up PostgreSQL database:
```bash
createdb authorize_net_payments
```

4. Run migrations (when available):
```bash
alembic upgrade head
```

5. Start the server:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

Run tests:
```bash
uv run pytest
```

Format code:
```bash
uv run black .
uv run ruff check .
```

