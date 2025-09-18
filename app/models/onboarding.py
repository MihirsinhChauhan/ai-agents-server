"""
Onboarding models for DebtEase user onboarding flow.
Defines Pydantic models for onboarding progress tracking, user goals, and related data structures.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


# Enums for onboarding data validation
class OnboardingStep(str, Enum):
    """Enumeration of onboarding steps"""
    WELCOME = "welcome"
    PROFILE_SETUP = "profile_setup"
    DEBT_COLLECTION = "debt_collection"
    GOAL_SETTING = "goal_setting"
    DASHBOARD_INTRO = "dashboard_intro"
    COMPLETED = "completed"


class FinancialExperience(str, Enum):
    """Enumeration of financial experience levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EmploymentStatus(str, Enum):
    """Enumeration of employment statuses"""
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"
    STUDENT = "student"


class IncomeFrequency(str, Enum):
    """Enumeration of income frequency options"""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    ANNUALLY = "annually"


class GoalType(str, Enum):
    """Enumeration of goal types"""
    DEBT_FREEDOM = "debt_freedom"
    REDUCE_INTEREST = "reduce_interest"
    SPECIFIC_AMOUNT = "specific_amount"
    CUSTOM = "custom"


class PreferredStrategy(str, Enum):
    """Enumeration of preferred debt repayment strategies"""
    SNOWBALL = "snowball"
    AVALANCHE = "avalanche"
    CUSTOM = "custom"


class DeviceType(str, Enum):
    """Enumeration of device types for analytics"""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


# Base data models for onboarding steps
class OnboardingProfileData(BaseModel):
    """Data collected during profile setup step"""
    monthly_income: Optional[float] = Field(None, ge=0, description="Monthly income amount")
    income_frequency: IncomeFrequency = Field(IncomeFrequency.MONTHLY, description="How often income is received")
    employment_status: Optional[EmploymentStatus] = Field(None, description="Current employment status")
    financial_experience: FinancialExperience = Field(FinancialExperience.BEGINNER, description="Self-reported financial experience level")

    @field_validator('monthly_income')
    @classmethod
    def validate_monthly_income(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly income is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly income cannot be negative")
        return v


class OnboardingDebtData(BaseModel):
    """Data collected during debt collection step"""
    debts_added: int = Field(0, ge=0, description="Number of debts added by user")
    total_debt_amount: float = Field(0.0, ge=0, description="Total amount of debt collected")
    debt_types: List[str] = Field(default_factory=list, description="Types of debts added")
    skip_debt_entry: bool = Field(False, description="Whether user chose to skip debt entry")


class OnboardingGoalData(BaseModel):
    """Data collected during goal setting step"""
    goal_type: str = Field(..., description="Type of financial goal")
    target_amount: Optional[float] = Field(None, ge=0, description="Monetary target for the goal")
    target_date: Optional[date] = Field(None, description="Target completion date")
    preferred_strategy: str = Field("snowball", description="Preferred debt repayment strategy")
    monthly_extra_payment: Optional[float] = Field(None, ge=0, description="Monthly extra payment amount")
    priority_level: int = Field(5, ge=1, le=10, description="Priority level (1-10)")
    description: Optional[str] = Field(None, max_length=1000, description="Optional goal description")

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate target date is in the future"""
        if v is not None and v <= date.today():
            raise ValueError("Target date must be in the future")
        return v

    @field_validator('monthly_extra_payment')
    @classmethod
    def validate_monthly_extra_payment(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly extra payment is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly extra payment cannot be negative")
        return v


# Database models
class OnboardingProgressBase(BaseModel):
    """Base model for onboarding progress"""
    user_id: UUID = Field(..., description="Reference to the user")
    current_step: OnboardingStep = Field(OnboardingStep.WELCOME, description="Current onboarding step")
    completed_steps: List[str] = Field(default_factory=list, description="List of completed step names")
    onboarding_data: Dict[str, Any] = Field(default_factory=dict, description="JSON data collected during onboarding")
    is_completed: bool = Field(False, description="Whether onboarding is completed")

    @field_validator('completed_steps')
    @classmethod
    def validate_completed_steps(cls, v: List[str]) -> List[str]:
        """Validate completed steps are valid step names"""
        valid_steps = {step.value for step in OnboardingStep}
        for step in v:
            if step not in valid_steps:
                raise ValueError(f"Invalid completed step: {step}")
        return v


class OnboardingProgressCreate(OnboardingProgressBase):
    """Model for creating new onboarding progress record"""
    user_id: UUID
    current_step: OnboardingStep = OnboardingStep.WELCOME
    completed_steps: List[str] = []
    onboarding_data: Dict[str, Any] = {}
    is_completed: bool = False


class OnboardingProgressUpdate(BaseModel):
    """Model for updating onboarding progress"""
    current_step: Optional[OnboardingStep] = None
    completed_steps: Optional[List[str]] = None
    onboarding_data: Optional[Dict[str, Any]] = None
    is_completed: Optional[bool] = None

    @field_validator('completed_steps')
    @classmethod
    def validate_completed_steps(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate completed steps are valid step names"""
        if v is not None:
            valid_steps = {step.value for step in OnboardingStep}
            for step in v:
                if step not in valid_steps:
                    raise ValueError(f"Invalid completed step: {step}")
        return v


class OnboardingProgressResponse(OnboardingProgressBase):
    """Response model for onboarding progress with database fields"""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    started_at: datetime = Field(default_factory=datetime.now, description="When onboarding started")
    completed_at: Optional[datetime] = Field(None, description="When onboarding was completed")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    progress_percentage: float = Field(0.0, ge=0, le=100, description="Calculated progress percentage")

    model_config = ConfigDict(from_attributes=True)


class UserGoalBase(BaseModel):
    """Base model for user goals"""
    user_id: UUID = Field(..., description="Reference to the user")
    goal_type: GoalType = Field(..., description="Type of financial goal")
    target_amount: Optional[float] = Field(None, ge=0, description="Monetary target amount")
    target_date: Optional[date] = Field(None, description="Target completion date")
    preferred_strategy: PreferredStrategy = Field(PreferredStrategy.SNOWBALL, description="Preferred repayment strategy")
    monthly_extra_payment: Optional[float] = Field(None, ge=0, description="Monthly extra payment")
    priority_level: int = Field(5, ge=1, le=10, description="Priority level (1-10)")
    description: Optional[str] = Field(None, max_length=1000, description="Goal description")
    is_active: bool = Field(True, description="Whether goal is active")

    @field_validator('target_amount')
    @classmethod
    def validate_target_amount(cls, v: Optional[float]) -> Optional[float]:
        """Validate target amount is positive"""
        if v is not None and v <= 0:
            raise ValueError("Target amount must be positive")
        return v

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate target date is in the future"""
        if v is not None and v <= date.today():
            raise ValueError("Target date must be in the future")
        return v

    @field_validator('monthly_extra_payment')
    @classmethod
    def validate_monthly_extra_payment(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly extra payment is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly extra payment cannot be negative")
        return v


class UserGoalCreate(UserGoalBase):
    """Model for creating new user goals"""
    user_id: UUID
    goal_type: GoalType
    is_active: bool = True


class UserGoalUpdate(BaseModel):
    """Model for updating user goals"""
    goal_type: Optional[GoalType] = None
    target_amount: Optional[float] = None
    target_date: Optional[date] = None
    preferred_strategy: Optional[PreferredStrategy] = None
    monthly_extra_payment: Optional[float] = None
    priority_level: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    progress_percentage: Optional[float] = None

    @field_validator('target_amount')
    @classmethod
    def validate_target_amount(cls, v: Optional[float]) -> Optional[float]:
        """Validate target amount is positive"""
        if v is not None and v <= 0:
            raise ValueError("Target amount must be positive")
        return v

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate target date is in the future"""
        if v is not None and v <= date.today():
            raise ValueError("Target date must be in the future")
        return v

    @field_validator('monthly_extra_payment')
    @classmethod
    def validate_monthly_extra_payment(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly extra payment is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly extra payment cannot be negative")
        return v

    @field_validator('progress_percentage')
    @classmethod
    def validate_progress_percentage(cls, v: Optional[float]) -> Optional[float]:
        """Validate progress percentage is between 0 and 100"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Progress percentage must be between 0 and 100")
        return v

    @field_validator('priority_level')
    @classmethod
    def validate_priority_level(cls, v: Optional[int]) -> Optional[int]:
        """Validate priority level is between 1 and 10"""
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Priority level must be between 1 and 10")
        return v


class UserGoalResponse(UserGoalBase):
    """Response model for user goals with database fields"""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    progress_percentage: float = Field(0.0, ge=0, le=100, description="Current progress percentage")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class OnboardingAnalyticsBase(BaseModel):
    """Base model for onboarding analytics"""
    user_id: UUID = Field(..., description="Reference to the user")
    step_name: str = Field(..., description="Name of the onboarding step")
    time_spent_seconds: Optional[int] = Field(None, gt=0, description="Time spent on step in seconds")
    completion_rate: Optional[float] = Field(None, ge=0, le=100, description="Completion rate percentage")
    drop_off_point: Optional[str] = Field(None, description="Point where user dropped off")
    user_agent: Optional[str] = Field(None, description="User's browser/device info")
    device_type: Optional[DeviceType] = Field(None, description="Type of device used")


class OnboardingAnalyticsCreate(OnboardingAnalyticsBase):
    """Model for creating onboarding analytics records"""
    user_id: UUID
    step_name: str


class OnboardingAnalyticsResponse(OnboardingAnalyticsBase):
    """Response model for onboarding analytics with database fields"""
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# Enhanced user models for onboarding
class UserOnboardingProfile(BaseModel):
    """Enhanced user model with onboarding fields"""
    monthly_income: Optional[float] = Field(None, ge=0, description="Monthly income")
    income_frequency: IncomeFrequency = Field(IncomeFrequency.MONTHLY, description="Income frequency")
    employment_status: Optional[EmploymentStatus] = Field(None, description="Employment status")
    financial_experience: FinancialExperience = Field(FinancialExperience.BEGINNER, description="Financial experience level")
    onboarding_completed: bool = Field(False, description="Whether onboarding is completed")
    onboarding_completed_at: Optional[datetime] = Field(None, description="When onboarding was completed")

    @field_validator('monthly_income')
    @classmethod
    def validate_monthly_income(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly income is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly income cannot be negative")
        return v


class UserProfileUpdateWithOnboarding(BaseModel):
    """Model for updating user profile with onboarding fields"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    monthly_income: Optional[float] = Field(None, ge=0)
    income_frequency: Optional[IncomeFrequency] = None
    employment_status: Optional[EmploymentStatus] = None
    financial_experience: Optional[FinancialExperience] = None
    phone_number: Optional[str] = Field(None, max_length=20)

    @field_validator('monthly_income')
    @classmethod
    def validate_monthly_income(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly income is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly income cannot be negative")
        return v


# Utility models for API responses
class OnboardingStatusResponse(BaseModel):
    """Response model for onboarding status"""
    current_step: OnboardingStep
    completed_steps: List[str]
    progress_percentage: float
    is_completed: bool
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    onboarding_data: Dict[str, Any]


class OnboardingSummaryResponse(BaseModel):
    """Response model for onboarding summary/analytics"""
    total_users: int
    completed_users: int
    completion_rate_percentage: float
    avg_completion_time_hours: Optional[float]


# Step-specific request/response models
class ProfileSetupRequest(BaseModel):
    """Request model for profile setup step"""
    monthly_income: Optional[float] = Field(None, ge=0)
    income_frequency: IncomeFrequency = IncomeFrequency.MONTHLY
    employment_status: Optional[EmploymentStatus] = None
    financial_experience: FinancialExperience = FinancialExperience.BEGINNER


class GoalSettingRequest(BaseModel):
    """Request model for goal setting step"""
    goal_type: GoalType
    target_amount: Optional[float] = Field(None, ge=0)
    target_date: Optional[date] = None
    preferred_strategy: PreferredStrategy = PreferredStrategy.SNOWBALL
    monthly_extra_payment: Optional[float] = Field(None, ge=0)
    priority_level: int = Field(5, ge=1, le=10)
    description: Optional[str] = Field(None, max_length=1000)


class StepCompletionRequest(BaseModel):
    """Request model for marking a step as completed"""
    step_name: str
    step_data: Optional[Dict[str, Any]] = None


# Progress calculation utilities
def calculate_onboarding_progress(completed_steps: List[str]) -> float:
    """
    Calculate onboarding progress percentage based on completed steps.

    Args:
        completed_steps: List of completed step names

    Returns:
        Progress percentage (0-100)
    """
    total_steps = len(OnboardingStep) - 1  # Exclude COMPLETED step
    completed_count = len(completed_steps)

    if total_steps == 0:
        return 100.0

    return min((completed_count / total_steps) * 100, 100.0)


def get_next_step(current_step: OnboardingStep, completed_steps: List[str]) -> OnboardingStep:
    """
    Determine the next step in the onboarding flow.

    Args:
        current_step: Current onboarding step
        completed_steps: List of completed steps

    Returns:
        Next step to navigate to
    """
    step_order = [
        OnboardingStep.WELCOME,
        OnboardingStep.PROFILE_SETUP,
        OnboardingStep.DEBT_COLLECTION,
        OnboardingStep.GOAL_SETTING,
        OnboardingStep.DASHBOARD_INTRO,
        OnboardingStep.COMPLETED
    ]

    current_index = step_order.index(current_step)

    # If current step is completed, move to next
    if current_step.value in completed_steps:
        if current_index + 1 < len(step_order):
            return step_order[current_index + 1]

    return current_step
