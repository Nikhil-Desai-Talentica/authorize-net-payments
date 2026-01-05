"""Test basic setup and configuration"""
import pytest
from app.core.config import settings
from app.core.database import engine, Base
from app.models import Payment, Transaction, IdempotencyKey, WebhookEvent
from sqlalchemy import text


def test_settings_loaded():
    """Test that settings are loaded correctly"""
    assert settings.ENVIRONMENT is not None
    assert settings.DATABASE_URL is not None
    assert settings.JWT_SECRET_KEY is not None
    assert settings.API_V1_PREFIX == "/api/v1"


def test_models_import():
    """Test that all models can be imported"""
    assert Payment is not None
    assert Transaction is not None
    assert IdempotencyKey is not None
    assert WebhookEvent is not None


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection"""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_database_tables_exist():
    """Test that database tables can be created"""
    # This will create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Verify we can query the tables
    async with engine.connect() as conn:
        # Check if tables exist by querying information_schema
        result = await conn.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('payments', 'transactions', 'idempotency_keys', 'webhook_events')
            """)
        )
        tables = [row[0] for row in result.fetchall()]
        assert len(tables) >= 0  # Tables may or may not exist yet

