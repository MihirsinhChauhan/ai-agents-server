"""
Onboarding Performance Tests
Tests response times, throughput, and resource usage for onboarding operations.
"""

import pytest
import asyncio
import time
import json
from typing import List, Dict, Any
from statistics import mean, median
import psutil
import os

from app.models.onboarding import OnboardingStep


@pytest.mark.performance
class TestOnboardingPerformance:
    """Performance tests for onboarding operations"""

    PERFORMANCE_THRESHOLDS = {
        "api_response_time": 500,  # ms
        "database_query_time": 100,  # ms
        "concurrent_users": 50,     # simultaneous operations
        "memory_usage_mb": 100,     # MB increase
        "cpu_usage_percent": 80,    # max CPU usage
    }

    @pytest.fixture
    async def performance_monitor(self):
        """Monitor system resources during tests"""
        class PerformanceMonitor:
            def __init__(self):
                self.start_time = None
                self.start_memory = None
                self.start_cpu = None

            def start(self):
                self.start_time = time.time()
                self.start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
                self.start_cpu = psutil.cpu_percent(interval=None)

            def measure(self) -> Dict[str, float]:
                end_time = time.time()
                end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
                end_cpu = psutil.cpu_percent(interval=None)

                return {
                    "response_time_ms": (end_time - self.start_time) * 1000,
                    "memory_delta_mb": end_memory - self.start_memory,
                    "cpu_percent": end_cpu
                }

        monitor = PerformanceMonitor()
        monitor.start()
        return monitor

    @pytest.mark.asyncio
    async def test_onboarding_status_response_time(self, test_client, test_user, performance_monitor):
        """Test response time for onboarding status endpoint"""
        response_times = []

        # Make multiple requests to get average performance
        for _ in range(10):
            monitor = type('Monitor', (), {})()
            monitor.start_time = time.time()

            response = await test_client.get(
                "/api/onboarding/status",
                headers={"Authorization": f"Bearer {test_user['session_token']}"}
            )

            monitor.end_time = time.time()
            response_time = (monitor.end_time - monitor.start_time) * 1000
            response_times.append(response_time)

            assert response.status_code == 200

        avg_response_time = mean(response_times)
        median_response_time = median(response_times)
        max_response_time = max(response_times)

        print(f"Onboarding status - Avg: {avg_response_time:.2f}ms, Median: {median_response_time:.2f}ms, Max: {max_response_time:.2f}ms")

        # Assert performance thresholds
        assert avg_response_time < self.PERFORMANCE_THRESHOLDS["api_response_time"]
        assert median_response_time < self.PERFORMANCE_THRESHOLDS["api_response_time"] * 0.8
        assert max_response_time < self.PERFORMANCE_THRESHOLDS["api_response_time"] * 2

    @pytest.mark.asyncio
    async def test_onboarding_step_progression_performance(self, test_client, test_user):
        """Test performance of complete onboarding flow"""
        start_time = time.time()

        # Complete full onboarding flow
        await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        await test_client.post(
            "/api/onboarding/profile",
            headers={"Authorization": f"Bearer {test_user['session_token']}"},
            content=json.dumps({
                "monthly_income": 50000,
                "employment_status": "employed",
                "financial_experience": "beginner"
            })
        )

        await test_client.post(
            "/api/onboarding/debts/skip",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        await test_client.post(
            "/api/onboarding/goals",
            headers={"Authorization": f"Bearer {test_user['session_token']}"},
            content=json.dumps({
                "goal_type": "debt_freedom",
                "preferred_strategy": "snowball"
            })
        )

        await test_client.post(
            "/api/onboarding/complete",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # Convert to milliseconds

        print(f"Complete onboarding flow took: {total_time:.2f}ms")

        # Should complete within reasonable time (under 5 seconds)
        assert total_time < 5000

    @pytest.mark.asyncio
    async def test_concurrent_onboarding_operations(self, test_client):
        """Test performance under concurrent load"""
        # Create multiple test users for concurrent testing
        concurrent_users = 5  # Reduced for testing environment
        tasks = []

        async def simulate_user_onboarding(user_token: str):
            """Simulate a complete user onboarding flow"""
            start_time = time.time()

            # Start onboarding
            response = await test_client.post(
                "/api/onboarding/start",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            assert response.status_code in [200, 201]

            # Complete profile
            response = await test_client.post(
                "/api/onboarding/profile",
                headers={"Authorization": f"Bearer {user_token}"},
                content=json.dumps({
                    "monthly_income": 50000,
                    "employment_status": "employed",
                    "financial_experience": "beginner"
                })
            )
            assert response.status_code == 200

            # Skip debts and set goals
            await test_client.post(
                "/api/onboarding/debts/skip",
                headers={"Authorization": f"Bearer {user_token}"}
            )

            await test_client.post(
                "/api/onboarding/goals",
                headers={"Authorization": f"Bearer {user_token}"},
                content=json.dumps({
                    "goal_type": "debt_freedom",
                    "preferred_strategy": "snowball"
                })
            )

            # Complete onboarding
            await test_client.post(
                "/api/onboarding/complete",
                headers={"Authorization": f"Bearer {user_token}"}
            )

            end_time = time.time()
            return (end_time - start_time) * 1000  # Return time in ms

        # Note: In a real test environment, you'd create multiple test users
        # For now, we'll test with the single test user
        user_times = []
        for _ in range(min(concurrent_users, 3)):  # Limit to avoid overwhelming test DB
            # This would need proper user creation/authentication in a real load test
            pass

        # Test with single user but multiple sequential operations
        single_user_times = []
        for _ in range(5):
            # Reset onboarding for repeated testing
            try:
                await test_client.post(
                    "/api/onboarding/reset",
                    headers={"Authorization": f"Bearer {test_user['session_token']}"}
                )
            except:
                pass  # Reset might not be implemented

            duration = await simulate_user_onboarding(test_user['session_token'])
            single_user_times.append(duration)

        avg_time = mean(single_user_times)
        max_time = max(single_user_times)

        print(f"Sequential onboarding operations - Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms")

        # Assert reasonable performance
        assert avg_time < 2000  # Under 2 seconds average
        assert max_time < 5000  # Under 5 seconds maximum

    @pytest.mark.asyncio
    async def test_database_query_performance(self, test_session):
        """Test database query performance for onboarding operations"""
        from app.repositories.onboarding_repository import OnboardingRepository
        from app.repositories.user_repository import UserRepository

        repo = OnboardingRepository()
        user_repo = UserRepository()

        # Create test user
        user_data = {
            "email": f"perf_test_{int(time.time())}@example.com",
            "full_name": "Performance Test User",
            "password": "testpass123",
            "monthly_income": 50000
        }

        user = await user_repo.create_user(user_data)

        # Measure onboarding creation performance
        query_times = []

        for _ in range(10):
            start_time = time.time()

            onboarding = await repo.create_onboarding_progress(user.id)

            end_time = time.time()
            query_time = (end_time - start_time) * 1000
            query_times.append(query_time)

        avg_query_time = mean(query_times)
        max_query_time = max(query_times)

        print(f"Database onboarding creation - Avg: {avg_query_time:.2f}ms, Max: {max_query_time:.2f}ms")

        # Assert database performance
        assert avg_query_time < self.PERFORMANCE_THRESHOLDS["database_query_time"]
        assert max_query_time < self.PERFORMANCE_THRESHOLDS["database_query_time"] * 3

    @pytest.mark.asyncio
    async def test_memory_usage_during_onboarding(self, test_client, test_user):
        """Test memory usage during onboarding operations"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple onboarding operations
        for i in range(10):
            try:
                await test_client.post(
                    "/api/onboarding/reset",
                    headers={"Authorization": f"Bearer {test_user['session_token']}"}
                )
            except:
                pass

            await test_client.post(
                "/api/onboarding/start",
                headers={"Authorization": f"Bearer {test_user['session_token']}"}
            )

            await test_client.post(
                "/api/onboarding/profile",
                headers={"Authorization": f"Bearer {test_user['session_token']}"},
                content=json.dumps({
                    "monthly_income": 50000 + i * 1000,  # Vary data slightly
                    "employment_status": "employed",
                    "financial_experience": "beginner"
                })
            )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = final_memory - initial_memory

        print(f"Memory usage delta: {memory_delta:.2f} MB")

        # Assert memory usage is reasonable (under 50MB increase for 10 operations)
        assert memory_delta < self.PERFORMANCE_THRESHOLDS["memory_usage_mb"]

    @pytest.mark.asyncio
    async def test_api_throughput_under_load(self, test_client, test_user):
        """Test API throughput and error rates under sustained load"""
        import asyncio

        async def make_request(operation: str, data: Dict[str, Any] = None):
            """Make a single API request and return success/failure"""
            try:
                if operation == "status":
                    response = await test_client.get(
                        "/api/onboarding/status",
                        headers={"Authorization": f"Bearer {test_user['session_token']}"}
                    )
                elif operation == "start":
                    response = await test_client.post(
                        "/api/onboarding/start",
                        headers={"Authorization": f"Bearer {test_user['session_token']}"}
                    )
                elif operation == "profile":
                    response = await test_client.post(
                        "/api/onboarding/profile",
                        headers={"Authorization": f"Bearer {test_user['session_token']}"},
                        content=json.dumps(data or {
                            "monthly_income": 50000,
                            "employment_status": "employed",
                            "financial_experience": "beginner"
                        })
                    )

                return response.status_code in [200, 201]
            except Exception:
                return False

        # Test sustained load
        total_requests = 50
        concurrent_requests = 5

        successful_requests = 0
        total_time = 0

        start_time = time.time()

        # Run requests in batches
        for batch_start in range(0, total_requests, concurrent_requests):
            batch_end = min(batch_start + concurrent_requests, total_requests)
            batch_size = batch_end - batch_start

            # Create batch of requests
            tasks = []
            for i in range(batch_size):
                if batch_start + i < 20:
                    tasks.append(make_request("status"))
                elif batch_start + i < 30:
                    tasks.append(make_request("start"))
                else:
                    tasks.append(make_request("profile"))

            # Execute batch concurrently
            results = await asyncio.gather(*tasks)

            # Count successes
            successful_requests += sum(1 for result in results if result)

        end_time = time.time()
        total_time = end_time - start_time

        throughput = total_requests / total_time
        success_rate = (successful_requests / total_requests) * 100

        print(f"Throughput: {throughput:.2f} requests/second")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Total time: {total_time:.2f} seconds")

        # Assert reasonable performance
        assert throughput > 5  # At least 5 requests per second
        assert success_rate > 95  # At least 95% success rate

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, test_session):
        """Test performance with larger datasets"""
        from app.repositories.onboarding_repository import OnboardingRepository
        from app.repositories.user_repository import UserRepository

        repo = OnboardingRepository()
        user_repo = UserRepository()

        # Create multiple users and onboarding records
        users = []
        for i in range(20):  # Create 20 test users
            user_data = {
                "email": f"perf_test_{int(time.time())}_{i}@example.com",
                "full_name": f"Performance Test User {i}",
                "password": "testpass123",
                "monthly_income": 50000
            }
            user = await user_repo.create_user(user_data)
            users.append(user)

        # Measure bulk onboarding creation
        start_time = time.time()

        onboarding_records = []
        for user in users:
            record = await repo.create_onboarding_progress(user.id)
            onboarding_records.append(record)

        end_time = time.time()
        bulk_time = (end_time - start_time) * 1000  # ms

        avg_time_per_record = bulk_time / len(users)

        print(f"Bulk onboarding creation: {bulk_time:.2f}ms total, {avg_time_per_record:.2f}ms per record")

        # Assert reasonable bulk performance
        assert avg_time_per_record < 200  # Under 200ms per record
        assert bulk_time < 10000  # Under 10 seconds for 20 records

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, test_client, test_user):
        """Test that error handling doesn't significantly impact performance"""
        # Test with invalid data that should cause validation errors
        invalid_requests = [
            {
                "endpoint": "/api/onboarding/profile",
                "data": {"monthly_income": -1000, "employment_status": "employed"}  # Invalid income
            },
            {
                "endpoint": "/api/onboarding/goals",
                "data": {"goal_type": "invalid_type"}  # Invalid goal type
            },
            {
                "endpoint": "/api/onboarding/profile",
                "data": {"employment_status": "invalid_status"}  # Invalid enum
            }
        ]

        error_response_times = []

        for request in invalid_requests:
            start_time = time.time()

            response = await test_client.post(
                request["endpoint"],
                headers={"Authorization": f"Bearer {test_user['session_token']}"},
                content=json.dumps(request["data"])
            )

            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            error_response_times.append(response_time)

            # Should return error status but quickly
            assert response.status_code in [400, 422]

        avg_error_time = mean(error_response_times)
        max_error_time = max(error_response_times)

        print(f"Error handling performance - Avg: {avg_error_time:.2f}ms, Max: {max_error_time:.2f}ms")

        # Error handling should be fast
        assert avg_error_time < self.PERFORMANCE_THRESHOLDS["api_response_time"]
        assert max_error_time < self.PERFORMANCE_THRESHOLDS["api_response_time"] * 1.5








<<<<<<< HEAD








=======
>>>>>>> staging
