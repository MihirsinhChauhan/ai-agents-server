"""
Enhanced Debt Analyzer Agent for DebtEase.
Updated to work with new database schema and frontend TypeScript interfaces.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic import BaseModel, Field

from app.configs.config import settings
from app.models.debt import DebtInDB, DebtResponse


class DebtAnalysisResult(BaseModel):
    """Enhanced debt analysis result matching frontend expectations."""
    
    # Core analysis metrics
    total_debt: float = Field(..., description="Total debt amount across all debts")
    debt_count: int = Field(..., description="Total number of active debts")
    average_interest_rate: float = Field(..., description="Weighted average interest rate")
    total_minimum_payments: float = Field(..., description="Sum of all minimum monthly payments")
    total_monthly_interest: float = Field(..., description="Total monthly interest costs")
    
    # Debt prioritization
    highest_interest_debt_id: str = Field(..., description="ID of debt with highest interest rate")
    highest_interest_rate: float = Field(..., description="Highest interest rate among debts")
    smallest_debt_id: str = Field(..., description="ID of debt with smallest balance")
    smallest_debt_amount: float = Field(..., description="Smallest debt amount")
    largest_debt_id: str = Field(..., description="ID of debt with largest balance")
    largest_debt_amount: float = Field(..., description="Largest debt amount")
    
    # High impact debts
    high_priority_debts: List[str] = Field(..., description="IDs of high priority debts")
    high_interest_debts: List[str] = Field(..., description="IDs of debts with interest > 10%")
    overdue_debts: List[str] = Field(..., description="IDs of overdue debts")
    
    # Financial health indicators
    monthly_cash_flow_impact: float = Field(..., description="Total monthly debt burden")
    debt_types_breakdown: Dict[str, int] = Field(..., description="Count of debts by type")
    critical_debt_types: List[str] = Field(..., description="Debt types requiring attention")
    
    # Actionable insights
    recommended_focus_areas: List[str] = Field(..., description="Specific actionable recommendations")
    risk_assessment: str = Field(..., description="Overall debt risk level: low, medium, high")
    
    # Metadata
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="When analysis was performed (ISO format)")
    
    class Config:
        populate_by_name = True


class EnhancedDebtAnalyzer:
    """Enhanced debt analyzer using Pydantic AI with improved frontend compatibility."""
    
    def __init__(self):
        """Initialize the enhanced debt analyzer based on settings."""
        self.model = self._initialize_model()
        self.agent = Agent(
            model=self.model,
            instructions=self._get_system_prompt(),
            output_type=DebtAnalysisResult
        )
    
    def _initialize_model(self):
        """Initialize the LLM model based on configuration."""
        if settings.LLM_PROVIDER == "openai":
            return OpenAIModel(
                model_name=settings.LLM_MODEL,
                provider=OpenAIProvider(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None
                )
            )
        elif settings.LLM_PROVIDER == "groq":
            return GroqModel(
                model_name=settings.LLM_MODEL,
                provider=GroqProvider(api_key=settings.GROQ_API_KEY)
            )
        elif settings.LLM_PROVIDER == "ollama":
            return OpenAIModel(
                model_name=settings.LLM_MODEL,
                provider=OpenAIProvider(
                    base_url=settings.LLM_BASE_URL,
                    api_key="dummy"
                )
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
    
    def _get_system_prompt(self) -> str:
        """Define the enhanced system prompt for debt analysis."""
        return """
        You are a Debt Analysis Expert for a debt management platform.
        Analyze the provided debt data and provide clear, actionable insights.

        Each debt object contains:
        - id: string (UUID)
        - name: string (debt name)
        - debt_type: string (credit_card, personal_loan, home_loan, vehicle_loan, education_loan, business_loan, gold_loan, overdraft, emi, other)
        - principal_amount: float (original loan amount)
        - current_balance: float (remaining balance)
        - interest_rate: float (annual percentage rate)
        - is_variable_rate: boolean
        - minimum_payment: float (required monthly payment)
        - due_date: string (YYYY-MM-DD format or null)
        - lender: string
        - remaining_term_months: integer or null
        - is_tax_deductible: boolean
        - payment_frequency: string (weekly, biweekly, monthly, quarterly)
        - is_high_priority: boolean (user-marked priority)
        - notes: string or null
        - days_past_due: integer (calculated field)

        Perform comprehensive analysis:

        1. **Basic Metrics**:
           - total_debt: Sum all current_balance values
           - debt_count: Count of active debts
           - average_interest_rate: Weighted average by current_balance
           - total_minimum_payments: Sum all minimum_payment (convert to monthly)
           - total_monthly_interest: Sum of (current_balance * interest_rate / 100 / 12)

        2. **Debt Prioritization**:
           - highest_interest_debt_id: ID of debt with max interest_rate
           - highest_interest_rate: The actual highest rate
           - smallest_debt_id: ID of debt with min current_balance
           - smallest_debt_amount: The actual smallest amount
           - largest_debt_id: ID of debt with max current_balance
           - largest_debt_amount: The actual largest amount

        3. **Critical Debt Identification**:
           - high_priority_debts: IDs where is_high_priority = true
           - high_interest_debts: IDs where interest_rate > 10%
           - overdue_debts: IDs where days_past_due > 0

        4. **Financial Health**:
           - monthly_cash_flow_impact: total_minimum_payments + total_monthly_interest
           - debt_types_breakdown: Count debts by debt_type
           - critical_debt_types: Types with high interest or large balances

        5. **Actionable Insights** (provide 3-5 specific recommendations):
           - Focus on highest interest debts if interest rates vary significantly
           - Consider debt snowball for motivation if many small debts
           - Address overdue debts immediately
           - Suggest consolidation for similar debt types
           - Recommend payment frequency optimization

        6. **Risk Assessment**:
           - "low": average_interest_rate < 8%, total_debt manageable
           - "medium": some high-interest debts or moderate overdue amounts
           - "high": multiple high-interest debts, significant overdue amounts, or high DTI

        Payment Frequency Conversion to Monthly:
        - weekly: multiply by 4.333 (52 weeks / 12 months)
        - biweekly: multiply by 2.167 (26 payments / 12 months)
        - monthly: as-is
        - quarterly: divide by 3 (4 quarters / 12 months)

        Return analysis in exact JSON format with all required fields.
        Be specific and actionable in recommendations.
        Round financial values to 2 decimal places.
        """
    
    async def analyze_debts(self, debts: List[DebtInDB]) -> DebtAnalysisResult:
        """
        Analyze the provided debts and return comprehensive insights.
        
        Args:
            debts: List of DebtInDB objects to analyze
            
        Returns:
            DebtAnalysisResult with comprehensive debt analysis
        """
        if not debts:
            # Return empty analysis for no debts
            return DebtAnalysisResult(
                total_debt=0.0,
                debt_count=0,
                average_interest_rate=0.0,
                total_minimum_payments=0.0,
                total_monthly_interest=0.0,
                highest_interest_debt_id="",
                highest_interest_rate=0.0,
                smallest_debt_id="",
                smallest_debt_amount=0.0,
                largest_debt_id="",
                largest_debt_amount=0.0,
                high_priority_debts=[],
                high_interest_debts=[],
                overdue_debts=[],
                monthly_cash_flow_impact=0.0,
                debt_types_breakdown={},
                critical_debt_types=[],
                recommended_focus_areas=["Add debts to start tracking your financial journey"],
                risk_assessment="low"
            )
        
        # Convert debts to frontend-compatible format for AI processing
        debt_data = []
        for debt in debts:
            debt_response = DebtResponse.from_debt_in_db(debt)
            debt_dict = debt_response.model_dump()
            debt_data.append(debt_dict)
        
        # Prepare input for AI agent
        input_data = {
            "debts": debt_data,
            "analysis_context": "comprehensive_debt_analysis"
        }
        
        # Run AI analysis - FIXED: use result.output instead of result
        result = await self.agent.run(json.dumps(input_data, default=str))
        return result.output
    
    def analyze_debts_sync(self, debts: List[DebtInDB]) -> DebtAnalysisResult:
        """
        Synchronous version of debt analysis.
        
        Args:
            debts: List of DebtInDB objects to analyze
            
        Returns:
            DebtAnalysisResult with comprehensive debt analysis
        """
        if not debts:
            # Return empty analysis for no debts
            return DebtAnalysisResult(
                total_debt=0.0,
                debt_count=0,
                average_interest_rate=0.0,
                total_minimum_payments=0.0,
                total_monthly_interest=0.0,
                highest_interest_debt_id="",
                highest_interest_rate=0.0,
                smallest_debt_id="",
                smallest_debt_amount=0.0,
                largest_debt_id="",
                largest_debt_amount=0.0,
                high_priority_debts=[],
                high_interest_debts=[],
                overdue_debts=[],
                monthly_cash_flow_impact=0.0,
                debt_types_breakdown={},
                critical_debt_types=[],
                recommended_focus_areas=["Add debts to start tracking your financial journey"],
                risk_assessment="low"
            )
        
        # Convert debts to frontend-compatible format for AI processing
        debt_data = []
        for debt in debts:
            debt_response = DebtResponse.from_debt_in_db(debt)
            debt_dict = debt_response.model_dump()
            debt_data.append(debt_dict)
        
        # Prepare input for AI agent
        input_data = {
            "debts": debt_data,
            "analysis_context": "comprehensive_debt_analysis"
        }
        
        # Run AI analysis
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result
