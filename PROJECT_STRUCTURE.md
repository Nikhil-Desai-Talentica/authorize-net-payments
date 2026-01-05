# Project Structure

- `app/` — application code
  - `main.py` — FastAPI app setup and router inclusion
  - `core/` — configuration, database/redis setup, security, logging
  - `api/v1/` — HTTP layer (routes, schemas, dependencies)
    - `routes/` — payments, transactions, webhooks
    - `schemas/` — request/response models
  - `adapters/authorize_net/` — Authorize.Net client, models, exceptions
  - `services/` — business logic (payments, webhooks)
  - `repositories/` — DB persistence helpers
  - `middleware/` — correlation ID, error handling
  - `utils/` — helpers (e.g., webhook signature verification)
- `scripts/` — helper entrypoints (e.g., `rq_worker.py` for RQ worker)
- `tests/` — unit and integration tests (sandbox-gated for Authorize.Net)
- `Dockerfile` — service image definition
- `docker-compose.yml` — local stack (api, worker, Postgres, Redis)
- `pyproject.toml`, `uv.lock` — dependencies and lockfile
- `README.md` — setup and usage guide
