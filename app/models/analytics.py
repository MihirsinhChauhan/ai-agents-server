from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from uuid import UUID, uuid4


class DTIMetricsResponse(BaseModel):
    """Response model matching frontend DTIMetrics interface exactly"""
    frontend_dti: float = Field(..., description="Housing costs only DTI ratio")
    backend_dti: float = Field(..., description="All debt payments DTI ratio")
    total_monthly_debt_payments: float = Field(..., description="Total monthly debt payments")
    monthly_income: float = Field(..., description="Monthly income")
    is_healthy: bool = Field(..., description="Whether DTI ratios are in healthy range")

    @field_validator('frontend_dti', 'backend_dti', 'total_monthly_debt_payments', 'monthly_income')
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        """Validate values are non-negative"""
        if v < 0:
            raise ValueError("Values cannot be negative")
        return v


class DebtSummaryResponse(BaseModel):
    """Response model matching frontend DebtSummary interface exactly"""
    total_debt: float = Field(..., description="Total debt amount")
    total_interest_paid: float = Field(..., description="Total interest paid to date")
    total_minimum_payments: float = Field(..., description="Total minimum monthly payments")
    average_interest_rate: float = Field(..., description="Average interest rate across all debts")
    debt_count: int = Field(..., description="Number of active debts")
    high_priority_count: int = Field(..., description="Number of high priority debts")
    upcomingPaymentsCount: int = Field(..., description="Number of upcoming payments")

    @field_validator('total_debt', 'total_interest_paid', 'total_minimum_payments', 'average_interest_rate')
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        """Validate values are non-negative"""
        if v < 0:
            raise ValueError("Values cannot be negative")
        return v

    @field_validator('debt_count', 'high_priority_count', 'upcomingPaymentsCount')
    @classmethod
    def validate_non_negative_int(cls, v: int) -> int:
        """Validate values are non-negative"""
        if v < 0:
            raise ValueError("Counts cannot be negative")
        return v


class UserStreakResponse(BaseModel):
    """Response model matching frontend UserStreak interface exactly"""
    id: str = Field(..., description="Unique streak identifier")
    user_id: str = Field(..., description="User ID this streak belongs to")
    current_streak: int = Field(..., description="Current consecutive payment streak")
    longest_streak: int = Field(..., description="Longest streak ever achieved")
    last_check_in: Optional[str] = Field(None, description="Last check-in date in YYYY-MM-DD format")
    total_payments_logged: int = Field(..., description="Total number of payments logged")
    milestones_achieved: List[str] = Field(..., description="List of achieved milestones")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @field_validator('current_streak', 'longest_streak', 'total_payments_logged')
    @classmethod
    def validate_non_negative_int(cls, v: int) -> int:
        """Validate values are non-negative"""
        if v < 0:
            raise ValueError("Streak values cannot be negative")
        return v

    @field_validator('last_check_in')
    @classmethod
    def validate_check_in_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate check-in date format"""
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Check-in date must be in YYYY-MM-DD format")
        return v


class AIRecommendationResponse(BaseModel):
    """Response model matching frontend AIRecommendation interface exactly"""
    id: str = Field(..., description="Unique recommendation identifier")
    user_id: str = Field(..., description="User ID this recommendation is for")
    recommendation_type: str = Field(..., description="Type of recommendation (snowball, avalanche, refinance)")
    title: str = Field(..., min_length=1, max_length=255, description="Recommendation title")
    description: str = Field(..., min_length=1, description="Detailed recommendation description")
    potential_savings: Optional[float] = Field(None, description="Potential savings amount")
    priority_score: int = Field(..., ge=0, le=10, description="Priority score from 0-10")
    is_dismissed: bool = Field(..., description="Whether user has dismissed this recommendation")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

    @field_validator('recommendation_type')
    @classmethod
    def validate_recommendation_type(cls, v: str) -> str:
        """Validate recommendation type"""
        valid_types = ['snowball', 'avalanche', 'refinance']
        if v not in valid_types:
            raise ValueError(f"Recommendation type must be one of: {', '.join(valid_types)}")
        return v

    @field_validator('potential_savings')
    @classmethod
    def validate_potential_savings(cls, v: Optional[float]) -> Optional[float]:
        """Validate potential savings is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Potential savings cannot be negative")
        return v


# Database models for internal use
class UserStreakInDB(BaseModel):
    """Database representation of user streak"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    current_streak: int = Field(default=0)
    longest_streak: int = Field(default=0)
    last_check_in: Optional[str] = None
    total_payments_logged: int = Field(default=0)
    milestones_achieved: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class AIRecommendationInDB(BaseModel):
    """Database representation of AI recommendation"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    recommendation_type: str
    title: str
    description: str
    potential_savings: Optional[float] = None
    priority_score: int
    is_dismissed: bool = Field(default=False)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


# Conversion methods
def convert_user_streak_to_response(streak: UserStreakInDB) -> UserStreakResponse:
    """Convert UserStreakInDB to UserStreakResponse"""
    return UserStreakResponse(
        id=str(streak.id),
        user_id=str(streak.user_id),
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_check_in=streak.last_check_in,
        total_payments_logged=streak.total_payments_logged,
        milestones_achieved=streak.milestones_achieved,
        created_at=streak.created_at.isoformat() if streak.created_at else None,
        updated_at=streak.updated_at.isoformat() if streak.updated_at else None
    )


def convert_ai_recommendation_to_response(recommendation: AIRecommendationInDB) -> AIRecommendationResponse:
    """Convert AIRecommendationInDB to AIRecommendationResponse"""
    return AIRecommendationResponse(
        id=str(recommendation.id),
        user_id=str(recommendation.user_id),
        recommendation_type=recommendation.recommendation_type,
        title=recommendation.title,
        description=recommendation.description,
        potential_savings=recommendation.potential_savings,
        priority_score=recommendation.priority_score,
        is_dismissed=recommendation.is_dismissed,
        created_at=recommendation.created_at.isoformat() if recommendation.created_at else None
    )
