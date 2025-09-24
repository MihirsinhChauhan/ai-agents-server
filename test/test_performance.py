"""
Performance tests for API endpoints and AI operations.
Tests response times, throughput, and resource usage.
"""

import pytest
import time
import asyncio
from statistics import mean, median
from typing import List, Dict, Any
import psutil
import os


@pytest.mark.performance
class TestAPIResponseTimes:
    """Test API endpoint response times."""

    async def test_debt_crud_response_times(self, test_client, authenticated_user, benchmark):
        """Test response times for debt CRUD operations."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])
        user_id = str(authenticated_user["user"].id)

        # Test CREATE response time
        debt_data = {
            "user_id": user_id,
            "name": "Performance Test Debt",
            "debt_type": "credit_card",
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 15.0,
            "minimum_payment": 150.0,
            "due_date": "2025-02-15",
            "lender": "Perf Bank",
            "payment_frequency": "monthly"
        }

        start_time = time.time()
        create_response = await test_client.post("/api/v2/debts", json=debt_data)
        create_time = time.time() - start_time

        assert create_response.status_code == 201
        assert create_time < 0.5  # Should be under 500ms

        debt_id = create_response.json()["id"]

        # Test READ response time
        start_time = time.time()
        read_response = await test_client.get(f"/api/v2/debts/{debt_id}")
        read_time = time.time() - start_time

        assert read_response.status_code == 200
        assert read_time < 0.2  # Should be under 200ms

        # Test UPDATE response time
        update_data = {"current_balance": 2500.0}
        start_time = time.time()
        update_response = await test_client.put(f"/api/v2/debts/{debt_id}", json=update_data)
        update_time = time.time() - start_time

        assert update_response.status_code == 200
        assert update_time < 0.3  # Should be under 300ms

        # Test DELETE response time
        start_time = time.time()
        delete_response = await test_client.delete(f"/api/v2/debts/{debt_id}")
        delete_time = time.time() - start_time

        assert delete_response.status_code == 204
        assert delete_time < 0.3  # Should be under 300ms

    async def test_ai_response_times(self, test_client, authenticated_user, test_debts):
        """Test response times for AI operations."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Test AI insights response time (may be cached)
        start_time = time.time()
        insights_response = await test_client.get("/api/ai/insights")
        insights_time = time.time() - start_time

        assert insights_response.status_code == 200
        # AI operations can be slower but should be reasonable
        assert insights_time < 5.0  # Should be under 5 seconds

        # Test DTI calculation response time
        start_time = time.time()
        dti_response = await test_client.get("/api/ai/dti")
        dti_time = time.time() - start_time

        assert dti_response.status_code == 200
        assert dti_time < 2.0  # Should be under 2 seconds

        # Test recommendations response time
        start_time = time.time()
        rec_response = await test_client.get("/api/ai/recommendations")
        rec_time = time.time() - start_time

        assert rec_response.status_code == 200
        assert rec_time < 1.0  # Should be under 1 second


@pytest.mark.performance
class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    async def test_concurrent_debt_operations(self, test_client, authenticated_user):
        """Test concurrent debt operations."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])
        user_id = str(authenticated_user["user"].id)

        async def create_debt_request(index: int):
            debt_data = {
                "user_id": user_id,
                "name": f"Concurrent Debt {index}",
                "debt_type": "credit_card",
                "principal_amount": 1000.0 * (index + 1),
                "current_balance": 800.0 * (index + 1),
                "interest_rate": 15.0,
                "minimum_payment": 40.0 * (index + 1),
                "due_date": f"2025-02-{15 + index}",
                "lender": f"Bank {index}",
                "payment_frequency": "monthly"
            }

            start_time = time.time()
            response = await test_client.post("/api/v2/debts", json=debt_data)
            end_time = time.time()

            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 201
            }

        # Create 10 concurrent requests
        tasks = [create_debt_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        avg_response_time = mean(r["response_time"] for r in results)
        max_response_time = max(r["response_time"] for r in results)

        assert successful_requests == 10, f"Expected 10 successful requests, got {successful_requests}"
        assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time}"
        assert max_response_time < 2.0, f"Max response time too high: {max_response_time}"

    async def test_concurrent_ai_requests(self, test_client, authenticated_user, test_debts):
        """Test concurrent AI insights requests."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        async def ai_request():
            start_time = time.time()
            response = await test_client.get("/api/ai/insights")
            end_time = time.time()

            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200
            }

        # Create 5 concurrent AI requests
        tasks = [ai_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        avg_response_time = mean(r["response_time"] for r in results)

        assert successful_requests >= 4, f"Expected at least 4 successful AI requests, got {successful_requests}"
        assert avg_response_time < 3.0, f"Average AI response time too high: {avg_response_time}"


@pytest.mark.performance
class TestResourceUsage:
    """Test resource usage during operations."""

    def test_memory_usage_during_operations(self):
        """Test memory usage during various operations."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform some memory-intensive operations
        large_data = [{"data": "x" * 1000} for _ in range(1000)]

        # Check memory after operations
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50, f"Memory increase too high: {memory_increase}MB"

    async def test_database_connection_pooling(self, test_client, authenticated_user):
        """Test database connection pooling under load."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Make multiple rapid requests to test connection pooling
        start_time = time.time()

        responses = []
        for _ in range(20):
            response = await test_client.get("/api/v2/debts")
            responses.append(response.status_code)

        end_time = time.time()
        total_time = end_time - start_time

        # All requests should succeed
        assert all(code == 200 for code in responses)

        # Total time should be reasonable (under 10 seconds for 20 requests)
        assert total_time < 10.0, f"Total request time too high: {total_time}s"


@pytest.mark.performance
@pytest.mark.slow
class TestLoadTesting:
    """Load testing for sustained performance."""

    async def test_sustained_api_load(self, test_client, authenticated_user):
        """Test sustained API load over time."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        response_times = []
        start_time = time.time()

        # Make 50 requests over 30 seconds
        for i in range(50):
            request_start = time.time()
            response = await test_client.get("/api/v2/debts")
            request_end = time.time()

            assert response.status_code == 200
            response_times.append(request_end - request_start)

            # Small delay to simulate real usage
            await asyncio.sleep(0.1)

        end_time = time.time()
        total_duration = end_time - start_time

        # Analyze performance metrics
        avg_response_time = mean(response_times)
        median_response_time = median(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        # Performance assertions
        assert avg_response_time < 0.5, f"Average response time too high: {avg_response_time}s"
        assert median_response_time < 0.3, f"Median response time too high: {median_response_time}s"
        assert max_response_time < 2.0, f"Max response time too high: {max_response_time}s"

        # Throughput check (should handle at least 1 request per second)
        throughput = len(response_times) / total_duration
        assert throughput > 1.0, f"Throughput too low: {throughput} req/s"


@pytest.mark.performance
class TestCachingPerformance:
    """Test caching performance improvements."""

    async def test_ai_caching_performance(self, test_client, authenticated_user, test_debts):
        """Test AI caching performance improvements."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # First request (cache miss)
        start_time = time.time()
        response1 = await test_client.get("/api/ai/insights")
        first_request_time = time.time() - start_time

        assert response1.status_code == 200

        # Second request (cache hit)
        start_time = time.time()
        response2 = await test_client.get("/api/ai/insights")
        second_request_time = time.time() - start_time

        assert response2.status_code == 200

        # Cached request should be significantly faster
        speedup_ratio = first_request_time / second_request_time
        assert speedup_ratio > 2.0, f"Caching speedup insufficient: {speedup_ratio}x"

        # Both responses should be identical
        assert response1.json() == response2.json()

    async def test_cache_invalidation_performance(self, test_client, authenticated_user, test_debts):
        """Test cache invalidation doesn't hurt performance significantly."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Get cached insights
        await test_client.get("/api/ai/insights")

        # Modify debt (should invalidate cache)
        debt_id = str(test_debts[0].id)
        update_data = {"current_balance": test_debts[0].current_balance - 50}

        start_time = time.time()
        update_response = await test_client.put(f"/api/v2/debts/{debt_id}", json=update_data)
        update_time = time.time() - start_time

        assert update_response.status_code == 200
        assert update_time < 0.5  # Cache invalidation should not significantly slow down updates

        # Next AI request should generate fresh results
        start_time = time.time()
        fresh_response = await test_client.get("/api/ai/insights")
        fresh_request_time = time.time() - start_time

        assert fresh_response.status_code == 200
        # Fresh request should still be reasonably fast
        assert fresh_request_time < 3.0
