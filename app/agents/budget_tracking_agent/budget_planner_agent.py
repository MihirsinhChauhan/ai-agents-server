import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.configs.config import settings
from app.models.budget import Budget, BudgetCategory

class BudgetPlan(BaseModel):
    """Result of budget planning."""
    user_id: str = Field(..., description="UUID of the user this budget plan belongs to")
    total_income: float = Field(..., description="Total income considered for the budget period")
    total_expenses: float = Field(..., description="Total estimated expenses for the budget period")
    discretionary_income: float = Field(..., description="Income remaining after fixed expenses and savings goals")
    recommended_budget: Budget = Field(..., description="The recommended budget object with categories and allocations")
    budget_insights: Dict[str, Any] = Field(..., description="Insights and recommendations for the budget")
    plan_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of budget plan creation")

class BudgetPlannerAgent:
    """Agent for planning and managing budgets using pydantic_ai.Agent."""
    
    def __init__(self):
        """Initialize the budget planner agent based on settings."""
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
            result_type=BudgetPlan
        )
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt for budget planning."""
        return """
        You are a Budget Planner Agent for DebtEase. Your task is to create a comprehensive budget plan based on user's financial information and goals.

        Input will include:
        - user_id: string (UUID)
        - income_sources: List of dictionaries with 'name', 'amount', 'frequency' (e.g., 'monthly', 'bi-weekly')
        - fixed_expenses: List of dictionaries with 'name', 'amount', 'frequency', 'due_date'
        - desired_categories: List of strings for budget categories (e.g., 'Groceries', 'Transportation', 'Entertainment')
        - financial_goals: List of FinancialGoal objects (from app.models.financial_goal)
        - current_budget: Optional existing Budget object to refine

        Your output should be a BudgetPlan object, including:
        1.  **total_income**: Sum of all income sources, annualized and then converted to monthly.
        2.  **total_expenses**: Sum of all fixed expenses, annualized and then converted to monthly. Also include estimated variable expenses based on common spending patterns if not explicitly provided.
        3.  **discretionary_income**: Calculate income remaining after fixed expenses and recommended savings for goals.
        4.  **recommended_budget**: A Budget object with:
            -   `user_id`, `name`, `start_date`, `end_date` (e.g., next month).
            -   `total_income`, `total_allocated` (sum of category allocations).
            -   `categories`: List of BudgetCategory objects with `name` and `allocated_amount`.
                -   Allocate amounts to `desired_categories` based on best practices (e.g., 50/30/20 rule: 50% needs, 30% wants, 20% savings/debt) and user's specific fixed expenses and goals.
                -   Ensure `spent_amount` is 0.0 and `limit_exceeded` is False for new budgets.
        5.  **budget_insights**: Dictionary with:
            -   "suggestions": List of strings (e.g., "Consider reducing entertainment spending by 10%").
            -   "risk_areas": List of strings (e.g., "High fixed expenses relative to income").
            -   "opportunities": List of strings (e.g., "Opportunity to increase savings by X amount").
            -   "summary": A concise summary of the budget plan.

        Rules:
        -   All financial figures should be rounded to 2 decimal places.
        -   Assume all frequencies are converted to monthly for calculations.
            -   'bi-weekly': amount * 2.1667
            -   'weekly': amount * 4.333
            -   'quarterly': amount / 3
            -   'annually': amount / 12
        -   If `current_budget` is provided, refine it by adjusting allocations based on new income/expenses/goals.
        -   Ensure the `total_allocated` in `recommended_budget` does not exceed `total_income`.
        -   Prioritize fixed expenses and financial goals before allocating to discretionary categories.
        """
    
    def plan_budget(self, user_id: str, income_sources: List[Dict[str, Any]], fixed_expenses: List[Dict[str, Any]], desired_categories: List[str], financial_goals: List[Dict[str, Any]], current_budget: Optional[Dict[str, Any]] = None) -> BudgetPlan:
        """Plan a budget based on provided financial data."""
        input_data = {
            "user_id": user_id,
            "income_sources": income_sources,
            "fixed_expenses": fixed_expenses,
            "desired_categories": desired_categories,
            "financial_goals": financial_goals,
            "current_budget": current_budget
        }
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result.data

def main():
    """Run the budget planner agent from the command line."""
    import argparse
    from uuid import uuid4
    
    parser = argparse.ArgumentParser(description='Plan a budget')
    parser.add_argument('--user_id', type=str, default=str(uuid4()), help='UUID of the user')
    parser.add_argument('--income_file', type=str, required=True, help='Path to JSON file with income sources')
    parser.add_argument('--expenses_file', type=str, required=True, help='Path to JSON file with fixed expenses')
    parser.add_argument('--categories', nargs='+', default=['Housing', 'Transportation', 'Food', 'Utilities', 'Insurance', 'Healthcare', 'Debt Payments', 'Savings', 'Entertainment', 'Shopping', 'Education', 'Miscellaneous'], help='List of desired budget categories')
    parser.add_argument('--goals_file', type=str, help='Path to JSON file with financial goals')
    parser.add_argument('--current_budget_file', type=str, help='Path to JSON file with current budget to refine')
    
    args = parser.parse_args()
    
    income_sources = []
    if os.path.exists(args.income_file):
        with open(args.income_file, 'r') as f:
            income_sources = json.load(f)
    else:
        print(f"Error: Income file '{args.income_file}' does not exist")
        return

    fixed_expenses = []
    if os.path.exists(args.expenses_file):
        with open(args.expenses_file, 'r') as f:
            fixed_expenses = json.load(f)
    else:
        print(f"Error: Expenses file '{args.expenses_file}' does not exist")
        return

    financial_goals = []
    if args.goals_file and os.path.exists(args.goals_file):
        with open(args.goals_file, 'r') as f:
            financial_goals = json.load(f)

    current_budget = None
    if args.current_budget_file and os.path.exists(args.current_budget_file):
        with open(args.current_budget_file, 'r') as f:
            current_budget = json.load(f)

    agent = BudgetPlannerAgent()
    
    print("Planning budget...")
    budget_plan_result = agent.plan_budget(
        user_id=args.user_id,
        income_sources=income_sources,
        fixed_expenses=fixed_expenses,
        desired_categories=args.categories,
        financial_goals=financial_goals,
        current_budget=current_budget
    )
    
    print("Budget Plan:")
    print(budget_plan_result.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
