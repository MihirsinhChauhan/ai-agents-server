"""AI Insights Cache Service

Service layer for managing AI insights caching to improve performance and reduce API costs.
Provides intelligent caching with invalidation based on user's debt portfolio changes.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID as PyUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.orm import selectinload

from app.models.ai_insights_cache import AIInsightsCache, AIProcessingQueue
from app.models.debt import DebtInDB
from app.models.user import User
from app.repositories.debt_repository import DebtRepository
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class AIInsightsCacheService:
    """
    Service for managing AI insights caching with intelligent invalidation.

    Features:
    - Smart cache validation based on debt portfolio changes
    - Background AI processing queue management
    - Automatic cache expiration and cleanup
    - Rate limiting compliance for AI API calls
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.debt_repo = DebtRepository()  # No session required for AsyncPG repository
        self.ai_service = AIService(debt_repo=self.debt_repo, user_repo=None, analytics_repo=None)

    async def get_ai_insights(self, user_id: PyUUID) -> Tuple[Dict[str, Any], bool]:
        """
        Get AI insights for user with intelligent caching.

        Returns:
            Tuple[Dict[str, Any], bool]: (insights_data, is_from_cache)
        """
        try:
            # Get current debt portfolio for cache validation
            user_debts = await self.debt_repo.get_debts_by_user_id(user_id)
            current_cache_key = AIInsightsCache.generate_cache_key(
                user_id,
                [debt.to_dict() for debt in user_debts]
            )

            # Check for valid cache entry
            cached_insights = await self._get_valid_cache_entry(user_id, current_cache_key)
            if cached_insights:
                logger.info(f"Returning cached AI insights for user {user_id}")
                return cached_insights.to_response_dict(), True

            # Check if already processing
            existing_job = await self._get_active_processing_job(user_id)
            if existing_job:
                logger.info(f"AI insights already processing for user {user_id}")
                # Return basic analysis while processing continues
                basic_analysis = await self._generate_basic_analysis(user_debts)
                return basic_analysis, False

            # Generate fresh AI insights
            logger.info(f"Generating fresh AI insights for user {user_id}")
            insights = await self._generate_and_cache_insights(user_id, user_debts, current_cache_key)
            return insights, False

        except Exception as e:
            logger.error(f"Error getting AI insights for user {user_id}: {e}")
            # Fallback to basic analysis
            user_debts = await self.debt_repo.get_debts_by_user_id(user_id)
            basic_analysis = await self._generate_basic_analysis(user_debts)
            return basic_analysis, False

    async def get_insights_status(self, user_id: PyUUID) -> Dict[str, Any]:
        """Get processing status for user's AI insights."""
        try:
            # Check for valid cache
            cached_insights = await self._get_latest_cache_entry(user_id)
            if cached_insights and not cached_insights.is_expired():
                return {
                    "status": "completed",
                    "cached": True,
                    "generated_at": cached_insights.generated_at.isoformat(),
                    "expires_at": cached_insights.expires_at.isoformat(),
                    "processing_time": cached_insights.processing_time,
                }

            # Check processing queue
            processing_job = await self._get_active_processing_job(user_id)
            if processing_job:
                return {
                    "status": processing_job.status,
                    "cached": False,
                    "started_at": processing_job.started_at.isoformat() if processing_job.started_at else None,
                    "attempts": processing_job.attempts,
                    "estimated_completion": self._estimate_completion_time(processing_job),
                }

            return {
                "status": "not_generated",
                "cached": False,
                "message": "AI insights have not been generated for this user"
            }

        except Exception as e:
            logger.error(f"Error getting insights status for user {user_id}: {e}")
            return {
                "status": "error",
                "cached": False,
                "message": str(e)
            }

    async def refresh_insights(self, user_id: PyUUID, force: bool = False) -> Dict[str, Any]:
        """Force refresh of AI insights for user."""
        try:
            # Get current debt portfolio
            user_debts = await self.debt_repo.get_debts_by_user_id(user_id)
            current_cache_key = AIInsightsCache.generate_cache_key(
                user_id,
                [debt.to_dict() for debt in user_debts]
            )

            if force:
                # Invalidate existing cache
                await self._invalidate_cache(user_id)

            # Queue background processing
            await self._queue_ai_processing(user_id, current_cache_key, priority=1)

            return {
                "status": "refresh_queued",
                "message": "AI insights refresh has been queued for processing",
                "estimated_completion": datetime.utcnow() + timedelta(minutes=2)
            }

        except Exception as e:
            logger.error(f"Error refreshing insights for user {user_id}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def invalidate_cache_for_user(self, user_id: PyUUID) -> bool:
        """Invalidate cache when user's debt portfolio changes."""
        try:
            await self._invalidate_cache(user_id)
            logger.info(f"Cache invalidated for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {e}")
            return False

    async def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries and return count of cleaned entries."""
        try:
            result = await self.db.execute(
                delete(AIInsightsCache).where(
                    AIInsightsCache.expires_at < datetime.utcnow()
                )
            )
            await self.db.commit()

            cleaned_count = result.rowcount
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return 0

    # Private methods

    async def _get_valid_cache_entry(self, user_id: PyUUID, cache_key: str) -> Optional[AIInsightsCache]:
        """Get valid cache entry for user with matching cache key."""
        try:
            result = await self.db.execute(
                select(AIInsightsCache)
                .where(
                    and_(
                        AIInsightsCache.user_id == user_id,
                        AIInsightsCache.cache_key == cache_key,
                        AIInsightsCache.expires_at > datetime.utcnow(),
                        AIInsightsCache.status == 'completed'
                    )
                )
                .order_by(AIInsightsCache.generated_at.desc())
                .limit(1)
            )

            cache_entry = result.scalar_one_or_none()
            return cache_entry

        except Exception as e:
            logger.error(f"Error getting valid cache entry: {e}")
            return None

    async def _get_latest_cache_entry(self, user_id: PyUUID) -> Optional[AIInsightsCache]:
        """Get latest cache entry for user (regardless of validity)."""
        try:
            result = await self.db.execute(
                select(AIInsightsCache)
                .where(AIInsightsCache.user_id == user_id)
                .order_by(AIInsightsCache.generated_at.desc())
                .limit(1)
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting latest cache entry: {e}")
            return None

    async def _get_active_processing_job(self, user_id: PyUUID) -> Optional[AIProcessingQueue]:
        """Get active processing job for user."""
        try:
            result = await self.db.execute(
                select(AIProcessingQueue)
                .where(
                    and_(
                        AIProcessingQueue.user_id == user_id,
                        AIProcessingQueue.task_type == 'ai_insights',
                        AIProcessingQueue.status.in_(['queued', 'processing'])
                    )
                )
                .order_by(AIProcessingQueue.created_at.desc())
                .limit(1)
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting active processing job: {e}")
            return None

    async def _generate_basic_analysis(self, debts: List[DebtInDB]) -> Dict[str, Any]:
        """Generate basic debt analysis without AI."""
        try:
            total_debt = sum(debt.current_balance for debt in debts)
            debt_count = len(debts)

            if debt_count == 0:
                return {
                    "debt_analysis": {
                        "total_debt": 0,
                        "debt_count": 0,
                        "average_interest_rate": 0,
                        "total_minimum_payments": 0,
                        "high_priority_count": 0,
                        "generated_at": datetime.utcnow().isoformat()
                    },
                    "recommendations": [],
                    "metadata": {
                        "cached": False,
                        "fallback_used": True,
                        "processing_status": "basic_analysis"
                    }
                }

            # Calculate basic metrics
            total_minimum_payments = sum(debt.minimum_payment for debt in debts)
            weighted_interest = sum(debt.current_balance * debt.interest_rate for debt in debts) / total_debt
            high_priority_count = sum(1 for debt in debts if debt.is_high_priority)

            # Generate basic recommendations
            recommendations = self._generate_basic_recommendations(debts)

            return {
                "debt_analysis": {
                    "total_debt": total_debt,
                    "debt_count": debt_count,
                    "average_interest_rate": weighted_interest,
                    "total_minimum_payments": total_minimum_payments,
                    "high_priority_count": high_priority_count,
                    "generated_at": datetime.utcnow().isoformat()
                },
                "recommendations": recommendations,
                "metadata": {
                    "processing_time": 0.1,  # Minimal time for basic analysis
                    "fallback_used": True,
                    "errors": [],
                    "generated_at": datetime.utcnow().isoformat(),
                    "cached": False,
                    "processing_status": "basic_analysis"
                }
            }

        except Exception as e:
            logger.error(f"Error generating basic analysis: {e}")
            return {
                "debt_analysis": {
                    "total_debt": 0,
                    "debt_count": 0,
                    "average_interest_rate": 0,
                    "total_minimum_payments": 0,
                    "high_priority_count": 0,
                    "generated_at": datetime.utcnow().isoformat()
                },
                "recommendations": [],
                "metadata": {
                    "processing_time": 0.0,  # Failed before completion
                    "fallback_used": True,
                    "errors": [str(e)],
                    "generated_at": datetime.utcnow().isoformat(),
                    "cached": False,
                    "processing_status": "error"
                }
            }

    def _generate_basic_recommendations(self, debts: List[DebtInDB]) -> List[Dict[str, Any]]:
        """Generate basic recommendations without AI."""
        recommendations = []

        if not debts:
            return recommendations

        # Find highest interest debt
        highest_interest_debt = max(debts, key=lambda d: d.interest_rate)
        if highest_interest_debt.interest_rate > 15:
            recommendations.append({
                "id": "basic_rec_1",
                "user_id": str(highest_interest_debt.user_id),
                "recommendation_type": "high_interest_priority",
                "title": f"Prioritize {highest_interest_debt.name} (High Interest)",
                "description": f"Focus on paying off {highest_interest_debt.name} with {highest_interest_debt.interest_rate}% interest rate to save money on interest charges.",
                "potential_savings": highest_interest_debt.current_balance * 0.1,  # Estimated 10% savings
                "priority_score": 9,
                "is_dismissed": False,
                "created_at": datetime.utcnow().isoformat()
            })

        # Emergency fund recommendation
        recommendations.append({
            "id": "basic_rec_2",
            "user_id": str(debts[0].user_id),
            "recommendation_type": "emergency_fund",
            "title": "Build Emergency Fund",
            "description": "Create an emergency fund to avoid taking on additional debt during unexpected expenses.",
            "potential_savings": 10000,  # Estimated benefit
            "priority_score": 8,
            "is_dismissed": False,
            "created_at": datetime.utcnow().isoformat()
        })

        return recommendations

    async def _generate_and_cache_insights(self, user_id: PyUUID, debts: List[DebtInDB], cache_key: str) -> Dict[str, Any]:
        """Generate fresh AI insights and cache them."""
        start_time = datetime.utcnow()

        try:
            # Generate AI insights
            ai_insights = await self.ai_service.generate_insights(user_id, include_dti=True)
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Cache the results
            cache_entry = AIInsightsCache(
                user_id=user_id,
                debt_analysis=ai_insights.get("debt_analysis", {}),
                recommendations=ai_insights.get("recommendations", []),
                ai_metadata=ai_insights.get("metadata", {}),
                cache_key=cache_key,
                expires_at=datetime.utcnow() + AIInsightsCache.get_default_ttl(),
                processing_time=processing_time,
                ai_model_used="groq/llama-3.1-8b-instant",
                status="completed"
            )

            self.db.add(cache_entry)
            await self.db.commit()

            logger.info(f"Cached AI insights for user {user_id} (processing time: {processing_time:.1f}s)")
            return cache_entry.to_response_dict()

        except Exception as e:
            logger.error(f"Error generating and caching insights for user {user_id}: {e}")
            # Return basic analysis on failure
            return await self._generate_basic_analysis(debts)

    async def _queue_ai_processing(self, user_id: PyUUID, cache_key: str, priority: int = 5):
        """Queue background AI processing job."""
        try:
            # Check if already queued
            existing_job = await self._get_active_processing_job(user_id)
            if existing_job:
                logger.info(f"AI processing already queued for user {user_id}")
                return existing_job

            # Create new processing job
            job = AIProcessingQueue(
                user_id=user_id,
                task_type="ai_insights",
                priority=priority,
                payload={"cache_key": cache_key}
            )

            self.db.add(job)
            await self.db.commit()

            logger.info(f"Queued AI processing job for user {user_id}")
            return job

        except Exception as e:
            logger.error(f"Error queuing AI processing for user {user_id}: {e}")
            return None

    async def _invalidate_cache(self, user_id: PyUUID):
        """Invalidate all cache entries for user."""
        await self.db.execute(
            delete(AIInsightsCache).where(
                AIInsightsCache.user_id == user_id
            )
        )
        await self.db.commit()

    def _estimate_completion_time(self, processing_job: AIProcessingQueue) -> str:
        """Estimate completion time for processing job."""
        if processing_job.status == "processing":
            # Assume 90 seconds processing time
            estimated_end = processing_job.started_at + timedelta(seconds=90)
            return estimated_end.isoformat()
        elif processing_job.status == "queued":
            # Estimate based on queue position and processing time
            estimated_start = datetime.utcnow() + timedelta(seconds=30)  # Queue delay
            estimated_end = estimated_start + timedelta(seconds=90)  # Processing time
            return estimated_end.isoformat()

        return (datetime.utcnow() + timedelta(seconds=90)).isoformat()