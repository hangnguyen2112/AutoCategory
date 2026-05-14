"""
End-to-End Tests for AutoCategory

Tests the full user journey from authentication to classification
"""

import pytest
import asyncio
from httpx import AsyncClient
from main import app
import json

BASE_URL = "http://test"


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url=BASE_URL) as c:
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
async def api_key(client, admin_token):
    """Create test API key"""
    response = await client.post(
        "/api/admin/api-keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Test API Key",
            "rate_limit": 1000,
            "expires_in_days": 365
        }
    )
    assert response.status_code == 201
    data = response.json()
    return data["key"]


@pytest.mark.asyncio
class TestAuthenticationFlow:
    """Test authentication and authorization"""
    
    async def test_login_success(self, client):
        """Test successful login"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == "admin"
    
    async def test_login_invalid_credentials(self, client):
        """Test login with wrong password"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong_password"}
        )
        
        assert response.status_code == 401
    
    async def test_protected_route_without_token(self, client):
        """Test accessing protected route without token"""
        response = await client.get("/api/admin/users")
        assert response.status_code == 401
    
    async def test_protected_route_with_token(self, client, admin_token):
        """Test accessing protected route with valid token"""
        response = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
class TestClassificationFlow:
    """Test classification API"""
    
    async def test_classify_with_api_key(self, client, api_key):
        """Test classification with valid API key"""
        response = await client.post(
            "/api/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "iPhone 14 Pro Max 256GB",
                "description": "Brand new, sealed with warranty",
                "price": 25000000
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "category_id" in data
        assert "category_name" in data
        assert "confidence" in data
        assert "alternatives" in data
        assert "processing_time_ms" in data
        
        # Check data types
        assert isinstance(data["category_id"], int)
        assert isinstance(data["confidence"], float)
        assert 0.0 <= data["confidence"] <= 1.0
        assert isinstance(data["alternatives"], list)
    
    async def test_classify_without_api_key(self, client):
        """Test classification without API key"""
        response = await client.post(
            "/api/classify",
            json={"title": "Test Product"}
        )
        assert response.status_code == 401
    
    async def test_classify_invalid_data(self, client, api_key):
        """Test classification with invalid data"""
        response = await client.post(
            "/api/classify",
            headers={"X-API-Key": api_key},
            json={"title": ""}  # Empty title
        )
        assert response.status_code == 422  # Validation error
    
    async def test_classify_with_price(self, client, api_key):
        """Test classification including price signal"""
        response = await client.post(
            "/api/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "MacBook Pro 16 inch M2",
                "price": 50000000
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "category_name" in data
        # High-priced electronics should be classified correctly


@pytest.mark.asyncio
class TestUserManagement:
    """Test user CRUD operations"""
    
    async def test_create_user(self, client, admin_token):
        """Test creating a new user"""
        response = await client.post(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "test_password",
                "full_name": "Test User",
                "role": "developer"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["role"] == "developer"
        assert "id" in data
    
    async def test_list_users(self, client, admin_token):
        """Test listing users"""
        response = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert len(data["users"]) > 0
    
    async def test_update_user(self, client, admin_token):
        """Test updating user"""
        # First create a user
        create_response = await client.post(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "updatetest",
                "email": "update@example.com",
                "password": "password",
                "full_name": "Update Test",
                "role": "viewer"
            }
        )
        user_id = create_response.json()["id"]
        
        # Update the user
        response = await client.put(
            f"/api/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"full_name": "Updated Name", "role": "developer"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["role"] == "developer"


@pytest.mark.asyncio
class TestTrainingDataWorkflow:
    """Test training data management"""
    
    async def test_add_training_sample(self, client, admin_token):
        """Test adding training sample"""
        response = await client.post(
            "/api/admin/training-data",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "Test Training Sample",
                "description": "This is a test",
                "price": 100000,
                "category_id": 123,
                "source": "manual"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Training Sample"
        assert data["is_validated"] == False
    
    async def test_validate_sample(self, client, admin_token):
        """Test validating a training sample"""
        # Create sample
        create_response = await client.post(
            "/api/admin/training-data",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": "Sample to Validate",
                "category_id": 123,
                "source": "manual"
            }
        )
        sample_id = create_response.json()["id"]
        
        # Validate it
        response = await client.put(
            f"/api/admin/training-data/{sample_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_validated": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_validated"] == True
    
    async def test_bulk_validate(self, client, admin_token):
        """Test bulk validation"""
        # Create multiple samples
        sample_ids = []
        for i in range(3):
            response = await client.post(
                "/api/admin/training-data",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "title": f"Bulk Sample {i}",
                    "category_id": 123,
                    "source": "manual"
                }
            )
            sample_ids.append(response.json()["id"])
        
        # Bulk validate
        response = await client.post(
            "/api/admin/training-data/bulk-validate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"sample_ids": sample_ids}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["validated_count"] >= 0


@pytest.mark.asyncio
class TestSystemOperations:
    """Test system control and monitoring"""
    
    async def test_health_check(self, client):
        """Test health endpoint"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    async def test_system_metrics(self, client, admin_token):
        """Test metrics endpoint"""
        response = await client.get(
            "/api/admin/system/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_mb" in data
        assert "disk_usage" in data
    
    async def test_clear_cache(self, client, admin_token):
        """Test cache clearing"""
        response = await client.delete(
            "/api/admin/system/cache?cache_type=redis",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    async def test_complete_listing_flow(self, client, api_key):
        """Test complete flow: classify -> feedback -> retrain"""
        
        # 1. Classify a product
        classify_response = await client.post(
            "/api/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "Samsung Galaxy S23 Ultra 512GB",
                "description": "Latest flagship smartphone",
                "price": 28000000
            }
        )
        
        assert classify_response.status_code == 200
        classification = classify_response.json()
        predicted_category = classification["category_id"]
        
        # 2. Submit feedback (user corrected category)
        actual_category = 456  # Different from prediction
        feedback_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": api_key},
            json={
                "title": "Samsung Galaxy S23 Ultra 512GB",
                "description": "Latest flagship smartphone",
                "predicted_category_id": predicted_category,
                "actual_category_id": actual_category,
                "confidence": classification["confidence"]
            }
        )
        
        assert feedback_response.status_code == 200
        
        # Feedback is now in training data and can be used for retraining
    
    async def test_rate_limiting(self, client, api_key):
        """Test rate limiting enforcement"""
        # This would need to make 1000+ requests to trigger rate limit
        # For testing, we'll just verify the headers are present
        
        response = await client.post(
            "/api/classify",
            headers={"X-API-Key": api_key},
            json={"title": "Test Product"}
        )
        
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    async def test_concurrent_requests(self, client, api_key):
        """Test handling concurrent requests"""
        
        async def make_request():
            return await client.post(
                "/api/classify",
                headers={"X-API-Key": api_key},
                json={"title": "Concurrent Test Product"}
            )
        
        # Make 10 concurrent requests
        results = await asyncio.gather(*[make_request() for _ in range(10)])
        
        # All should succeed
        for response in results:
            assert response.status_code == 200


# Performance benchmark tests
@pytest.mark.asyncio
@pytest.mark.benchmark
class TestPerformance:
    """Performance and load tests"""
    
    async def test_classification_speed(self, client, api_key):
        """Test classification response time"""
        import time
        
        start_time = time.time()
        response = await client.post(
            "/api/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "Performance Test Product",
                "description": "Testing response time",
                "price": 100000
            }
        )
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Response time should be under 2 seconds
        assert response_time < 2000, f"Response time {response_time}ms exceeds threshold"
    
    async def test_bulk_operations_speed(self, client, admin_token):
        """Test bulk operations performance"""
        import time
        
        # Prepare 100 samples
        samples = [
            {
                "title": f"Bulk Test Product {i}",
                "category_id": 123,
                "source": "manual"
            }
            for i in range(100)
        ]
        
        # Measure bulk insert time
        start_time = time.time()
        for sample in samples:
            await client.post(
                "/api/admin/training-data",
                headers={"Authorization": f"Bearer {admin_token}"},
                json=sample
            )
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_sample = (total_time / 100) * 1000
        
        # Average time per sample should be under 100ms
        assert avg_time_per_sample < 100, f"Avg time {avg_time_per_sample}ms is too slow"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
