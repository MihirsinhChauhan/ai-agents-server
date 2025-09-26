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
        """
        Initialize AI insights cache service with SQLAlchemy session.

        Args:
            db_session: SQLAlchemy AsyncSession for cache operations only.
                       This session is completely isolated from main DB operations.
        """
        if not isinstance(db_session, AsyncSession):
            raise TypeError(f"Expected AsyncSession, got {type(db_session)}")

        self.db = db_session
        self.debt_repo = DebtRepository()  # Uses AsyncPG for main operations
        self.ai_service = AIService(debt_repo=self.debt_repo, user_repo=None, analytics_repo=None)

        logger.debug("AIInsightsCacheService initialized with SQLAlchemy session")

    async def _check_session_health(self) -> bool:
        """
        Check if the SQLAlchemy session is healthy and connected.
        Returns True if session is healthy, False otherwise.
        """
        try:
            # Simple query to test session health
            await self.db.execute(select(1))
            return True
        except Exception as e:
            logger.error(f"Session health check failed: {e}")
            return False

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

    async def get_ai_recommendations(self, user_id: PyUUID) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Get AI recommendations for user with intelligent caching.

        This method provides dedicated recommendations caching to ensure consistency
        and reduce AI API costs for the /recommendations endpoint.

        Returns:
            Tuple[List[Dict[str, Any]], bool]: (recommendations_list, is_from_cache)
        """
        try:
            # Get current debt portfolio for cache validation
            user_debts = await self.debt_repo.get_debts_by_user_id(user_id)
            if not user_debts:
                logger.info(f"No debts found for user {user_id}, returning empty recommendations")
                return [], False

            current_cache_key = AIInsightsCache.generate_cache_key(
                user_id,
                [debt.to_dict() for debt in user_debts]
            )

            # Check for valid cache entry containing recommendations
            cached_insights = await self._get_valid_cache_entry(user_id, current_cache_key)
            if cached_insights and cached_insights.recommendations:
                logger.info(f"Returning cached AI recommendations for user {user_id}")
                return cached_insights.recommendations, True

            # Check if already processing insights (which include recommendations)
            existing_job = await self._get_active_processing_job(user_id)
            if existing_job:
                logger.info(f"AI insights (with recommendations) already processing for user {user_id}")
                # Return basic recommendations while processing continues
                basic_recommendations = self._generate_basic_recommendations(user_debts)
                return basic_recommendations, False

            # Generate fresh AI insights (which includes recommendations) and cache them
            logger.info(f"Generating fresh AI recommendations for user {user_id}")
            insights = await self._generate_and_cache_insights(user_id, user_debts, current_cache_key)
            recommendations = insights.get("recommendations", [])
            return recommendations, False

        except Exception as e:
            logger.error(f"Error getting AI recommendations for user {user_id}: {e}")
            # Fallback to basic recommendations
            try:
                user_debts = await self.debt_repo.get_debts_by_user_id(user_id)
                basic_recommendations = self._generate_basic_recommendations(user_debts)
                return basic_recommendations, False
            except Exception as fallback_error:
                logger.error(f"Error generating fallback recommendations for user {user_id}: {fallback_error}")
                return [], False

    async def get_insights_status(self, user_id: PyUUID) -> Dict[str, Any]:
        """Get processing status for user's AI insights."""
        try:
            logger.debug(f"Getting insights status for user {user_id}")

            # Get current debt portfolio to generate cache key (same logic as get_ai_insights)
            user_debts = await self.debt_repo.get_debts_by_user_id(user_id)
            current_cache_key = AIInsightsCache.generate_cache_key(
                user_id,
                [debt.to_dict() for debt in user_debts]
            )

            logger.debug(f"Generated cache key for user {user_id}: {current_cache_key[:16]}...")

            # Check for valid cache using same validation logic as get_ai_insights
            cached_insights = await self._get_valid_cache_entry(user_id, current_cache_key)
            if cached_insights:
                logger.debug(f"Found valid cache entry for user {user_id}")
                return {
                    "status": "completed",
                    "cached": True,
                    "generated_at": cached_insights.generated_at.isoformat(),
                    "expires_at": cached_insights.expires_at.isoformat(),
                    "processing_time": cached_insights.processing_time,
                    "cache_key_match": True,
                }

            # Check if there's any cache entry (even if expired or invalid) to provide more detail
            latest_cache = await self._get_latest_cache_entry(user_id)
            if latest_cache:
                is_expired = latest_cache.is_expired()
                cache_key_match = latest_cache.cache_key == current_cache_key

                if is_expired and cache_key_match:
                    # Cache exists but expired - insights available but need refresh
                    return {
                        "status": "expired",
                        "cached": False,
                        "generated_at": latest_cache.generated_at.isoformat(),
                        "expires_at": latest_cache.expires_at.isoformat(),
                        "cache_key_match": True,
                        "message": "AI insights exist but have expired"
                    }
                elif not cache_key_match and not is_expired:
                    # Cache exists but debt portfolio changed - insights need regeneration
                    return {
                        "status": "stale",
                        "cached": False,
                        "generated_at": latest_cache.generated_at.isoformat(),
                        "expires_at": latest_cache.expires_at.isoformat(),
                        "cache_key_match": False,
                        "message": "AI insights exist but debt portfolio has changed"
                    }
                elif not cache_key_match and is_expired:
                    # Cache exists but both expired and debt portfolio changed
                    return {
                        "status": "expired_and_stale",
                        "cached": False,
                        "generated_at": latest_cache.generated_at.isoformat(),
                        "expires_at": latest_cache.expires_at.isoformat(),
                        "cache_key_match": False,
                        "message": "AI insights exist but are expired and debt portfolio has changed"
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
                    "cache_exists": latest_cache is not None
                }

            # Truly no insights have been generated
            return {
                "status": "not_generated",
                "cached": False,
                "cache_exists": False,
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
        """
        Invalidate cache when user's debt portfolio changes.
        Enhanced with session health checks and error isolation.
        """
        try:
            # Check session health before attempting cache operations
            if not await self._check_session_health():
                logger.error(f"Session unhealthy, skipping cache invalidation for user {user_id}")
                return False

            logger.debug(f"Session health check passed for user {user_id}")
            await self._invalidate_cache(user_id)
            logger.info(f"Cache invalidated successfully for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {type(e).__name__}: {str(e)}")
            logger.error(f"Full cache invalidation error:", exc_info=True)

            # Attempt session recovery if possible
            try:
                await self.db.rollback()
                logger.debug(f"Session rolled back successfully for user {user_id}")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback session for user {user_id}: {rollback_error}")

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

    async def has_insights_available(self, user_id: PyUUID) -> Tuple[bool, Optional[str]]:
        """
        Check if user has any AI insights available (cached or processing).

        Returns:
            Tuple[bool, Optional[str]]: (has_insights, status_reason)
        """
        try:
            # Check for any cache entry first
            latest_cache = await self._get_latest_cache_entry(user_id)
            if latest_cache:
                # Get current cache key to check if it's still valid
                user_debts = await self.debt_repo.get_debts_by_user_id(user_id)
                current_cache_key = AIInsightsCache.generate_cache_key(
                    user_id,
                    [debt.to_dict() for debt in user_debts]
                )

                if latest_cache.is_valid(current_cache_key):
                    return True, "cached_valid"
                elif not latest_cache.is_expired():
                    return True, "cached_stale"  # Portfolio changed
                else:
                    return True, "cached_expired"

            # Check if processing
            processing_job = await self._get_active_processing_job(user_id)
            if processing_job:
                return True, "processing"

            return False, "not_generated"

        except Exception as e:
            logger.error(f"Error checking insights availability for user {user_id}: {e}")
            return False, "error"

    async def get_recommendations_status(self, user_id: PyUUID) -> Dict[str, Any]:
        """
        Get processing status for user's AI recommendations.

        This provides the same status information as insights since recommendations
        are part of the cached insights data.
        """
        try:
            status_info = await self.get_insights_status(user_id)
            # Add recommendations-specific metadata
            status_info["endpoint_type"] = "recommendations"
            status_info["cache_shared_with_insights"] = True

            # If we have cached data, check if recommendations exist
            if status_info.get("status") == "completed":
                latest_cache = await self._get_latest_cache_entry(user_id)
                if latest_cache:
                    recommendations_count = len(latest_cache.recommendations) if latest_cache.recommendations else 0
                    status_info["recommendations_count"] = recommendations_count
                    status_info["has_recommendations"] = recommendations_count > 0

            return status_info

        except Exception as e:
            logger.error(f"Error getting recommendations status for user {user_id}: {e}")
            return {
                "status": "error",
                "cached": False,
                "endpoint_type": "recommendations",
                "message": str(e)
            }

    async def has_recommendations_available(self, user_id: PyUUID) -> Tuple[bool, Optional[str]]:
        """
        Check if user has any AI recommendations available (cached or processing).

        This uses the same logic as insights since recommendations are part of insights.

        Returns:
            Tuple[bool, Optional[str]]: (has_recommendations, status_reason)
        """
        try:
            has_insights, status_reason = await self.has_insights_available(user_id)

            # If we have valid cached insights, check if they contain recommendations
            if has_insights and status_reason == "cached_valid":
                latest_cache = await self._get_latest_cache_entry(user_id)
                if latest_cache and latest_cache.recommendations:
                    recommendations_count = len(latest_cache.recommendations)
                    if recommendations_count > 0:
                        return True, f"cached_valid_{recommendations_count}_recommendations"
                    else:
                        return True, "cached_valid_no_recommendations"

            return has_insights, status_reason

        except Exception as e:
            logger.error(f"Error checking recommendations availability for user {user_id}: {e}")
            return False, "error"

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

    async def _get_active_processing_job(self, user_id: PyUUID, task_type: str = 'ai_insights') -> Optional[AIProcessingQueue]:
        """Get active processing job for user for a specific task type."""
        try:
            result = await self.db.execute(
                select(AIProcessingQueue)
                .where(
                    and_(
                        AIProcessingQueue.user_id == user_id,
                        AIProcessingQueue.task_type == task_type,
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
            ai_insights = await self.ai_service.get_ai_insights(user_id=user_id, include_dti=True)
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
        """
        Invalidate all cache entries for user with enhanced error handling.
        Protected against session corruption.
        """
        try:
            logger.debug(f"Starting cache invalidation for user {user_id}")

            # Use a more explicit delete query with proper type conversion
            result = await self.db.execute(
                delete(AIInsightsCache).where(
                    AIInsightsCache.user_id == str(user_id)  # Ensure string conversion
                )
            )

            # Only commit if the execute succeeded
            await self.db.commit()

            deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
            logger.debug(f"Cache invalidation completed for user {user_id}, deleted {deleted_count} entries")

        except Exception as e:
            logger.error(f"Cache invalidation failed for user {user_id}: {type(e).__name__}: {str(e)}")
            logger.error(f"Full error details: {e}", exc_info=True)

            # Rollback the transaction to prevent corruption
            try:
                await self.db.rollback()
                logger.debug("Transaction rolled back successfully")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")

            # Re-raise the original error
            raise

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