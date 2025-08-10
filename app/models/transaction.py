from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Transaction(BaseModel):
    id: str = Field(..., description="Unique identifier for the transaction (UUID)")
    user_id: str = Field(..., description="UUID of the user this transaction belongs to")
    amount: float = Field(..., description="Amount of the transaction")
    type: str = Field(..., description="Type of transaction (e.g., 'expense', 'income')")
    category: str = Field(..., description="Categorization of the transaction (e.g., 'Groceries', 'Salary')")
    description: Optional[str] = Field(None, description="Brief description of the transaction")
    date: datetime = Field(..., description="Date and time of the transaction")
    source: str = Field(..., description="Source of the transaction (e.g., 'bank', 'credit_card', 'manual')")
    details: Optional[dict] = Field(None, description="Additional details about the transaction")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of transaction creation")
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of last transaction update")
