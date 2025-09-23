"""
Goals repository for managing user financial goals and related operations.
Handles goal creation, updates, progress tracking, and analytics.
"""

import asyncpg
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from uuid import UUID

from app.models.onboarding import (
    UserGoalCreate,
    UserGoalUpdate,
    UserGoalResponse,
    GoalType,
    PreferredStrategy
)
from app.repositories.base_repository import BaseRepository, RecordNotFoundError, DatabaseError

logger = logging.getLogger(__name__)


class GoalsRepository(BaseRepository[UserGoalResponse]):
    """
    Repository for user goals operations.

    Handles all database operations related to user financial goals,
    including creation, updates, progress tracking, and analytics.
    """

    def __init__(self):
        super().__init__("user_goals")

    def _record_to_model(self, record: asyncpg.Record) -> UserGoalResponse:
        """Convert database record to UserGoalResponse model"""
        return UserGoalResponse(
            id=record['id'],
            user_id=record['user_id'],
            goal_type=record['goal_type'],
            target_amount=record['target_amount'],
            target_date=record['target_date'],
            preferred_strategy=record['preferred_strategy'],
            monthly_extra_payment=record['monthly_extra_payment'],
            priority_level=record['priority_level'],
            description=record['description'],
            is_active=record['is_active'],
            progress_percentage=record['progress_percentage'] or 0.0,
            created_at=record['created_at'],
            updated_at=record['updated_at']
        )

    def _model_to_dict(self, model: Union[UserGoalCreate, UserGoalResponse]) -> Dict[str, Any]:
        """Convert UserGoalCreate or UserGoalResponse model to dictionary for database operations"""
        if isinstance(model, UserGoalCreate):
            # For UserGoalCreate, exclude fields that are auto-generated
            return {
                'user_id': str(model.user_id),
                'goal_type': model.goal_type,
                'target_amount': model.target_amount,
                'target_date': model.target_date,
                'preferred_strategy': model.preferred_strategy,
                'monthly_extra_payment': model.monthly_extra_payment,
                'priority_level': model.priority_level,
                'description': model.description,
                'is_active': model.is_active
            }
        else:
            # For UserGoalResponse, include all fields
            return {
                'id': str(model.id),
                'user_id': str(model.user_id),
                'goal_type': model.goal_type,
                'target_amount': model.target_amount,
                'target_date': model.target_date,
                'preferred_strategy': model.preferred_strategy,
                'monthly_extra_payment': model.monthly_extra_payment,
                'priority_level': model.priority_level,
                'description': model.description,
                'is_active': model.is_active,
                'progress_percentage': model.progress_percentage,
                'created_at': model.created_at,
                'updated_at': model.updated_at
            }

    async def create_user_goal(self, goal_data: UserGoalCreate) -> UserGoalResponse:
        """
        Create a new user financial goal.

        Args:
            goal_data: Goal creation data

        Returns:
            Created goal record

        Raises:
            DatabaseError: For database errors
        """
        return await self.create(goal_data)

    async def get_user_goals(
        self,
        user_id: UUID,
        active_only: bool = True,
        goal_type: Optional[GoalType] = None
    ) -> List[UserGoalResponse]:
        """
        Get user's financial goals with optional filtering.

        Args:
            user_id: The user's UUID
            active_only: Whether to return only active goals
            goal_type: Optional filter by goal type

        Returns:
            List of user's goals
        """
        query = """
            SELECT * FROM user_goals
            WHERE user_id = $1
        """
        params = [str(user_id)]

        if active_only:
            query += " AND is_active = true"

        if goal_type:
            query += " AND goal_type = $2"
            params.append(goal_type.value)

        query += " ORDER BY priority_level DESC, created_at DESC"

        records = await self._fetch_all_with_error_handling(query, *params)
        return [self._record_to_model(record) for record in records]

    async def get_goal_by_id(self, goal_id: UUID) -> Optional[UserGoalResponse]:
        """
        Get a specific goal by its ID.

        Args:
            goal_id: The goal's UUID

        Returns:
            Goal record if found, None otherwise
        """
        return await self.get_by_id(goal_id)

    async def update_goal(self, goal_id: UUID, update_data: UserGoalUpdate) -> Optional[UserGoalResponse]:
        """
        Update a user's goal.

        Args:
            goal_id: The goal's UUID
            update_data: Data to update

        Returns:
            Updated goal if found, None otherwise

        Raises:
            DatabaseError: For database errors
        """
        update_dict = update_data.model_dump(exclude_unset=True)
        return await self.update(goal_id, update_dict)

    async def update_goal_progress(
        self,
        goal_id: UUID,
        progress_percentage: float
    ) -> Optional[UserGoalResponse]:
        """
        Update goal progress percentage.

        Args:
            goal_id: The goal's UUID
            progress_percentage: New progress percentage (0-100)

        Returns:
            Updated goal if found, None otherwise

        Raises:
            ValueError: If progress percentage is invalid
            DatabaseError: For database errors
        """
        if progress_percentage < 0 or progress_percentage > 100:
            raise ValueError("Progress percentage must be between 0 and 100")

        return await self.update(goal_id, {'progress_percentage': progress_percentage})

    async def delete_goal(self, goal_id: UUID) -> bool:
        """
        Delete a user's goal (soft delete by setting is_active to false).

        Args:
            goal_id: The goal's UUID

        Returns:
            True if goal was deactivated, False if not found
        """
        return await self.soft_delete(goal_id) is not None

    async def activate_goal(self, goal_id: UUID) -> Optional[UserGoalResponse]:
        """
        Reactivate a previously deactivated goal.

        Args:
            goal_id: The goal's UUID

        Returns:
            Updated goal if found, None otherwise
        """
        return await self.update(goal_id, {'is_active': True})

    async def deactivate_goal(self, goal_id: UUID) -> Optional[UserGoalResponse]:
        """
        Deactivate a goal without deleting it.

        Args:
            goal_id: The goal's UUID

        Returns:
            Updated goal if found, None otherwise
        """
        return await self.update(goal_id, {'is_active': False})

    async def get_goals_by_type(self, goal_type: GoalType, active_only: bool = True) -> List[UserGoalResponse]:
        """
        Get all goals of a specific type.

        Args:
            goal_type: Type of goals to retrieve
            active_only: Whether to return only active goals

        Returns:
            List of goals of the specified type
        """
        query = """
            SELECT * FROM user_goals
            WHERE goal_type = $1
        """
        params = [goal_type.value]

        if active_only:
            query += " AND is_active = true"

        query += " ORDER BY priority_level DESC, created_at DESC"

        records = await self._fetch_all_with_error_handling(query, *params)
        return [self._record_to_model(record) for record in records]

    async def get_goals_due_soon(self, days_ahead: int = 30) -> List[UserGoalResponse]:
        """
        Get goals that are due within the specified number of days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of goals due within the specified timeframe
        """
        query = """
            SELECT * FROM user_goals
            WHERE target_date IS NOT NULL
            AND target_date <= CURRENT_DATE + INTERVAL '%s days'
            AND target_date >= CURRENT_DATE
            AND is_active = true
            ORDER BY target_date ASC, priority_level DESC
        """ % days_ahead

        records = await self._fetch_all_with_error_handling(query)
        return [self._record_to_model(record) for record in records]

    async def get_overdue_goals(self) -> List[UserGoalResponse]:
        """
        Get goals that are past their target date.

        Returns:
            List of overdue goals
        """
        query = """
            SELECT * FROM user_goals
            WHERE target_date IS NOT NULL
            AND target_date < CURRENT_DATE
            AND is_active = true
            AND progress_percentage < 100
            ORDER BY target_date ASC, priority_level DESC
        """

        records = await self._fetch_all_with_error_handling(query)
        return [self._record_to_model(record) for record in records]

    async def get_completed_goals(self, user_id: Optional[UUID] = None, limit: Optional[int] = None) -> List[UserGoalResponse]:
        """
        Get completed goals.

        Args:
            user_id: Optional user ID to filter by specific user
            limit: Maximum number of records to return

        Returns:
            List of completed goals
        """
        query = """
            SELECT * FROM user_goals
            WHERE progress_percentage >= 100
            AND is_active = true
        """
        params = []

        if user_id:
            query += " AND user_id = $1"
            params.append(str(user_id))

        query += " ORDER BY updated_at DESC"

        if limit:
            query += f" LIMIT {limit}"

        records = await self._fetch_all_with_error_handling(query, *params)
        return [self._record_to_model(record) for record in records]

    async def get_goals_by_priority(self, user_id: UUID, min_priority: int = 1, max_priority: int = 10) -> List[UserGoalResponse]:
        """
        Get user's goals filtered by priority level range.

        Args:
            user_id: The user's UUID
            min_priority: Minimum priority level (inclusive)
            max_priority: Maximum priority level (inclusive)

        Returns:
            List of goals within the priority range
        """
        query = """
            SELECT * FROM user_goals
            WHERE user_id = $1
            AND priority_level BETWEEN $2 AND $3
            AND is_active = true
            ORDER BY priority_level DESC, created_at DESC
        """

        records = await self._fetch_all_with_error_handling(query, str(user_id), min_priority, max_priority)
        return [self._record_to_model(record) for record in records]

    async def get_goals_with_amounts(self, user_id: UUID) -> List[UserGoalResponse]:
        """
        Get user's goals that have target amounts set.

        Args:
            user_id: The user's UUID

        Returns:
            List of goals with target amounts
        """
        query = """
            SELECT * FROM user_goals
            WHERE user_id = $1
            AND target_amount IS NOT NULL
            AND target_amount > 0
            AND is_active = true
            ORDER BY target_amount DESC, priority_level DESC
        """

        records = await self._fetch_all_with_error_handling(query, str(user_id))
        return [self._record_to_model(record) for record in records]

    async def calculate_goal_progress_based_on_debts(self, goal_id: UUID) -> Optional[float]:
        """
        Calculate goal progress based on actual debt payments.

        This is a simplified calculation that could be enhanced with more complex logic.

        Args:
            goal_id: The goal's UUID

        Returns:
            Calculated progress percentage or None if calculation not possible
        """
        goal = await self.get_by_id(goal_id)
        if not goal or not goal.target_amount:
            return None

        # This is a placeholder for actual progress calculation
        # In a real implementation, this would query payment history
        # and calculate progress based on actual debt reduction

        # For now, return the stored progress percentage
        return goal.progress_percentage

    async def bulk_update_goal_priorities(self, user_id: UUID, goal_updates: List[Dict[str, Any]]) -> List[UserGoalResponse]:
        """
        Bulk update priorities for multiple goals.

        Args:
            user_id: The user's UUID
            goal_updates: List of dicts with goal_id and new priority_level

        Returns:
            List of updated goals

        Raises:
            DatabaseError: For database errors
        """
        updated_goals = []

        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.transaction():
                    for update in goal_updates:
                        goal_id = update.get('goal_id')
                        priority_level = update.get('priority_level')

                        if goal_id and priority_level:
                            query = """
                                UPDATE user_goals
                                SET priority_level = $1, updated_at = $2
                                WHERE id = $3 AND user_id = $4
                                RETURNING *
                            """

                            record = await conn.fetchrow(
                                query,
                                priority_level,
                                datetime.now(),
                                str(goal_id),
                                str(user_id)
                            )

                            if record:
                                updated_goals.append(self._record_to_model(record))

            return updated_goals

        except asyncpg.PostgresError as e:
            logger.error(f"Database error in bulk priority update: {e}")
            raise DatabaseError(f"Failed to bulk update goal priorities: {e}")

    async def get_goal_statistics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get goal statistics for analysis.

        Args:
            user_id: Optional user ID to filter by specific user

        Returns:
            Dictionary with goal statistics
        """
        base_query = """
            SELECT
                COUNT(*) as total_goals,
                COUNT(CASE WHEN progress_percentage >= 100 THEN 1 END) as completed_goals,
                COUNT(CASE WHEN target_date < CURRENT_DATE AND progress_percentage < 100 THEN 1 END) as overdue_goals,
                AVG(priority_level) as avg_priority,
                AVG(target_amount) as avg_target_amount,
                SUM(target_amount) as total_target_amount
            FROM user_goals
            WHERE is_active = true
        """
        params = []

        if user_id:
            base_query += " AND user_id = $1"
            params.append(str(user_id))

        record = await self._fetch_one_with_error_handling(base_query, *params)

        if record:
            return {
                'total_goals': record['total_goals'],
                'completed_goals': record['completed_goals'],
                'overdue_goals': record['overdue_goals'],
                'avg_priority': float(record['avg_priority'] or 0),
                'avg_target_amount': float(record['avg_target_amount'] or 0),
                'total_target_amount': float(record['total_target_amount'] or 0),
                'completion_rate': (
                    (record['completed_goals'] / record['total_goals'] * 100)
                    if record['total_goals'] > 0 else 0
                )
            }

        return {
            'total_goals': 0,
            'completed_goals': 0,
            'overdue_goals': 0,
            'avg_priority': 0.0,
            'avg_target_amount': 0.0,
            'total_target_amount': 0.0,
            'completion_rate': 0.0
        }

    async def archive_completed_goals(self, user_id: UUID, days_old: int = 30) -> int:
        """
        Archive completed goals that are older than specified days.

        Args:
            user_id: The user's UUID
            days_old: Number of days after which to archive completed goals

        Returns:
            Number of goals archived
        """
        query = """
            UPDATE user_goals
            SET is_active = false, updated_at = $1
            WHERE user_id = $2
            AND progress_percentage >= 100
            AND is_active = true
            AND updated_at < NOW() - INTERVAL '%s days'
        """ % days_old

        result = await self._execute_with_error_handling(query, datetime.now(), str(user_id))

        # Extract the number of affected rows
        if hasattr(result, 'split'):
            rows_affected = int(result.split()[-1])
            return rows_affected
        return 0
