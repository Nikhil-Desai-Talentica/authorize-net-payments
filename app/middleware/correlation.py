"""Correlation ID middleware for request tracing"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests and responses"""

    async def dispatch(self, request: Request, call_next):
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Add to request state
        request.state.correlation_id = correlation_id

        # Bind logger with correlation ID
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id,
        )

        # Process request
        response: Response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            correlation_id=correlation_id,
        )

        return response

