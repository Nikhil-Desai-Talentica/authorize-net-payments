"""Integration tests for API endpoints"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert "X-Correlation-ID" in response.headers


def test_health_endpoint_correlation_id(client):
    """Test that correlation ID is returned in headers"""
    response = client.get("/health")
    assert "X-Correlation-ID" in response.headers
    correlation_id = response.headers["X-Correlation-ID"]
    assert len(correlation_id) > 0


def test_custom_correlation_id(client):
    """Test that custom correlation ID is respected"""
    custom_id = "test-correlation-123"
    response = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.headers["X-Correlation-ID"] == custom_id


def test_protected_endpoint_without_auth(client):
    """Test that protected endpoints require authentication"""
    response = client.post("/api/v1/payments/purchase")
    assert response.status_code == 403  # Forbidden - no auth token provided


def test_api_docs_available(client):
    """Test that API documentation is available"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema_available(client):
    """Test that OpenAPI schema is available"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "Authorize.Net Payment Service"

