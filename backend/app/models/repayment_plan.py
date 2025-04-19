from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID


class StrategyType(str, Enum):
    AVALANCHE = "avalanche"
    SNOWBALL = "snowball"
    CUSTOM = "custom"


class RepaymentPlanBase(BaseModel):
    user_id: UUID
    strategy: StrategyType
    monthly_payment_amount: Optional[float] = None
    debt_order: List[UUID] = Field(default_factory=list)
    payment_schedule: List[Dict[str, Any]] = Field(default_factory=list)
    total_interest_saved: Optional[float] = None
    expected_completion_date: Optional[date] = None


class RepaymentPlanCreate(RepaymentPlanBase):
    pass


class RepaymentPlanInDB(RepaymentPlanBase):
    id: UUID = Field(default_factory=UUID, alias="id")
    is_active: bool = True
    blockchain_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class RepaymentPlan(RepaymentPlanBase):
    id: UUID = Field(alias="id")
    is_active: bool
    blockchain_id: Optional[str] = None
    created_at: datetime

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class RepaymentPlanUpdate(BaseModel):
    strategy: Optional[StrategyType] = None
    monthly_payment_amount: Optional[float] = None
    debt_order: Optional[List[UUID]] = None
    payment_schedule: Optional[List[Dict[str, Any]]] = None
    total_interest_saved: Optional[float] = None
    expected_completion_date: Optional[date] = None
    is_active: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True