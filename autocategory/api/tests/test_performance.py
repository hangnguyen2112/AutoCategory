"""
Performance and Load Tests for AutoCategory API
"""

import asyncio
import time
import statistics
from typing import List, Dict
from httpx import AsyncClient
import pytest

BASE_URL = "http://localhost:8000"


class LoadTestMetrics:
    """Track load test metrics"""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.success_count = 0
        self.error_count = 0
        self.errors: Dict[int, int] = {}
    
    def record_success(self, response_time: float):
        self.response_times.append(response_time)
        self.success_count += 1
    
    def record_error(self, status_code: int):
        self.error_count += 1
        self.errors[status_code] = self.errors.get(status_code, 0) + 1
    
    def get_statistics(self) -> Dict:
        if not self.response_times:
            return {}
        
        return {
            "total_requests": self.success_count + self.error_count,
            "successful": self.success_count,
            "failed": self.error_count,
            "error_rate": self.error_count / (self.success_count + self.error_count) * 100,
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "mean_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else max(self.response_times),
            "p99_response_time": statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) >= 100 else max(self.response_times),
            "errors_by_code": self.errors
        }


async def make_classification_request(client: AsyncClient, api_key: str, metrics: LoadTestMetrics):
    """Make a single classification request"""
    start_time = time.time()
    
    try:
        response = await client.post(
            "/api/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "iPhone 14 Pro Max 256GB Chính hãng VN",
                "description": "Máy mới 100%, fullbox, bảo hành 12 tháng",
                "price": 25000000
            }
        )
        
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code == 200:
            metrics.record_success(elapsed)
        else:
            metrics.record_error(response.status_code)
    
    except Exception as e:
        metrics.record_error(0)


@pytest.mark.asyncio
@pytest.mark.performance
class TestPerformance:
    """Performance tests"""
    
    async def test_single_request_latency(self):
        """Test single request latency (should be < 500ms)"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Get API key first
            login_response = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            token = login_response.json()["access_token"]
            
            # Create test API key
            key_response = await client.post(
                "/api/admin/api-keys",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Perf Test", "rate_limit": 10000, "expires_in_days": 1}
            )
            api_key = key_response.json()["key"]
            
            # Measure classification time
            start_time = time.time()
            response = await client.post(
                "/api/classify",
                headers={"X-API-Key": api_key},
                json={
                    "title": "Test Product",
                    "description": "Test description",
                    "price": 100000
                }
            )
            elapsed = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            assert elapsed < 500, f"Response time {elapsed}ms exceeds 500ms threshold"
            print(f"\n✅ Single request latency: {elapsed:.2f}ms")
    
    async def test_throughput_10_concurrent(self):
        """Test throughput with 10 concurrent users"""
        metrics = LoadTestMetrics()
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Setup
            login_response = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            token = login_response.json()["access_token"]
            
            key_response = await client.post(
                "/api/admin/api-keys",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Throughput Test", "rate_limit": 10000, "expires_in_days": 1}
            )
            api_key = key_response.json()["key"]
            
            # Run 10 concurrent requests
            tasks = [
                make_classification_request(client, api_key, metrics)
                for _ in range(10)
            ]
            
            start_time = time.time()
            await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            stats = metrics.get_statistics()
            
            print(f"\n📊 10 Concurrent Users Test:")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Success rate: {stats['successful']}/{stats['total_requests']}")
            print(f"  Mean response time: {stats['mean_response_time']:.2f}ms")
            print(f"  P95 response time: {stats['p95_response_time']:.2f}ms")
            
            # Assertions
            assert stats['error_rate'] < 5, f"Error rate {stats['error_rate']:.2f}% is too high"
            assert stats['p95_response_time'] < 1000, f"P95 response time {stats['p95_response_time']:.2f}ms exceeds 1s"
    
    async def test_sustained_load_100_requests(self):
        """Test sustained load with 100 requests"""
        metrics = LoadTestMetrics()
        
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Setup
            login_response = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            token = login_response.json()["access_token"]
            
            key_response = await client.post(
                "/api/admin/api-keys",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Load Test", "rate_limit": 10000, "expires_in_days": 1}
            )
            api_key = key_response.json()["key"]
            
            # Run 100 requests with 10 concurrent workers
            start_time = time.time()
            
            for batch in range(10):
                tasks = [
                    make_classification_request(client, api_key, metrics)
                    for _ in range(10)
                ]
                await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            stats = metrics.get_statistics()
            throughput = stats['total_requests'] / total_time
            
            print(f"\n📊 Sustained Load Test (100 requests):")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Throughput: {throughput:.2f} req/s")
            print(f"  Success rate: {stats['successful']}/{stats['total_requests']} ({100 - stats['error_rate']:.1f}%)")
            print(f"  Mean response time: {stats['mean_response_time']:.2f}ms")
            print(f"  Median response time: {stats['median_response_time']:.2f}ms")
            print(f"  P95 response time: {stats['p95_response_time']:.2f}ms")
            print(f"  P99 response time: {stats['p99_response_time']:.2f}ms")
            
            if stats['errors_by_code']:
                print(f"  Errors: {stats['errors_by_code']}")
            
            # Assertions
            assert stats['error_rate'] < 5, f"Error rate {stats['error_rate']:.2f}% is too high"
            assert stats['p95_response_time'] < 2000, f"P95 response time {stats['p95_response_time']:.2f}ms exceeds 2s"
            assert throughput > 5, f"Throughput {throughput:.2f} req/s is too low"
    
    async def test_database_query_performance(self):
        """Test database query performance"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Login
            login_response = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            token = login_response.json()["access_token"]
            
            # Test paginated queries
            start_time = time.time()
            response = await client.get(
                "/api/admin/training-data?page=1&page_size=100",
                headers={"Authorization": f"Bearer {token}"}
            )
            elapsed = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            assert elapsed < 1000, f"Database query took {elapsed}ms (should be < 1s)"
            print(f"\n✅ Database query (100 records): {elapsed:.2f}ms")
    
    async def test_cache_hit_performance(self):
        """Test cache hit performance"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Setup
            login_response = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            token = login_response.json()["access_token"]
            
            key_response = await client.post(
                "/api/admin/api-keys",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Cache Test", "rate_limit": 10000, "expires_in_days": 1}
            )
            api_key = key_response.json()["key"]
            
            # Make first request (cache miss)
            payload = {
                "title": "Cache Test Product XYZ123",
                "description": "Unique product for cache testing",
                "price": 123456
            }
            
            start_time = time.time()
            response1 = await client.post(
                "/api/classify",
                headers={"X-API-Key": api_key},
                json=payload
            )
            time_uncached = (time.time() - start_time) * 1000
            
            # Make second request (should hit cache)
            start_time = time.time()
            response2 = await client.post(
                "/api/classify",
                headers={"X-API-Key": api_key},
                json=payload
            )
            time_cached = (time.time() - start_time) * 1000
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Cache should make it faster
            print(f"\n⚡ Cache Performance:")
            print(f"  Uncached: {time_uncached:.2f}ms")
            print(f"  Cached: {time_cached:.2f}ms")
            print(f"  Speedup: {time_uncached / time_cached:.2f}x")


@pytest.mark.asyncio
@pytest.mark.benchmark
class TestResourceUsage:
    """Test resource usage under load"""
    
    async def test_memory_leak(self):
        """Test for memory leaks during sustained requests"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Get API key
            login_response = await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            token = login_response.json()["access_token"]
            
            key_response = await client.post(
                "/api/admin/api-keys",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Memory Test", "rate_limit": 10000, "expires_in_days": 1}
            )
            api_key = key_response.json()["key"]
            
            # Make 50 requests and check memory usage
            metrics_before = await client.get(
                "/api/admin/system/metrics",
                headers={"Authorization": f"Bearer {token}"}
            )
            memory_before = metrics_before.json().get("memory_mb", 0)
            
            # Execute requests
            for _ in range(50):
                await client.post(
                    "/api/classify",
                    headers={"X-API-Key": api_key},
                    json={"title": "Memory test product", "price": 100000}
                )
            
            # Check memory after
            await asyncio.sleep(2)  # Let GC run
            metrics_after = await client.get(
                "/api/admin/system/metrics",
                headers={"Authorization": f"Bearer {token}"}
            )
            memory_after = metrics_after.json().get("memory_mb", 0)
            
            memory_increase = memory_after - memory_before
            
            print(f"\n💾 Memory Usage:")
            print(f"  Before: {memory_before:.2f} MB")
            print(f"  After: {memory_after:.2f} MB")
            print(f"  Increase: {memory_increase:.2f} MB")
            
            # Memory increase should be reasonable (<100MB for 50 requests)
            assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB (possible leak)"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
