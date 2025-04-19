from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email": True,
            "sms": False
        }
    )


class UserCreate(UserBase):
    hashed_password: str


class UserInDB(UserBase):
    id: UUID = Field(default_factory=UUID, alias="id")
    hashed_password: str
    is_verified: bool = False
    plaid_access_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class User(UserBase):
    id: UUID = Field(alias="id")
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    notification_preferences: Optional[Dict[str, bool]] = None
    is_verified: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True