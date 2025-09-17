import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.configs.config import settings
from app.models.transaction import Transaction

class CategorizedTransaction(BaseModel):
    """Represents a single transaction with an assigned category."""
    transaction_id: str = Field(..., description="ID of the original transaction")
    amount: float = Field(..., description="Amount of the transaction")
    type: str = Field(..., description="Type of transaction (e.g., 'expense', 'income')")
    category: str = Field(..., description="Assigned category for the transaction")
    description: Optional[str] = Field(None, description="Description of the transaction")
    date: datetime = Field(..., description="Date of the transaction")

class ExpenseTrackingSummary(BaseModel):
    """Summary of expense tracking and categorization."""
    user_id: str = Field(..., description="UUID of the user")
    total_expenses: float = Field(..., description="Total sum of all categorized expenses")
    total_income: float = Field(..., description="Total sum of all categorized income")
    categorized_transactions: List[CategorizedTransaction] = Field(..., description="List of all transactions with their assigned categories")
    spending_by_category: Dict[str, float] = Field(..., description="Dictionary summarizing spending per category")
    uncategorized_transactions_count: int = Field(..., description="Number of transactions that could not be categorized automatically")
    tracking_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of expense tracking summary creation")
    insights: List[str] = Field(..., description="Key insights from the expense tracking, e.g., top spending categories")

class ExpenseTrackerAgent:
    """Agent for categorizing and tracking expenses using pydantic_ai.Agent."""
    
    def __init__(self):
        """Initialize the expense tracker agent based on settings."""
        if settings.LLM_PROVIDER == "openai":
            model = OpenAIModel(
                model_name=settings.LLM_MODEL,
                provider=OpenAIProvider(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None
                )
            )
        elif settings.LLM_PROVIDER == "groq":
            model = GroqModel(
                model_name=settings.LLM_MODEL,
                provider=GroqProvider(api_key=settings.GROQ_API_KEY)
            )
        elif settings.LLM_PROVIDER == "ollama":
            model = OpenAIModel(
                model_name=settings.LLM_MODEL,
                provider=OpenAIProvider(
                    base_url=settings.LLM_BASE_URL,
                    api_key="dummy"
                )
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

        self.agent = Agent(
            model=model,
            system_prompt=self._get_system_prompt(),
            result_type=ExpenseTrackingSummary
        )
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt for expense tracking and categorization."""
        return """
        You are an Expense Tracker Agent for DebtEase. Your primary task is to categorize raw financial transactions and provide a summary of spending.

        Input will be a JSON string containing:
        - user_id: string (UUID)
        - transactions: List of dictionaries, each representing a raw transaction. Each transaction will have at least:
            - id: string (UUID)
            - amount: float
            - description: string (e.g., "Starbucks Coffee", "Payroll Deposit", "Amazon.com")
            - date: string (ISO format or any date format)
            - type: string (e.g., "debit", "credit", "expense", "income")
        - available_categories: List of strings representing predefined categories (e.g., ["Groceries", "Utilities", "Transportation", "Dining Out", "Salary", "Rent", "Shopping", "Entertainment", "Healthcare", "Education", "Miscellaneous"])

        Your output should be an ExpenseTrackingSummary object. For each transaction, you must:
        1.  Determine if it's an 'expense' or 'income'.
        2.  Assign the most appropriate category from `available_categories` based on the transaction description. If no suitable category is found, assign it to "Uncategorized".
        3.  Calculate `total_expenses` and `total_income`.
        4.  Summarize `spending_by_category`.
        5.  Identify `uncategorized_transactions_count`.
        6.  Provide `insights` such as top spending categories, potential miscategorizations, or suggestions for new categories.

        Output Format (strict JSON):
        {
            "user_id": str,
            "total_expenses": float,
            "total_income": float,
            "categorized_transactions": [
                {
                    "transaction_id": str,
                    "amount": float,
                    "type": str,
                    "category": str,
                    "description": str,
                    "date": str (MUST be in ISO format like "2025-06-07T00:00:00.000Z" or "2025-06-07T00:00:00+00:00")
                }
            ],
            "spending_by_category": {"category_name": float},
            "uncategorized_transactions_count": int,
            "tracking_timestamp": "string (ISO datetime with timezone like 2025-08-11T01:27:40.386675+00:00)",
            "insights": [str]
        }

        Rules:
        -   All financial figures should be rounded to 2 decimal places.
        -   Prioritize accurate categorization. If unsure, use "Uncategorized".
        -   Ensure all input transactions are present in `categorized_transactions`.
        -   The `type` field in `CategorizedTransaction` should be either 'expense' or 'income'. Convert 'debit' to 'expense' and 'credit' to 'income'.
        -   CRITICAL: Ensure all dates in the output are in proper ISO datetime format with timezone (e.g., "2025-06-07T00:00:00+00:00" or "2025-06-07T00:00:00.000Z"). If input date is "2025-06-07 00:00:00", convert it to "2025-06-07T00:00:00+00:00".
        """
    
    def track_expenses(self, user_id: str, transactions: List[Dict[str, Any]], available_categories: List[str]) -> ExpenseTrackingSummary:
        """Categorize and summarize financial transactions."""
        input_data = {
            "user_id": user_id,
            "transactions": transactions,
            "available_categories": available_categories
        }
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result.data

def main():
    """Run the expense tracker agent from the command line."""
    import argparse
    from uuid import uuid4
    
    parser = argparse.ArgumentParser(description='Track and categorize expenses')
    parser.add_argument('--user_id', type=str, default=str(uuid4()), help='UUID of the user')
    parser.add_argument('--transactions_file', type=str, required=True, help='Path to JSON file with raw transactions')
    parser.add_argument('--categories', nargs='+', default=['Groceries', 'Utilities', 'Transportation', 'Dining Out', 'Salary', 'Rent', 'Shopping', 'Entertainment', 'Healthcare', 'Education', 'Miscellaneous', 'Uncategorized'], help='List of available categories for categorization')
    
    args = parser.parse_args()
    
    transactions = []
    if os.path.exists(args.transactions_file):
        with open(args.transactions_file, 'r') as f:
            transactions = json.load(f)
    else:
        print(f"Error: Transactions file '{args.transactions_file}' does not exist")
        return

    agent = ExpenseTrackerAgent()
    
    print("Tracking expenses...")
    tracking_summary = agent.track_expenses(
        user_id=args.user_id,
        transactions=transactions,
        available_categories=args.categories
    )
    
    print("Expense Tracking Summary:")
    print(tracking_summary.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
