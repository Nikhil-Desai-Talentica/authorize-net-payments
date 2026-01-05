"""FastAPI application entry point"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api.v1.routes import payments, transactions, webhooks
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging()
    async with engine.begin() as conn:
        # Create tables (in production, use migrations)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Authorize.Net Payment Service",
    description="Payment service integrating with Authorize.Net",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Custom middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# Include routers
app.include_router(payments.router, prefix=settings.API_V1_PREFIX, tags=["payments"])
app.include_router(
    transactions.router, prefix=settings.API_V1_PREFIX, tags=["transactions"]
)
app.include_router(webhooks.router, prefix=settings.API_V1_PREFIX, tags=["webhooks"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

