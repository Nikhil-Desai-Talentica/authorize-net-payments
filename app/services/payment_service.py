"""Payment service for business logic"""
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.authorize_net.client import AuthorizeNetClient
from app.adapters.authorize_net.models import (
    PurchaseRequest as AdapterPurchaseRequest,
    CreditCard,
    CustomerAddress,
    CustomerData,
    LineItem,
    CaptureRequest as AdapterCaptureRequest,
    VoidRequest as AdapterVoidRequest,
    RefundRequest as AdapterRefundRequest,
    SubscriptionRequest as AdapterSubscriptionRequest,
    SubscriptionSchedule as AdapterSubscriptionSchedule,
)
from app.repositories.payment_repository import PaymentRepository
from app.models.transaction import TransactionType, TransactionStatus
from app.api.v1.schemas.payment import (
    PurchaseRequestSchema,
    CaptureRequestSchema,
    VoidRequestSchema,
    RefundRequestSchema,
    SubscriptionRequestSchema,
)
import structlog

logger = structlog.get_logger()


class PaymentService:
    """Service for payment operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PaymentRepository(session)
        self.authorize_net_client = AuthorizeNetClient()

    async def process_purchase(
        self,
        request: PurchaseRequestSchema,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """Process a purchase transaction (auth + capture)"""
        try:
            # Create payment record
            payment = await self.repository.create_payment(
                customer_id=request.customer_id,
                billing_address=request.customer_address.model_dump(),
            )

            # Create pending transaction record
            transaction = await self.repository.create_transaction(
                payment_id=payment.id,
                transaction_type=TransactionType.PURCHASE,
                amount=float(request.amount),
                currency="USD",
                customer_id=request.customer_id,
                customer_email=request.customer_email,
                correlation_id=correlation_id,
                extra_data={
                    "invoice_number": request.invoice_number,
                    "description": request.description,
                },
            )

            logger.info(
                "Processing purchase transaction",
                transaction_id=str(transaction.id),
                amount=str(request.amount),
                correlation_id=correlation_id,
            )

            # Convert schema to adapter request
            adapter_request = self._convert_to_adapter_request(
                request, correlation_id, idempotency_key=idempotency_key
            )

            # Call Authorize.Net API
            response = self.authorize_net_client.purchase(adapter_request)

            # Update transaction based on response
            if response.success:
                await self.repository.update_transaction_status(
                    transaction_id=transaction.id,
                    status=TransactionStatus.CAPTURED,
                    authorize_net_transaction_id=response.transaction_id,
                )
                await self.session.commit()

                logger.info(
                    "Purchase transaction successful",
                    transaction_id=str(transaction.id),
                    authorize_net_transaction_id=response.transaction_id,
                    correlation_id=correlation_id,
                )

                return {
                    "transaction_id": str(transaction.id),
                    "status": "captured",
                    "amount": request.amount,
                    "currency": "USD",
                    "authorize_net_transaction_id": response.transaction_id,
                    "message": response.message_description,
                    "correlation_id": correlation_id,
                }
            else:
                # Transaction failed
                error_message = response.error_text or response.message_description or "Transaction failed"
                await self.repository.update_transaction_status(
                    transaction_id=transaction.id,
                    status=TransactionStatus.FAILED,
                    error_message=error_message,
                )
                await self.session.commit()

                logger.error(
                    "Purchase transaction failed",
                    transaction_id=str(transaction.id),
                    error_code=response.error_code,
                    error_text=error_message,
                    correlation_id=correlation_id,
                )

                raise Exception(f"Transaction failed: {error_message}")

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Error processing purchase",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise

    async def process_authorize(
        self,
        request: PurchaseRequestSchema,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """Authorize a transaction without capturing"""
        try:
            payment = await self.repository.create_payment(
                customer_id=request.customer_id,
                billing_address=request.customer_address.model_dump(),
            )

            transaction = await self.repository.create_transaction(
                payment_id=payment.id,
                transaction_type=TransactionType.AUTHORIZE,
                amount=float(request.amount),
                currency="USD",
                customer_id=request.customer_id,
                customer_email=request.customer_email,
                correlation_id=correlation_id,
                extra_data={
                    "invoice_number": request.invoice_number,
                    "description": request.description,
                },
            )

            logger.info(
                "Processing authorization transaction",
                transaction_id=str(transaction.id),
                amount=str(request.amount),
                correlation_id=correlation_id,
            )

            adapter_request = self._convert_to_adapter_request(
                request, correlation_id, idempotency_key=idempotency_key
            )
            response = self.authorize_net_client.authorize(adapter_request)

            if response.success:
                await self.repository.update_transaction_status(
                    transaction_id=transaction.id,
                    status=TransactionStatus.AUTHORIZED,
                    authorize_net_transaction_id=response.transaction_id,
                )
                await self.session.commit()

                logger.info(
                    "Authorization successful",
                    transaction_id=str(transaction.id),
                    authorize_net_transaction_id=response.transaction_id,
                    correlation_id=correlation_id,
                )

                return {
                    "transaction_id": str(transaction.id),
                    "status": "authorized",
                    "amount": request.amount,
                    "currency": "USD",
                    "authorize_net_transaction_id": response.transaction_id,
                    "message": response.message_description,
                    "correlation_id": correlation_id,
                }
            else:
                error_message = response.error_text or response.message_description or "Authorization failed"
                await self.repository.update_transaction_status(
                    transaction_id=transaction.id,
                    status=TransactionStatus.FAILED,
                    error_message=error_message,
                )
                await self.session.commit()

                logger.error(
                    "Authorization failed",
                    transaction_id=str(transaction.id),
                    error_code=response.error_code,
                    error_text=error_message,
                    correlation_id=correlation_id,
                )
                raise Exception(f"Authorization failed: {error_message}")

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Error processing authorization",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise

    async def process_capture(
        self,
        transaction_id: str,
        request: CaptureRequestSchema,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """Capture a previously authorized transaction"""
        from uuid import UUID

        try:
            auth_txn = await self.repository.get_transaction_by_id(UUID(transaction_id))
            if not auth_txn:
                raise ValueError("Transaction not found")
            if auth_txn.status != TransactionStatus.AUTHORIZED:
                raise ValueError("Transaction is not in an authorized state")
            if not auth_txn.authorize_net_transaction_id:
                raise ValueError("Missing Authorize.Net transaction reference for capture")

            amount = request.amount if request and request.amount else auth_txn.amount

            logger.info(
                "Processing capture transaction",
                transaction_id=transaction_id,
                auth_net_transaction_id=auth_txn.authorize_net_transaction_id,
                amount=str(amount),
                correlation_id=correlation_id,
            )

            capture_request = AdapterCaptureRequest(
                amount=Decimal(str(amount)),
                transaction_id=auth_txn.authorize_net_transaction_id,
                ref_id=idempotency_key or correlation_id,
            )

            response = self.authorize_net_client.capture(capture_request)

            if response.success:
                await self.repository.update_transaction_status(
                    transaction_id=auth_txn.id,
                    status=TransactionStatus.CAPTURED,
                    authorize_net_transaction_id=response.transaction_id,
                    extra_data={
                        "auth_transaction_id": auth_txn.authorize_net_transaction_id,
                    },
                )
                await self.session.commit()

                logger.info(
                    "Capture successful",
                    transaction_id=transaction_id,
                    capture_transaction_id=response.transaction_id,
                    correlation_id=correlation_id,
                )

                return {
                    "transaction_id": transaction_id,
                    "status": "captured",
                    "amount": Decimal(str(amount)),
                    "currency": auth_txn.currency,
                    "authorize_net_transaction_id": response.transaction_id,
                    "message": response.message_description,
                    "correlation_id": correlation_id,
                }

            error_message = response.error_text or response.message_description or "Capture failed"
            await self.repository.update_transaction_status(
                transaction_id=auth_txn.id,
                status=TransactionStatus.FAILED,
                error_message=error_message,
            )
            await self.session.commit()

            logger.error(
                "Capture failed",
                transaction_id=transaction_id,
                error_code=response.error_code,
                error_text=error_message,
                correlation_id=correlation_id,
            )
            raise Exception(f"Capture failed: {error_message}")

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Error processing capture",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise

    async def process_void(
        self,
        transaction_id: str,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """Void (cancel) a previously authorized/unsettled transaction"""
        from uuid import UUID

        try:
            txn = await self.repository.get_transaction_by_id(UUID(transaction_id))
            if not txn:
                raise ValueError("Transaction not found")
            if txn.status not in (TransactionStatus.AUTHORIZED, TransactionStatus.PENDING):
                raise ValueError("Transaction is not voidable")
            if not txn.authorize_net_transaction_id:
                raise ValueError("Missing Authorize.Net transaction reference for void")

            logger.info(
                "Processing void transaction",
                transaction_id=transaction_id,
                auth_net_transaction_id=txn.authorize_net_transaction_id,
                correlation_id=correlation_id,
            )

            void_request = AdapterVoidRequest(
                transaction_id=txn.authorize_net_transaction_id,
                ref_id=idempotency_key or correlation_id,
            )

            response = self.authorize_net_client.void(void_request)

            if response.success:
                await self.repository.update_transaction_status(
                    transaction_id=txn.id,
                    status=TransactionStatus.VOIDED,
                    authorize_net_transaction_id=response.transaction_id,
                    extra_data={
                        "voided_auth_transaction_id": txn.authorize_net_transaction_id,
                    },
                )
                await self.session.commit()

                logger.info(
                    "Void successful",
                    transaction_id=transaction_id,
                    void_transaction_id=response.transaction_id,
                    correlation_id=correlation_id,
                )

                return {
                    "transaction_id": transaction_id,
                    "status": "voided",
                    "amount": Decimal(str(txn.amount)),
                    "currency": txn.currency,
                    "authorize_net_transaction_id": response.transaction_id,
                    "message": response.message_description,
                    "correlation_id": correlation_id,
                }

            error_message = response.error_text or response.message_description or "Void failed"
            await self.repository.update_transaction_status(
                transaction_id=txn.id,
                status=TransactionStatus.FAILED,
                error_message=error_message,
            )
            await self.session.commit()

            logger.error(
                "Void failed",
                transaction_id=transaction_id,
                error_code=response.error_code,
                error_text=error_message,
                correlation_id=correlation_id,
            )
            raise Exception(f"Void failed: {error_message}")

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Error processing void",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise

    async def process_refund(
        self,
        transaction_id: str,
        request: RefundRequestSchema,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """Refund a captured transaction (full or partial)"""
        from uuid import UUID

        try:
            txn = await self.repository.get_transaction_by_id(UUID(transaction_id))
            if not txn:
                raise ValueError("Transaction not found")
            if txn.status != TransactionStatus.CAPTURED:
                raise ValueError("Transaction is not in a captured state")
            if not txn.authorize_net_transaction_id:
                raise ValueError("Missing Authorize.Net transaction reference for refund")

            amount = request.amount if request and request.amount else txn.amount
            if Decimal(str(amount)) > Decimal(str(txn.amount)):
                raise ValueError("Refund amount cannot exceed captured amount")

            if not request.card_number_last4 or len(request.card_number_last4) != 4:
                raise ValueError("card_number_last4 is required and must be 4 digits for refund")

            logger.info(
                "Processing refund transaction",
                transaction_id=transaction_id,
                auth_net_transaction_id=txn.authorize_net_transaction_id,
                amount=str(amount),
                correlation_id=correlation_id,
            )

            refund_request = AdapterRefundRequest(
                amount=Decimal(str(amount)),
                transaction_id=txn.authorize_net_transaction_id,
                card_number_last4=request.card_number_last4,
                ref_id=idempotency_key or correlation_id,
            )

            response = self.authorize_net_client.refund(refund_request)

            if response.success:
                await self.repository.update_transaction_status(
                    transaction_id=txn.id,
                    status=TransactionStatus.REFUNDED,
                    authorize_net_transaction_id=response.transaction_id,
                    extra_data={
                        "refunded_transaction_id": txn.authorize_net_transaction_id,
                        "refund_amount": str(amount),
                    },
                )
                await self.session.commit()

                logger.info(
                    "Refund successful",
                    transaction_id=transaction_id,
                    refund_transaction_id=response.transaction_id,
                    correlation_id=correlation_id,
                )

                return {
                    "transaction_id": transaction_id,
                    "status": "refunded",
                    "amount": Decimal(str(amount)),
                    "currency": txn.currency,
                    "authorize_net_transaction_id": response.transaction_id,
                    "message": response.message_description,
                    "correlation_id": correlation_id,
                }

            error_message = response.error_text or response.message_description or "Refund failed"
            await self.repository.update_transaction_status(
                transaction_id=txn.id,
                status=TransactionStatus.FAILED,
                error_message=error_message,
            )
            await self.session.commit()

            logger.error(
                "Refund failed",
                transaction_id=transaction_id,
                error_code=response.error_code,
                error_text=error_message,
                correlation_id=correlation_id,
            )
            raise Exception(f"Refund failed: {error_message}")

        except Exception as e:
            await self.session.rollback()
            logger.exception(
                "Error processing refund",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise

    async def process_create_subscription(
        self,
        request: SubscriptionRequestSchema,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """Create a recurring subscription via Authorize.Net ARB"""
        try:
            adapter_request = self._convert_to_subscription_request(
                request, correlation_id, idempotency_key=idempotency_key
            )
            response = self.authorize_net_client.create_subscription(adapter_request)

            if response.success:
                logger.info(
                    "Subscription creation successful",
                    subscription_id=response.subscription_id,
                    correlation_id=correlation_id,
                )
                return {
                    "subscription_id": response.subscription_id,
                    "status": "active",
                    "message_code": response.message_code,
                    "message_text": response.message_text,
                    "correlation_id": correlation_id,
                }

            logger.error(
                "Subscription creation failed",
                error_code=response.error_code,
                error_text=response.error_text,
                correlation_id=correlation_id,
            )
            raise Exception(response.error_text or "Subscription creation failed")

        except Exception as e:
            logger.exception(
                "Error processing subscription creation",
                error=str(e),
                correlation_id=correlation_id,
            )
            raise
    def _convert_to_adapter_request(
        self,
        request: PurchaseRequestSchema,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> AdapterPurchaseRequest:
        """Convert API schema to adapter request"""
        credit_card = CreditCard(
            card_number=request.credit_card.card_number,
            expiration_date=request.credit_card.expiration_date,
            card_code=request.credit_card.card_code,
        )

        customer_address = CustomerAddress(
            first_name=request.customer_address.first_name,
            last_name=request.customer_address.last_name,
            company=request.customer_address.company,
            address=request.customer_address.address,
            city=request.customer_address.city,
            state=request.customer_address.state,
            zip=request.customer_address.zip,
            country=request.customer_address.country,
        )

        customer_data = CustomerData(
            customer_id=request.customer_id,
            email=request.customer_email,
        )

        line_items = None
        if request.line_items:
            line_items = [
                LineItem(
                    item_id=item.item_id,
                    name=item.name,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in request.line_items
            ]

        return AdapterPurchaseRequest(
            amount=request.amount,
            credit_card=credit_card,
            customer_address=customer_address,
            customer_data=customer_data,
            invoice_number=request.invoice_number,
            description=request.description,
            line_items=line_items,
            ref_id=idempotency_key or correlation_id,
        )

    def _convert_to_subscription_request(
        self,
        request: SubscriptionRequestSchema,
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> AdapterSubscriptionRequest:
        """Convert subscription schema to adapter request"""
        credit_card = CreditCard(
            card_number=request.credit_card.card_number,
            expiration_date=request.credit_card.expiration_date,
            card_code=request.credit_card.card_code,
        )

        customer_address = CustomerAddress(
            first_name=request.customer_address.first_name,
            last_name=request.customer_address.last_name,
            company=request.customer_address.company,
            address=request.customer_address.address,
            city=request.customer_address.city,
            state=request.customer_address.state,
            zip=request.customer_address.zip,
            country=request.customer_address.country,
        )

        schedule = AdapterSubscriptionSchedule(
            interval_length=request.schedule.interval_length,
            interval_unit=request.schedule.interval_unit,
            start_date=request.schedule.start_date,
            total_occurrences=request.schedule.total_occurrences,
            trial_occurrences=request.schedule.trial_occurrences,
            trial_amount=request.schedule.trial_amount,
        )

        return AdapterSubscriptionRequest(
            name=request.name,
            amount=request.amount,
            credit_card=credit_card,
            customer_address=customer_address,
            schedule=schedule,
            ref_id=idempotency_key or correlation_id,
        )
