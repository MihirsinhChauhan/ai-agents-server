from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentBase(BaseModel):
    debt_id: UUID
    amount: float
    date: datetime = Field(default_factory=datetime.now)
    status: PaymentStatus = PaymentStatus.CONFIRMED
    notes: Optional[str] = None
    extra_details: Dict[str, Any] = Field(default_factory=dict)


class PaymentCreate(PaymentBase):
    user_id: UUID


class PaymentInDB(PaymentBase):
    id: UUID = Field(default_factory=UUID, alias="id")
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.now)
    blockchain_id: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class Payment(PaymentBase):
    id: UUID = Field(alias="id")
    user_id: UUID
    created_at: datetime
    blockchain_id: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    date: Optional[datetime] = None
    status: Optional[PaymentStatus] = None
    notes: Optional[str] = None
    extra_details: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True