# Test Report

Current test execution was not run in this environment (network-restricted). Below is the status of the existing suites and guidance to run them.

## Suites
- **Unit**: logic and utilities (e.g., webhook signature verification).
- **Integration (sandbox)**: Authorize.Net end-to-end flows (purchase, authorize/capture, void, refund, subscription). Gated by `RUN_AUTHORIZE_NET_SANDBOX_TESTS=1` and require sandbox credentials.

## What to run
- Unit only:  
  `uv run -m pytest tests/unit -vv`
- All integration (live sandbox):  
  ```bash
  set -a; source .env; set +a
  export RUN_AUTHORIZE_NET_SANDBOX_TESTS=1
  uv run -m pytest -m integration -vv
  ```
- Single integration examples:  
  `uv run -m pytest -m integration tests/integration/test_authorize_net_purchase.py -vv`

## Notes & outcomes
- Refund tests may skip if the referenced transaction is not yet settled (Authorize.Net error 54). Re-run after settlement or use a previously settled transaction.
- Webhook processing tests are not present yet; webhooks are exercised manually or can be added later with Redis + RQ worker running.

## Environment prerequisites
- `.env` with Authorize.Net sandbox credentials and `AUTHORIZE_NET_ENVIRONMENT=sandbox`.
- Gate variable: `RUN_AUTHORIZE_NET_SANDBOX_TESTS=1` for integration tests.
- Redis/Postgres running if you add API-level integration or webhook queue tests (compose provides both).
