"""
Onboarding repository for managing user onboarding progress and related operations.
Handles onboarding progress tracking, step management, and analytics.
"""

import asyncpg
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.onboarding import (
    OnboardingProgressCreate,
    OnboardingProgressUpdate,
    OnboardingProgressResponse,
    OnboardingAnalyticsCreate,
    OnboardingAnalyticsResponse,
    OnboardingStep,
    calculate_onboarding_progress,
    get_next_step
)
from app.repositories.base_repository import BaseRepository, RecordNotFoundError, DatabaseError

logger = logging.getLogger(__name__)


class OnboardingRepository(BaseRepository[OnboardingProgressResponse]):
    """
    Repository for onboarding progress operations.

    Handles all database operations related to user onboarding progress,
    including progress tracking, step management, and analytics.
    """

    def __init__(self):
        super().__init__("onboarding_progress")

    def _record_to_model(self, record: asyncpg.Record) -> OnboardingProgressResponse:
        """Convert database record to OnboardingProgressResponse model"""
        # Parse JSON fields back to Python objects
        completed_steps = json.loads(record['completed_steps']) if record['completed_steps'] else []
        onboarding_data = json.loads(record['onboarding_data']) if record['onboarding_data'] else {}
        
        # Calculate progress percentage based on completed steps
        progress_percentage = calculate_onboarding_progress(completed_steps)

        return OnboardingProgressResponse(
            id=record['id'],
            user_id=record['user_id'],
            current_step=record['current_step'],
            completed_steps=completed_steps,
            onboarding_data=onboarding_data,
            is_completed=record['is_completed'],
            started_at=record['started_at'],
            completed_at=record['completed_at'],
            created_at=record['created_at'],
            updated_at=record['updated_at'],
            progress_percentage=progress_percentage
        )

    def _model_to_dict(self, model) -> Dict[str, Any]:
        """Convert onboarding model to dictionary for database operations"""
        base_dict = {
            'user_id': str(model.user_id),
            'current_step': model.current_step.value if hasattr(model.current_step, 'value') else model.current_step,
            'completed_steps': json.dumps(model.completed_steps),
            'onboarding_data': json.dumps(model.onboarding_data),
            'is_completed': model.is_completed,
        }
        
        # Add additional fields if they exist (for updates)
        if hasattr(model, 'id') and model.id is not None:
            base_dict['id'] = str(model.id)
        if hasattr(model, 'started_at') and model.started_at is not None:
            base_dict['started_at'] = model.started_at
        if hasattr(model, 'completed_at') and model.completed_at is not None:
            base_dict['completed_at'] = model.completed_at
        if hasattr(model, 'created_at') and model.created_at is not None:
            base_dict['created_at'] = model.created_at
        if hasattr(model, 'updated_at') and model.updated_at is not None:
            base_dict['updated_at'] = model.updated_at
            
        return base_dict

    async def create_onboarding_progress(self, user_id: UUID) -> OnboardingProgressResponse:
        """
        Create initial onboarding progress for a user.

        Args:
            user_id: The user's UUID

        Returns:
            Created onboarding progress record

        Raises:
            DuplicateRecordError: If onboarding progress already exists for user
            DatabaseError: For other database errors
        """
        # Check if onboarding progress already exists
        existing = await self.get_user_onboarding(user_id)
        if existing:
            raise DuplicateRecordError(f"Onboarding progress already exists for user {user_id}")

        onboarding_create = OnboardingProgressCreate(
            user_id=user_id,
            current_step=OnboardingStep.WELCOME,
            completed_steps=[],
            onboarding_data={},
            is_completed=False
        )

        return await self.create(onboarding_create)

    async def get_user_onboarding(self, user_id: UUID) -> Optional[OnboardingProgressResponse]:
        """
        Get user's onboarding progress.

        Args:
            user_id: The user's UUID

        Returns:
            User's onboarding progress if found, None otherwise
        """
        return await self.find_one_by_field('user_id', str(user_id))

    async def update_onboarding_step(
        self,
        user_id: UUID,
        step: OnboardingStep,
        step_data: Optional[Dict[str, Any]] = None
    ) -> OnboardingProgressResponse:
        """
        Update onboarding step and store step data.

        Args:
            user_id: The user's UUID
            step: New current step
            step_data: Optional data to store for this step

        Returns:
            Updated onboarding progress

        Raises:
            RecordNotFoundError: If onboarding progress not found for user
            DatabaseError: For other database errors
        """
        onboarding = await self.get_user_onboarding(user_id)
        if not onboarding:
            raise RecordNotFoundError(f"Onboarding progress not found for user {user_id}")

        # Update onboarding data if step data provided
        updated_data = onboarding.onboarding_data.copy()
        if step_data:
            updated_data[step.value] = step_data

        update_data = {
            'current_step': step.value,
            'onboarding_data': json.dumps(updated_data)
        }

        updated_onboarding = await self.update(onboarding.id, update_data)
        if not updated_onboarding:
            raise DatabaseError(f"Failed to update onboarding step for user {user_id}")

        return updated_onboarding

    async def mark_step_completed(
        self,
        user_id: UUID,
        step: str
    ) -> bool:
        """
        Mark a specific step as completed.

        Args:
            user_id: The user's UUID
            step: Name of the step to mark as completed

        Returns:
            True if step was marked as completed

        Raises:
            RecordNotFoundError: If onboarding progress not found for user
            DatabaseError: For other database errors
        """
        onboarding = await self.get_user_onboarding(user_id)
        if not onboarding:
            raise RecordNotFoundError(f"Onboarding progress not found for user {user_id}")

        completed_steps = onboarding.completed_steps.copy()

        # Add step to completed list if not already there
        if step not in completed_steps:
            completed_steps.append(step)

            update_data = {'completed_steps': json.dumps(completed_steps)}
            updated = await self.update(onboarding.id, update_data)
            return updated is not None

        return True  # Step was already completed

    async def complete_onboarding(self, user_id: UUID) -> bool:
        """
        Mark onboarding as fully completed.

        Args:
            user_id: The user's UUID

        Returns:
            True if onboarding was marked as completed

        Raises:
            RecordNotFoundError: If onboarding progress not found for user
            DatabaseError: For other database errors
        """
        onboarding = await self.get_user_onboarding(user_id)
        if not onboarding:
            raise RecordNotFoundError(f"Onboarding progress not found for user {user_id}")

        completed_steps = onboarding.completed_steps.copy()
        if OnboardingStep.COMPLETED.value not in completed_steps:
            completed_steps.append(OnboardingStep.COMPLETED.value)

        update_data = {
            'current_step': OnboardingStep.COMPLETED.value,
            'completed_steps': json.dumps(completed_steps),
            'is_completed': True,
            'completed_at': datetime.now()
        }

        updated = await self.update(onboarding.id, update_data)
        return updated is not None

    async def get_onboarding_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get onboarding completion analytics for a user.

        Args:
            user_id: The user's UUID

        Returns:
            Dictionary with onboarding analytics
        """
        onboarding = await self.get_user_onboarding(user_id)

        analytics = {
            'user_id': str(user_id),
            'has_started': onboarding is not None,
            'current_step': onboarding.current_step if onboarding else None,
            'completed_steps': onboarding.completed_steps if onboarding else [],
            'progress_percentage': onboarding.progress_percentage if onboarding else 0.0,
            'is_completed': onboarding.is_completed if onboarding else False,
            'started_at': onboarding.started_at if onboarding else None,
            'completed_at': onboarding.completed_at if onboarding else None,
            'time_spent_seconds': None
        }

        # Calculate time spent if onboarding exists
        if onboarding and onboarding.started_at:
            end_time = onboarding.completed_at or datetime.now()
            time_spent = end_time - onboarding.started_at
            analytics['time_spent_seconds'] = int(time_spent.total_seconds())

        return analytics

    async def get_onboarding_summary(self) -> Dict[str, Any]:
        """
        Get overall onboarding completion summary.

        Returns:
            Dictionary with summary statistics
        """
        query = """
            SELECT
                COUNT(*) as total_users,
                COUNT(CASE WHEN is_completed = true THEN 1 END) as completed_users,
                ROUND(
                    COUNT(CASE WHEN is_completed = true THEN 1 END)::numeric /
                    NULLIF(COUNT(*), 0) * 100, 2
                ) as completion_rate_percentage,
                AVG(EXTRACT(EPOCH FROM (completed_at - started_at))/3600) as avg_completion_time_hours
            FROM onboarding_progress
            WHERE started_at >= CURRENT_DATE - INTERVAL '30 days'
        """

        record = await self._fetch_one_with_error_handling(query)

        if record:
            return {
                'total_users': record['total_users'],
                'completed_users': record['completed_users'],
                'completion_rate_percentage': float(record['completion_rate_percentage'] or 0),
                'avg_completion_time_hours': float(record['avg_completion_time_hours'] or 0) if record['avg_completion_time_hours'] else None
            }

        return {
            'total_users': 0,
            'completed_users': 0,
            'completion_rate_percentage': 0.0,
            'avg_completion_time_hours': None
        }

    async def get_users_by_step(self, step: OnboardingStep) -> List[OnboardingProgressResponse]:
        """
        Get all users currently on a specific onboarding step.

        Args:
            step: The onboarding step to filter by

        Returns:
            List of onboarding progress records for users on this step
        """
        return await self.find_by_field('current_step', step.value)

    async def get_completed_onboardings(self, limit: Optional[int] = None) -> List[OnboardingProgressResponse]:
        """
        Get all completed onboarding records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of completed onboarding records
        """
        query = """
            SELECT * FROM onboarding_progress
            WHERE is_completed = true
            ORDER BY completed_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        records = await self._fetch_all_with_error_handling(query)
        return [self._record_to_model(record) for record in records]

    async def get_dropped_off_users(self, step: OnboardingStep) -> List[OnboardingProgressResponse]:
        """
        Get users who dropped off at a specific step (stayed on same step for extended period).

        Args:
            step: The step to check for drop-offs

        Returns:
            List of onboarding records for users who may have dropped off
        """
        # Consider users who have been on the same step for more than 7 days
        query = """
            SELECT * FROM onboarding_progress
            WHERE current_step = $1
            AND is_completed = false
            AND updated_at < NOW() - INTERVAL '7 days'
            ORDER BY updated_at ASC
        """

        records = await self._fetch_all_with_error_handling(query, step.value)
        return [self._record_to_model(record) for record in records]

    async def update_onboarding_data(
        self,
        user_id: UUID,
        step_data: Dict[str, Any],
        merge: bool = True
    ) -> Optional[OnboardingProgressResponse]:
        """
        Update onboarding data for a user.

        Args:
            user_id: The user's UUID
            step_data: Data to update
            merge: Whether to merge with existing data or replace

        Returns:
            Updated onboarding progress if found
        """
        onboarding = await self.get_user_onboarding(user_id)
        if not onboarding:
            return None

        if merge:
            updated_data = onboarding.onboarding_data.copy()
            updated_data.update(step_data)
        else:
            updated_data = step_data

        return await self.update(onboarding.id, {'onboarding_data': json.dumps(updated_data)})

    async def reset_onboarding(self, user_id: UUID) -> Optional[OnboardingProgressResponse]:
        """
        Reset onboarding progress for a user.

        Args:
            user_id: The user's UUID

        Returns:
            Reset onboarding progress if found
        """
        onboarding = await self.get_user_onboarding(user_id)
        if not onboarding:
            return None

        reset_data = {
            'current_step': OnboardingStep.WELCOME.value,
            'completed_steps': json.dumps([]),
            'onboarding_data': json.dumps({}),
            'is_completed': False,
            'completed_at': None
        }

        return await self.update(onboarding.id, reset_data)

    # Analytics-specific methods
    async def create_onboarding_analytics(self, analytics_data: OnboardingAnalyticsCreate) -> OnboardingAnalyticsResponse:
        """
        Create onboarding analytics record.

        Args:
            analytics_data: Analytics data to create

        Returns:
            Created analytics record
        """
        query = """
            INSERT INTO onboarding_analytics (
                user_id, step_name, time_spent_seconds, completion_rate,
                drop_off_point, user_agent, device_type, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """

        values = (
            str(analytics_data.user_id),
            analytics_data.step_name,
            analytics_data.time_spent_seconds,
            analytics_data.completion_rate,
            analytics_data.drop_off_point,
            analytics_data.user_agent,
            analytics_data.device_type.value if analytics_data.device_type else None,
            datetime.now()
        )

        try:
            async with self.db_manager.get_connection() as conn:
                record = await conn.fetchrow(query, *values)
                if record:
                    return OnboardingAnalyticsResponse(
                        id=record['id'],
                        user_id=record['user_id'],
                        step_name=record['step_name'],
                        time_spent_seconds=record['time_spent_seconds'],
                        completion_rate=record['completion_rate'],
                        drop_off_point=record['drop_off_point'],
                        user_agent=record['user_agent'],
                        device_type=record['device_type'],
                        created_at=record['created_at']
                    )
                else:
                    raise DatabaseError("Failed to create onboarding analytics record")
        except asyncpg.PostgresError as e:
            logger.error(f"Database error creating analytics: {e}")
            raise DatabaseError(f"Failed to create onboarding analytics: {e}")

    async def get_user_onboarding_analytics(self, user_id: UUID) -> List[OnboardingAnalyticsResponse]:
        """
        Get onboarding analytics for a specific user.

        Args:
            user_id: The user's UUID

        Returns:
            List of analytics records for the user
        """
        query = """
            SELECT * FROM onboarding_analytics
            WHERE user_id = $1
            ORDER BY created_at DESC
        """

        records = await self._fetch_all_with_error_handling(query, str(user_id))

        analytics_list = []
        for record in records:
            analytics_list.append(OnboardingAnalyticsResponse(
                id=record['id'],
                user_id=record['user_id'],
                step_name=record['step_name'],
                time_spent_seconds=record['time_spent_seconds'],
                completion_rate=record['completion_rate'],
                drop_off_point=record['drop_off_point'],
                user_agent=record['user_agent'],
                device_type=record['device_type'],
                created_at=record['created_at']
            ))

        return analytics_list

    async def get_onboarding_step_analytics(self, step_name: str) -> Dict[str, Any]:
        """
        Get analytics for a specific onboarding step.

        Args:
            step_name: Name of the step to analyze

        Returns:
            Dictionary with step analytics
        """
        query = """
            SELECT
                COUNT(*) as total_attempts,
                AVG(time_spent_seconds) as avg_time_spent,
                AVG(completion_rate) as avg_completion_rate,
                COUNT(CASE WHEN drop_off_point IS NOT NULL THEN 1 END) as drop_offs,
                COUNT(DISTINCT user_id) as unique_users
            FROM onboarding_analytics
            WHERE step_name = $1
            AND created_at >= CURRENT_DATE - INTERVAL '30 days'
        """

        record = await self._fetch_one_with_error_handling(query, step_name)

        if record:
            return {
                'step_name': step_name,
                'total_attempts': record['total_attempts'],
                'avg_time_spent_seconds': float(record['avg_time_spent'] or 0),
                'avg_completion_rate': float(record['avg_completion_rate'] or 0),
                'drop_off_count': record['drop_offs'],
                'unique_users': record['unique_users']
            }

        return {
            'step_name': step_name,
            'total_attempts': 0,
            'avg_time_spent_seconds': 0.0,
            'avg_completion_rate': 0.0,
            'drop_off_count': 0,
            'unique_users': 0
        }
