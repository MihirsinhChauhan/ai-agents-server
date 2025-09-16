"""
Enhanced Debt Optimizer Agent for DebtEase.
Updated to work with new database schema and provide frontend-compatible responses.
"""

import json
from datetime import datetime, date, timedelta
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
from .enhanced_debt_analyzer import DebtAnalysisResult


class OptimizationStrategy(BaseModel):
    """Debt repayment strategy recommendation."""
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    benefits: List[str] = Field(..., description="Benefits of this strategy")
    drawbacks: List[str] = Field(..., description="Potential drawbacks")
    ideal_for: List[str] = Field(..., description="Situations where this strategy works best")
    debt_order: List[str] = Field(..., description="Order of debt IDs to prioritize")
    reasoning: str = Field(..., description="Why this strategy is recommended")
    estimated_savings: Optional[float] = Field(None, description="Estimated interest savings")
    payoff_timeline: Optional[int] = Field(None, description="Estimated months to debt freedom")


class RepaymentPlan(BaseModel):
    """Enhanced repayment plan matching frontend expectations."""
    
    # Plan overview
    strategy: str = Field(..., description="Recommended strategy name")
    monthly_payment_amount: float = Field(..., description="Total recommended monthly payment")
    total_debt: float = Field(..., description="Total debt amount")
    minimum_payment_sum: float = Field(..., description="Sum of minimum payments")
    
    # Projections
    time_to_debt_free: int = Field(..., description="Months to become debt-free")
    total_interest_saved: float = Field(..., description="Interest saved vs minimum payments")
    expected_completion_date: str = Field(..., description="Expected payoff date (YYYY-MM-DD)")
    
    # Debt prioritization
    debt_order: List[str] = Field(..., description="Prioritized order of debt IDs")
    milestone_dates: Dict[str, str] = Field(..., description="Debt ID to payoff date mapping")
    monthly_breakdown: List[Dict[str, Any]] = Field(..., description="Month-by-month payment plan")
    
    # Strategy alternatives
    primary_strategy: OptimizationStrategy = Field(..., description="Recommended primary strategy")
    alternative_strategies: List[OptimizationStrategy] = Field(..., description="Alternative approaches")
    
    # Insights and recommendations
    key_insights: List[str] = Field(..., description="Key financial insights")
    action_items: List[str] = Field(..., description="Immediate action items")
    risk_factors: List[str] = Field(..., description="Potential risks to consider")
    
    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Plan creation timestamp (ISO format)")
    
    class Config:
        populate_by_name = True


class EnhancedDebtOptimizer:
    """Enhanced debt optimizer providing comprehensive repayment strategies."""
    
    def __init__(self):
        """Initialize the enhanced debt optimizer based on settings."""
        self.model = self._initialize_model()
        self.agent = Agent(
            model=self.model,
            instructions=self._get_system_prompt(),
            output_type=RepaymentPlan
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
        """Define the enhanced system prompt for debt optimization."""
        return """
        You are an Enhanced Debt Optimizer for DebtEase, specializing in creating comprehensive, 
        actionable debt repayment plans. Generate optimized strategies based on debt data and analysis.

        Inputs:
        - **debts**: Array of debt objects with all financial details
        - **analysis**: DebtAnalysisResult with insights about the debt portfolio
        - **monthly_payment_budget**: Optional preferred monthly payment amount
        - **user_preferences**: Optional strategy preferences

        Your task is to create a comprehensive RepaymentPlan that includes:

        1. **Strategy Selection**:
           - Choose primary strategy: "avalanche" (high interest first), "snowball" (small balance first), or "Custom"
           - Base choice on analysis insights and debt characteristics
           - Consider user's financial situation and psychology

        2. **Financial Calculations**:
           - monthly_payment_amount: Recommend 1.2-1.5x minimum payments (adjustable based on user capacity)
           - total_debt: Sum of all current balances
           - minimum_payment_sum: Sum of all minimum payments (monthly equivalent)
           - time_to_debt_free: Calculate using recommended payment and strategy
           - total_interest_saved: Compare recommended plan vs minimum payments only
           - expected_completion_date: Today + time_to_debt_free months

        3. **Debt Prioritization**:
           - debt_order: Array of debt IDs in payment priority order
           - For avalanche: Sort by interest_rate (highest first)
           - For snowball: Sort by current_balance (smallest first)
           - For hybrid: Balance both factors based on analysis

        4. **Timeline Planning**:
           - milestone_dates: Map each debt_id to its projected payoff date
           - monthly_breakdown: First 12 months of detailed payment allocation
           - Consider minimum payments for all debts, extra payment to priority debt

        5. **Strategy Alternatives**:
           - primary_strategy: Detailed recommended approach
           - alternative_strategies: At least 2 other viable options with pros/cons
           - Include estimated_savings and payoff_timeline for each

        6. **Actionable Insights**:
           - key_insights: 3-5 important observations about the debt situation
           - action_items: Immediate steps the user should take
           - risk_factors: Potential challenges or risks to plan success

        Calculation Guidelines:
        - Monthly interest = balance * (annual_rate / 100) / 12
        - Payment allocation: Cover all minimums first, then extra to priority debt
        - Payoff calculation: Use amortization formula or iterative simulation
        - Account for payment frequency differences (convert to monthly)

        Strategy Decision Logic:
        - Avalanche: Best for high-interest debt (>12% APR) or large interest savings
        - Snowball: Best for motivation with many small debts or psychological factors
        - Hybrid: Balance of both when debts have mixed characteristics

        Output comprehensive JSON matching the RepaymentPlan schema exactly.
        Be specific, actionable, and realistic in all recommendations.
        Round financial values to 2 decimal places.
        """
    
    async def optimize_repayment(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        monthly_payment_budget: Optional[float] = None,
        preferred_strategy: Optional[str] = None
    ) -> RepaymentPlan:
        """
        Generate an optimized debt repayment plan.
        
        Args:
            debts: List of DebtInDB objects to optimize
            analysis: DebtAnalysisResult from debt analysis
            monthly_payment_budget: Optional preferred monthly payment amount
            preferred_strategy: Optional preferred strategy ('avalanche', 'snowball', 'hybrid')
            
        Returns:
            RepaymentPlan with comprehensive optimization strategy
        """
        if not debts:
            # Return minimal plan for no debts
            return RepaymentPlan(
                strategy="none",
                monthly_payment_amount=0.0,
                total_debt=0.0,
                minimum_payment_sum=0.0,
                time_to_debt_free=0,
                total_interest_saved=0.0,
                expected_completion_date=date.today().isoformat(),
                debt_order=[],
                milestone_dates={},
                monthly_breakdown=[],
                primary_strategy=OptimizationStrategy(
                    name="No Debts",
                    description="No active debts to optimize",
                    benefits=["Debt-free status"],
                    drawbacks=[],
                    ideal_for=["Users with no current debt obligations"],
                    debt_order=[],
                    reasoning="No debts require optimization"
                ),
                alternative_strategies=[],
                key_insights=["You are debt-free! Focus on building emergency fund and investments."],
                action_items=["Consider building emergency fund", "Explore investment opportunities"],
                risk_factors=[]
            )
        
        # Convert debts to frontend-compatible format
        debt_data = []
        for debt in debts:
            debt_response = DebtResponse.from_debt_in_db(debt)
            debt_dict = debt_response.model_dump()
            debt_data.append(debt_dict)
        
        # Prepare input for AI agent
        input_data = {
            "debts": debt_data,
            "analysis": analysis.model_dump(),
            "monthly_payment_budget": monthly_payment_budget,
            "preferred_strategy": preferred_strategy,
            "optimization_context": "comprehensive_repayment_planning"
        }
        
        # Run AI optimization - FIXED: use result.output instead of result
        result = await self.agent.run(json.dumps(input_data, default=str))
        return result.output
    
    def optimize_repayment_sync(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        monthly_payment_budget: Optional[float] = None,
        preferred_strategy: Optional[str] = None
    ) -> RepaymentPlan:
        """
        Synchronous version of repayment optimization.
        
        Args:
            debts: List of DebtInDB objects to optimize
            analysis: DebtAnalysisResult from debt analysis
            monthly_payment_budget: Optional preferred monthly payment amount
            preferred_strategy: Optional preferred strategy
            
        Returns:
            RepaymentPlan with comprehensive optimization strategy
        """
        if not debts:
            # Return minimal plan for no debts
            return RepaymentPlan(
                strategy="none",
                monthly_payment_amount=0.0,
                total_debt=0.0,
                minimum_payment_sum=0.0,
                time_to_debt_free=0,
                total_interest_saved=0.0,
                expected_completion_date=date.today().isoformat(),
                debt_order=[],
                milestone_dates={},
                monthly_breakdown=[],
                primary_strategy=OptimizationStrategy(
                    name="No Debts",
                    description="No active debts to optimize",
                    benefits=["Debt-free status"],
                    drawbacks=[],
                    ideal_for=["Users with no current debt obligations"],
                    debt_order=[],
                    reasoning="No debts require optimization"
                ),
                alternative_strategies=[],
                key_insights=["You are debt-free! Focus on building emergency fund and investments."],
                action_items=["Consider building emergency fund", "Explore investment opportunities"],
                risk_factors=[]
            )
        
        # Convert debts to frontend-compatible format
        debt_data = []
        for debt in debts:
            debt_response = DebtResponse.from_debt_in_db(debt)
            debt_dict = debt_response.model_dump()
            debt_data.append(debt_dict)
        
        # Prepare input for AI agent
        input_data = {
            "debts": debt_data,
            "analysis": analysis.model_dump(),
            "monthly_payment_budget": monthly_payment_budget,
            "preferred_strategy": preferred_strategy,
            "optimization_context": "comprehensive_repayment_planning"
        }
        
        # Run AI optimization
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result
