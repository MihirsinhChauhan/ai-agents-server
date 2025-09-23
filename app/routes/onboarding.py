"""
Onboarding routes for DebtEase application.
Handles user onboarding flow including profile setup, debt collection, goal setting, and completion.
Provides comprehensive API endpoints with proper authentication, validation, and error handling.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime

from app.services.onboarding_service import OnboardingService, OnboardingValidationError
from app.repositories.onboarding_repository import OnboardingRepository
from app.repositories.goals_repository import GoalsRepository
from app.repositories.user_repository import UserRepository
from app.middleware.auth import CurrentUser, VerifiedUser
from app.models.onboarding import (
    OnboardingProfileData,
    OnboardingGoalData,
    OnboardingStep,
    UserGoalResponse
)
from app.models.user import UserOnboardingUpdate, UserProfileResponse
from app.databases.database import db_manager

router = APIRouter()

# Dependency injection for service
def get_onboarding_service() -> OnboardingService:
    """Get onboarding service instance with dependencies"""
    return OnboardingService(
        onboarding_repo=OnboardingRepository(),
        goals_repo=GoalsRepository(),
        user_repo=UserRepository()
    )


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_onboarding(
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Initialize onboarding process for authenticated user.
    Creates onboarding progress record and returns initial status.
    """
    try:
        result = await service.start_onboarding(current_user.id)
        return result
    except OnboardingValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start onboarding: {str(e)}"
        )


@router.get("/status")
async def get_onboarding_status(
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Get current onboarding progress and status for authenticated user.
    Returns step information, completion status, and progress percentage.
    """
    try:
        result = await service.get_onboarding_status(current_user.id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get onboarding status: {str(e)}"
        )


@router.post("/profile")
async def update_profile(
    profile_data: OnboardingProfileData,
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Update user profile information during onboarding.
    Handles monthly income, employment status, and financial experience.
    """
    try:
        result = await service.update_profile_step(current_user.id, profile_data)
        return result
    except OnboardingValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post("/debts/skip")
async def skip_debt_entry(
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Skip debt collection step during onboarding.
    Marks debt collection as skipped and advances to next step.
    """
    try:
        result = await service.skip_debt_collection(current_user.id)
        return result
    except OnboardingValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to skip debt entry: {str(e)}"
        )


@router.post("/goals")
async def set_goals(
    goal_data: OnboardingGoalData,
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Set financial goals during onboarding.
    Handles goal type, target amounts, preferred strategies, and priorities.
    """
    try:
        result = await service.set_financial_goals(current_user.id, goal_data)
        return result
    except OnboardingValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set goals: {str(e)}"
        )


@router.post("/complete")
async def complete_onboarding(
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Complete the onboarding process.
    Marks onboarding as completed and prepares user for dashboard.
    """
    try:
        result = await service.complete_onboarding(current_user.id)
        return result
    except OnboardingValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.get("/analytics")
async def get_onboarding_analytics(
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Get onboarding analytics and completion statistics.
    Returns completion rates, time spent, and drop-off analysis.
    """
    try:
        result = await service.get_onboarding_analytics(current_user.id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get onboarding analytics: {str(e)}"
        )


# Advanced Navigation Endpoints

@router.post("/navigate/{step_name}")
async def navigate_to_step(
    current_user: CurrentUser,
    step_name: OnboardingStep = Path(..., description="Step to navigate to"),
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Navigate to a specific onboarding step.

    Useful for allowing users to go back to previous steps or skip forward.
    Validates that navigation is allowed based on current progress.
    """
    try:
        result = await service.go_to_step(current_user.id, step_name)
        return result
    except OnboardingValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to navigate to step: {str(e)}"
        )


@router.post("/reset")
async def reset_onboarding(
    current_user: CurrentUser,
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Reset the user's onboarding progress.

    This allows users to restart their onboarding from the beginning.
    All progress will be lost and user will need to start over.
    """
    try:
        result = await service.reset_onboarding(current_user.id)
        return result
    except OnboardingValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset onboarding: {str(e)}"
        )


# Goal Management Endpoints

@router.get("/goals")
async def get_user_goals(
    current_user: CurrentUser,
    active_only: bool = Query(True, description="Return only active goals"),
    goal_type: Optional[str] = Query(None, description="Filter by goal type")
) -> List[UserGoalResponse]:
    """
    Get user's financial goals.

    Returns all goals or filtered by active status and goal type.
    """
    try:
        goals_repo = GoalsRepository()
        goals = await goals_repo.get_user_goals(
            current_user.id,
            active_only=active_only,
            goal_type=goal_type
        )
        return goals
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user goals: {str(e)}"
        )


@router.get("/goals/{goal_id}")
async def get_goal_by_id(
    current_user: CurrentUser,
    goal_id: UUID = Path(..., description="Goal ID")
) -> UserGoalResponse:
    """
    Get a specific financial goal by ID.

    Returns detailed information about a specific goal.
    """
    try:
        goals_repo = GoalsRepository()
        goal = await goals_repo.get_goal_by_id(goal_id)

        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        # Ensure user owns this goal
        if goal.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this goal"
            )

        return goal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get goal: {str(e)}"
        )


@router.put("/goals/{goal_id}")
async def update_goal(
    goal_data: OnboardingGoalData,
    current_user: CurrentUser,
    goal_id: UUID = Path(..., description="Goal ID")
) -> UserGoalResponse:
    """
    Update an existing financial goal.

    Allows users to modify their goal parameters after initial setup.
    """
    try:
        goals_repo = GoalsRepository()

        # Check if goal exists and belongs to user
        existing_goal = await goals_repo.get_goal_by_id(goal_id)
        if not existing_goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        if existing_goal.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this goal"
            )

        # Update the goal
        from app.models.onboarding import UserGoalUpdate
        update_data = UserGoalUpdate(**goal_data.model_dump())
        updated_goal = await goals_repo.update_goal(goal_id, update_data)

        if not updated_goal:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update goal"
            )

        return updated_goal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update goal: {str(e)}"
        )


@router.put("/goals/{goal_id}/progress")
async def update_goal_progress(
    progress_data: Dict[str, float],
    current_user: CurrentUser,
    goal_id: UUID = Path(..., description="Goal ID")
) -> UserGoalResponse:
    """
    Update the progress percentage of a goal.

    Allows manual progress updates for goals.
    """
    try:
        progress_percentage = progress_data.get("progress_percentage", 0.0)

        if not (0 <= progress_percentage <= 100):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Progress percentage must be between 0 and 100"
            )

        goals_repo = GoalsRepository()

        # Check if goal exists and belongs to user
        existing_goal = await goals_repo.get_goal_by_id(goal_id)
        if not existing_goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        if existing_goal.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this goal"
            )

        updated_goal = await goals_repo.update_goal_progress(goal_id, progress_percentage)

        if not updated_goal:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update goal progress"
            )

        return updated_goal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update goal progress: {str(e)}"
        )


@router.delete("/goals/{goal_id}")
async def delete_goal(
    current_user: CurrentUser,
    goal_id: UUID = Path(..., description="Goal ID")
) -> Dict[str, str]:
    """
    Soft delete a financial goal.

    Marks the goal as inactive rather than permanently deleting it.
    """
    try:
        goals_repo = GoalsRepository()

        # Check if goal exists and belongs to user
        existing_goal = await goals_repo.get_goal_by_id(goal_id)
        if not existing_goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        if existing_goal.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this goal"
            )

        success = await goals_repo.delete_goal(goal_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete goal"
            )

        return {"message": "Goal deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete goal: {str(e)}"
        )


@router.patch("/goals/{goal_id}/activate")
async def activate_goal(
    current_user: CurrentUser,
    goal_id: UUID = Path(..., description="Goal ID")
) -> UserGoalResponse:
    """
    Reactivate a previously deactivated goal.
    """
    try:
        goals_repo = GoalsRepository()

        # Check if goal exists and belongs to user
        existing_goal = await goals_repo.get_goal_by_id(goal_id)
        if not existing_goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found"
            )

        if existing_goal.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this goal"
            )

        activated_goal = await goals_repo.activate_goal(goal_id)

        if not activated_goal:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to activate goal"
            )

        return activated_goal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate goal: {str(e)}"
        )


# User Profile Management Endpoints

@router.put("/profile")
async def update_user_profile(
    profile_data: UserOnboardingUpdate,
    current_user: CurrentUser,
) -> UserProfileResponse:
    """
    Update user profile information during or after onboarding.

    Allows users to update their financial profile information.
    """
    try:
        user_repo = UserRepository()
        updated_user = await user_repo.update_user(current_user.id, profile_data.model_dump())

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile"
            )

        return UserProfileResponse.from_user_in_db(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}"
        )


# Advanced Analytics Endpoints

@router.get("/stats")
async def get_onboarding_statistics(
    current_user: VerifiedUser,  # Requires verified user
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Get comprehensive onboarding statistics.

    Requires verified user account. Returns detailed analytics
    about onboarding completion rates and user behavior patterns.
    """
    try:
        # Get user's personal analytics
        user_analytics = await service.get_onboarding_analytics(current_user.id)

        # Get overall statistics (could be cached for performance)
        from app.repositories.onboarding_repository import OnboardingRepository
        onboarding_repo = OnboardingRepository()
        overall_stats = await onboarding_repo.get_onboarding_summary()

        return {
            "user_analytics": user_analytics,
            "overall_statistics": overall_stats,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get onboarding statistics: {str(e)}"
        )


# Health Check Endpoints

@router.get("/health")
async def onboarding_health_check(
    service: OnboardingService = Depends(get_onboarding_service)
) -> Dict[str, Any]:
    """
    Health check endpoint for onboarding service.

    Returns the health status of all onboarding-related components.
    """
    try:
        onboarding_repo = OnboardingRepository()
        goals_repo = GoalsRepository()
        user_repo = UserRepository()

        # Check repository health
        onboarding_health = await onboarding_repo.get_health_check()
        goals_health = await goals_repo.get_health_check()
        user_health = await user_repo.get_health_check()

        overall_health = all([
            onboarding_health.get("status") == "healthy",
            goals_health.get("status") == "healthy",
            user_health.get("status") == "healthy"
        ])

        return {
            "status": "healthy" if overall_health else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "onboarding_repository": onboarding_health,
                "goals_repository": goals_health,
                "user_repository": user_health,
                "onboarding_service": {
                    "status": "healthy",
                    "message": "Service operational"
                }
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "components": {
                "error": "Health check failed"
            }
        }
