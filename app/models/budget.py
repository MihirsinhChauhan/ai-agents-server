from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class BudgetCategory(BaseModel):
    name: str = Field(..., description="Name of the budget category (e.g., 'Groceries', 'Utilities')")
    allocated_amount: float = Field(..., description="Amount allocated to this category for the budget period")
    spent_amount: float = Field(0.0, description="Amount already spent in this category for the current period")
    limit_exceeded: bool = Field(False, description="True if spent_amount exceeds allocated_amount")

class Budget(BaseModel):
    user_id: str = Field(..., description="UUID of the user this budget belongs to")
    name: str = Field(..., description="Name of the budget (e.g., 'Monthly Budget', 'Vacation Budget')")
    start_date: datetime = Field(..., description="Start date of the budget period")
    end_date: datetime = Field(..., description="End date of the budget period")
    total_income: float = Field(..., description="Total expected income for the budget period")
    total_allocated: float = Field(..., description="Sum of all allocated amounts across categories")
    categories: List[BudgetCategory] = Field(..., description="List of budget categories with their allocated and spent amounts")
    is_active: bool = Field(True, description="Whether this budget is currently active")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of budget creation")
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of last budget update")
