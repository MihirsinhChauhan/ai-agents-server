"""AI Insights Cache Models

Database models for caching AI insights to improve performance and reduce API calls.
"""

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from uuid import UUID as PyUUID, uuid4
import hashlib
import json
from typing import Dict, List, Any, Optional

from app.models.base import Base


class AIInsightsCache(Base):
    """
    Cache table for AI insights to avoid regenerating expensive AI analysis.

    This table stores complete AI analysis results including debt analysis,
    recommendations, and metadata to provide instant responses to users.
    """
    __tablename__ = "ai_insights_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Core AI insights data (stored as JSONB for efficient querying)
    debt_analysis = Column(JSONB, nullable=False, comment="Debt analysis results from AI")
    recommendations = Column(JSONB, nullable=False, comment="AI-generated recommendations array")
    ai_metadata = Column(JSONB, default=dict, comment="Processing metadata and quality scores")

    # Cache management fields
    cache_key = Column(String(255), nullable=False, comment="Hash of user's debt portfolio for invalidation")
    generated_at = Column(TIMESTAMP, default=func.current_timestamp(), comment="When AI analysis was performed")
    expires_at = Column(TIMESTAMP, nullable=False, comment="Cache expiration time")

    # Version and status tracking
    version = Column(Integer, default=1, comment="Schema version for migrations")
    status = Column(String(20), default="completed", comment="Cache entry status")

    # Performance and debugging info
    processing_time = Column(Float, nullable=True, comment="Time taken to generate insights (seconds)")
    ai_model_used = Column(String(100), nullable=True, comment="AI model used for generation")
    error_log = Column(Text, nullable=True, comment="Error details if generation failed")

    # Relationship with lazy loading to avoid import issues
    user = relationship("User", back_populates="ai_insights_cache", lazy="select")

    @classmethod
    def generate_cache_key(cls, user_id: PyUUID, debt_data: List[Dict[str, Any]]) -> str:
        """
        Generate a cache key based on user's debt portfolio.

        This key changes when debts are modified, triggering cache invalidation.
        """
        # Sort debts by ID for consistent hashing
        sorted_debts = sorted(debt_data, key=lambda x: str(x.get('id', '')))

        # Create hash from relevant debt data
        debt_signature = {
            'user_id': str(user_id),
            'debts': [
                {
                    'id': str(debt.get('id', '')),
                    'balance': debt.get('current_balance', 0),
                    'interest_rate': debt.get('interest_rate', 0),
                    'minimum_payment': debt.get('minimum_payment', 0),
                    'debt_type': debt.get('debt_type', ''),
                }
                for debt in sorted_debts
            ]
        }

        # Generate SHA256 hash
        signature_str = json.dumps(debt_signature, sort_keys=True, default=str)
        return hashlib.sha256(signature_str.encode()).hexdigest()

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self, current_cache_key: str) -> bool:
        """Check if cache entry is valid (not expired and key matches)."""
        return not self.is_expired() and self.cache_key == current_cache_key

    @classmethod
    def get_default_ttl(cls) -> timedelta:
        """Get default cache TTL (7 days)."""
        return timedelta(days=7)

    def to_response_dict(self) -> Dict[str, Any]:
        """Convert cache entry to API response format."""
        return {
            "debt_analysis": self.debt_analysis,
            "recommendations": self.recommendations,
            "metadata": {
                **self.ai_metadata,
                "processing_time": self.processing_time or 0.0,
                "fallback_used": self.ai_metadata.get("fallback_used", False),
                "errors": self.ai_metadata.get("errors", []),
                "generated_at": self.generated_at.isoformat(),
                "cached": True,
                "expires_at": self.expires_at.isoformat(),
                "ai_model_used": self.ai_model_used,
                "cache_version": self.version,
            }
        }


class AIProcessingQueue(Base):
    """
    Queue for background AI processing tasks.

    This table manages background generation of AI insights to avoid blocking
    user requests and provide better rate limiting control.
    """
    __tablename__ = "ai_processing_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Task configuration
    task_type = Column(String(50), default="ai_insights", comment="Type of AI task to process")
    status = Column(String(20), default="queued", comment="Processing status")
    priority = Column(Integer, default=5, comment="Processing priority (1=highest, 10=lowest)")

    # Retry and error handling
    attempts = Column(Integer, default=0, comment="Number of processing attempts")
    max_attempts = Column(Integer, default=3, comment="Maximum retry attempts")
    error_log = Column(Text, nullable=True, comment="Error details from failed attempts")

    # Task data
    payload = Column(JSONB, default=dict, comment="Task-specific data and parameters")
    result = Column(JSONB, nullable=True, comment="Processing result data")

    # Timestamps
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    started_at = Column(TIMESTAMP, nullable=True, comment="When processing started")
    completed_at = Column(TIMESTAMP, nullable=True, comment="When processing completed")

    # Relationship with lazy loading to avoid import issues
    user = relationship("User", back_populates="ai_processing_jobs", lazy="select")

    @property
    def processing_time(self) -> Optional[float]:
        """Calculate processing time if task is completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.attempts < self.max_attempts and self.status in ["failed", "queued"]

    @property
    def is_stale(self, stale_threshold: timedelta = timedelta(hours=1)) -> bool:
        """Check if task has been processing for too long."""
        if self.status == "processing" and self.started_at:
            return datetime.utcnow() - self.started_at > stale_threshold
        return False

    def mark_started(self):
        """Mark task as started processing."""
        self.status = "processing"
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_completed(self, result: Dict[str, Any]):
        """Mark task as completed successfully."""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str):
        """Mark task as failed and increment attempts."""
        self.status = "failed"
        self.attempts += 1
        self.error_log = error_message
        self.updated_at = datetime.utcnow()

        # Reset to queued if can retry
        if self.can_retry:
            self.status = "queued"

    def to_dict(self) -> Dict[str, Any]:
        """Convert queue entry to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "task_type": self.task_type,
            "status": self.status,
            "priority": self.priority,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "payload": self.payload,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time,
        }


# Update User model to include relationship (add to existing User model)
"""
Add this to your existing User model:

# AI insights cache relationship
ai_insights_cache = relationship("AIInsightsCache", back_populates="user", cascade="all, delete-orphan")
"""