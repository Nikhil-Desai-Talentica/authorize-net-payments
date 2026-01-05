"""Quick setup test script"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    try:
        from app.core.config import settings
        print("✓ Config imported")
        
        from app.core.database import engine, Base, get_db
        print("✓ Database imported")
        
        from app.models import Payment, Transaction, IdempotencyKey, WebhookEvent
        print("✓ Models imported")
        
        from app.middleware.correlation import CorrelationIdMiddleware
        print("✓ Middleware imported")
        
        from app.api.v1.routes import payments, transactions, webhooks
        print("✓ Routes imported")
        
        print("\n✅ All imports successful!")
        return True
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
        return False


async def test_settings():
    """Test settings loading"""
    print("\nTesting settings...")
    try:
        from app.core.config import settings
        print(f"✓ Environment: {settings.ENVIRONMENT}")
        print(f"✓ Log Level: {settings.LOG_LEVEL}")
        print(f"✓ API Prefix: {settings.API_V1_PREFIX}")
        if settings.DATABASE_URL:
            # Mask password in URL
            masked_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "***"
            print(f"✓ Database URL: ...@{masked_url}")
        return True
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 50)
    print("Testing Authorize.Net Payment Service Setup")
    print("=" * 50)
    
    results = []
    
    results.append(await test_settings())
    results.append(await test_imports())
    results.append(await test_database_connection())
    
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All tests passed! Setup is ready.")
        print("\nNext steps:")
        print("1. Start the server: uvicorn app.main:app --reload")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Visit http://localhost:8000/health for health check")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

