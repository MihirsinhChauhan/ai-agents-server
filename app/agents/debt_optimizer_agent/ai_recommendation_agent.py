"""
AI Recommendation Agent for DebtEase.
Generates personalized financial recommendations based on debt analysis.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic import BaseModel, Field

from app.configs.config import settings
from app.models.debt import DebtInDB, DebtResponse
from .enhanced_debt_analyzer import DebtAnalysisResult


class AIRecommendationInternal(BaseModel):
    """Internal AI-generated recommendation with detailed information."""

    recommendation_type: str = Field(..., description="Type: snowball, avalanche, refinance, consolidation, automation, negotiation, behavioral")
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


class AIRecommendation(BaseModel):
    """AI-generated recommendation matching frontend TypeScript interface exactly."""

    id: str = Field(..., description="Unique recommendation identifier")
    user_id: str = Field(..., description="User ID this recommendation belongs to")
    recommendation_type: str = Field(..., description="Type: snowball, avalanche, refinance")
    title: str = Field(..., description="Short, actionable title")
    description: str = Field(..., description="Detailed explanation of the recommendation")
    potential_savings: Optional[float] = Field(None, description="Estimated savings if followed")
    priority_score: int = Field(..., ge=1, le=10, description="Priority score 1-10")
    is_dismissed: bool = Field(default=False, description="Whether user dismissed this recommendation")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

    class Config:
        populate_by_name = True


class RecommendationSetInternal(BaseModel):
    """Internal set of AI recommendations with detailed information."""

    recommendations: List[AIRecommendationInternal] = Field(..., description="List of personalized recommendations")
    overall_strategy: str = Field(..., description="Recommended overall debt strategy")
    priority_order: List[int] = Field(..., description="Recommended order to implement recommendations")
    estimated_impact: Dict[str, float] = Field(..., description="Expected impact metrics")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Generation timestamp (ISO format)")

    class Config:
        populate_by_name = True


class RecommendationSet(BaseModel):
    """Frontend-compatible set of AI recommendations."""

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
        """Initialize the AI recommendation agent with robust fallback strategies."""
        self.model = self._initialize_model()

        # Original agent for backward compatibility
        self.agent = Agent(
            model=self.model,
            instructions=self._get_system_prompt(),
            output_type=RecommendationSetInternal
        )

        # NEW: Simplified agent for reliable AI processing
        self.simple_agent = Agent(
            model=self.model,
            instructions=self._get_simple_prompt(),
            output_type=str  # Use string to avoid function calling
        )

        # Track fallback usage for monitoring
        self.fallback_stats = {
            "pydantic_attempts": 0,
            "string_attempts": 0,
            "calculation_fallbacks": 0
        }

    def _convert_to_frontend_format(self, internal_recommendations: RecommendationSetInternal, user_id: str) -> RecommendationSet:
        """Convert internal recommendations to frontend-compatible format."""

        frontend_recommendations = []
        for rec in internal_recommendations.recommendations:
            frontend_rec = AIRecommendation(
                id=str(uuid4()),
                user_id=user_id,
                recommendation_type=rec.recommendation_type,
                title=rec.title,
                description=rec.description,
                potential_savings=rec.potential_savings,
                priority_score=rec.priority_score,
                is_dismissed=False,
                created_at=internal_recommendations.generated_at
            )
            frontend_recommendations.append(frontend_rec)

        return RecommendationSet(
            recommendations=frontend_recommendations,
            overall_strategy=internal_recommendations.overall_strategy,
            priority_order=internal_recommendations.priority_order,
            estimated_impact=internal_recommendations.estimated_impact,
            generated_at=internal_recommendations.generated_at
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

    def _get_simple_prompt(self) -> str:
        """Simplified prompt that avoids function calling triggers."""
        return """You are a debt advisor. Analyze the provided debt data and provide 3-5 specific recommendations.

Return ONLY valid JSON in this exact format:
{
  "recommendations": [
    {
      "recommendation_type": "avalanche|snowball|refinance|consolidation|automation",
      "title": "Brief title here",
      "description": "Specific actionable description",
      "priority_score": 8,
      "action_steps": ["Step 1", "Step 2"],
      "timeline": "Short-term"
    }
  ],
  "overall_strategy": "balanced_approach"
}

Focus on:
- High-interest debts (>15% APR)
- Payment consolidation opportunities
- Payment automation benefits
- Debt snowball vs avalanche strategies

Be concise and actionable."""

    async def generate_recommendations_simple_string(self, debts: List[DebtInDB], analysis: DebtAnalysisResult) -> RecommendationSet:
        """Strategy 2: Simple string output approach for reliability."""
        try:
            # Prepare simplified input data
            simple_data = {
                "total_debt": sum(d.current_balance for d in debts),
                "highest_rate": max(d.interest_rate for d in debts),
                "debt_count": len(debts),
                "risk_level": analysis.risk_assessment,
                "high_interest_count": sum(1 for d in debts if d.interest_rate > 15)
            }

            result = await self.simple_agent.run(json.dumps(simple_data))
            self.fallback_stats["string_attempts"] += 1

            # Parse JSON response
            try:
                parsed = json.loads(result.output)

                # Convert to RecommendationSet
                return self._convert_string_to_recommendation_set(parsed, str(debts[0].user_id) if debts else "unknown")

            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {e}")
                raise

        except Exception as e:
            print(f"String output approach failed: {e}")
            raise

    def generate_recommendations_calculation_fallback(self, debts: List[DebtInDB], analysis: DebtAnalysisResult) -> RecommendationSet:
        """Strategy 3: Pure calculation fallback (always works)."""
        self.fallback_stats["calculation_fallbacks"] += 1

        recommendations = []
        user_id = str(debts[0].user_id) if debts else "unknown"

        # Rule-based recommendations
        if debts:
            # High-interest debt focus
            high_interest = [d for d in debts if d.interest_rate > 15]
            if high_interest:
                highest = max(high_interest, key=lambda d: d.interest_rate)
                recommendations.append(AIRecommendation(
                    id=str(uuid4()),
                    user_id=user_id,
                    recommendation_type="avalanche",
                    title=f"Pay {highest.name} first",
                    description=f"Your {highest.name} has {highest.interest_rate}% interest - prioritize this to save on interest",
                    priority_score=9,
                    potential_savings=highest.current_balance * (highest.interest_rate / 100),
                    is_dismissed=False,
                    created_at=datetime.now().isoformat()
                ))

            # Consolidation opportunity
            if len(debts) > 2:
                total_balance = sum(d.current_balance for d in debts)
                recommendations.append(AIRecommendation(
                    id=str(uuid4()),
                    user_id=user_id,
                    recommendation_type="consolidation",
                    title="Consider debt consolidation",
                    description=f"You have {len(debts)} debts totaling ${total_balance:,.0f} - consolidation could simplify payments",
                    priority_score=7,
                    is_dismissed=False,
                    created_at=datetime.now().isoformat()
                ))

        # Always include automation recommendation
        recommendations.append(AIRecommendation(
            id=str(uuid4()),
            user_id=user_id,
            recommendation_type="automation",
            title="Set up automatic payments",
            description="Automate payments to avoid late fees and potentially earn interest rate discounts",
            priority_score=6,
            is_dismissed=False,
            created_at=datetime.now().isoformat()
        ))

        return RecommendationSet(
            recommendations=recommendations[:5],
            overall_strategy="balanced_approach",
            priority_order=list(range(len(recommendations))),
            estimated_impact={"fallback_used": True, "recommendation_count": len(recommendations)},
            generated_at=datetime.now().isoformat()
        )

    def _convert_string_to_recommendation_set(self, parsed_data: dict, user_id: str) -> RecommendationSet:
        """Convert string output to RecommendationSet."""
        recommendations = []
        for rec_data in parsed_data.get("recommendations", []):
            recommendations.append(AIRecommendation(
                id=str(uuid4()),
                user_id=user_id,
                recommendation_type=rec_data.get("recommendation_type", "general"),
                title=rec_data.get("title", "Recommendation"),
                description=rec_data.get("description", "Description"),
                priority_score=rec_data.get("priority_score", 5),
                is_dismissed=False,
                created_at=datetime.now().isoformat()
            ))

        return RecommendationSet(
            recommendations=recommendations[:5],
            overall_strategy=parsed_data.get("overall_strategy", "balanced"),
            priority_order=list(range(len(recommendations))),
            estimated_impact={"recommendation_count": len(recommendations)},
            generated_at=datetime.now().isoformat()
        )

    async def generate_recommendations_robust(self, debts: List[DebtInDB], analysis: DebtAnalysisResult) -> RecommendationSet:
        """Robust method with 3-tier fallback strategy."""
        # Strategy 1: Try original complex AI approach
        try:
            self.fallback_stats["pydantic_attempts"] += 1
            return await self.generate_recommendations_original(debts, analysis)
        except Exception as e:
            print(f"Original AI approach failed: {e}")

        # Strategy 2: Try simple string output approach
        try:
            return await self.generate_recommendations_simple_string(debts, analysis)
        except Exception as e:
            print(f"String output approach failed: {e}")

        # Strategy 3: Use calculation fallback (always works)
        print("Using calculation fallback for recommendations")
        return self.generate_recommendations_calculation_fallback(debts, analysis)

    async def generate_recommendations_original(self, debts: List[DebtInDB], analysis: DebtAnalysisResult) -> RecommendationSet:
        """Original complex AI approach (for backward compatibility)."""
        if not debts:
            # Return basic recommendations for debt-free users
            user_id = "unknown"
            return RecommendationSet(
                recommendations=[
                    AIRecommendation(
                        id=str(uuid4()),
                        user_id=user_id,
                        recommendation_type="behavioral",
                        title="Build Emergency Fund",
                        description="Establish 3-6 months of expenses in savings to avoid future debt",
                        priority_score=9,
                        is_dismissed=False,
                        created_at=datetime.now().isoformat()
                    ),
                    AIRecommendation(
                        id=str(uuid4()),
                        user_id=user_id,
                        recommendation_type="behavioral",
                        title="Start Investing",
                        description="Begin investing for long-term wealth building",
                        priority_score=7,
                        is_dismissed=False,
                        created_at=datetime.now().isoformat()
                    )
                ],
                overall_strategy="wealth_building",
                priority_order=[0, 1],
                estimated_impact={"emergency_fund_months": 6, "investment_growth": 0.07},
                generated_at=datetime.now().isoformat()
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
            "user_profile": {},
            "context": "personalized_recommendation_generation"
        }

        # Generate recommendations using internal model
        result = await self.agent.run(json.dumps(input_data, default=str))
        internal_recommendations = result.output

        # Convert to frontend-compatible format
        return self._convert_to_frontend_format(internal_recommendations, str(debts[0].user_id))

    async def generate_recommendations(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> RecommendationSet:
        """
        Generate personalized AI recommendations with robust fallback strategies.

        Args:
            debts: List of user's debts
            analysis: Debt analysis results
            user_profile: Optional user profile information

        Returns:
            RecommendationSet with personalized recommendations
        """
        return await self.generate_recommendations_robust(debts, analysis)
    
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
        # For sync version, we use the calculation fallback as it's the most reliable
        # In a production environment, you might want to implement async-to-sync conversion
        return self.generate_recommendations_calculation_fallback(debts, analysis)
