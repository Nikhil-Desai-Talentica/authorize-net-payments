"""Payment repository for database operations"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.payment import Payment
from app.models.transaction import Transaction, TransactionType, TransactionStatus


class PaymentRepository:
    """Repository for payment and transaction operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_payment(
        self,
        customer_id: str,
        payment_method_token: str | None = None,
        billing_address: dict | None = None,
    ) -> Payment:
        """Create a new payment record"""
        payment = Payment(
            customer_id=customer_id,
            payment_method_token=payment_method_token,
            billing_address=billing_address,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def create_transaction(
        self,
        payment_id: UUID,
        transaction_type: TransactionType,
        amount: float,
        currency: str = "USD",
        customer_id: str | None = None,
        customer_email: str | None = None,
        correlation_id: str | None = None,
        extra_data: dict | None = None,
    ) -> Transaction:
        """Create a new transaction record"""
        transaction = Transaction(
            payment_id=payment_id,
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            amount=amount,
            currency=currency,
            customer_id=customer_id,
            customer_email=customer_email,
            correlation_id=correlation_id,
            extra_data=extra_data,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def get_transaction_by_id(self, transaction_id: UUID) -> Transaction | None:
        """Get transaction by ID"""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(selectinload(Transaction.payment))
        )
        return result.scalar_one_or_none()

    async def update_transaction_status(
        self,
        transaction_id: UUID,
        status: TransactionStatus,
        authorize_net_transaction_id: str | None = None,
        error_message: str | None = None,
        extra_data: dict | None = None,
    ) -> Transaction | None:
        """Update transaction status"""
        transaction = await self.get_transaction_by_id(transaction_id)
        if transaction:
            transaction.status = status
            if authorize_net_transaction_id:
                transaction.authorize_net_transaction_id = authorize_net_transaction_id
            if error_message:
                transaction.error_message = error_message
            if extra_data:
                existing = transaction.extra_data or {}
                existing.update(extra_data)
                transaction.extra_data = existing
            await self.session.flush()
        return transaction

    async def get_transaction_by_authorize_net_id(self, auth_net_transaction_id: str) -> Transaction | None:
        """Get transaction by Authorize.Net transaction ID"""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.authorize_net_transaction_id == auth_net_transaction_id)
            .options(selectinload(Transaction.payment))
        )
        return result.scalar_one_or_none()

    async def get_payment_by_id(self, payment_id: UUID) -> Payment | None:
        """Get payment by ID with transactions"""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.transactions))
        )
        return result.scalar_one_or_none()
