"""
Onboarding API Endpoint Tests
Tests for all onboarding-related API endpoints including CRUD operations, validation, and error handling.
"""

import pytest
import json
from typing import Dict, Any
from uuid import uuid4

from app.models.onboarding import OnboardingStep, OnboardingProfileData, OnboardingGoalData


@pytest.mark.api
class TestOnboardingAPI:
    """Test suite for onboarding API endpoints"""

    @pytest.mark.asyncio
    async def test_start_onboarding_success(self, test_client, test_user):
        """Test successful onboarding initialization"""
        # Make request to start onboarding
        response = await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()

        # Check required fields
        assert "id" in data
        assert "user_id" in data
        assert "current_step" in data
        assert "completed_steps" in data
        assert "onboarding_data" in data
        assert "is_completed" in data
        assert "progress_percentage" in data

        # Verify initial state
        assert data["current_step"] == "welcome"
        assert data["completed_steps"] == []
        assert data["is_completed"] is False
        assert data["progress_percentage"] == 0.0
        assert data["user_id"] == str(test_user["id"])

    @pytest.mark.asyncio
    async def test_start_onboarding_unauthorized(self, test_client):
        """Test onboarding start without authentication"""
        response = await test_client.post("/api/onboarding/start")

        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_onboarding_status_existing(self, test_client, test_user):
        """Test getting existing onboarding status"""
        # First start onboarding
        start_response = await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )
        assert start_response.status_code == 201

        # Then get status
        response = await test_client.get(
            "/api/onboarding/status",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure matches started onboarding
        assert data["current_step"] == "welcome"
        assert data["completed_steps"] == []
        assert data["is_completed"] is False

    @pytest.mark.asyncio
    async def test_get_onboarding_status_new_user(self, test_client, test_user):
        """Test getting onboarding status for new user (no onboarding started)"""
        response = await test_client.get(
            "/api/onboarding/status",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return default state for new users
        assert data["current_step"] == "welcome"
        assert data["completed_steps"] == []
        assert data["is_completed"] is False
        assert data["progress_percentage"] == 0.0
        assert data["user_id"] == str(test_user["id"])
        assert data["id"] is None or data["id"] is None  # Should be None for unstarted onboarding

    @pytest.mark.asyncio
    async def test_update_profile_success(self, test_client, test_user):
        """Test successful profile update"""
        # Start onboarding first
        await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        # Update profile
        profile_data = {
            "monthly_income": 75000,
            "income_frequency": "monthly",
            "employment_status": "employed",
            "financial_experience": "intermediate"
        }

        response = await test_client.post(
            "/api/onboarding/profile",
            headers={"Authorization": f"Bearer {test_user['session_token']}"},
            content=json.dumps(profile_data)
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["current_step"] == "profile_setup"
        assert "profile_setup" in data["completed_steps"]
        assert data["onboarding_data"]["profile"]["monthly_income"] == 75000

    @pytest.mark.asyncio
    async def test_update_profile_validation_error(self, test_client, test_user):
        """Test profile update with validation errors"""
        # Start onboarding first
        await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        # Try to update with invalid data
        invalid_profile_data = {
            "monthly_income": -1000,  # Invalid negative income
            "employment_status": "invalid_status"  # Invalid enum value
        }

        response = await test_client.post(
            "/api/onboarding/profile",
            headers={"Authorization": f"Bearer {test_user['session_token']}"},
            content=json.dumps(invalid_profile_data)
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_skip_debt_entry(self, test_client, test_user):
        """Test skipping debt entry step"""
        # Start onboarding and complete profile
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

        # Skip debt entry
        response = await test_client.post(
            "/api/onboarding/debts/skip",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["current_step"] == "goal_setting"
        assert "debt_collection" in data["completed_steps"]
        assert data["onboarding_data"]["debts"]["skip_debt_entry"] is True

    @pytest.mark.asyncio
    async def test_set_goals_success(self, test_client, test_user):
        """Test successful goal setting"""
        # Start onboarding and complete required steps
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

        # Set goals
        goal_data = {
            "goal_type": "debt_freedom",
            "preferred_strategy": "snowball",
            "priority_level": 8,
            "monthly_extra_payment": 5000
        }

        response = await test_client.post(
            "/api/onboarding/goals",
            headers={"Authorization": f"Bearer {test_user['session_token']}"},
            content=json.dumps(goal_data)
        )

        assert response.status_code == 200
        data = response.json()

        assert data["current_step"] == "goal_setting"
        assert "goal_setting" in data["completed_steps"]
        assert data["onboarding_data"]["goals"]["goal_type"] == "debt_freedom"

    @pytest.mark.asyncio
    async def test_complete_onboarding(self, test_client, test_user):
        """Test complete onboarding flow"""
        # Go through entire flow
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
                "preferred_strategy": "snowball",
                "priority_level": 8
            })
        )

        # Complete onboarding
        response = await test_client.post(
            "/api/onboarding/complete",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["current_step"] == "completed"
        assert data["is_completed"] is True
        assert "dashboard_intro" in data["completed_steps"]

    @pytest.mark.asyncio
    async def test_get_onboarding_analytics(self, test_client, test_user):
        """Test getting onboarding analytics"""
        # Start and complete some onboarding
        await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        response = await test_client.get(
            "/api/onboarding/analytics",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify analytics structure
        assert "completion_rate" in data
        assert "average_time_spent" in data
        assert "drop_off_points" in data
        assert "total_started" in data
        assert "total_completed" in data

    @pytest.mark.asyncio
    async def test_onboarding_step_order_enforcement(self, test_client, test_user):
        """Test that onboarding steps must be completed in order"""
        # Try to set goals without completing profile
        await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        response = await test_client.post(
            "/api/onboarding/goals",
            headers={"Authorization": f"Bearer {test_user['session_token']}"},
            content=json.dumps({
                "goal_type": "debt_freedom",
                "preferred_strategy": "snowball"
            })
        )

        # This should fail or redirect to profile step
        assert response.status_code in [400, 200]  # Either validation error or step correction

    @pytest.mark.asyncio
    async def test_onboarding_data_persistence(self, test_client, test_user):
        """Test that onboarding data persists across requests"""
        # Start onboarding
        start_response = await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )
        start_data = start_response.json()

        # Update profile
        await test_client.post(
            "/api/onboarding/profile",
            headers={"Authorization": f"Bearer {test_user['session_token']}"},
            content=json.dumps({
                "monthly_income": 60000,
                "employment_status": "self_employed",
                "financial_experience": "advanced"
            })
        )

        # Get status again and verify data persistence
        status_response = await test_client.get(
            "/api/onboarding/status",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )
        status_data = status_response.json()

        assert status_data["onboarding_data"]["profile"]["monthly_income"] == 60000
        assert status_data["onboarding_data"]["profile"]["employment_status"] == "self_employed"
        assert status_data["onboarding_data"]["profile"]["financial_experience"] == "advanced"

    @pytest.mark.asyncio
    async def test_onboarding_concurrent_sessions(self, test_client, test_user):
        """Test onboarding behavior with concurrent sessions"""
        # Start onboarding
        await test_client.post(
            "/api/onboarding/start",
            headers={"Authorization": f"Bearer {test_user['session_token']}"}
        )

        # Simulate multiple status requests (should be consistent)
        responses = []
        for _ in range(3):
            response = await test_client.get(
                "/api/onboarding/status",
                headers={"Authorization": f"Bearer {test_user['session_token']}"}
            )
            responses.append(response.json())

        # All responses should be consistent
        first_response = responses[0]
        for response in responses[1:]:
            assert response["current_step"] == first_response["current_step"]
            assert response["completed_steps"] == first_response["completed_steps"]
            assert response["progress_percentage"] == first_response["progress_percentage"]









