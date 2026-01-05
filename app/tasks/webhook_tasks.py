"""RQ tasks for webhook processing"""
import asyncio
import structlog

from app.core.database import AsyncSessionLocal
from app.services.webhook_service import WebhookService

logger = structlog.get_logger()


def process_webhook_event(event_id: str):
    """Entry point for RQ worker to process a webhook event."""

    async def _run():
        async with AsyncSessionLocal() as session:
            service = WebhookService(session)
            await service.process_event(event_id)

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.exception("Webhook task failed", event_id=event_id, error=str(e))
        raise
