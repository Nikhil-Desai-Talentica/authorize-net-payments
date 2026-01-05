"""Repository for webhook event persistence"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.webhook_event import WebhookEvent


class WebhookRepository:
    """Repository to store and update webhook events"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(
        self,
        event_type: str,
        authorize_net_transaction_id: str | None,
        raw_payload: dict,
        correlation_id: str | None = None,
    ) -> WebhookEvent:
        event = WebhookEvent(
            event_type=event_type,
            authorize_net_transaction_id=authorize_net_transaction_id,
            raw_payload=raw_payload,
            correlation_id=correlation_id,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def mark_processed(self, event: WebhookEvent, error_message: str | None = None):
        """Mark a webhook event as processed"""
        event.processed = error_message is None
        event.error_message = error_message
        event.processed_at = datetime.utcnow()
        await self.session.flush()

    async def get_by_id(self, event_id) -> WebhookEvent | None:
        result = await self.session.execute(
            select(WebhookEvent).where(WebhookEvent.id == event_id)
        )
        return result.scalar_one_or_none()
