"""
Onboarding Service Layer Tests
Unit tests for onboarding business logic, validation, and state management.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.onboarding_service import OnboardingService, OnboardingValidationError
from app.models.onboarding import (
    OnboardingStep,
    OnboardingProfileData,
    OnboardingGoalData,
    UserGoalCreate
)


@pytest.mark.unit
class TestOnboardingService:
    """Test suite for OnboardingService business logic"""

    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories for testing"""
        onboarding_repo = AsyncMock()
        goals_repo = AsyncMock()
        user_repo = AsyncMock()

        return {
            "onboarding_repo": onboarding_repo,
            "goals_repo": goals_repo,
            "user_repo": user_repo
        }

    @pytest.fixture
    def service(self, mock_repos):
        """Create OnboardingService instance with mocked repositories"""
        return OnboardingService(
            onboarding_repo=mock_repos["onboarding_repo"],
            goals_repo=mock_repos["goals_repo"],
            user_repo=mock_repos["user_repo"]
        )

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing"""
        return uuid4()

    @pytest.fixture
    def sample_profile_data(self):
        """Sample valid profile data"""
        return OnboardingProfileData(
            monthly_income=50000,
            income_frequency="monthly",
            employment_status="employed",
            financial_experience="intermediate"
        )

    @pytest.fixture
    def sample_goal_data(self):
        """Sample valid goal data"""
        return OnboardingGoalData(
            goal_type="debt_freedom",
            preferred_strategy="snowball",
            priority_level=8,
            monthly_extra_payment=3000
        )

    def test_service_initialization(self, mock_repos):
        """Test service initializes with repositories"""
        service = OnboardingService(
            onboarding_repo=mock_repos["onboarding_repo"],
            goals_repo=mock_repos["goals_repo"],
            user_repo=mock_repos["user_repo"]
        )

        assert service.onboarding_repo == mock_repos["onboarding_repo"]
        assert service.goals_repo == mock_repos["goals_repo"]
        assert service.user_repo == mock_repos["user_repo"]

    @pytest.mark.asyncio
    async def test_start_onboarding_new_user(self, service, sample_user_id, mock_repos):
        """Test starting onboarding for new user"""
        # Mock repository to return None (no existing onboarding)
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = None
        mock_repos["onboarding_repo"].create_onboarding_progress.return_value = {
            "id": str(uuid4()),
            "user_id": str(sample_user_id),
            "current_step": "welcome",
            "completed_steps": [],
            "onboarding_data": {},
            "is_completed": False,
            "progress_percentage": 0.0,
            "started_at": datetime.now().isoformat()
        }

        result = await service.start_onboarding(sample_user_id)

        assert result["current_step"] == "welcome"
        assert result["completed_steps"] == []
        assert result["is_completed"] is False
        assert result["progress_percentage"] == 0.0

        # Verify repository calls (called once in start_onboarding, once in get_onboarding_status)
        assert mock_repos["onboarding_repo"].get_user_onboarding.call_count == 2
        mock_repos["onboarding_repo"].get_user_onboarding.assert_any_call(sample_user_id)
        mock_repos["onboarding_repo"].create_onboarding_progress.assert_called_once_with(sample_user_id)

    @pytest.mark.asyncio
    async def test_start_onboarding_existing_incomplete(self, service, sample_user_id, mock_repos):
        """Test starting onboarding when incomplete onboarding exists"""
        existing_onboarding = {
            "id": str(uuid4()),
            "user_id": str(sample_user_id),
            "current_step": "profile_setup",
            "completed_steps": ["welcome"],
            "onboarding_data": {},
            "is_completed": False,
            "progress_percentage": 25.0,
            "started_at": datetime.now().isoformat()
        }

        mock_repos["onboarding_repo"].get_user_onboarding.return_value = existing_onboarding

        result = await service.start_onboarding(sample_user_id)

        # Should return existing status, not create new
        assert result["current_step"] == "profile_setup"
        assert result["completed_steps"] == ["welcome"]
        assert result["progress_percentage"] == 25.0

        # Should not create new onboarding
        mock_repos["onboarding_repo"].create_onboarding_progress.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_onboarding_already_completed(self, service, sample_user_id, mock_repos):
        """Test starting onboarding when already completed"""
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = {
            "is_completed": True,
            "current_step": "completed"
        }

        with pytest.raises(OnboardingValidationError, match="User has already completed onboarding"):
            await service.start_onboarding(sample_user_id)

    @pytest.mark.asyncio
    async def test_get_onboarding_status_with_data(self, service, sample_user_id, mock_repos):
        """Test getting onboarding status with existing data"""
        mock_onboarding = {
            "id": str(uuid4()),
            "user_id": str(sample_user_id),
            "current_step": "debt_collection",
            "completed_steps": ["welcome", "profile_setup"],
            "onboarding_data": {"profile": {"monthly_income": 50000}},
            "is_completed": False,
            "progress_percentage": 50.0,
            "started_at": datetime.now(),
            "completed_at": None
        }

        mock_repos["onboarding_repo"].get_user_onboarding.return_value = mock_onboarding

        result = await service.get_onboarding_status(sample_user_id)

        assert result["id"] == mock_onboarding["id"]
        assert result["user_id"] == str(sample_user_id)
        assert result["current_step"] == "debt_collection"
        assert result["completed_steps"] == ["welcome", "profile_setup"]
        assert result["progress_percentage"] == 50.0
        assert result["is_completed"] is False

    @pytest.mark.asyncio
    async def test_get_onboarding_status_new_user(self, service, sample_user_id, mock_repos):
        """Test getting onboarding status for user with no onboarding"""
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = None

        result = await service.get_onboarding_status(sample_user_id)

        # Should return default state
        assert result["id"] is None
        assert result["user_id"] == str(sample_user_id)
        assert result["current_step"] == "welcome"
        assert result["completed_steps"] == []
        assert result["is_completed"] is False
        assert result["progress_percentage"] == 0.0
        assert result["started_at"] is None
        assert result["completed_at"] is None
        assert result["onboarding_data"] == {}

    @pytest.mark.asyncio
    async def test_update_profile_success(self, service, sample_user_id, sample_profile_data, mock_repos):
        """Test successful profile update"""
        # Mock existing onboarding
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = {
            "current_step": "welcome",
            "completed_steps": []
        }

        # Mock user update
        mock_repos["user_repo"].update_user.return_value = {
            "id": str(sample_user_id),
            "monthly_income": 50000
        }

        # Mock onboarding step updates
        mock_repos["onboarding_repo"].update_onboarding_step.return_value = {
            "current_step": "profile_setup",
            "completed_steps": ["welcome", "profile_setup"]
        }

        result = await service.update_profile_step(sample_user_id, sample_profile_data)

        # Verify user repo was called with correct data
        mock_repos["user_repo"].update_user.assert_called_once()
        update_call_args = mock_repos["user_repo"].update_user.call_args[0]
        assert update_call_args[0] == sample_user_id
        assert update_call_args[1]["monthly_income"] == 50000
        assert update_call_args[1]["employment_status"] == "employed"

        # Verify onboarding step was updated
        assert mock_repos["onboarding_repo"].update_onboarding_step.called
        assert mock_repos["onboarding_repo"].mark_step_completed.called

        # Verify result contains updated status
        assert result["current_step"] == "profile_setup"
        assert "profile_setup" in result["completed_steps"]

    @pytest.mark.asyncio
    async def test_update_profile_validation_error(self, service, sample_user_id, mock_repos):
        """Test profile update with invalid data"""
        invalid_profile_data = OnboardingProfileData(
            monthly_income=-1000,  # Invalid negative income
            employment_status="employed",
            financial_experience="beginner"
        )

        with pytest.raises(OnboardingValidationError):
            await service.update_profile_step(sample_user_id, invalid_profile_data)

    @pytest.mark.asyncio
    async def test_skip_debt_collection(self, service, sample_user_id, mock_repos):
        """Test skipping debt collection step"""
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = {
            "current_step": "debt_collection",
            "completed_steps": ["welcome", "profile_setup"]
        }

        result = await service.skip_debt_collection(sample_user_id)

        # Verify debt collection was marked as skipped
        update_call = mock_repos["onboarding_repo"].update_onboarding_step.call_args
        assert update_call[1]["step"] == OnboardingStep.DEBT_COLLECTION
        assert update_call[1]["step_data"]["skip_debt_entry"] is True

        # Verify step was completed
        mock_repos["onboarding_repo"].mark_step_completed.assert_called_once_with(
            sample_user_id, OnboardingStep.DEBT_COLLECTION.value
        )

        assert result["current_step"] == "goal_setting"
        assert "debt_collection" in result["completed_steps"]

    @pytest.mark.asyncio
    async def test_set_financial_goals_success(self, service, sample_user_id, sample_goal_data, mock_repos):
        """Test successful goal setting"""
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = {
            "current_step": "goal_setting",
            "completed_steps": ["welcome", "profile_setup", "debt_collection"]
        }

        result = await service.set_financial_goals(sample_user_id, sample_goal_data)

        # Verify goal was created
        mock_repos["goals_repo"].create_user_goal.assert_called_once()
        goal_call_args = mock_repos["goals_repo"].create_user_goal.call_args[0]
        assert goal_call_args[0] == sample_user_id
        assert goal_call_args[1].goal_type == "debt_freedom"
        assert goal_call_args[1].preferred_strategy == "snowball"

        # Verify onboarding was updated
        assert mock_repos["onboarding_repo"].update_onboarding_step.called
        assert mock_repos["onboarding_repo"].mark_step_completed.called

        assert result["current_step"] == "goal_setting"
        assert "goal_setting" in result["completed_steps"]

    @pytest.mark.asyncio
    async def test_set_financial_goals_validation_error(self, service, sample_user_id, mock_repos):
        """Test goal setting with invalid data"""
        invalid_goal_data = OnboardingGoalData(
            goal_type="invalid_type",  # Invalid goal type
            preferred_strategy="snowball"
        )

        with pytest.raises(OnboardingValidationError):
            await service.set_financial_goals(sample_user_id, invalid_goal_data)

    @pytest.mark.asyncio
    async def test_complete_onboarding_success(self, service, sample_user_id, mock_repos):
        """Test successful onboarding completion"""
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = {
            "current_step": "dashboard_intro",
            "completed_steps": ["welcome", "profile_setup", "debt_collection", "goal_setting"],
            "is_completed": False
        }

        result = await service.complete_onboarding(sample_user_id)

        # Verify completion was marked
        complete_call = mock_repos["onboarding_repo"].complete_onboarding.call_args[0]
        assert complete_call[0] == sample_user_id

        assert result["current_step"] == "completed"
        assert result["is_completed"] is True
        assert "dashboard_intro" in result["completed_steps"]

    @pytest.mark.asyncio
    async def test_complete_onboarding_validation_error(self, service, sample_user_id, mock_repos):
        """Test completing onboarding with incomplete steps"""
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = {
            "current_step": "profile_setup",
            "completed_steps": ["welcome"],
            "is_completed": False
        }

        with pytest.raises(OnboardingValidationError, match="Cannot complete onboarding"):
            await service.complete_onboarding(sample_user_id)

    @pytest.mark.asyncio
    async def test_get_onboarding_analytics(self, service, sample_user_id, mock_repos):
        """Test getting onboarding analytics"""
        # Mock repository responses
        mock_repos["onboarding_repo"].get_onboarding_summary.return_value = {
            "completion_rate_percentage": 75.5,
            "total_users": 100,
            "completed_users": 75,
            "avg_completion_time_hours": 2.5
        }

        mock_repos["onboarding_repo"].get_onboarding_analytics.return_value = {
            "has_started": True,
            "current_step": "goal_setting",
            "progress_percentage": 75.0
        }

        mock_repos["onboarding_repo"].get_user_onboarding_analytics.return_value = [
            {"completion_rate": 80.0, "drop_off_point": None},
            {"completion_rate": 90.0, "drop_off_point": "debt_collection"}
        ]

        result = await service.get_onboarding_analytics(sample_user_id)

        # Verify structure
        assert "completion_rate" in result
        assert "average_time_spent" in result
        assert "drop_off_points" in result
        assert "total_started" in result
        assert "total_completed" in result

        # Verify data
        assert result["completion_rate"] == 75.5
        assert result["average_time_spent"] == 2.5
        assert result["total_started"] == 100
        assert result["total_completed"] == 75
        assert "debt_collection" in result["drop_off_points"]

    @pytest.mark.asyncio
    async def test_go_to_step_success(self, service, sample_user_id, mock_repos):
        """Test navigating to a specific step"""
        mock_repos["onboarding_repo"].get_user_onboarding.return_value = {
            "current_step": "welcome",
            "completed_steps": []
        }

        result = await service.go_to_step(sample_user_id, OnboardingStep.PROFILE_SETUP)

        assert result["current_step"] == "profile_setup"

        # Verify repository was called
        mock_repos["onboarding_repo"].update_onboarding_step.assert_called_once()
        update_call = mock_repos["onboarding_repo"].update_onboarding_step.call_args
        assert update_call[1]["step"] == OnboardingStep.PROFILE_SETUP

    @pytest.mark.asyncio
    async def test_reset_onboarding(self, service, sample_user_id, mock_repos):
        """Test resetting onboarding progress"""
        result = await service.reset_onboarding(sample_user_id)

        # Verify reset was called
        mock_repos["onboarding_repo"].reset_onboarding.assert_called_once_with(sample_user_id)

        # Verify result indicates reset
        assert result["current_step"] == "welcome"
        assert result["completed_steps"] == []
        assert result["is_completed"] is False
        assert result["progress_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_service_error_handling(self, service, sample_user_id, mock_repos):
        """Test service error handling"""
        # Simulate repository error
        mock_repos["onboarding_repo"].get_user_onboarding.side_effect = Exception("Database error")

        with pytest.raises(OnboardingValidationError, match="Failed to get onboarding status"):
            await service.get_onboarding_status(sample_user_id)
