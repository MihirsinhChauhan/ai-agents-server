from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FinancialGoal(BaseModel):
    id: str = Field(..., description="Unique identifier for the financial goal (UUID)")
    user_id: str = Field(..., description="UUID of the user this goal belongs to")
    name: str = Field(..., description="Name of the financial goal (e.g., 'Emergency Fund', 'Down Payment')")
    target_amount: float = Field(..., description="The total amount to save for this goal")
    current_amount: float = Field(0.0, description="The current amount saved towards this goal")
    target_date: Optional[datetime] = Field(None, description="Optional target date for achieving the goal")
    priority: int = Field(0, description="Priority level of the goal (higher number means higher priority)")
    is_achieved: bool = Field(False, description="True if the goal has been achieved")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of goal creation")
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of last goal update")
