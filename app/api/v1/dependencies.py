"""Shared API dependencies"""
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import verify_token
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_idempotency_key(
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
) -> str | None:
    """Extract idempotency key from header"""
    return x_idempotency_key


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request state"""
    return getattr(request.state, "correlation_id", None)

