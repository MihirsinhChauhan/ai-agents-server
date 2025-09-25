"""
Onboarding Repository Layer Tests
Integration tests for onboarding database operations and data persistence.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.goals_repository import GoalsRepository
from app.models.onboarding import OnboardingStep, OnboardingProgressCreate


@pytest.mark.integration
class TestOnboardingRepository:
    """Test suite for OnboardingRepository database operations"""

    @pytest.mark.asyncio
    async def test_create_onboarding_progress(self, test_session):
        """Test creating new onboarding progress"""
        repo = OnboardingRepository()
        user_id = uuid4()

        result = await repo.create_onboarding_progress(user_id)

        assert result.id is not None
        assert result.user_id == user_id
        assert result.current_step == OnboardingStep.WELCOME
        assert result.completed_steps == []
        assert result.onboarding_data == {}
        assert result.is_completed is False
        assert result.progress_percentage == 0.0
        assert result.started_at is not None

    @pytest.mark.asyncio
    async def test_get_user_onboarding_existing(self, test_session):
        """Test getting existing onboarding progress"""
        repo = OnboardingRepository()
        user_id = uuid4()

        # Create onboarding first
        created = await repo.create_onboarding_progress(user_id)

        # Retrieve it
        retrieved = await repo.get_user_onboarding(user_id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.user_id == user_id
        assert retrieved.current_step == OnboardingStep.WELCOME

    @pytest.mark.asyncio
    async def test_get_user_onboarding_nonexistent(self, test_session):
        """Test getting onboarding for user who hasn't started"""
        repo = OnboardingRepository()
        user_id = uuid4()

        result = await repo.get_user_onboarding(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_onboarding_step(self, test_session):
        """Test updating onboarding step and data"""
        repo = OnboardingRepository()
        user_id = uuid4()

        # Create initial onboarding
        await repo.create_onboarding_progress(user_id)

        # Update step
        step_data = {
            "monthly_income": 50000,
            "employment_status": "employed",
            "updated_at": datetime.now().isoformat()
        }

        result = await repo.update_onboarding_step(
            user_id=user_id,
            step=OnboardingStep.PROFILE_SETUP,
            step_data=step_data
        )

        assert result.current_step == OnboardingStep.PROFILE_SETUP
        assert result.onboarding_data["profile"]["monthly_income"] == 50000
        assert result.onboarding_data["profile"]["employment_status"] == "employed"

    @pytest.mark.asyncio
    async def test_mark_step_completed(self, test_session):
        """Test marking a step as completed"""
        repo = OnboardingRepository()
        user_id = uuid4()

        # Create onboarding
        await repo.create_onboarding_progress(user_id)

        # Mark welcome step as completed
        await repo.mark_step_completed(user_id, OnboardingStep.WELCOME.value)

        # Check that step is in completed_steps
        updated = await repo.get_user_onboarding(user_id)
        assert OnboardingStep.WELCOME.value in updated.completed_steps

    @pytest.mark.asyncio
    async def test_complete_onboarding(self, test_session):
        """Test completing onboarding"""
        repo = OnboardingRepository()
        user_id = uuid4()

        # Create onboarding
        await repo.create_onboarding_progress(user_id)

        # Complete onboarding
        result = await repo.complete_onboarding(user_id)

        assert result.is_completed is True
        assert result.current_step == OnboardingStep.COMPLETED
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_get_onboarding_summary(self, test_session):
        """Test getting onboarding completion summary"""
        repo = OnboardingRepository()

        # Create some test data
        user1 = uuid4()
        user2 = uuid4()

        # Create onboarding for both users
        await repo.create_onboarding_progress(user1)
        await repo.create_onboarding_progress(user2)

        # Complete one user's onboarding
        await repo.complete_onboarding(user1)

        # Get summary
        summary = await repo.get_onboarding_summary()

        assert "total_users" in summary
        assert "completed_users" in summary
        assert "completion_rate_percentage" in summary
        assert summary["total_users"] >= 2
        assert summary["completed_users"] >= 1
        assert 0 <= summary["completion_rate_percentage"] <= 100

    @pytest.mark.asyncio
    async def test_get_onboarding_analytics(self, test_session):
        """Test getting user-specific onboarding analytics"""
        repo = OnboardingRepository()
        user_id = uuid4()

        # Create onboarding
        await repo.create_onboarding_progress(user_id)

        # Get analytics
        analytics = await repo.get_onboarding_analytics(user_id)

        assert analytics["user_id"] == str(user_id)
        assert analytics["has_started"] is True
        assert analytics["current_step"] == OnboardingStep.WELCOME.value
        assert analytics["completed_steps"] == []
        assert analytics["progress_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_reset_onboarding(self, test_session):
        """Test resetting onboarding progress"""
        repo = OnboardingRepository()
        user_id = uuid4()

        # Create and modify onboarding
        await repo.create_onboarding_progress(user_id)
        await repo.update_onboarding_step(
            user_id=user_id,
            step=OnboardingStep.PROFILE_SETUP,
            step_data={"test": "data"}
        )
        await repo.mark_step_completed(user_id, OnboardingStep.WELCOME.value)

        # Reset onboarding
        result = await repo.reset_onboarding(user_id)

        assert result.current_step == OnboardingStep.WELCOME
        assert result.completed_steps == []
        assert result.onboarding_data == {}
        assert result.is_completed is False
        assert result.progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_user_isolation(self, test_session):
        """Test that users' onboarding data is properly isolated"""
        repo = OnboardingRepository()
        user1 = uuid4()
        user2 = uuid4()

        # Create onboarding for both users
        await repo.create_onboarding_progress(user1)
        await repo.create_onboarding_progress(user2)

        # Update user1's progress
        await repo.update_onboarding_step(
            user_id=user1,
            step=OnboardingStep.PROFILE_SETUP,
            step_data={"user": "user1"}
        )

        # Check user2's data is unchanged
        user2_data = await repo.get_user_onboarding(user2)
        assert user2_data.current_step == OnboardingStep.WELCOME
        assert user2_data.onboarding_data == {}

        # Check user1's data is updated
        user1_data = await repo.get_user_onboarding(user1)
        assert user1_data.current_step == OnboardingStep.PROFILE_SETUP
        assert user1_data.onboarding_data["profile"]["user"] == "user1"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_session):
        """Test concurrent onboarding operations"""
        repo = OnboardingRepository()
        user_id = uuid4()

        await repo.create_onboarding_progress(user_id)

        # Simulate concurrent updates
        import asyncio

        async def update_step_1():
            await repo.update_onboarding_step(
                user_id=user_id,
                step=OnboardingStep.PROFILE_SETUP,
                step_data={"step": 1}
            )

        async def update_step_2():
            await repo.update_onboarding_step(
                user_id=user_id,
                step=OnboardingStep.DEBT_COLLECTION,
                step_data={"step": 2}
            )

        # Run concurrent operations
        await asyncio.gather(update_step_1(), update_step_2())

        # Verify final state (last update should win)
        final_data = await repo.get_user_onboarding(user_id)
        assert final_data.onboarding_data["debt_collection"]["step"] == 2

    @pytest.mark.asyncio
    async def test_data_persistence_across_sessions(self, test_session):
        """Test that onboarding data persists correctly"""
        repo = OnboardingRepository()
        user_id = uuid4()

        # Create onboarding
        created = await repo.create_onboarding_progress(user_id)

        # Simulate multiple retrievals (like multiple API calls)
        for _ in range(3):
            retrieved = await repo.get_user_onboarding(user_id)
            assert retrieved.id == created.id
            assert retrieved.user_id == user_id
            assert retrieved.current_step == OnboardingStep.WELCOME

        # Update and verify persistence
        updated = await repo.update_onboarding_step(
            user_id=user_id,
            step=OnboardingStep.PROFILE_SETUP,
            step_data={"persistent": True}
        )

        # Retrieve again and verify update persisted
        final = await repo.get_user_onboarding(user_id)
        assert final.current_step == OnboardingStep.PROFILE_SETUP
        assert final.onboarding_data["profile"]["persistent"] is True


@pytest.mark.integration
class TestGoalsRepository:
    """Test suite for GoalsRepository database operations"""

    @pytest.mark.asyncio
    async def test_create_user_goal(self, test_session):
        """Test creating a user goal"""
        repo = GoalsRepository()
        user_id = uuid4()

        goal_data = {
            "goal_type": "debt_freedom",
            "target_amount": 100000,
            "preferred_strategy": "snowball",
            "priority_level": 8,
            "monthly_extra_payment": 2000,
            "description": "Test goal"
        }

        result = await repo.create_user_goal(user_id, goal_data)

        assert result.id is not None
        assert result.user_id == user_id
        assert result.goal_type == "debt_freedom"
        assert result.target_amount == 100000
        assert result.preferred_strategy == "snowball"
        assert result.priority_level == 8
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_get_user_goals(self, test_session):
        """Test getting user goals"""
        repo = GoalsRepository()
        user_id = uuid4()

        # Create multiple goals
        goal1_data = {"goal_type": "debt_freedom", "preferred_strategy": "snowball"}
        goal2_data = {"goal_type": "save_interest", "preferred_strategy": "avalanche"}

        await repo.create_user_goal(user_id, goal1_data)
        await repo.create_user_goal(user_id, goal2_data)

        # Get all active goals
        goals = await repo.get_user_goals(user_id, active_only=True)

        assert len(goals) == 2
        assert all(goal.user_id == user_id for goal in goals)
        assert all(goal.is_active for goal in goals)

    @pytest.mark.asyncio
    async def test_update_goal_progress(self, test_session):
        """Test updating goal progress"""
        repo = GoalsRepository()
        user_id = uuid4()

        # Create goal
        goal_data = {"goal_type": "debt_freedom", "preferred_strategy": "snowball"}
        created_goal = await repo.create_user_goal(user_id, goal_data)

        # Update progress
        updated_goal = await repo.update_goal_progress(created_goal.id, 75.5)

        assert updated_goal.progress_percentage == 75.5
        assert updated_goal.id == created_goal.id

    @pytest.mark.asyncio
    async def test_delete_goal(self, test_session):
        """Test soft deleting a goal"""
        repo = GoalsRepository()
        user_id = uuid4()

        # Create goal
        goal_data = {"goal_type": "debt_freedom", "preferred_strategy": "snowball"}
        created_goal = await repo.create_user_goal(user_id, goal_data)

        # Delete goal
        success = await repo.delete_goal(created_goal.id)

        assert success is True

        # Verify goal is marked as inactive
        goals = await repo.get_user_goals(user_id, active_only=True)
        assert len(goals) == 0

        # But still exists when including inactive
        all_goals = await repo.get_user_goals(user_id, active_only=False)
        assert len(all_goals) == 1
        assert not all_goals[0].is_active

    @pytest.mark.asyncio
    async def test_activate_goal(self, test_session):
        """Test reactivating a goal"""
        repo = GoalsRepository()
        user_id = uuid4()

        # Create and delete goal
        goal_data = {"goal_type": "debt_freedom", "preferred_strategy": "snowball"}
        created_goal = await repo.create_user_goal(user_id, goal_data)
        await repo.delete_goal(created_goal.id)

        # Reactivate goal
        activated_goal = await repo.activate_goal(created_goal.id)

        assert activated_goal.is_active is True
        assert activated_goal.id == created_goal.id

        # Verify it appears in active goals
        active_goals = await repo.get_user_goals(user_id, active_only=True)
        assert len(active_goals) == 1
        assert active_goals[0].id == created_goal.id













