from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, EmailStr, field_validator
from uuid import UUID, uuid4


class UserBase(BaseModel):
    """Base user model with core fields"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    monthly_income: Optional[float] = Field(None, ge=0, description="Monthly income for DTI calculations")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email": True,
            "sms": False
        },
        description="Notification preferences"
    )

    @field_validator('monthly_income')
    @classmethod
    def validate_monthly_income(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly income is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly income cannot be negative")
        return v


class UserCreate(BaseModel):
    """Model for creating a new user"""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255)
    monthly_income: Optional[float] = Field(None, ge=0)
    phone_number: Optional[str] = Field(None, max_length=20)
    hashed_password: str
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email": True,
            "sms": False
        }
    )


class UserInDB(UserBase):
    """Database representation of user"""
    id: UUID = Field(default_factory=uuid4)
    hashed_password: str
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    plaid_access_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UserProfileResponse(BaseModel):
    """Response model matching frontend UserProfile interface exactly"""
    id: str = Field(..., description="Unique user identifier")
    email: Optional[str] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, description="Full name of the user")
    monthly_income: Optional[float] = Field(None, description="Monthly income for DTI calculations")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @classmethod
    def from_user_in_db(cls, user: UserInDB) -> "UserProfileResponse":
        """Convert UserInDB to UserProfileResponse"""
        return cls(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            monthly_income=user.monthly_income,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )


class UserUpdate(BaseModel):
    """Model for updating an existing user"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    monthly_income: Optional[float] = Field(None, ge=0)
    phone_number: Optional[str] = Field(None, max_length=20)
    notification_preferences: Optional[Dict[str, bool]] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator('monthly_income')
    @classmethod
    def validate_monthly_income(cls, v: Optional[float]) -> Optional[float]:
        """Validate monthly income is non-negative"""
        if v is not None and v < 0:
            raise ValueError("Monthly income cannot be negative")
        return v

    class Config:
        arbitrary_types_allowed = True


# Legacy compatibility - alias for UserProfileResponse
User = UserProfileResponse