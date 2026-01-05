"""Global error handler middleware"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle errors globally"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as exc:
            correlation_id = getattr(request.state, "correlation_id", None)
            logger.error(
                "Validation error",
                errors=exc.errors(),
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Validation error",
                    "details": exc.errors(),
                    "correlation_id": correlation_id,
                },
            )
        except Exception as exc:
            correlation_id = getattr(request.state, "correlation_id", None)
            logger.exception(
                "Unhandled exception",
                error=str(exc),
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id,
                },
            )

