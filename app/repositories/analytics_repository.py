"""
Analytics repository for AI recommendations, user streaks, and analytics data.
Handles AI recommendation storage, user gamification data, and analytics operations.
"""

import asyncpg
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID

from app.models.analytics import (
    AIRecommendationInDB, UserStreakInDB, DTIMetricsResponse,
    AIRecommendationResponse, UserStreakResponse,
    convert_ai_recommendation_to_response, convert_user_streak_to_response
)
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AnalyticsRepository(BaseRepository):
    """Repository for analytics, AI recommendations, and gamification data"""

    def __init__(self):
        # Note: This repository handles multiple tables, so we'll override methods as needed
        super().__init__("ai_recommendations")  # Default table

    def _record_to_model(self, record: asyncpg.Record) -> Any:
        """This method will be overridden by specific methods"""
        pass

    def _model_to_dict(self, model: Any) -> Dict[str, Any]:
        """This method will be overridden by specific methods"""
        pass

    # AI Recommendations Methods
    def _ai_recommendation_record_to_model(self, record: asyncpg.Record) -> AIRecommendationInDB:
        """Convert database record to AIRecommendationInDB model"""
        return AIRecommendationInDB(
            id=record['id'],
            user_id=record['user_id'],
            recommendation_type=record['recommendation_type'],
            title=record['title'],
            description=record['description'],
            potential_savings=float(record['potential_savings']) if record['potential_savings'] else None,
            priority_score=record['priority_score'],
            is_dismissed=record['is_dismissed'],
            metadata=record.get('metadata', {}),
            created_at=record['created_at'],
            updated_at=record['updated_at']
        )

    def _ai_recommendation_model_to_dict(self, model: AIRecommendationInDB) -> Dict[str, Any]:
        """Convert AIRecommendationInDB model to dictionary"""
        return {
            'id': str(model.id),
            'user_id': str(model.user_id),
            'recommendation_type': model.recommendation_type,
            'title': model.title,
            'description': model.description,
            'potential_savings': model.potential_savings,
            'priority_score': model.priority_score,
            'is_dismissed': model.is_dismissed,
            'metadata': model.metadata,
            'created_at': model.created_at,
            'updated_at': model.updated_at
        }

    async def create_ai_recommendation(
        self, 
        user_id: UUID,
        recommendation_type: str,
        title: str,
        description: str,
        potential_savings: Optional[float] = None,
        priority_score: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AIRecommendationInDB:
        """
        Create a new AI recommendation.
        
        Args:
            user_id: User's ID
            recommendation_type: Type of recommendation
            title: Recommendation title
            description: Recommendation description
            potential_savings: Potential savings amount
            priority_score: Priority score (0-10)
            metadata: Additional metadata
            
        Returns:
            Created AI recommendation
        """
        recommendation = AIRecommendationInDB(
            user_id=user_id,
            recommendation_type=recommendation_type,
            title=title,
            description=description,
            potential_savings=potential_savings,
            priority_score=priority_score,
            is_dismissed=False,
            metadata=metadata or {},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Insert into ai_recommendations table
        model_dict = self._ai_recommendation_model_to_dict(recommendation)
        insert_data = {k: v for k, v in model_dict.items() if v is not None}
        
        columns = list(insert_data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(insert_data.values())
        
        query = f"""
            INSERT INTO ai_recommendations ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        
        record = await self._fetch_one_with_error_handling(query, *values)
        return self._ai_recommendation_record_to_model(record)

    async def get_user_recommendations(
        self, 
        user_id: UUID, 
        include_dismissed: bool = False,
        limit: Optional[int] = None
    ) -> List[AIRecommendationResponse]:
        """
        Get AI recommendations for a user.
        
        Args:
            user_id: User's ID
            include_dismissed: Whether to include dismissed recommendations
            limit: Maximum number of recommendations to return
            
        Returns:
            List of AI recommendations
        """
        query = "SELECT * FROM ai_recommendations WHERE user_id = $1"
        args = [str(user_id)]
        
        if not include_dismissed:
            query += " AND is_dismissed = false"
        
        query += " ORDER BY priority_score DESC, created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        records = await self._fetch_all_with_error_handling(query, *args)
        
        recommendations = []
        for record in records:
            db_recommendation = self._ai_recommendation_record_to_model(record)
            response_recommendation = convert_ai_recommendation_to_response(db_recommendation)
            recommendations.append(response_recommendation)
        
        return recommendations

    async def dismiss_recommendation(self, recommendation_id: UUID) -> Optional[AIRecommendationInDB]:
        """
        Dismiss an AI recommendation.
        
        Args:
            recommendation_id: Recommendation's ID
            
        Returns:
            Updated recommendation if found, None otherwise
        """
        query = """
            UPDATE ai_recommendations 
            SET is_dismissed = true, updated_at = $1 
            WHERE id = $2 
            RETURNING *
        """
        
        record = await self._fetch_one_with_error_handling(
            query, 
            datetime.now(), 
            str(recommendation_id)
        )
        
        if record:
            return self._ai_recommendation_record_to_model(record)
        return None

    async def get_recommendation_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get recommendation statistics for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            Dictionary with recommendation statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_recommendations,
                COUNT(*) FILTER (WHERE is_dismissed = false) as active_recommendations,
                COUNT(*) FILTER (WHERE is_dismissed = true) as dismissed_recommendations,
                AVG(priority_score) as avg_priority_score,
                SUM(potential_savings) as total_potential_savings,
                COUNT(DISTINCT recommendation_type) as unique_types
            FROM ai_recommendations 
            WHERE user_id = $1
        """
        
        record = await self._fetch_one_with_error_handling(query, str(user_id))
        
        if record:
            return {
                'total_recommendations': record['total_recommendations'],
                'active_recommendations': record['active_recommendations'],
                'dismissed_recommendations': record['dismissed_recommendations'],
                'avg_priority_score': float(record['avg_priority_score']) if record['avg_priority_score'] else 0.0,
                'total_potential_savings': float(record['total_potential_savings']) if record['total_potential_savings'] else 0.0,
                'unique_types': record['unique_types']
            }
        
        return {
            'total_recommendations': 0,
            'active_recommendations': 0,
            'dismissed_recommendations': 0,
            'avg_priority_score': 0.0,
            'total_potential_savings': 0.0,
            'unique_types': 0
        }

    # User Streaks Methods
    def _user_streak_record_to_model(self, record: asyncpg.Record) -> UserStreakInDB:
        """Convert database record to UserStreakInDB model"""
        return UserStreakInDB(
            id=record['id'],
            user_id=record['user_id'],
            current_streak=record['current_streak'],
            longest_streak=record['longest_streak'],
            last_check_in=record['last_check_in'],
            total_payments_logged=record['total_payments_logged'],
            milestones_achieved=record.get('milestones_achieved', []),
            created_at=record['created_at'],
            updated_at=record['updated_at']
        )

    def _user_streak_model_to_dict(self, model: UserStreakInDB) -> Dict[str, Any]:
        """Convert UserStreakInDB model to dictionary"""
        return {
            'id': str(model.id),
            'user_id': str(model.user_id),
            'current_streak': model.current_streak,
            'longest_streak': model.longest_streak,
            'last_check_in': model.last_check_in,
            'total_payments_logged': model.total_payments_logged,
            'milestones_achieved': model.milestones_achieved,
            'created_at': model.created_at,
            'updated_at': model.updated_at
        }

    async def get_or_create_user_streak(self, user_id: UUID) -> UserStreakInDB:
        """
        Get user streak record or create if it doesn't exist.
        
        Args:
            user_id: User's ID
            
        Returns:
            User streak record
        """
        # Try to get existing streak
        query = "SELECT * FROM user_streaks WHERE user_id = $1"
        record = await self._fetch_one_with_error_handling(query, str(user_id))
        
        if record:
            return self._user_streak_record_to_model(record)
        
        # Create new streak record
        streak = UserStreakInDB(
            user_id=user_id,
            current_streak=0,
            longest_streak=0,
            last_check_in=None,
            total_payments_logged=0,
            milestones_achieved=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        model_dict = self._user_streak_model_to_dict(streak)
        insert_data = {k: v for k, v in model_dict.items() if v is not None}
        
        columns = list(insert_data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(insert_data.values())
        
        create_query = f"""
            INSERT INTO user_streaks ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """
        
        new_record = await self._fetch_one_with_error_handling(create_query, *values)
        return self._user_streak_record_to_model(new_record)

    async def update_user_streak(
        self, 
        user_id: UUID,
        current_streak: Optional[int] = None,
        longest_streak: Optional[int] = None,
        last_check_in: Optional[str] = None,
        total_payments_logged: Optional[int] = None,
        milestones_achieved: Optional[List[str]] = None
    ) -> UserStreakInDB:
        """
        Update user streak data.
        
        Args:
            user_id: User's ID
            current_streak: New current streak value
            longest_streak: New longest streak value
            last_check_in: Last check-in date
            total_payments_logged: Total payments logged
            milestones_achieved: List of achieved milestones
            
        Returns:
            Updated user streak
        """
        # Get current streak record
        streak = await self.get_or_create_user_streak(user_id)
        
        # Build update data
        update_data = {'updated_at': datetime.now()}
        
        if current_streak is not None:
            update_data['current_streak'] = current_streak
        if longest_streak is not None:
            update_data['longest_streak'] = longest_streak
        if last_check_in is not None:
            update_data['last_check_in'] = last_check_in
        if total_payments_logged is not None:
            update_data['total_payments_logged'] = total_payments_logged
        if milestones_achieved is not None:
            update_data['milestones_achieved'] = milestones_achieved
        
        # Build update query
        set_clauses = [f"{column} = ${i+2}" for i, column in enumerate(update_data.keys())]
        values = [str(user_id)] + list(update_data.values())
        
        query = f"""
            UPDATE user_streaks
            SET {', '.join(set_clauses)}
            WHERE user_id = $1
            RETURNING *
        """
        
        record = await self._fetch_one_with_error_handling(query, *values)
        return self._user_streak_record_to_model(record)

    async def get_user_streak_response(self, user_id: UUID) -> UserStreakResponse:
        """
        Get user streak as response model.
        
        Args:
            user_id: User's ID
            
        Returns:
            User streak response
        """
        streak = await self.get_or_create_user_streak(user_id)
        return convert_user_streak_to_response(streak)

    async def log_payment_for_streak(self, user_id: UUID, payment_date: str) -> UserStreakResponse:
        """
        Log a payment and update streak accordingly.
        
        Args:
            user_id: User's ID
            payment_date: Payment date in YYYY-MM-DD format
            
        Returns:
            Updated user streak response
        """
        streak = await self.get_or_create_user_streak(user_id)
        
        # Parse payment date
        payment_dt = datetime.strptime(payment_date, '%Y-%m-%d').date()
        today = date.today()
        
        # Calculate new streak
        current_streak = streak.current_streak
        last_check_in_dt = None
        
        if streak.last_check_in:
            last_check_in_dt = datetime.strptime(streak.last_check_in, '%Y-%m-%d').date()
        
        # Update streak logic
        if last_check_in_dt:
            days_diff = (payment_dt - last_check_in_dt).days
            if days_diff == 1:
                # Continue streak
                current_streak += 1
            elif days_diff > 1:
                # Streak broken, restart
                current_streak = 1
            # If same day, don't change streak
        else:
            # First payment
            current_streak = 1
        
        # Update longest streak if needed
        longest_streak = max(streak.longest_streak, current_streak)
        
        # Check for new milestones
        milestones = list(streak.milestones_achieved)
        
        # Add milestones based on current streak
        if current_streak >= 7 and "7_day_streak" not in milestones:
            milestones.append("7_day_streak")
        if current_streak >= 30 and "30_day_streak" not in milestones:
            milestones.append("30_day_streak")
        if current_streak >= 100 and "100_day_streak" not in milestones:
            milestones.append("100_day_streak")
        
        # Add milestones based on total payments
        total_payments = streak.total_payments_logged + 1
        if total_payments >= 10 and "10_payments" not in milestones:
            milestones.append("10_payments")
        if total_payments >= 50 and "50_payments" not in milestones:
            milestones.append("50_payments")
        if total_payments >= 100 and "100_payments" not in milestones:
            milestones.append("100_payments")
        
        # Update streak record
        updated_streak = await self.update_user_streak(
            user_id=user_id,
            current_streak=current_streak,
            longest_streak=longest_streak,
            last_check_in=payment_date,
            total_payments_logged=total_payments,
            milestones_achieved=milestones
        )
        
        return convert_user_streak_to_response(updated_streak)

    # Analytics Methods
    async def calculate_dti_metrics(
        self, 
        user_id: UUID, 
        monthly_income: float
    ) -> DTIMetricsResponse:
        """
        Calculate DTI metrics for a user.
        
        Args:
            user_id: User's ID
            monthly_income: User's monthly income
            
        Returns:
            DTI metrics response
        """
        if monthly_income <= 0:
            raise ValueError("Monthly income must be positive")
        
        # Get debt payment information
        query = """
            SELECT 
                SUM(minimum_payment) as total_monthly_payments,
                SUM(minimum_payment) FILTER (WHERE debt_type = 'home_loan') as housing_payments
            FROM debts 
            WHERE user_id = $1 AND is_active = true
        """
        
        record = await self._fetch_one_with_error_handling(query, str(user_id))
        
        total_monthly_payments = float(record['total_monthly_payments']) if record['total_monthly_payments'] else 0.0
        housing_payments = float(record['housing_payments']) if record['housing_payments'] else 0.0
        
        # Calculate DTI ratios
        frontend_dti = (housing_payments / monthly_income) * 100
        backend_dti = (total_monthly_payments / monthly_income) * 100
        
        # Determine if DTI is healthy (frontend <= 28%, backend <= 36%)
        is_healthy = frontend_dti <= 28 and backend_dti <= 36
        
        return DTIMetricsResponse(
            frontend_dti=round(frontend_dti, 2),
            backend_dti=round(backend_dti, 2),
            total_monthly_debt_payments=total_monthly_payments,
            monthly_income=monthly_income,
            is_healthy=is_healthy
        )

    async def get_user_analytics_summary(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive analytics summary for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            Dictionary with analytics summary
        """
        # Get recommendation stats
        rec_stats = await self.get_recommendation_stats(user_id)
        
        # Get streak data
        streak_response = await self.get_user_streak_response(user_id)
        
        # Get user's monthly income for DTI calculation
        user_query = "SELECT monthly_income FROM users WHERE id = $1"
        user_record = await self._fetch_one_with_error_handling(user_query, str(user_id))
        
        dti_metrics = None
        if user_record and user_record['monthly_income']:
            dti_metrics = await self.calculate_dti_metrics(user_id, float(user_record['monthly_income']))
        
        return {
            'recommendations': rec_stats,
            'streaks': streak_response.model_dump(),
            'dti_metrics': dti_metrics.model_dump() if dti_metrics else None,
            'analysis_date': datetime.now().isoformat()
        }

    async def cleanup_old_recommendations(self, days_old: int = 30) -> int:
        """
        Clean up old dismissed recommendations.
        
        Args:
            days_old: Number of days old recommendations should be to be cleaned up
            
        Returns:
            Number of recommendations cleaned up
        """
        query = """
            DELETE FROM ai_recommendations 
            WHERE is_dismissed = true 
            AND updated_at < NOW() - INTERVAL '%s days'
        """ % days_old
        
        result = await self._execute_with_error_handling(query)
        
        # Extract number of deleted rows
        if hasattr(result, 'split'):
            rows_affected = int(result.split()[-1])
            return rows_affected
        return 0

    async def get_analytics_health_check(self) -> Dict[str, Any]:
        """
        Get health check information for analytics tables.
        
        Returns:
            Dictionary with health check information
        """
        try:
            # Check ai_recommendations table
            rec_query = "SELECT COUNT(*) FROM ai_recommendations"
            rec_record = await self._fetch_one_with_error_handling(rec_query)
            rec_count = rec_record[0] if rec_record else 0
            
            # Check user_streaks table
            streak_query = "SELECT COUNT(*) FROM user_streaks"
            streak_record = await self._fetch_one_with_error_handling(streak_query)
            streak_count = streak_record[0] if streak_record else 0
            
            return {
                'status': 'healthy',
                'ai_recommendations_count': rec_count,
                'user_streaks_count': streak_count,
                'connection': 'ok'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'connection': 'failed'
            }
