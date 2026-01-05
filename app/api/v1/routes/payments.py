"""Payment endpoints"""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_current_user, get_idempotency_key, get_correlation_id
from app.api.v1.schemas.payment import (
    PurchaseRequestSchema,
    PurchaseResponseSchema,
    AuthorizeRequestSchema,
    AuthorizeResponseSchema,
    CaptureRequestSchema,
    CaptureResponseSchema,
    VoidRequestSchema,
    VoidResponseSchema,
    RefundRequestSchema,
    RefundResponseSchema,
    SubscriptionRequestSchema,
    SubscriptionResponseSchema,
)
from app.core.database import get_db
from app.services.payment_service import PaymentService
from app.services.idempotency_service import IdempotencyService
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

router = APIRouter()

@router.post("/payments/subscriptions", response_model=SubscriptionResponseSchema)
async def create_subscription(
    subscription_request: SubscriptionRequestSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> SubscriptionResponseSchema:
    """Create a recurring subscription"""
    correlation_id = get_correlation_id(request)

    idempotency_service = IdempotencyService(db)
    request_body = subscription_request.model_dump()

    if idempotency_key:
        cached_response = await idempotency_service.check_idempotency(
            idempotency_key, request_body
        )
        if cached_response:
            logger.info(
                "Returning cached idempotent response",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=cached_response["status_code"],
                content=cached_response["response_body"],
                headers={"X-Correlation-ID": correlation_id},
            )

    try:
        payment_service = PaymentService(db)
        result = await payment_service.process_create_subscription(
            subscription_request, correlation_id, idempotency_key=idempotency_key
        )

        if idempotency_key:
            await idempotency_service.store_idempotency(
                idempotency_key=idempotency_key,
                request_body=request_body,
                response_body=result,
                status_code=status.HTTP_200_OK,
            )
            await db.commit()

        return SubscriptionResponseSchema(**result)

    except ValueError as e:
        await db.rollback()
        logger.error(
            "Idempotency key error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Subscription creation error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}",
        )


@router.post("/payments/purchase", response_model=PurchaseResponseSchema)
async def purchase(
    purchase_request: PurchaseRequestSchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
):
    """Process a purchase transaction (authorize + capture in one step)"""
    correlation_id = get_correlation_id(request)

    # Check idempotency
    idempotency_service = IdempotencyService(db)
    request_body = purchase_request.model_dump()

    if idempotency_key:
        cached_response = await idempotency_service.check_idempotency(
            idempotency_key, request_body
        )
        if cached_response:
            logger.info(
                "Returning cached idempotent response",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=cached_response["status_code"],
                content=cached_response["response_body"],
                headers={"X-Correlation-ID": correlation_id},
            )

    try:
        # Process purchase
        payment_service = PaymentService(db)
        result = await payment_service.process_purchase(
            purchase_request, correlation_id, idempotency_key=idempotency_key
        )

        # Store idempotency key if provided
        if idempotency_key:
            await idempotency_service.store_idempotency(
                idempotency_key=idempotency_key,
                request_body=request_body,
                response_body=result,
                status_code=status.HTTP_200_OK,
            )
            await db.commit()

        return PurchaseResponseSchema(**result)

    except ValueError as e:
        # Idempotency key mismatch
        await db.rollback()
        logger.error(
            "Idempotency key error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Purchase transaction error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process purchase: {str(e)}",
        )


@router.post("/payments/authorize", response_model=AuthorizeResponseSchema)
async def authorize(
    authorize_request: AuthorizeRequestSchema,
    request: Request,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
) -> AuthorizeResponseSchema:
    """Authorize endpoint"""
    correlation_id = get_correlation_id(request)

    idempotency_service = IdempotencyService(db)
    request_body = authorize_request.model_dump()

    if idempotency_key:
        cached_response = await idempotency_service.check_idempotency(
            idempotency_key, request_body
        )
        if cached_response:
            logger.info(
                "Returning cached idempotent response",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=cached_response["status_code"],
                content=cached_response["response_body"],
                headers={"X-Correlation-ID": correlation_id},
            )

    try:
        payment_service = PaymentService(db)
        result = await payment_service.process_authorize(
            authorize_request, correlation_id, idempotency_key=idempotency_key
        )

        if idempotency_key:
            await idempotency_service.store_idempotency(
                idempotency_key=idempotency_key,
                request_body=request_body,
                response_body=result,
                status_code=status.HTTP_200_OK,
            )
            await db.commit()

        return AuthorizeResponseSchema(**result)

    except ValueError as e:
        await db.rollback()
        logger.error(
            "Idempotency key error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Authorization transaction error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authorize: {str(e)}",
        )


@router.post("/payments/capture/{transaction_id}", response_model=CaptureResponseSchema)
async def capture(
    transaction_id: str,
    capture_request: CaptureRequestSchema,
    request: Request,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
) -> CaptureResponseSchema:
    """Capture endpoint"""
    correlation_id = get_correlation_id(request)

    idempotency_service = IdempotencyService(db)
    request_body = capture_request.model_dump()
    request_body["transaction_id"] = transaction_id

    if idempotency_key:
        cached_response = await idempotency_service.check_idempotency(
            idempotency_key, request_body
        )
        if cached_response:
            logger.info(
                "Returning cached idempotent response",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=cached_response["status_code"],
                content=cached_response["response_body"],
                headers={"X-Correlation-ID": correlation_id},
            )

    try:
        payment_service = PaymentService(db)
        result = await payment_service.process_capture(
            transaction_id, capture_request, correlation_id, idempotency_key=idempotency_key
        )

        if idempotency_key:
            await idempotency_service.store_idempotency(
                idempotency_key=idempotency_key,
                request_body=request_body,
                response_body=result,
                status_code=status.HTTP_200_OK,
            )
            await db.commit()

        return CaptureResponseSchema(**result)

    except ValueError as e:
        await db.rollback()
        logger.error(
            "Idempotency or validation error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Capture transaction error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to capture: {str(e)}",
        )


@router.post("/payments/refund/{transaction_id}", response_model=RefundResponseSchema)
async def refund(
    transaction_id: str,
    refund_request: RefundRequestSchema,
    request: Request,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
) -> RefundResponseSchema:
    """Refund endpoint"""
    correlation_id = get_correlation_id(request)

    idempotency_service = IdempotencyService(db)
    request_body = refund_request.model_dump()
    request_body["transaction_id"] = transaction_id

    if idempotency_key:
        cached_response = await idempotency_service.check_idempotency(
            idempotency_key, request_body
        )
        if cached_response:
            logger.info(
                "Returning cached idempotent response",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=cached_response["status_code"],
                content=cached_response["response_body"],
                headers={"X-Correlation-ID": correlation_id},
            )

    try:
        payment_service = PaymentService(db)
        result = await payment_service.process_refund(
            transaction_id, refund_request, correlation_id, idempotency_key=idempotency_key
        )

        if idempotency_key:
            await idempotency_service.store_idempotency(
                idempotency_key=idempotency_key,
                request_body=request_body,
                response_body=result,
                status_code=status.HTTP_200_OK,
            )
            await db.commit()

        return RefundResponseSchema(**result)

    except ValueError as e:
        await db.rollback()
        logger.error(
            "Idempotency or validation error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Refund transaction error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund: {str(e)}",
        )


@router.post("/payments/cancel/{transaction_id}", response_model=VoidResponseSchema)
async def cancel(
    transaction_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db),
):
    """Cancel/Void endpoint"""
    correlation_id = get_correlation_id(request)

    idempotency_service = IdempotencyService(db)
    request_body = {"transaction_id": transaction_id}

    if idempotency_key:
        cached_response = await idempotency_service.check_idempotency(
            idempotency_key, request_body
        )
        if cached_response:
            logger.info(
                "Returning cached idempotent response",
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=cached_response["status_code"],
                content=cached_response["response_body"],
                headers={"X-Correlation-ID": correlation_id},
            )

    try:
        payment_service = PaymentService(db)
        result = await payment_service.process_void(
            transaction_id, correlation_id, idempotency_key=idempotency_key
        )

        if idempotency_key:
            await idempotency_service.store_idempotency(
                idempotency_key=idempotency_key,
                request_body=request_body,
                response_body=result,
                status_code=status.HTTP_200_OK,
            )
            await db.commit()

        return VoidResponseSchema(**result)

    except ValueError as e:
        await db.rollback()
        logger.error(
            "Idempotency or validation error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Void transaction error",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to void: {str(e)}",
        )
