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
from app.models.budget import Budget
from app.models.transaction import Transaction

class Alert(BaseModel):
    """Represents a single alert or notification."""
    type: str = Field(..., description="Type of alert (e.g., 'budget_exceeded', 'unusual_spending', 'bill_due')")
    message: str = Field(..., description="The notification message for the user")
    severity: str = Field("info", description="Severity of the alert ('info', 'warning', 'critical')")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp when the alert was generated")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details related to the alert")

class AlertNotificationSummary(BaseModel):
    """Summary of alerts and notifications generated."""
    user_id: str = Field(..., description="UUID of the user")
    alerts: List[Alert] = Field(..., description="List of generated alerts")
    summary_message: str = Field(..., description="A concise summary of all alerts")
    notification_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of notification summary creation")

class AlertNotificationAgent:
    """Agent for generating alerts and notifications using pydantic_ai.Agent."""
    
    def __init__(self):
        """Initialize the alert and notification agent based on settings."""
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
            result_type=AlertNotificationSummary
        )
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt for alert and notification generation."""
        return """
        You are an Alert & Notification Agent for DebtEase. Your role is to monitor financial data and generate timely, actionable alerts and notifications for the user.

        Input will include a JSON string containing:
        - user_id: string (UUID)
        - current_budget: Optional Budget object (from app.models.budget) with `categories` including `spent_amount` and `allocated_amount`.
        - recent_transactions: List of recent Transaction objects (from app.models.transaction).
        - upcoming_bills: List of dictionaries with 'name', 'amount', 'due_date' (ISO format).
        - historical_spending_patterns: Optional dictionary summarizing typical spending by category over time.

        Your output should be an AlertNotificationSummary object, containing a list of Alert objects. Generate alerts for the following conditions:
        1.  **Budget Exceeded/Nearing Limit**: If `spent_amount` in any `BudgetCategory` is >= 90% of `allocated_amount` or has exceeded it.
            -   Type: 'budget_exceeded' or 'budget_nearing_limit'
            -   Severity: 'warning' or 'critical'
        2.  **Unusual Spending**: If a recent transaction is significantly higher than typical spending for that category (compare with `historical_spending_patterns` if available, or a general heuristic like >2x average transaction in that category).
            -   Type: 'unusual_spending'
            -   Severity: 'warning'
        3.  **Upcoming Bills**: If a bill's `due_date` is within the next 7 days.
            -   Type: 'bill_due'
            -   Severity: 'info'
        4.  **Manual Expense Reminder**: If no manual transactions have been logged for a certain period (e.g., 3 days) and the user relies on manual input.
            -   Type: 'manual_input_reminder'
            -   Severity: 'info'

        For each alert, provide a clear `message` and relevant `details`.
        Finally, provide a `summary_message` that concisely summarizes all generated alerts.

        Output Format (strict JSON):
        {
            "user_id": str,
            "alerts": [
                {
                    "type": str,
                    "message": str,
                    "severity": str,
                    "timestamp": "string (ISO datetime)",
                    "details": dict
                }
            ],
            "summary_message": str,
            "notification_timestamp": "string (ISO datetime)"
        }

        Rules:
        -   Only generate alerts for conditions that are met.
        -   Ensure `timestamp` for each alert and `notification_timestamp` are in ISO 8601 format.
        -   Be specific in alert messages, e.g., "Your 'Groceries' budget is 95% used."
        """
    
    def generate_alerts(self, user_id: str, current_budget: Optional[Dict[str, Any]] = None, recent_transactions: Optional[List[Dict[str, Any]]] = None, upcoming_bills: Optional[List[Dict[str, Any]]] = None, historical_spending_patterns: Optional[Dict[str, Any]] = None) -> AlertNotificationSummary:
        """Generate alerts based on financial data."""
        input_data = {
            "user_id": user_id,
            "current_budget": current_budget,
            "recent_transactions": recent_transactions,
            "upcoming_bills": upcoming_bills,
            "historical_spending_patterns": historical_spending_patterns
        }
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result.data

def main():
    """Run the alert and notification agent from the command line."""
    import argparse
    from uuid import uuid4
    
    parser = argparse.ArgumentParser(description='Generate financial alerts and notifications')
    parser.add_argument('--user_id', type=str, default=str(uuid4()), help='UUID of the user')
    parser.add_argument('--budget_file', type=str, help='Path to JSON file with current budget')
    parser.add_argument('--transactions_file', type=str, help='Path to JSON file with recent transactions')
    parser.add_argument('--bills_file', type=str, help='Path to JSON file with upcoming bills')
    parser.add_argument('--history_file', type=str, help='Path to JSON file with historical spending patterns')
    
    args = parser.parse_args()
    
    current_budget = None
    if args.budget_file and os.path.exists(args.budget_file):
        with open(args.budget_file, 'r') as f:
            current_budget = json.load(f)

    recent_transactions = None
    if args.transactions_file and os.path.exists(args.transactions_file):
        with open(args.transactions_file, 'r') as f:
            recent_transactions = json.load(f)

    upcoming_bills = None
    if args.bills_file and os.path.exists(args.bills_file):
        with open(args.bills_file, 'r') as f:
            upcoming_bills = json.load(f)

    historical_spending_patterns = None
    if args.history_file and os.path.exists(args.history_file):
        with open(args.history_file, 'r') as f:
            historical_spending_patterns = json.load(f)

    agent = AlertNotificationAgent()
    
    print("Generating alerts...")
    alerts_summary = agent.generate_alerts(
        user_id=args.user_id,
        current_budget=current_budget,
        recent_transactions=recent_transactions,
        upcoming_bills=upcoming_bills,
        historical_spending_patterns=historical_spending_patterns
    )
    
    print("Alerts Summary:")
    print(alerts_summary.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
