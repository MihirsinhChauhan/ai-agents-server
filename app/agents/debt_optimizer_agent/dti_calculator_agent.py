"""
DTI (Debt-to-Income) Calculator Agent for DebtEase.
Calculates and analyzes debt-to-income ratios with AI insights.
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


class DTIAnalysis(BaseModel):
    """DTI analysis result matching frontend TypeScript interface."""
    
    # Core DTI metrics
    frontend_dti: float = Field(..., description="Housing costs DTI (mortgage/rent payments only)")
    backend_dti: float = Field(..., description="Total debt DTI (all debt payments)")
    total_monthly_debt_payments: float = Field(..., description="Sum of all monthly debt payments")
    monthly_income: float = Field(..., description="User's monthly income")
    
    # Health assessment
    is_healthy: bool = Field(..., description="Whether DTI ratios are in healthy ranges")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    
    # Detailed breakdown
    housing_payments: float = Field(..., description="Monthly housing-related debt payments")
    non_housing_payments: float = Field(..., description="Monthly non-housing debt payments")
    debt_breakdown: Dict[str, float] = Field(..., description="Payments by debt type")
    
    # Insights and recommendations
    key_insights: List[str] = Field(..., description="Important observations about DTI")
    improvement_suggestions: List[str] = Field(..., description="Actionable ways to improve DTI")
    income_recommendations: List[str] = Field(..., description="Income-focused suggestions")
    debt_recommendations: List[str] = Field(..., description="Debt reduction suggestions")
    
    # Benchmarks and targets
    target_frontend_dti: float = Field(default=28.0, description="Target housing DTI percentage")
    target_backend_dti: float = Field(default=36.0, description="Target total DTI percentage")
    monthly_reduction_needed: float = Field(..., description="Monthly payment reduction needed for health")
    income_increase_needed: float = Field(..., description="Monthly income increase needed for health")
    
    # Metadata
    calculated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Calculation timestamp (ISO format)")
    
    class Config:
        populate_by_name = True


class DTICalculatorAgent:
    """Agent for calculating and analyzing debt-to-income ratios."""
    
    def __init__(self):
        """Initialize the DTI calculator agent."""
        self.model = self._initialize_model()
        self.agent = Agent(
            model=self.model,
            instructions=self._get_system_prompt(),
            output_type=DTIAnalysis
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
        """Define the system prompt for DTI calculation and analysis."""
        return """
        You are a DTI (Debt-to-Income) Calculator and Analyst for DebtEase. 
        Calculate comprehensive debt-to-income ratios and provide actionable insights.

        Input Data:
        - **debts**: Array of debt objects with payment and type information
        - **monthly_income**: User's gross monthly income
        - **include_housing**: Whether to include housing costs in analysis

        DTI Calculation Rules:

        1. **Frontend DTI (Housing Ratio)**:
           - Include only housing-related debt payments: home_loan, mortgage
           - Formula: (housing_payments / monthly_income) * 100
           - Healthy range: ≤ 28%
           - Acceptable range: 28-31%
           - Concerning range: > 31%

        2. **Backend DTI (Total Debt Ratio)**:
           - Include ALL debt payments: housing + credit cards + loans + etc.
           - Formula: (total_monthly_payments / monthly_income) * 100
           - Healthy range: ≤ 36%
           - Acceptable range: 36-43%
           - Concerning range: > 43%

        3. **Payment Frequency Conversion**:
           - Weekly: multiply by 4.333 (52 weeks ÷ 12 months)
           - Biweekly: multiply by 2.167 (26 payments ÷ 12 months)
           - Monthly: use as-is
           - Quarterly: divide by 3 (4 quarters ÷ 12 months)

        4. **Debt Type Classification**:
           - Housing: home_loan, mortgage-related debts
           - Non-housing: credit_card, personal_loan, vehicle_loan, education_loan, etc.

        Analysis Requirements:

        **Health Assessment**:
        - is_healthy: True if frontend_dti ≤ 28% AND backend_dti ≤ 36%
        - risk_level:
          - "low": Both ratios in healthy ranges
          - "medium": One ratio slightly elevated (28-31% frontend, 36-43% backend)
          - "high": One ratio concerning (>31% frontend, >43% backend)
          - "critical": Both ratios concerning or backend_dti > 50%

        **Improvement Calculations**:
        - monthly_reduction_needed: Payment reduction to reach healthy DTI
        - income_increase_needed: Income increase to reach healthy DTI
        - Consider both options and recommend the more realistic path

        **Insights Generation** (provide 3-5 key observations):
        - Compare user's ratios to healthy benchmarks
        - Identify which debt types contribute most to DTI
        - Highlight improvement opportunities
        - Consider income vs debt reduction strategies

        **Recommendations** (provide specific, actionable suggestions):
        
        **improvement_suggestions**: General DTI improvement strategies
        - "Focus on paying down high-interest credit cards first"
        - "Consider debt consolidation to reduce monthly payments"
        - "Increase income through side work or skill development"

        **income_recommendations**: Income-focused strategies
        - "Negotiate salary increase or promotion at current job"
        - "Develop freelance or consulting income streams"
        - "Consider part-time work or gig economy opportunities"

        **debt_recommendations**: Debt reduction strategies
        - "Pay extra $X monthly toward highest-interest debt"
        - "Refinance mortgage to reduce monthly payment by $X"
        - "Consolidate credit cards to lower monthly obligations"

        **Debt Breakdown**: Categorize monthly payments by debt type:
        - Group payments by debt_type
        - Calculate percentage contribution to total DTI
        - Identify highest-impact debt categories

        Provide comprehensive analysis that helps users understand their DTI situation
        and gives them clear paths to improvement. Be specific with numbers and realistic
        with recommendations based on their actual financial situation.
        """
    
    async def calculate_dti(
        self,
        debts: List[DebtInDB],
        monthly_income: float,
        include_housing: bool = True
    ) -> DTIAnalysis:
        """
        Calculate comprehensive DTI analysis.
        
        Args:
            debts: List of user's debts
            monthly_income: User's gross monthly income
            include_housing: Whether to include housing costs
            
        Returns:
            DTIAnalysis with comprehensive DTI insights
        """
        if monthly_income <= 0:
            raise ValueError("Monthly income must be positive")
        
        if not debts:
            # Return analysis for no debts
            return DTIAnalysis(
                frontend_dti=0.0,
                backend_dti=0.0,
                total_monthly_debt_payments=0.0,
                monthly_income=monthly_income,
                is_healthy=True,
                risk_level="low",
                housing_payments=0.0,
                non_housing_payments=0.0,
                debt_breakdown={},
                key_insights=["You have no debt payments - excellent financial position!"],
                improvement_suggestions=["Maintain debt-free status", "Build emergency fund", "Focus on investments"],
                income_recommendations=["Continue growing income for wealth building"],
                debt_recommendations=["Avoid taking on unnecessary debt"],
                monthly_reduction_needed=0.0,
                income_increase_needed=0.0
            )
        
        # Convert debts to frontend format
        debt_data = []
        for debt in debts:
            debt_response = DebtResponse.from_debt_in_db(debt)
            debt_dict = debt_response.model_dump()
            debt_data.append(debt_dict)
        
        # Prepare input for AI agent
        input_data = {
            "debts": debt_data,
            "monthly_income": monthly_income,
            "include_housing": include_housing,
            "context": "comprehensive_dti_analysis"
        }
        
        # Calculate DTI with AI insights
        # FIXED: use result.output instead of result
        result = await self.agent.run(json.dumps(input_data, default=str))
        return result.output
    
    def calculate_dti_sync(
        self,
        debts: List[DebtInDB],
        monthly_income: float,
        include_housing: bool = True
    ) -> DTIAnalysis:
        """
        Synchronous version of DTI calculation.
        
        Args:
            debts: List of user's debts
            monthly_income: User's gross monthly income
            include_housing: Whether to include housing costs
            
        Returns:
            DTIAnalysis with comprehensive DTI insights
        """
        if monthly_income <= 0:
            raise ValueError("Monthly income must be positive")
        
        if not debts:
            # Return analysis for no debts
            return DTIAnalysis(
                frontend_dti=0.0,
                backend_dti=0.0,
                total_monthly_debt_payments=0.0,
                monthly_income=monthly_income,
                is_healthy=True,
                risk_level="low",
                housing_payments=0.0,
                non_housing_payments=0.0,
                debt_breakdown={},
                key_insights=["You have no debt payments - excellent financial position!"],
                improvement_suggestions=["Maintain debt-free status", "Build emergency fund", "Focus on investments"],
                income_recommendations=["Continue growing income for wealth building"],
                debt_recommendations=["Avoid taking on unnecessary debt"],
                monthly_reduction_needed=0.0,
                income_increase_needed=0.0
            )
        
        # Convert debts to frontend format
        debt_data = []
        for debt in debts:
            debt_response = DebtResponse.from_debt_in_db(debt)
            debt_dict = debt_response.model_dump()
            debt_data.append(debt_dict)
        
        # Prepare input for AI agent
        input_data = {
            "debts": debt_data,
            "monthly_income": monthly_income,
            "include_housing": include_housing,
            "context": "comprehensive_dti_analysis"
        }
        
        # Calculate DTI with AI insights
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result
    
    def calculate_basic_dti(
        self,
        debts: List[DebtInDB],
        monthly_income: float
    ) -> Dict[str, float]:
        """
        Calculate basic DTI ratios without AI analysis.
        
        Args:
            debts: List of user's debts
            monthly_income: User's gross monthly income
            
        Returns:
            Dictionary with basic DTI calculations
        """
        if monthly_income <= 0:
            return {
                "frontend_dti": 0.0,
                "backend_dti": 0.0,
                "total_monthly_debt_payments": 0.0,
                "monthly_income": monthly_income,
                "is_healthy": False
            }
        
        # Calculate monthly payments
        housing_payments = 0.0
        total_payments = 0.0
        
        for debt in debts:
            # Convert payment to monthly
            monthly_payment = debt.minimum_payment
            if debt.payment_frequency == "weekly":
                monthly_payment *= 4.333
            elif debt.payment_frequency == "biweekly":
                monthly_payment *= 2.167
            elif debt.payment_frequency == "quarterly":
                monthly_payment /= 3
            
            total_payments += monthly_payment
            
            # Check if housing-related debt
            if debt.debt_type in ["home_loan"]:
                housing_payments += monthly_payment
        
        # Calculate DTI ratios
        frontend_dti = (housing_payments / monthly_income) * 100
        backend_dti = (total_payments / monthly_income) * 100
        
        # Determine health status
        is_healthy = frontend_dti <= 28.0 and backend_dti <= 36.0
        
        return {
            "frontend_dti": round(frontend_dti, 2),
            "backend_dti": round(backend_dti, 2),
            "total_monthly_debt_payments": round(total_payments, 2),
            "housing_payments": round(housing_payments, 2),
            "monthly_income": monthly_income,
            "is_healthy": is_healthy
        }
