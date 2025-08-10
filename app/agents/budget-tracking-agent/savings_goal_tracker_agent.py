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
from app.models.financial_goal import FinancialGoal

class SavingsGoalTrackingSummary(BaseModel):
    """Summary of savings goal tracking and progress."""
    user_id: str = Field(..., description="UUID of the user")
    goals: List[FinancialGoal] = Field(..., description="List of financial goals with updated progress")
    total_saved_across_goals: float = Field(..., description="Total amount saved across all active goals")
    overall_progress_percentage: float = Field(..., description="Overall progress towards all active goals (weighted by target amount)")
    recommendations: List[str] = Field(..., description="Recommendations to accelerate savings or adjust goals")
    tracking_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of savings tracking summary creation")

class SavingsGoalTrackerAgent:
    """Agent for tracking progress towards financial goals and providing recommendations."""
    
    def __init__(self):
        """Initialize the savings goal tracker agent based on settings."""
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
            result_type=SavingsGoalTrackingSummary
        )
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt for savings goal tracking."""
        return """
        You are a Savings & Goal Tracker Agent for DebtEase. Your task is to track the user's progress towards their financial goals and provide actionable recommendations.

        Input will include a JSON string containing:
        - user_id: string (UUID)
        - financial_goals: List of FinancialGoal objects (from app.models.financial_goal), potentially with updated `current_amount`.
        - available_income_for_savings: float (discretionary income or amount user can allocate to savings)

        Your output should be a SavingsGoalTrackingSummary object. For each goal, you should:
        1.  Calculate the `progress_percentage` (current_amount / target_amount * 100).
        2.  Estimate `time_to_achieve` if current saving rate continues.
        3.  Update `is_achieved` status if `current_amount` >= `target_amount`.

        The summary should include:
        -   `goals`: The updated list of FinancialGoal objects.
        -   `total_saved_across_goals`: Sum of `current_amount` for all active goals.
        -   `overall_progress_percentage`: Weighted average progress across all active goals.
        -   `recommendations`: List of actionable suggestions, such as:
            -   How to allocate `available_income_for_savings` among goals (e.g., prioritize highest priority, or smallest remaining).
            -   Suggestions to increase savings rate.
            -   Advice on adjusting target amounts or dates if goals are unrealistic.
            -   Celebratory messages for achieved goals.

        Output Format (strict JSON):
        {
            "user_id": str,
            "goals": [
                {
                    "id": str,
                    "user_id": str,
                    "name": str,
                    "target_amount": float,
                    "current_amount": float,
                    "target_date": "string (ISO datetime)" or null,
                    "priority": int,
                    "is_achieved": bool,
                    "created_at": "string (ISO datetime)",
                    "updated_at": "string (ISO datetime)"
                }
            ],
            "total_saved_across_goals": float,
            "overall_progress_percentage": float,
            "recommendations": [str],
            "tracking_timestamp": "string (ISO datetime)"
        }

        Rules:
        -   All financial figures should be rounded to 2 decimal places.
        -   Ensure `updated_at` for each goal reflects the current timestamp if its status or amount is changed.
        -   Prioritize recommendations based on goal priority and feasibility.
        """
    
    def track_goals(self, user_id: str, financial_goals: List[Dict[str, Any]], available_income_for_savings: float) -> SavingsGoalTrackingSummary:
        """Track progress towards financial goals and provide recommendations."""
        input_data = {
            "user_id": user_id,
            "financial_goals": financial_goals,
            "available_income_for_savings": available_income_for_savings
        }
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result.data

def main():
    """Run the savings goal tracker agent from the command line."""
    import argparse
    from uuid import uuid4
    
    parser = argparse.ArgumentParser(description='Track financial goals and provide recommendations')
    parser.add_argument('--user_id', type=str, default=str(uuid4()), help='UUID of the user')
    parser.add_argument('--goals_file', type=str, required=True, help='Path to JSON file with financial goals')
    parser.add_argument('--available_income', type=float, default=0.0, help='Amount of income available for savings')
    
    args = parser.parse_args()
    
    financial_goals = []
    if os.path.exists(args.goals_file):
        with open(args.goals_file, 'r') as f:
            financial_goals = json.load(f)
    else:
        print(f"Error: Goals file '{args.goals_file}' does not exist")
        return

    agent = SavingsGoalTrackerAgent()
    
    print("Tracking financial goals...")
    tracking_summary = agent.track_goals(
        user_id=args.user_id,
        financial_goals=financial_goals,
        available_income_for_savings=args.available_income
    )
    
    print("Savings Goal Tracking Summary:")
    print(tracking_summary.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
