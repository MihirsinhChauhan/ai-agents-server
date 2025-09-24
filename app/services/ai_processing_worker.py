"""
AI Processing Worker

Background task processor for handling AI insights generation queue.
Provides asynchronous processing of AI analysis tasks with retry logic.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID as PyUUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.databases.database import get_db
from app.models.ai_insights_cache import AIProcessingQueue, AIInsightsCache
from app.services.ai_service import AIService
from app.repositories.debt_repository import DebtRepository
from app.repositories.user_repository import UserRepository
from app.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)


class AIProcessingWorker:
    """
    Background worker for processing AI insights generation queue.

    Features:
    - Concurrent processing with configurable worker count
    - Automatic retry with exponential backoff
    - Graceful error handling and recovery
    - Processing metrics and health monitoring
    """

    def __init__(self, max_workers: int = 2, poll_interval: int = 30):
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.is_running = False
        self.workers: List[asyncio.Task] = []

    async def start(self):
        """Start the background processing workers."""
        if self.is_running:
            logger.warning("AI processing worker already running")
            return

        logger.info(f"Starting AI processing worker with {self.max_workers} workers")
        self.is_running = True

        # Start worker tasks
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(
                self._worker_loop(worker_id=i),
                name=f"ai-worker-{i}"
            )
            self.workers.append(worker_task)

        logger.info("AI processing workers started successfully")

    async def stop(self):
        """Stop all background workers gracefully."""
        if not self.is_running:
            return

        logger.info("Stopping AI processing workers...")
        self.is_running = False

        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers.clear()
        logger.info("AI processing workers stopped")

    async def _worker_loop(self, worker_id: int):
        """Main worker loop for processing queue items."""
        logger.info(f"AI worker {worker_id} started")

        try:
            while self.is_running:
                try:
                    # Get database session
                    async for db_session in get_db():
                        try:
                            # Process next available job
                            processed = await self._process_next_job(db_session, worker_id)
                            if not processed:
                                # No jobs available, wait before polling again
                                await asyncio.sleep(self.poll_interval)

                        finally:
                            await db_session.close()

                except Exception as e:
                    logger.error(f"Worker {worker_id} error in processing loop: {e}", exc_info=True)
                    # Wait before retrying to prevent tight error loops
                    await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            logger.info(f"AI worker {worker_id} cancelled")
            raise
        except Exception as e:
            logger.error(f"AI worker {worker_id} unexpected error: {e}", exc_info=True)
        finally:
            logger.info(f"AI worker {worker_id} stopped")

    async def _process_next_job(self, db_session: AsyncSession, worker_id: int) -> bool:
        """Process the next available job in the queue."""
        try:
            # Get next queued job with highest priority
            result = await db_session.execute(
                select(AIProcessingQueue)
                .where(
                    and_(
                        AIProcessingQueue.status == "queued",
                        AIProcessingQueue.attempts < AIProcessingQueue.max_attempts
                    )
                )
                .order_by(
                    AIProcessingQueue.priority.asc(),
                    AIProcessingQueue.created_at.asc()
                )
                .limit(1)
                .with_for_update(skip_locked=True)  # Prevent race conditions
            )

            job = result.scalar_one_or_none()
            if not job:
                return False

            logger.info(f"Worker {worker_id} processing job {job.id} for user {job.user_id}")

            # Mark job as processing
            job.mark_started()
            await db_session.commit()

            # Process the AI insights
            success = await self._process_ai_insights(db_session, job, worker_id)

            if success:
                # Job completed successfully, it's already marked as completed
                logger.info(f"Worker {worker_id} completed job {job.id}")
            else:
                # Job failed, handle retry logic
                job.mark_failed("AI processing failed")
                await db_session.commit()
                logger.warning(f"Worker {worker_id} failed job {job.id} (attempt {job.attempts})")

            return True

        except Exception as e:
            logger.error(f"Worker {worker_id} error processing job: {e}", exc_info=True)
            # Try to mark job as failed if we have the job reference
            try:
                if 'job' in locals() and job:
                    job.mark_failed(f"Processing error: {str(e)}")
                    await db_session.commit()
            except Exception:
                pass  # Don't fail on cleanup errors
            return False

    async def _process_ai_insights(self, db_session: AsyncSession, job: AIProcessingQueue, worker_id: int) -> bool:
        """Process AI insights for a specific job."""
        try:
            # Initialize repositories
            debt_repo = DebtRepository()  # AsyncPG repository doesn't need session
            user_repo = UserRepository(db_session)
            analytics_repo = AnalyticsRepository(db_session)

            # Initialize AI service
            ai_service = AIService(
                debt_repo=debt_repo,
                user_repo=user_repo,
                analytics_repo=analytics_repo
            )

            # Get user's current debt data
            user_debts = await debt_repo.get_debts_by_user_id(job.user_id)
            if not user_debts:
                logger.warning(f"No debts found for user {job.user_id}, marking job as completed")
                job.mark_completed({"message": "No debts found for analysis"})
                await db_session.commit()
                return True

            # Generate cache key
            cache_key = job.payload.get("cache_key") if job.payload else None
            if not cache_key:
                cache_key = AIInsightsCache.generate_cache_key(
                    job.user_id,
                    [debt.to_dict() for debt in user_debts]
                )

            start_time = datetime.utcnow()

            # Generate AI insights
            logger.info(f"Worker {worker_id} generating AI insights for user {job.user_id}")
            ai_insights = await ai_service.generate_insights(job.user_id, include_dti=True)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Cache the results
            cache_entry = AIInsightsCache(
                user_id=job.user_id,
                debt_analysis=ai_insights.get("debt_analysis", {}),
                recommendations=ai_insights.get("recommendations", []),
                ai_metadata=ai_insights.get("metadata", {}),
                cache_key=cache_key,
                expires_at=datetime.utcnow() + AIInsightsCache.get_default_ttl(),
                processing_time=processing_time,
                ai_model_used="groq/llama-3.1-8b-instant",
                status="completed"
            )

            db_session.add(cache_entry)

            # Mark job as completed
            job.mark_completed({
                "cache_entry_id": str(cache_entry.id),
                "processing_time": processing_time,
                "insights_generated": True
            })

            await db_session.commit()

            logger.info(f"Worker {worker_id} cached AI insights for user {job.user_id} (processing time: {processing_time:.1f}s)")
            return True

        except Exception as e:
            logger.error(f"Worker {worker_id} failed to process AI insights for user {job.user_id}: {e}", exc_info=True)
            return False

    async def get_queue_status(self, db_session: AsyncSession) -> dict:
        """Get current queue processing status."""
        try:
            # Count jobs by status
            result = await db_session.execute(
                select(AIProcessingQueue.status, AIProcessingQueue.task_type)
            )

            status_counts = {}
            for status, task_type in result.fetchall():
                key = f"{task_type}_{status}"
                status_counts[key] = status_counts.get(key, 0) + 1

            # Get oldest queued job
            oldest_queued = await db_session.execute(
                select(AIProcessingQueue.created_at)
                .where(AIProcessingQueue.status == "queued")
                .order_by(AIProcessingQueue.created_at.asc())
                .limit(1)
            )
            oldest_queued_time = oldest_queued.scalar_one_or_none()

            # Calculate queue age
            queue_age = None
            if oldest_queued_time:
                queue_age = (datetime.utcnow() - oldest_queued_time).total_seconds()

            return {
                "worker_status": "running" if self.is_running else "stopped",
                "active_workers": len(self.workers),
                "max_workers": self.max_workers,
                "queue_counts": status_counts,
                "oldest_queued_age_seconds": queue_age,
                "poll_interval": self.poll_interval
            }

        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {
                "worker_status": "error",
                "error": str(e)
            }

    async def cleanup_stale_jobs(self, db_session: AsyncSession, stale_threshold_hours: int = 1) -> int:
        """Clean up jobs that have been processing for too long."""
        try:
            stale_cutoff = datetime.utcnow() - timedelta(hours=stale_threshold_hours)

            result = await db_session.execute(
                select(AIProcessingQueue)
                .where(
                    and_(
                        AIProcessingQueue.status == "processing",
                        AIProcessingQueue.started_at < stale_cutoff
                    )
                )
            )

            stale_jobs = result.scalars().all()
            cleanup_count = 0

            for job in stale_jobs:
                job.mark_failed("Job exceeded processing time limit")
                cleanup_count += 1

            if cleanup_count > 0:
                await db_session.commit()
                logger.info(f"Cleaned up {cleanup_count} stale processing jobs")

            return cleanup_count

        except Exception as e:
            logger.error(f"Error cleaning up stale jobs: {e}")
            return 0


# Global worker instance
_worker_instance: Optional[AIProcessingWorker] = None


async def start_ai_worker(max_workers: int = 2, poll_interval: int = 30):
    """Start the global AI processing worker."""
    global _worker_instance

    if _worker_instance and _worker_instance.is_running:
        logger.warning("AI worker already running")
        return _worker_instance

    _worker_instance = AIProcessingWorker(max_workers, poll_interval)
    await _worker_instance.start()
    return _worker_instance


async def stop_ai_worker():
    """Stop the global AI processing worker."""
    global _worker_instance

    if _worker_instance:
        await _worker_instance.stop()
        _worker_instance = None


def get_ai_worker() -> Optional[AIProcessingWorker]:
    """Get the global AI processing worker instance."""
    return _worker_instance