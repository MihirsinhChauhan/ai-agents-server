from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class DebtType(str, Enum):
    CREDIT_CARD = "credit_card"
    PERSONAL_LOAN = "personal_loan"
    STUDENT_LOAN = "student_loan"
    AUTO_LOAN = "auto_loan"
    MORTGAGE = "mortgage"
    MEDICAL = "medical"
    FAMILY = "family"
    OTHER = "other"


class DebtSource(str, Enum):
    MANUAL = "manual"
    PLAID = "plaid"


class PaymentFrequency(str, Enum):
    MONTHLY = "monthly"
    BI_WEEKLY = "bi_weekly"
    WEEKLY = "weekly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class DebtBase(BaseModel):
    name: str
    type: DebtType
    amount: float
    interest_rate: float
    minimum_payment: Optional[float] = None  # Allow null to fix validation error
    payment_frequency: PaymentFrequency = PaymentFrequency.MONTHLY
    source: DebtSource
    details: Dict[str, Any] = Field(default_factory=dict)


class DebtCreate(DebtBase):
    user_id: UUID
    due_date: Optional[date] = None

    @field_validator('due_date')
    def validate_due_date(cls, v):
        if v is not None:
            day = v.day
            if day < 1 or day > 31:
                raise ValueError("Due date day must be between 1 and 31")
        return v


class DebtInDB(DebtBase):
    id: UUID = Field(default_factory=UUID, alias="id")
    user_id: UUID
    due_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.now)
    blockchain_id: Optional[str] = None
    is_active: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class Debt(DebtBase):
    id: UUID = Field(alias="id")
    user_id: UUID
    due_date: Optional[date] = None
    created_at: datetime
    blockchain_id: Optional[str] = None
    is_active: bool

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class DebtUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    payment_frequency: Optional[PaymentFrequency] = None
    due_date: Optional[date] = None
    details: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    @field_validator('due_date')
    def validate_due_date(cls, v):
        if v is not None:
            day = v.day
            if day < 1 or day > 31:
                raise ValueError("Due date day must be between 1 and 31")
        return v

    class Config:
        arbitrary_types_allowed = True