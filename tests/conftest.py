"""Pytest configuration and fixtures"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

