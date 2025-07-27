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
from app.models.debt import Debt
from app.agents.debt_analyzer_agent import DebtAnalysis

class OptimizationStrategy(BaseModel):
    """Debt repayment strategy recommendation."""
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    benefits: List[str] = Field(..., description="Benefits of this strategy")
    drawbacks: List[str] = Field(..., description="Drawbacks of this strategy")
    ideal_for: List[str] = Field(..., description="Types of situations this strategy is ideal for")
    debt_order: List[str] = Field(..., description="Order of debt UUIDs to focus on")
    reasoning: str = Field(..., description="Reasoning behind this strategy")

class RepaymentPlanSummary(BaseModel):
    """Summary of a repayment plan."""
    total_debt: float = Field(..., description="Total debt amount")
    minimum_payment_sum: float = Field(..., description="Sum of minimum payments")
    recommended_monthly_payment: float = Field(..., description="Recommended monthly payment amount")
    time_to_debt_free: int = Field(..., description="Estimated months to become debt-free")
    total_interest_saved: float = Field(..., description="Total interest saved compared to minimum payments")
    expected_completion_date: str = Field(..., description="Expected completion date (ISO date, e.g., '2025-04-13')")
    milestone_dates: Dict[str, str] = Field(..., description="Debt UUIDs to payoff dates (ISO date)")
    recommended_strategy: str = Field(..., description="Recommended strategy name")
    alternative_strategies: List[OptimizationStrategy] = Field(..., description="Alternative strategies")
    optimization_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of optimization")

class DebtOptimizerAgent:
    """Agent for optimizing debt repayment strategies using pydantic_ai.Agent."""
    
    def __init__(self):
        """Initialize the debt optimizer agent based on settings."""
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
            result_type=RepaymentPlanSummary
        )
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt for debt optimization."""
        return """
        You are a Debt Optimizer Agent for DebtEase. Your task is to generate an optimized repayment plan based on a list of debts and a DebtAnalysis result.

        Inputs:
        - **debts**: List of debt objects with:
          - id: string (UUID, unique identifier)
          - name: string (debt name)
          - type: string (e.g., 'credit_card', 'personal_loan')
          - amount: float (outstanding balance)
          - interest_rate: float (annual percentage rate)
          - minimum_payment: float or null
          - payment_frequency: string (e.g., 'monthly', 'bi_weekly', 'weekly', 'quarterly', 'custom')
          - source: string (e.g., 'manual', 'plaid')
          - due_date: string (ISO date, e.g., '2025-04-15', or null)
          - details: optional dictionary (additional metadata)
          - user_id: string (UUID)
          - created_at: string (ISO datetime)
          - updated_at: string (ISO datetime)
          - blockchain_id: string or null
          - is_active: boolean
        - **analysis**: DebtAnalysis object with:
          - total_debt: float
          - highest_interest_debt: str (UUID)
          - lowest_interest_debt: str (UUID)
          - smallest_debt: str (UUID)
          - largest_debt: str (UUID)
          - highest_impact_debts: [str] (UUIDs)
          - min_payment_sum: float
          - monthly_cash_flow_impact: float
          - recommended_focus_areas: [str]
          - interest_insights: {average_interest_rate, total_monthly_interest, high_interest_debts_count, critical_debt_types, notable_patterns}
          - analysis_timestamp: str

        Tasks:

        1. **total_debt**: Use analysis.total_debt.
        2. **minimum_payment_sum**: Use analysis.min_payment_sum.
        3. **recommended_monthly_payment**: Suggest 1.5x analysis.min_payment_sum, capped at total_debt/12, adjusted per recommended_focus_areas.
        4. **time_to_debt_free**: Estimate months to pay off all debts using recommended_monthly_payment, following recommended_strategy.
        5. **total_interest_saved**: Calculate interest saved vs. minimum payments, using amortization.
        6. **expected_completion_date**: ISO date (today + time_to_debt_free months, e.g., '2025-04-13').
        7. **milestone_dates**: Map debt UUIDs to payoff dates (ISO date).
        8. **recommended_strategy**: Choose 'avalanche', 'snowball', or 'custom' based on analysis (e.g., avalanche if high_interest_debts_count > 1).
        9. **alternative_strategies**: Provide at least 2 other strategies.

        Strategies:
        - **Avalanche**: Prioritize highest interest rates (use analysis.highest_interest_debt).
        - **Snowball**: Prioritize smallest balances (use analysis.smallest_debt).
        - **Custom**: Hybrid based on analysis.critical_debt_types.

        Calculations:
        - Monthly interest: amount * interest_rate / 100 / 12
        - Amortization: n = -log(1 - (r * P) / M) / log(1 + r), where r = monthly rate, P = principal, M = payment
        - If minimum_payment is null, use 2% of amount.
        - Simulate applying recommended_monthly_payment in strategy order, covering minimum payments first.

        Output Format (strict JSON):
        {
            "total_debt": float,
            "minimum_payment_sum": float,
            "recommended_monthly_payment": float,
            "time_to_debt_free": int,
            "total_interest_saved": float,
            "expected_completion_date": "string (ISO date)",
            "milestone_dates": {"debt_uuid": "string (ISO date)"},
            "recommended_strategy": str,
            "alternative_strategies": [
                {
                    "name": str,
                    "description": str,
                    "benefits": [str],
                    "drawbacks": [str],
                    "ideal_for": [str],
                    "debt_order": [str],
                    "reasoning": str
                }
            ],
            "optimization_timestamp": "string (ISO datetime)"
        }

        Rules:
        - Use 'id' (UUID as string) for debt identifiers.
        - Handle null minimum_payment (2% of amount).
        - Parse due_date as ISO date string or null.
        - Ignore payment_history (handled separately).
        - Align recommended_strategy with analysis.recommended_focus_areas.
        - Ensure at least 2 alternative strategies.
        - Dates in ISO8601 format (e.g., '2025-04-13' for dates, '2025-04-13T00:00:00' for datetimes).
        - Round financials to 2 decimal places.
        """
    
    def optimize(self, debts: List[Debt], analysis: DebtAnalysis) -> RepaymentPlanSummary:
        """Optimize debt repayment using debt data and analysis."""
        input_data = {
            "debts": [debt.model_dump(by_alias=True) for debt in debts],
            "analysis": analysis.model_dump()
        }
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result.data

def save_optimization_results(optimization_result: RepaymentPlanSummary, output_dir: str) -> str:
    """Save optimization results to a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = optimization_result.optimization_timestamp.strftime('%Y%m%d_%H%M%S')
    filename = f"debt_optimization_{timestamp}.json"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w') as f:
        f.write(optimization_result.model_dump_json(indent=2))
    return output_path

def main():
    """Run the debt optimizer agent from the command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimize debt repayment strategies')
    parser.add_argument('--input_file', type=str, required=True, help='Path to JSON file with debt data')
    parser.add_argument('--analysis_file', type=str, required=True, help='Path to JSON file with debt analysis')
    parser.add_argument('--output_dir', type=str, default='outputs', help='Directory to save results')
    
    args = parser.parse_args()
    
    # Load debts
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        return
    with open(args.input_file, 'r') as f:
        debts_data = json.load(f)
    debts = [Debt.model_validate(debt) for debt in debts_data]
    
    # Load analysis
    if not os.path.exists(args.analysis_file):
        print(f"Error: Analysis file '{args.analysis_file}' does not exist")
        return
    with open(args.analysis_file, 'r') as f:
        analysis_data = json.load(f)
    analysis = DebtAnalysis.model_validate(analysis_data)
    
    # Optimize based on analysis
    print("Optimizing debt repayment...")
    optimizer = DebtOptimizerAgent()
    optimization_result = optimizer.optimize(debts, analysis)
    
    output_path = save_optimization_results(optimization_result, args.output_dir)
    print(f"Optimization results saved to '{output_path}'")

if __name__ == "__main__":
    main()