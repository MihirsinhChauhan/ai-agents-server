"""SQLAlchemy User Model

Database model for User table to support relationships with AI cache services.
This is separate from the Pydantic User models used for API serialization.
"""

from sqlalchemy import Column, String, Boolean, TIMESTAMP, func, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from app.models.base import Base


class User(Base):
    """
    SQLAlchemy User model for database relationships.

    This model supports the AI insights cache system while maintaining
    compatibility with the existing AsyncPG-based user management.
    """
    __tablename__ = "users"

    # Primary key and basic fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # Profile fields
    monthly_income = Column(Float, nullable=True, comment="Monthly income for DTI calculations")

    # Onboarding fields
    onboarding_completed = Column(Boolean, default=False, comment="Whether onboarding is complete")
    onboarding_completed_at = Column(TIMESTAMP, nullable=True, comment="When onboarding was completed")

    # Account status
    is_active = Column(Boolean, default=True, comment="Whether account is active")

    # Timestamps
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    ai_insights_cache = relationship("AIInsightsCache", back_populates="user", cascade="all, delete-orphan")
    ai_processing_jobs = relationship("AIProcessingQueue", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

    def to_dict(self):
        """Convert SQLAlchemy model to dictionary for compatibility."""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "monthly_income": self.monthly_income,
            "onboarding_completed": self.onboarding_completed,
            "onboarding_completed_at": self.onboarding_completed_at.isoformat() if self.onboarding_completed_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }