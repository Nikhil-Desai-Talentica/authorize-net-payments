"""Webhook endpoints"""
import json

from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_db
from app.repositories.payment_repository import PaymentRepository
from app.repositories.webhook_repository import WebhookRepository
from app.utils.authorize_net_webhook import verify_signature
from app.models.transaction import TransactionStatus
from app.core.redis import get_queue
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

router = APIRouter()


def _extract_trans_id(payload: dict) -> str | None:
    """Extract Authorize.Net transaction ID from webhook payload"""
    if not payload:
        return None
    return (
        payload.get("id")
        or payload.get("transId")
        or payload.get("payload", {}).get("id")
        or payload.get("payload", {}).get("transId")
    )


@router.post("/webhooks/authorize-net")
async def authorize_net_webhook(
    request: Request,
    x_authorize_net_signature: str | None = Header(None, alias="X-Authorize-Net-Signature"),
    x_anet_signature: str | None = Header(None, alias="X-ANET-SIGNATURE"),
    db: AsyncSession = Depends(get_db),
):
    """Handle Authorize.Net webhook events"""
    raw_body = await request.body()
    signature = x_authorize_net_signature or x_anet_signature

    if not verify_signature(signature, raw_body, settings.AUTHORIZE_NET_WEBHOOK_SECRET):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_type = payload.get("eventType")
    trans_id = _extract_trans_id(payload)
    correlation_id = payload.get("refId")
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

    webhook_repo = WebhookRepository(db)
    payment_repo = PaymentRepository(db)

    event_record = await webhook_repo.create_event(
        event_type=event_type or "unknown",
        authorize_net_transaction_id=trans_id,
        raw_payload=payload,
        correlation_id=correlation_id,
    )

    error_message = None

    try:
        # enqueue async processing
        queue = get_queue("webhooks")
        queue.enqueue("app.tasks.webhook_tasks.process_webhook_event", str(event_record.id))
        logger.info(
            "Enqueued webhook event",
            event_id=str(event_record.id),
            event_type=event_type,
            correlation_id=correlation_id,
        )
    except Exception as e:
        error_message = str(e)
        logger.exception("Error enqueueing webhook", error=error_message)
        await db.rollback()
        await webhook_repo.mark_processed(event_record, error_message=error_message)
        await db.commit()
        raise

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok"},
    )
    response.headers["X-Correlation-ID"] = correlation_id or request.state.correlation_id or ""
    return response
