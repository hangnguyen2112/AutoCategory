"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from httpx import AsyncClient
from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Create test HTTP client"""
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


@pytest.fixture
async def admin_token(client):
    """Get admin authentication token"""
    response = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest.fixture
async def developer_token(client, admin_token):
    """Create and get developer token"""
    # Create developer user
    response = await client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "developer",
            "email": "dev@test.com",
            "password": "dev123",
            "full_name": "Developer User",
            "role": "developer"
        }
    )
    
    # Login as developer
    login_response = await client.post(
        "/api/auth/login",
        json={"username": "developer", "password": "dev123"}
    )
    return login_response.json()["access_token"]


@pytest.fixture
async def viewer_token(client, admin_token):
    """Create and get viewer token"""
    # Create viewer user
    response = await client.post(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "viewer",
            "email": "viewer@test.com",
            "password": "viewer123",
            "full_name": "Viewer User",
            "role": "viewer"
        }
    )
    
    # Login as viewer
    login_response = await client.post(
        "/api/auth/login",
        json={"username": "viewer", "password": "viewer123"}
    )
    return login_response.json()["access_token"]


@pytest.fixture
async def api_key(client, admin_token):
    """Create test API key"""
    response = await client.post(
        "/api/admin/api-keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Test API Key",
            "rate_limit": 10000,
            "expires_in_days": 365
        }
    )
    assert response.status_code == 201
    data = response.json()
    return data["key"]


@pytest.fixture
async def sample_category():
    """Sample category for testing"""
    return {
        "id": 1,
        "name": "Electronics",
        "slug": "electronics",
        "parent_id": None,
        "level": 0,
        "is_leaf": False,
        "is_active": True,
        "description": "Electronic devices"
    }


@pytest.fixture
async def sample_training_data():
    """Sample training data for testing"""
    return {
        "title": "iPhone 14 Pro Max 256GB",
        "description": "Brand new sealed with warranty",
        "price": 25000000,
        "category_id": 123,
        "source": "manual"
    }


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
