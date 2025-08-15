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

class DebtAnalysis(BaseModel):
    """Result of debt analysis."""
    total_debt: float = Field(..., description="Total debt amount across all debts")
    highest_interest_debt: str = Field(..., description="UUID of debt with the highest interest rate")
    lowest_interest_debt: str = Field(..., description="UUID of debt with the lowest interest rate")
    smallest_debt: str = Field(..., description="UUID of debt with the smallest balance")
    largest_debt: str = Field(..., description="UUID of debt with the largest balance")
    highest_impact_debts: List[str] = Field(..., description="UUIDs of debts with the highest impact on total debt")
    min_payment_sum: float = Field(..., description="Sum of minimum payments, adjusted to monthly")
    monthly_cash_flow_impact: float = Field(..., description="Total monthly burden (minimum payments + interest)")
    recommended_focus_areas: List[str] = Field(..., description="Actionable debt reduction suggestions")
    interest_insights: Dict[str, Any] = Field(..., description="Insights about interest rates and payments")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of analysis")

class DebtAnalyzingAgent:
    """Agent for analyzing complex debt data using pydantic_ai.Agent."""
    
    def __init__(self):
        """Initialize the debt analyzing agent based on settings."""
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
            result_type=DebtAnalysis
        )
    
    def _get_system_prompt(self) -> str:
        """Define the system prompt for debt analysis."""
        return """
        You are a Debt Analyzing Agent for DebtEase. Your task is to analyze a list of debts and produce a comprehensive DebtAnalysis result to guide debt optimization.

        Each debt object contains:
        - id: string (UUID, unique identifier)
        - name: string (debt name)
        - type: string (e.g., 'credit_card', 'personal_loan', 'student_loan', 'auto_loan', 'mortgage', 'medical', 'family', 'other')
        - amount: float (outstanding balance)
        - interest_rate: float (annual percentage rate)
        - minimum_payment: float or null (minimum payment amount)
        - payment_frequency: string (e.g., 'monthly', 'bi_weekly', 'weekly', 'quarterly', 'custom')
        - source: string (e.g., 'manual', 'plaid')
        - due_date: string (ISO date, e.g., '2025-04-15', or null)
        - details: optional dictionary (additional metadata)
        - user_id: string (UUID of the user)
        - created_at: string (ISO datetime)
        - updated_at: string (ISO datetime)
        - blockchain_id: string or null
        - is_active: boolean

        Perform these analyses:

        1. **total_debt**: Sum all debt amounts.
        2. **highest_interest_debt**: UUID of the debt with the highest interest_rate.
        3. **lowest_interest_debt**: UUID of the debt with the lowest interest_rate.
        4. **smallest_debt**: UUID of the debt with the smallest amount.
        5. **largest_debt**: UUID of the debt with the largest amount.
        6. **highest_impact_debts**: Up to 3 debt UUIDs with significant impact (high interest > 10% or amount > 20% of total_debt).
        7. **min_payment_sum**: Sum of minimum payments, adjusted to monthly:
           - 'monthly': as is
           - 'bi_weekly': * 2.1667 (26/year ÷ 12)
           - 'weekly': * 4.333 (52/year ÷ 12)
           - 'quarterly': / 3 (4/year ÷ 12)
           - 'custom': assume monthly
           - If minimum_payment is null, use 2% of amount (amount * 0.02).
        8. **monthly_cash_flow_impact**: Sum of monthly minimum payments + monthly interest (amount * interest_rate / 100 / 12 per debt).
        9. **recommended_focus_areas**: At least 3 suggestions (e.g., "Prioritize high-interest debts", "Set payments for null minimums").
        10. **interest_insights**: Dictionary with:
            - "average_interest_rate": weighted average (by amount)
            - "total_monthly_interest": sum of monthly interest costs
            - "high_interest_debts_count": debts with interest_rate > 10%
            - "critical_debt_types": list of debt types with high interest or large amounts
            - "notable_patterns": string (e.g., "Credit card debts drive costs")

        Output Format (strict JSON):
        {
            "total_debt": float,
            "highest_interest_debt": str,
            "lowest_interest_debt": str,
            "smallest_debt": str,
            "largest_debt": str,
            "highest_impact_debts": [str],
            "min_payment_sum": float,
            "monthly_cash_flow_impact": float,
            "recommended_focus_areas": [str],
            "interest_insights": {
                "average_interest_rate": float,
                "total_monthly_interest": float,
                "high_interest_debts_count": int,
                "critical_debt_types": [str],
                "notable_patterns": str
            },
            "analysis_timestamp": "string (ISO datetime)"
        }

        Rules:
        - Use 'id' (UUID as string) for debt identifiers.
        - Handle null minimum_payment by assuming 2% of amount.
        - Parse due_date as ISO date string or null.
        - Ignore payment_history (handled separately).
        - Dates in ISO8601 format.
        - Round financials to 2 decimal places.
        """
    
    def analyze(self, debts: List[Debt]) -> DebtAnalysis:
        """Analyze the provided debts."""
        input_data = {
            "debts": [debt.model_dump(by_alias=True) for debt in debts]
        }
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result.data

def save_analysis_results(analysis_result: DebtAnalysis, output_dir: str) -> str:
    """Save analysis results to a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = analysis_result.analysis_timestamp.strftime('%Y%m%d_%H%M%S')
    filename = f"debt_analysis_{timestamp}.json"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w') as f:
        f.write(analysis_result.model_dump_json(indent=2))
    return output_path

def main():
    """Run the debt analyzer agent from the command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze debt data')
    parser.add_argument('--input_file', type=str, required=True, help='Path to JSON file with debt data')
    parser.add_argument('--output_dir', type=str, default='outputs', help='Directory to save analysis results')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        return
    
    with open(args.input_file, 'r') as f:
        debts_data = json.load(f)
    
    debts = [Debt.model_validate(debt) for debt in debts_data]
    agent = DebtAnalyzingAgent()
    
    print("Analyzing debt data...")
    analysis_result = agent.analyze(debts)
    
    output_path = save_analysis_results(analysis_result, args.output_dir)
    print(f"Analysis results saved to '{output_path}'")

if __name__ == "__main__":
    main()