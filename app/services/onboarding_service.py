"""
Onboarding Service Layer for DebtEase
Handles business logic for user onboarding flow including step progression, data validation, and completion tracking
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.goals_repository import GoalsRepository
from app.repositories.user_repository import UserRepository
from app.models.onboarding import (
    OnboardingStep,
    OnboardingProgressResponse,
    OnboardingProfileData,
    OnboardingGoalData,
    UserGoalCreate,
    calculate_onboarding_progress,
    get_next_step
)
from app.models.user import UserOnboardingUpdate, UserUpdate
from app.models.user import UserResponse

logger = logging.getLogger(__name__)


class OnboardingValidationError(Exception):
    """Custom exception for onboarding validation errors"""
    def __init__(self, message: str, step: Optional[OnboardingStep] = None, field: Optional[str] = None):
        self.message = message
        self.step = step
        self.field = field
        super().__init__(message)


class OnboardingService:
    """
    Service layer for onboarding operations, providing business logic
    for the onboarding flow including step progression, validation, and completion tracking
    """

    def __init__(
        self,
        onboarding_repo: OnboardingRepository,
        goals_repo: GoalsRepository,
        user_repo: UserRepository
    ):
        self.onboarding_repo = onboarding_repo
        self.goals_repo = goals_repo
        self.user_repo = user_repo

    async def start_onboarding(self, user_id: UUID) -> Dict[str, Any]:
        """
        Initialize onboarding process for a new user.

        Args:
            user_id: The user's UUID

        Returns:
            Onboarding status with current step and progress

        Raises:
            OnboardingValidationError: If onboarding already exists
        """
        try:
            logger.info(f"Starting onboarding for user {user_id}")

            # Check if onboarding already exists
            existing_onboarding = await self.onboarding_repo.get_user_onboarding(user_id)
            if existing_onboarding:
                if existing_onboarding.is_completed:
                    raise OnboardingValidationError(
                        "User has already completed onboarding",
                        step=OnboardingStep.COMPLETED
                    )
                else:
                    # Return existing onboarding status
                    return await self.get_onboarding_status(user_id)

            # Create new onboarding progress
            onboarding_progress = await self.onboarding_repo.create_onboarding_progress(user_id)

            logger.info(f"Successfully started onboarding for user {user_id}")

            # Return the created onboarding data directly instead of fetching again
            return {
                "id": str(onboarding_progress.id),
                "user_id": str(onboarding_progress.user_id),
                "current_step": onboarding_progress.current_step.value,
                "completed_steps": onboarding_progress.completed_steps,
                "onboarding_data": onboarding_progress.onboarding_data,
                "is_completed": onboarding_progress.is_completed,
                "progress_percentage": onboarding_progress.progress_percentage,
                "started_at": onboarding_progress.started_at.isoformat() if onboarding_progress.started_at else None,
                "completed_at": onboarding_progress.completed_at.isoformat() if onboarding_progress.completed_at else None
            }

        except Exception as e:
            logger.error(f"Failed to start onboarding for user {user_id}: {e}")
            if isinstance(e, OnboardingValidationError):
                raise
            raise OnboardingValidationError(f"Failed to start onboarding: {str(e)}")

    async def get_onboarding_status(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get current onboarding status for a user.

        Args:
            user_id: The user's UUID

        Returns:
            OnboardingProgressResponse compatible data structure
        """
        try:
            logger.info(f"Getting onboarding status for user {user_id}")

            onboarding = await self.onboarding_repo.get_user_onboarding(user_id)

            if not onboarding:
                # Return default onboarding progress structure for new users
                return {
                    "id": None,  # Will be set when onboarding starts
                    "user_id": str(user_id),
                    "current_step": OnboardingStep.WELCOME.value,
                    "completed_steps": [],
                    "onboarding_data": {},
                    "is_completed": False,
                    "progress_percentage": 0.0,
                    "started_at": None,
                    "completed_at": None
                }

            # Return existing onboarding data in frontend-compatible format
            return {
                "id": str(onboarding.id),
                "user_id": str(onboarding.user_id),
                "current_step": onboarding.current_step.value,
                "completed_steps": onboarding.completed_steps,
                "onboarding_data": onboarding.onboarding_data,
                "is_completed": onboarding.is_completed,
                "progress_percentage": onboarding.progress_percentage,
                "started_at": onboarding.started_at.isoformat() if onboarding.started_at else None,
                "completed_at": onboarding.completed_at.isoformat() if onboarding.completed_at else None
            }

        except Exception as e:
            logger.error(f"Failed to get onboarding status for user {user_id}: {e}")
            raise OnboardingValidationError(f"Failed to get onboarding status: {str(e)}")

    async def update_profile_step(
        self,
        user_id: UUID,
        profile_data: OnboardingProfileData
    ) -> Dict[str, Any]:
        """
        Handle profile setup step completion.

        Args:
            user_id: The user's UUID
            profile_data: Profile data to update

        Returns:
            Updated onboarding status

        Raises:
            OnboardingValidationError: If validation fails
        """
        try:
            logger.info(f"Updating profile step for user {user_id}")

            # Validate profile data
            await self._validate_profile_data(profile_data)

            # Update user profile in database
            user_update = UserOnboardingUpdate(
                monthly_income=profile_data.monthly_income,
                income_frequency=profile_data.income_frequency,
                employment_status=profile_data.employment_status,
                financial_experience=profile_data.financial_experience
            )

            updated_user = await self.user_repo.update_user(user_id, user_update)
            if not updated_user:
                raise OnboardingValidationError("Failed to update user profile")

            # Update onboarding progress
            step_data = {
                "monthly_income": profile_data.monthly_income,
                "income_frequency": profile_data.income_frequency.value,
                "employment_status": profile_data.employment_status.value if profile_data.employment_status else None,
                "financial_experience": profile_data.financial_experience.value,
                "updated_at": datetime.now().isoformat()
            }

            await self.onboarding_repo.update_onboarding_step(
                user_id=user_id,
                step=OnboardingStep.PROFILE_SETUP,
                step_data=step_data
            )

            # Mark step as completed
            await self.onboarding_repo.mark_step_completed(user_id, OnboardingStep.PROFILE_SETUP.value)

            logger.info(f"Successfully updated profile step for user {user_id}")
            return await self.get_onboarding_status(user_id)

        except Exception as e:
            logger.error(f"Failed to update profile step for user {user_id}: {e}")
            if isinstance(e, OnboardingValidationError):
                raise
            raise OnboardingValidationError(f"Failed to update profile: {str(e)}")

    async def skip_debt_collection(self, user_id: UUID) -> Dict[str, Any]:
        """
        Skip debt collection step (user chooses not to add debts).

        Args:
            user_id: The user's UUID

        Returns:
            Updated onboarding status

        Raises:
            OnboardingValidationError: If operation fails
        """
        try:
            logger.info(f"Skipping debt collection for user {user_id}")

            # Update onboarding data to indicate debt collection was skipped
            step_data = {
                "skip_debt_entry": True,
                "debts_added": 0,
                "total_debt_amount": 0.0,
                "debt_types": [],
                "skipped_at": datetime.now().isoformat()
            }

            await self.onboarding_repo.update_onboarding_step(
                user_id=user_id,
                step=OnboardingStep.DEBT_COLLECTION,
                step_data=step_data
            )

            # Mark step as completed
            await self.onboarding_repo.mark_step_completed(user_id, OnboardingStep.DEBT_COLLECTION.value)

            logger.info(f"Successfully skipped debt collection for user {user_id}")
            return await self.get_onboarding_status(user_id)

        except Exception as e:
            logger.error(f"Failed to skip debt collection for user {user_id}: {e}")
            raise OnboardingValidationError(f"Failed to skip debt collection: {str(e)}")

    async def set_financial_goals(
        self,
        user_id: UUID,
        goal_data: OnboardingGoalData
    ) -> Dict[str, Any]:
        """
        Handle goal setting step completion.

        Args:
            user_id: The user's UUID
            goal_data: Goal data to create

        Returns:
            Updated onboarding status

        Raises:
            OnboardingValidationError: If validation fails
        """
        try:
            logger.info(f"Setting financial goals for user {user_id}")

            # Validate goal data
            await self._validate_goal_data(goal_data)

            # Create user goal
            goal_create = UserGoalCreate(
                user_id=user_id,
                goal_type=goal_data.goal_type,
                target_amount=goal_data.target_amount,
                target_date=goal_data.target_date,
                preferred_strategy=goal_data.preferred_strategy,
                monthly_extra_payment=goal_data.monthly_extra_payment,
                priority_level=goal_data.priority_level,
                description=goal_data.description
            )

            created_goal = await self.goals_repo.create_user_goal(goal_create)

            # Update onboarding progress
            step_data = {
                "goal_id": str(created_goal.id),
                "goal_type": goal_data.goal_type,
                "target_amount": goal_data.target_amount,
                "target_date": goal_data.target_date.isoformat() if goal_data.target_date else None,
                "preferred_strategy": goal_data.preferred_strategy,
                "monthly_extra_payment": goal_data.monthly_extra_payment,
                "priority_level": goal_data.priority_level,
                "description": goal_data.description,
                "created_at": datetime.now().isoformat()
            }

            await self.onboarding_repo.update_onboarding_step(
                user_id=user_id,
                step=OnboardingStep.GOAL_SETTING,
                step_data=step_data
            )

            # Mark step as completed
            await self.onboarding_repo.mark_step_completed(user_id, OnboardingStep.GOAL_SETTING.value)

            logger.info(f"Successfully set financial goals for user {user_id}")
            return await self.get_onboarding_status(user_id)

        except Exception as e:
            logger.error(f"Failed to set financial goals for user {user_id}: {e}")
            if isinstance(e, OnboardingValidationError):
                raise
            raise OnboardingValidationError(f"Failed to set goals: {str(e)}")

    async def complete_onboarding(self, user_id: UUID) -> Dict[str, Any]:
        """
        Complete the onboarding process.

        Args:
            user_id: The user's UUID

        Returns:
            Final onboarding status

        Raises:
            OnboardingValidationError: If completion fails
        """
        try:
            logger.info(f"Completing onboarding for user {user_id}")

            # Verify all required steps are completed
            await self._validate_onboarding_completion(user_id)

            # Mark onboarding as completed
            await self.onboarding_repo.complete_onboarding(user_id)

            # Update user record to mark onboarding as completed
            user_update = UserUpdate(onboarding_completed=True)
            await self.user_repo.update_user(user_id, user_update)

            logger.info(f"Successfully completed onboarding for user {user_id}")
            return await self.get_onboarding_status(user_id)

        except Exception as e:
            logger.error(f"Failed to complete onboarding for user {user_id}: {e}")
            if isinstance(e, OnboardingValidationError):
                raise
            raise OnboardingValidationError(f"Failed to complete onboarding: {str(e)}")

    async def reset_onboarding(self, user_id: UUID) -> Dict[str, Any]:
        """
        Reset onboarding progress for a user.

        Args:
            user_id: The user's UUID

        Returns:
            Reset onboarding status

        Raises:
            OnboardingValidationError: If reset fails
        """
        try:
            logger.info(f"Resetting onboarding for user {user_id}")

            # Reset onboarding progress
            await self.onboarding_repo.reset_onboarding(user_id)

            # Reset user onboarding completion status
            user_update = {
                "onboarding_completed": False,
                "onboarding_completed_at": None
            }
            await self.user_repo.update_user(user_id, user_update)

            logger.info(f"Successfully reset onboarding for user {user_id}")
            return await self.get_onboarding_status(user_id)

        except Exception as e:
            logger.error(f"Failed to reset onboarding for user {user_id}: {e}")
            raise OnboardingValidationError(f"Failed to reset onboarding: {str(e)}")

    async def go_to_step(self, user_id: UUID, step: OnboardingStep) -> Dict[str, Any]:
        """
        Navigate to a specific onboarding step.

        Args:
            user_id: The user's UUID
            step: The step to navigate to

        Returns:
            Updated onboarding status

        Raises:
            OnboardingValidationError: If navigation fails
        """
        try:
            logger.info(f"Navigating user {user_id} to step {step.value}")

            # Update current step
            await self.onboarding_repo.update_onboarding_step(
                user_id=user_id,
                step=step,
                step_data={"navigated_to_step": step.value, "navigation_time": datetime.now().isoformat()}
            )

            logger.info(f"Successfully navigated user {user_id} to step {step.value}")
            return await self.get_onboarding_status(user_id)

        except Exception as e:
            logger.error(f"Failed to navigate user {user_id} to step {step.value}: {e}")
            raise OnboardingValidationError(f"Failed to navigate to step: {str(e)}")

    async def get_onboarding_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get onboarding analytics for a user.

        Args:
            user_id: The user's UUID

        Returns:
            Onboarding analytics data compatible with frontend expectations
        """
        try:
            logger.info(f"Getting onboarding analytics for user {user_id}")

            # Get overall onboarding summary statistics
            summary = await self.onboarding_repo.get_onboarding_summary()

            # Get user's personal analytics
            user_analytics = await self.onboarding_repo.get_onboarding_analytics(user_id)

            # Get user's analytics records for detailed drop-off analysis
            analytics_records = await self.onboarding_repo.get_user_onboarding_analytics(user_id)

            # Calculate drop-off points from analytics records
            drop_off_points = []
            completion_rates = []
            for record in analytics_records:
                if record.drop_off_point:
                    drop_off_points.append(record.drop_off_point)
                if record.completion_rate is not None:
                    completion_rates.append(record.completion_rate)

            # Calculate average completion rate
            avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0

            # Return data structure that matches frontend expectations
            return {
                "completion_rate": summary.get("completion_rate_percentage", 0),
                "average_time_spent": summary.get("avg_completion_time_hours", 0),
                "drop_off_points": drop_off_points,
                "total_started": summary.get("total_users", 0),
                "total_completed": summary.get("completed_users", 0),
                # Additional user-specific data
                "user_progress": user_analytics,
                "user_completion_rate": avg_completion_rate
            }

        except Exception as e:
            logger.error(f"Failed to get onboarding analytics for user {user_id}: {e}")
            raise OnboardingValidationError(f"Failed to get analytics: {str(e)}")

    # Private validation methods
    async def _validate_profile_data(self, profile_data: OnboardingProfileData) -> None:
        """
        Validate profile data.

        Args:
            profile_data: Profile data to validate

        Raises:
            OnboardingValidationError: If validation fails
        """
        if profile_data.monthly_income is not None and profile_data.monthly_income <= 0:
            raise OnboardingValidationError(
                "Monthly income must be greater than 0",
                step=OnboardingStep.PROFILE_SETUP,
                field="monthly_income"
            )

        # Additional validation can be added here as needed

    async def _validate_goal_data(self, goal_data: OnboardingGoalData) -> None:
        """
        Validate goal data.

        Args:
            goal_data: Goal data to validate

        Raises:
            OnboardingValidationError: If validation fails
        """
        if goal_data.target_amount is not None and goal_data.target_amount <= 0:
            raise OnboardingValidationError(
                "Target amount must be greater than 0",
                step=OnboardingStep.GOAL_SETTING,
                field="target_amount"
            )

        if goal_data.monthly_extra_payment is not None and goal_data.monthly_extra_payment < 0:
            raise OnboardingValidationError(
                "Monthly extra payment cannot be negative",
                step=OnboardingStep.GOAL_SETTING,
                field="monthly_extra_payment"
            )

        if goal_data.target_date and goal_data.target_date <= datetime.now().date():
            raise OnboardingValidationError(
                "Target date must be in the future",
                step=OnboardingStep.GOAL_SETTING,
                field="target_date"
            )

    async def _validate_onboarding_completion(self, user_id: UUID) -> None:
        """
        Validate that onboarding can be completed.

        Args:
            user_id: The user's UUID

        Raises:
            OnboardingValidationError: If completion validation fails
        """
        onboarding = await self.onboarding_repo.get_user_onboarding(user_id)
        if not onboarding:
            raise OnboardingValidationError("No onboarding progress found")

        required_steps = [OnboardingStep.PROFILE_SETUP.value, OnboardingStep.GOAL_SETTING.value]
        missing_steps = []

        for step in required_steps:
            if step not in onboarding.completed_steps:
                missing_steps.append(step)

        if missing_steps:
            raise OnboardingValidationError(
                f"Cannot complete onboarding. Missing required steps: {', '.join(missing_steps)}"
            )

    async def _calculate_step_completion_times(self, user_id: UUID) -> Dict[str, Any]:
        """
        Calculate completion times for each step.

        Args:
            user_id: The user's UUID

        Returns:
            Dictionary with step completion time data
        """
        onboarding = await self.onboarding_repo.get_user_onboarding(user_id)
        if not onboarding or not onboarding.onboarding_data:
            return {}

        step_times = {}
        onboarding_data = onboarding.onboarding_data

        for step in OnboardingStep:
            step_key = step.value
            if step_key in onboarding_data and "updated_at" in onboarding_data[step_key]:
                try:
                    updated_at = datetime.fromisoformat(onboarding_data[step_key]["updated_at"])
                    if onboarding.started_at:
                        time_spent = updated_at - onboarding.started_at
                        step_times[step_key] = {
                            "completed_at": updated_at.isoformat(),
                            "time_spent_seconds": int(time_spent.total_seconds())
                        }
                except (ValueError, TypeError):
                    continue

        return step_times

    async def _calculate_data_completeness(self, user_id: UUID) -> float:
        """
        Calculate percentage of data completeness for AI readiness.

        Args:
            user_id: The user's UUID

        Returns:
            Percentage of data completeness (0-100)
        """
        try:
            completeness_score = 0.0
            max_score = 4.0  # Profile + Debt + Goals + Completion

            # Check profile completeness
            user = await self.user_repo.get_user_by_id(user_id)
            if user and user.monthly_income:
                completeness_score += 1.0

            # Check onboarding progress
            onboarding = await self.onboarding_repo.get_user_onboarding(user_id)
            if onboarding:
                # Profile step
                if OnboardingStep.PROFILE_SETUP.value in onboarding.completed_steps:
                    completeness_score += 0.5

                # Debt collection (can be skipped)
                if OnboardingStep.DEBT_COLLECTION.value in onboarding.completed_steps:
                    completeness_score += 0.5

                # Goals
                if OnboardingStep.GOAL_SETTING.value in onboarding.completed_steps:
                    completeness_score += 0.5

                # Completion
                if onboarding.is_completed:
                    completeness_score += 1.0

            return min((completeness_score / max_score) * 100, 100.0)

        except Exception as e:
            logger.error(f"Failed to calculate data completeness for user {user_id}: {e}")
            return 0.0
