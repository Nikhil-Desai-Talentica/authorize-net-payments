"""Idempotency service for ensuring idempotent operations"""
import hashlib
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.idempotency import IdempotencyKey
import structlog

logger = structlog.get_logger()


class IdempotencyService:
    """Service for handling idempotency keys"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _hash_request(self, request_body: dict) -> str:
        """Create a hash of the request body"""
        request_str = json.dumps(request_body, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()

    async def check_idempotency(
        self,
        idempotency_key: str,
        request_body: dict,
    ) -> Optional[dict]:
        """Check if request with this idempotency key was already processed"""
        if not idempotency_key:
            return None

        request_hash = self._hash_request(request_body)

        # Check for existing idempotency key
        result = await self.session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.idempotency_key == idempotency_key
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Check if expired
            if existing.expires_at < datetime.utcnow():
                logger.warning(
                    "Idempotency key expired",
                    idempotency_key=idempotency_key,
                )
                return None

            # Check if request hash matches
            if existing.request_hash == request_hash:
                logger.info(
                    "Idempotent request detected",
                    idempotency_key=idempotency_key,
                )
                return {
                    "response_body": existing.response_body,
                    "status_code": existing.status_code,
                }
            else:
                logger.warning(
                    "Idempotency key exists but request hash mismatch",
                    idempotency_key=idempotency_key,
                )
                raise ValueError(
                    "Idempotency key already used with different request"
                )

        return None

    async def store_idempotency(
        self,
        idempotency_key: str,
        request_body: dict,
        response_body: dict,
        status_code: int,
    ) -> None:
        """Store idempotency key and response"""
        if not idempotency_key:
            return

        request_hash = self._hash_request(request_body)

        idempotency_record = IdempotencyKey(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            response_body=response_body,
            status_code=status_code,
            expires_at=IdempotencyKey.create_expires_at(hours=24),
        )

        self.session.add(idempotency_record)
        await self.session.flush()

        logger.info(
            "Stored idempotency key",
            idempotency_key=idempotency_key,
        )

