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

class FinancialInsight(BaseModel):
    """Represents financial insights and recommendations."""
    user_id: str = Field(..., description="UUID of the user")
    spending_trends: Dict[str, Any] = Field(..., description="Analysis of spending trends over time (e.g., monthly, quarterly)")
    budget_performance: Dict[str, Any] = Field(..., description="Analysis of how well the user adhered to their budget")
    cost_saving_opportunities: List[str] = Field(..., description="Actionable suggestions for reducing expenses")
    financial_forecast: Dict[str, Any] = Field(..., description="Forecast of future financial situation based on current patterns")
    overall_recommendations: List[str] = Field(..., description="General recommendations for improving financial health")
    insight_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of insight generation")

class InsightAnalysisAgent:
    """Agent for analyzing financial data to provide insights and recommendations."""
    
    def __init__(self):
        """Initialize the insight and analysis agent based on settings."""
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
            result_type=FinancialInsight
        )
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt for financial insight and analysis."""
        return """
        You are an Insight & Analysis Agent for DebtEase. Your role is to analyze a user's historical financial data (budgets and transactions) to provide deep insights, identify trends, and offer actionable recommendations for improving financial health.

        Input will include a JSON string containing:
        - user_id: string (UUID)
        - historical_budgets: List of Budget objects (from app.models.budget) representing past budget periods.
        - historical_transactions: List of Transaction objects (from app.models.transaction) representing past spending and income.
        - current_financial_goals: List of FinancialGoal objects (from app.models.financial_goal).

        Your output should be a FinancialInsight object, including:
        1.  **spending_trends**: Analyze spending patterns over time (e.g., month-over-month, quarter-over-quarter). Identify categories with increasing/decreasing spending, seasonal variations, and significant one-off expenses. Provide a summary for each trend.
        2.  **budget_performance**: Evaluate how well the user adhered to their past budgets. Calculate budget adherence rates per category and overall. Highlight categories where the user consistently overspent or underspent.
        3.  **cost_saving_opportunities**: Based on spending trends and budget performance, suggest specific, actionable ways the user can save money. Examples: "Reduce dining out by 15%", "Consider cheaper alternatives for subscriptions", "Optimize utility usage".
        4.  **financial_forecast**: Project the user's financial situation into the near future (e.g., next 3-6 months) based on current income, spending habits, and financial goals. This could include projected savings, cash flow, or potential shortfalls.
        5.  **overall_recommendations**: Provide overarching advice for improving financial health, such as "Increase emergency fund contributions", "Automate savings", "Review high-interest debts (if applicable)".

        Output Format (strict JSON):
        {
            "user_id": str,
            "spending_trends": {"category_name": "trend_description"},
            "budget_performance": {"category_name": "performance_summary"},
            "cost_saving_opportunities": [str],
            "financial_forecast": {"summary": "forecast_description", "details": dict},
            "overall_recommendations": [str],
            "insight_timestamp": "string (ISO datetime)"
        }

        Rules:
        -   All financial figures should be rounded to 2 decimal places.
        -   Insights should be clear, concise, and actionable.
        -   If historical data is limited, state that and provide more general insights.
        -   Focus on identifying patterns and providing forward-looking advice.
        """
    
    def analyze_financial_data(self, user_id: str, historical_budgets: List[Dict[str, Any]], historical_transactions: List[Dict[str, Any]], current_financial_goals: List[Dict[str, Any]]) -> FinancialInsight:
        """Analyze historical financial data to provide insights and recommendations."""
        input_data = {
            "user_id": user_id,
            "historical_budgets": historical_budgets,
            "historical_transactions": historical_transactions,
            "current_financial_goals": current_financial_goals
        }
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result.data

def main():
    """Run the insight and analysis agent from the command line."""
    import argparse
    from uuid import uuid4
    
    parser = argparse.ArgumentParser(description='Analyze financial data and provide insights')
    parser.add_argument('--user_id', type=str, default=str(uuid4()), help='UUID of the user')
    parser.add_argument('--budgets_file', type=str, help='Path to JSON file with historical budgets')
    parser.add_argument('--transactions_file', type=str, help='Path to JSON file with historical transactions')
    parser.add_argument('--goals_file', type=str, help='Path to JSON file with current financial goals')
    
    args = parser.parse_args()
    
    historical_budgets = []
    if args.budgets_file and os.path.exists(args.budgets_file):
        with open(args.budgets_file, 'r') as f:
            historical_budgets = json.load(f)

    historical_transactions = []
    if args.transactions_file and os.path.exists(args.transactions_file):
        with open(args.transactions_file, 'r') as f:
            historical_transactions = json.load(f)

    current_financial_goals = []
    if args.goals_file and os.path.exists(args.goals_file):
        with open(args.goals_file, 'r') as f:
            current_financial_goals = json.load(f)

    agent = InsightAnalysisAgent()
    
    print("Analyzing financial data...")
    insights_summary = agent.analyze_financial_data(
        user_id=args.user_id,
        historical_budgets=historical_budgets,
        historical_transactions=historical_transactions,
        current_financial_goals=current_financial_goals
    )
    
    print("Financial Insights Summary:")
    print(insights_summary.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
