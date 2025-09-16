"""
AI Recommendation Agent for DebtEase.
Generates personalized financial recommendations based on debt analysis.
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
from .enhanced_debt_analyzer import DebtAnalysisResult


class AIRecommendation(BaseModel):
    """AI-generated recommendation matching frontend TypeScript interface."""
    
    recommendation_type: str = Field(..., description="Type: snowball, avalanche, refinance, consolidation, automation")
    title: str = Field(..., description="Short, actionable title")
    description: str = Field(..., description="Detailed explanation of the recommendation")
    potential_savings: Optional[float] = Field(None, description="Estimated savings if followed")
    priority_score: int = Field(..., ge=1, le=10, description="Priority score 1-10")
    
    # Additional context
    affected_debt_ids: List[str] = Field(default_factory=list, description="Debt IDs this recommendation affects")
    action_steps: List[str] = Field(..., description="Specific steps to implement")
    timeline: str = Field(..., description="Suggested implementation timeline")
    difficulty: str = Field(..., description="Implementation difficulty: easy, medium, hard")
    
    # Risk and benefit analysis
    benefits: List[str] = Field(..., description="Key benefits of following this recommendation")
    risks: List[str] = Field(default_factory=list, description="Potential risks or downsides")
    prerequisites: List[str] = Field(default_factory=list, description="Requirements before implementation")
    
    class Config:
        populate_by_name = True


class RecommendationSet(BaseModel):
    """Set of AI recommendations for a user."""
    
    recommendations: List[AIRecommendation] = Field(..., description="List of personalized recommendations")
    overall_strategy: str = Field(..., description="Recommended overall debt strategy")
    priority_order: List[int] = Field(..., description="Recommended order to implement recommendations")
    estimated_impact: Dict[str, float] = Field(..., description="Expected impact metrics")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Generation timestamp (ISO format)")
    
    class Config:
        populate_by_name = True


class AIRecommendationAgent:
    """Agent for generating personalized AI recommendations."""
    
    def __init__(self):
        """Initialize the AI recommendation agent."""
        self.model = self._initialize_model()
        self.agent = Agent(
            model=self.model,
            instructions=self._get_system_prompt(),
            output_type=RecommendationSet
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
        """Define the system prompt for AI recommendations."""
        return """
        You are an AI Financial Advisor for DebtEase, specializing in personalized debt management recommendations.
        Generate 3-5 actionable recommendations based on debt analysis and user financial situation.

        Input Data:
        - **debts**: Array of user's debt objects with complete financial details
        - **analysis**: DebtAnalysisResult with comprehensive debt insights
        - **user_profile**: Optional user information (income, preferences, etc.)

        Generate recommendations covering these areas:

        1. **Debt Strategy Recommendations**:
           - Avalanche strategy for high-interest debts (>12% APR)
           - Snowball strategy for motivation and quick wins
           - Hybrid approaches for mixed debt portfolios

        2. **Refinancing & Consolidation**:
           - Credit card balance transfers for high-interest cards
           - Personal loan consolidation for multiple debts
           - Student loan refinancing opportunities
           - Home equity options for homeowners

        3. **Payment Optimization**:
           - Increase payment frequency (bi-weekly vs monthly)
           - Automate payments for interest rate discounts
           - Round-up payment strategies
           - Windfall allocation strategies

        4. **Interest Rate Reduction**:
           - Negotiate with lenders for rate reductions
           - Take advantage of promotional rates
           - Improve credit score for better rates
           - Consider secured debt options

        5. **Behavioral & Psychological**:
           - Debt tracking and monitoring systems
           - Emergency fund building to avoid new debt
           - Spending habit modifications
           - Motivation and milestone celebration

        For each recommendation, provide:

        **recommendation_type**: Choose from:
        - "avalanche": High-interest first strategy
        - "snowball": Small balance first strategy  
        - "refinance": Rate reduction through refinancing
        - "consolidation": Combining multiple debts
        - "automation": Payment automation strategies
        - "negotiation": Rate negotiation with lenders
        - "behavioral": Habit and mindset changes

        **priority_score**: 1-10 based on:
        - Potential savings impact (1-4 points)
        - Implementation difficulty (1-3 points, easier = higher score)
        - User's financial situation urgency (1-3 points)

        **potential_savings**: Calculate realistic annual savings where applicable:
        - Interest savings from rate reductions
        - Time savings from faster payoff
        - Fee savings from consolidation

        **action_steps**: Provide 3-5 specific, actionable steps:
        - "Contact [lender] to request rate reduction"
        - "Research balance transfer cards with 0% intro APR"
        - "Set up automatic payment for 0.25% rate discount"

        **timeline**: Suggest realistic implementation timeframe:
        - "Immediate" (within 1 week)
        - "Short-term" (1-4 weeks)
        - "Medium-term" (1-3 months)
        - "Long-term" (3+ months)

        **difficulty**: Assess implementation complexity:
        - "easy": Simple online actions, no credit requirements
        - "medium": Some research needed, moderate credit requirements
        - "hard": Extensive research, excellent credit needed, complex process

        **Overall Strategy**: Recommend primary approach:
        - Focus on highest-impact recommendations first
        - Balance quick wins with long-term optimization
        - Consider user's psychological and financial capacity

        **Priority Order**: Rank recommendations by implementation order:
        - Start with easy, high-impact items
        - Build momentum with early wins
        - Progress to more complex optimizations

        Generate comprehensive, personalized recommendations that users can actually implement.
        Be specific with numbers, timelines, and action steps.
        Consider both financial and psychological factors in debt management.
        """
    
    async def generate_recommendations(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> RecommendationSet:
        """
        Generate personalized AI recommendations.
        
        Args:
            debts: List of user's debts
            analysis: Debt analysis results
            user_profile: Optional user profile information
            
        Returns:
            RecommendationSet with personalized recommendations
        """
        if not debts:
            # Return basic recommendations for debt-free users
            return RecommendationSet(
                recommendations=[
                    AIRecommendation(
                        recommendation_type="behavioral",
                        title="Build Emergency Fund",
                        description="Establish 3-6 months of expenses in savings to avoid future debt",
                        priority_score=9,
                        action_steps=[
                            "Calculate monthly expenses",
                            "Set up automatic transfer to savings",
                            "Target 3-6 months of expenses"
                        ],
                        timeline="Medium-term",
                        difficulty="easy",
                        benefits=["Financial security", "Debt prevention", "Peace of mind"]
                    ),
                    AIRecommendation(
                        recommendation_type="behavioral",
                        title="Start Investing",
                        description="Begin investing for long-term wealth building",
                        priority_score=7,
                        action_steps=[
                            "Open investment account",
                            "Start with index funds",
                            "Set up automatic contributions"
                        ],
                        timeline="Short-term",
                        difficulty="easy",
                        benefits=["Wealth growth", "Compound returns", "Financial independence"]
                    )
                ],
                overall_strategy="wealth_building",
                priority_order=[0, 1],
                estimated_impact={"emergency_fund_months": 6, "investment_growth": 0.07}
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
            "analysis": analysis.model_dump(),
            "user_profile": user_profile or {},
            "context": "personalized_recommendation_generation"
        }
        
        # Generate recommendations
        # FIXED: use result.output instead of result
        result = await self.agent.run(json.dumps(input_data, default=str))
        return result.output
    
    def generate_recommendations_sync(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> RecommendationSet:
        """
        Synchronous version of recommendation generation.
        
        Args:
            debts: List of user's debts
            analysis: Debt analysis results
            user_profile: Optional user profile information
            
        Returns:
            RecommendationSet with personalized recommendations
        """
        if not debts:
            # Return basic recommendations for debt-free users
            return RecommendationSet(
                recommendations=[
                    AIRecommendation(
                        recommendation_type="behavioral",
                        title="Build Emergency Fund",
                        description="Establish 3-6 months of expenses in savings to avoid future debt",
                        priority_score=9,
                        action_steps=[
                            "Calculate monthly expenses",
                            "Set up automatic transfer to savings",
                            "Target 3-6 months of expenses"
                        ],
                        timeline="Medium-term",
                        difficulty="easy",
                        benefits=["Financial security", "Debt prevention", "Peace of mind"]
                    ),
                    AIRecommendation(
                        recommendation_type="behavioral",
                        title="Start Investing",
                        description="Begin investing for long-term wealth building",
                        priority_score=7,
                        action_steps=[
                            "Open investment account",
                            "Start with index funds",
                            "Set up automatic contributions"
                        ],
                        timeline="Short-term",
                        difficulty="easy",
                        benefits=["Wealth growth", "Compound returns", "Financial independence"]
                    )
                ],
                overall_strategy="wealth_building",
                priority_order=[0, 1],
                estimated_impact={"emergency_fund_months": 6, "investment_growth": 0.07}
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
            "analysis": analysis.model_dump(),
            "user_profile": user_profile or {},
            "context": "personalized_recommendation_generation"
        }
        
        # Generate recommendations
        result = self.agent.run_sync(json.dumps(input_data, default=str))
        return result
