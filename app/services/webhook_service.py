"""Service for processing Authorize.Net webhook events"""
import structlog
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.payment_repository import PaymentRepository
from app.repositories.webhook_repository import WebhookRepository
from app.models.transaction import TransactionStatus

logger = structlog.get_logger()


class WebhookService:
    """Processes webhook events asynchronously"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.webhook_repo = WebhookRepository(session)

    async def process_event(self, event_id: str):
        """Load and process a webhook event by ID"""
        event_uuid = UUID(event_id)
        event = await self.webhook_repo.get_by_id(event_uuid)
        if not event:
            logger.warning("Webhook event not found", event_id=event_id)
            return

        if event.processed:
            logger.info("Webhook event already processed", event_id=event_id)
            return

        correlation_id = event.correlation_id
        if correlation_id:
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        payload = event.raw_payload
        event_type = payload.get("eventType")
        trans_id = (
            payload.get("id")
            or payload.get("transId")
            or payload.get("payload", {}).get("id")
            or payload.get("payload", {}).get("transId")
        )

        error_message = None

        try:
            status_map = {
                "net.authorize.payment.authcapture.created": TransactionStatus.CAPTURED,
                "net.authorize.payment.authorization.created": TransactionStatus.AUTHORIZED,
                "net.authorize.payment.void.created": TransactionStatus.VOIDED,
                "net.authorize.payment.refund.created": TransactionStatus.REFUNDED,
            }

            if event_type in status_map and trans_id:
                txn = await self.payment_repo.get_transaction_by_authorize_net_id(trans_id)
                if txn:
                    await self.payment_repo.update_transaction_status(
                        transaction_id=txn.id,
                        status=status_map[event_type],
                        authorize_net_transaction_id=trans_id,
                        extra_data={"webhook_event_id": str(event.id)},
                    )
                    await self.session.commit()
                    logger.info(
                        "Updated transaction from webhook",
                        transaction_id=str(txn.id),
                        event_type=event_type,
                        authorize_net_transaction_id=trans_id,
                    )
                else:
                    logger.warning(
                        "Transaction not found for webhook",
                        event_type=event_type,
                        authorize_net_transaction_id=trans_id,
                    )
            else:
                logger.info("Unhandled webhook event type", event_type=event_type)

        except Exception as e:
            error_message = str(e)
            logger.exception("Error processing webhook", error=error_message)
            await self.session.rollback()

        await self.webhook_repo.mark_processed(event, error_message=error_message)
        await self.session.commit()
