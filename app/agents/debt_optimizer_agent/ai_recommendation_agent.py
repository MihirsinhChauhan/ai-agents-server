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
from app.models.onboarding import UserGoalResponse
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

        # Main agent configured for text generation (no function calling)
        self.agent = Agent(
            model=self.model,
            instructions=self._get_system_prompt(),
            output_type=str  # Use string output to avoid function calling
        )

        # Simplified agent for fallback scenarios
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
        """Define the professional Indian debt consultant system prompt for AI recommendations."""
        return """
        You are a Professional Debt Consultant for DebtEase India specializing in Indian financial systems.

        **CRITICAL: ALL AMOUNTS IN INDIAN RUPEES (₹). Never use USD ($).**

        **INDIAN CONTEXT:**
        - Banks: HDFC, ICICI, SBI, Axis (rates 8-45%)
        - Payments: UPI auto-pay, NEFT, EMI alignment with salary
        - Credit: CIBIL score optimization (target 750+)
        - Culture: Diwali goals, family planning, festival bonuses
        - Tax: 80C benefits, home loan deductions

        **STRATEGY FRAMEWORK:**
        1. **आपातकाल (Emergency)**: ₹25K-75K fund in high-yield savings first
        2. **हिमस्खलन (Avalanche)**: Target credit cards 40%+ rates
        3. **स्नोबॉल (Snowball)**: Small debts for family motivation
        4. **समेकन (Consolidation)**: Personal loan 10-14% vs multiple debts
        5. **स्वचालन (Automation)**: UPI setup, payment optimization

        **IMPLEMENTATION PHASES:**
        - Foundation (Weeks 1-4): Emergency fund, CIBIL check, banking setup
        - Attack (Months 2-6): Debt elimination, bonus utilization
        - Optimization (6+ months): Refinancing, investment transition
        RESPOND WITH ONLY VALID JSON. NO TEXT BEFORE OR AFTER. NO EXPLANATIONS.

        {
          "recommendations": [
            {
              "recommendation_type": "emergency_fund|avalanche|snowball|consolidation|automation|cibil_building",
              "title": "Action-oriented title (max 60 chars)",
              "description": "Detailed guidance with Indian context, ₹ amounts (150-250 words)",
              "priority_score": 8,
              "potential_savings": 25000,
              "action_steps": [
                "Week 1: Specific step with Indian banking details",
                "Week 2: Implementation with ₹ amounts",
                "Month 2: Progress milestone"
              ],
              "timeline": "Foundation Phase (1-4 weeks)",
              "benefits": ["Interest savings ₹X", "CIBIL improvement"],
              "risks": ["Income volatility", "Festival expenses"],
              "prerequisites": ["CIBIL 650+", "Salary account"]
            }
          ]
        }

        Include specific Indian bank names (HDFC/ICICI/SBI), ₹ amounts, CIBIL optimization, UPI setup, and Diwali goals.
        """

    def _get_simple_prompt(self) -> str:
        """Professional Indian debt consultant simplified prompt with cultural context."""
        return """You are a Debt Consultant for DebtEase India.

**CRITICAL: Use Indian Rupees (₹) only, never USD ($).**

**Indian Context:**
- Banks: HDFC, ICICI, SBI, Axis
- CIBIL: Target 750+ score
- Culture: Diwali goals, family planning
- Payments: UPI, NEFT, EMI alignment

**Strategies:**
1. आपातकाल (Emergency): ₹25K-75K fund first
2. हिमस्खलन (Avalanche): Target 40%+ credit cards
3. स्नोबॉल (Snowball): Small debts for motivation
4. समेकन (Consolidation): Personal loan 10-14%

RESPOND WITH ONLY VALID JSON. NO EXPLANATIONS. NO MARKDOWN. NO TEXT BEFORE OR AFTER JSON.

{
  "recommendations": [
    {
      "recommendation_type": "emergency_fund|avalanche|snowball|consolidation|automation",
      "title": "Title (max 60 chars)",
      "description": "Detailed guidance with ₹ amounts and Indian context (150-200 words)",
      "potential_savings": 25000,
      "priority_score": 8,
      "action_steps": ["Step 1", "Step 2", "Step 3"],
      "timeline": "Foundation Phase (1-4 weeks)",
      "benefits": ["Interest savings ₹X", "CIBIL improvement"],
      "risks": ["Income volatility", "Festival expenses"],
      "prerequisites": ["CIBIL 650+", "Salary account"]
    }
  ]
}"""

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
        """Strategy 3: Pure calculation fallback with Indian financial context (always works)."""
        self.fallback_stats["calculation_fallbacks"] += 1

        recommendations = []
        user_id = str(debts[0].user_id) if debts else "unknown"

        # Rule-based recommendations with Indian context
        if debts:
            total_debt = sum(d.current_balance for d in debts)

            # Emergency fund foundation (highest priority for Indian users)
            recommendations.append(AIRecommendation(
                id=str(uuid4()),
                user_id=user_id,
                recommendation_type="emergency_fund",
                title="आपातकालीन फंड: Build Emergency Foundation First",
                description=f"Before aggressive debt payments, establish ₹{min(75000, total_debt * 0.1):,.0f} emergency fund in high-yield savings account (SBI/HDFC/ICICI). This prevents new debt during medical emergencies or job loss, which is critical for Indian families.",
                priority_score=9,
                potential_savings=total_debt * 0.05,  # 5% of total debt saved by avoiding new debt
                is_dismissed=False,
                created_at=datetime.now().isoformat()
            ))

            # High-interest debt focus with Indian banking context
            high_interest = [d for d in debts if d.interest_rate > 15]
            if high_interest:
                highest = max(high_interest, key=lambda d: d.interest_rate)
                indian_bank_context = "HDFC" if "hdfc" in highest.name.lower() else "your bank"
                recommendations.append(AIRecommendation(
                    id=str(uuid4()),
                    user_id=user_id,
                    recommendation_type="avalanche",
                    title=f"हिमस्खलन रणनीति: Attack {highest.name} at {highest.interest_rate}%",
                    description=f"Your {highest.name} at {highest.interest_rate}% interest is costing you ₹{highest.current_balance * (highest.interest_rate / 100) / 12:,.0f} per month. Prioritize this debt while making minimum payments on others. Consider balance transfer to {indian_bank_context} lifetime free cards for lower rates.",
                    priority_score=8,
                    potential_savings=highest.current_balance * (highest.interest_rate / 100) * 0.6,  # 60% interest savings
                    is_dismissed=False,
                    created_at=datetime.now().isoformat()
                ))

            # Cash flow optimization with Indian lifestyle
            recommendations.append(AIRecommendation(
                id=str(uuid4()),
                user_id=user_id,
                recommendation_type="cash_flow",
                title="नकदी प्रवाह सुधार: Optimize Indian Expense Categories",
                description=f"Audit monthly expenses across Indian categories: groceries (₹8,000), transport (₹3,000), utilities (₹2,500), family support (₹5,000). Reducing dining out by ₹3,000/month adds ₹36,000 annual debt payment capacity. Use festival bonuses and salary increments for debt acceleration.",
                priority_score=7,
                potential_savings=36000,  # Annual savings from expense optimization
                is_dismissed=False,
                created_at=datetime.now().isoformat()
            ))

            # Consolidation opportunity with Indian banking products
            if len(debts) > 2:
                recommendations.append(AIRecommendation(
                    id=str(uuid4()),
                    user_id=user_id,
                    recommendation_type="consolidation",
                    title="समेकन: Consolidate with Indian Personal Loan",
                    description=f"You have {len(debts)} debts totaling ₹{total_debt:,.0f}. Consider consolidating with personal loan from SBI/HDFC at 10-12% interest rate versus current weighted average. This simplifies payments and potentially reduces interest burden by ₹{total_debt * 0.08:,.0f} annually.",
                    priority_score=6,
                    potential_savings=total_debt * 0.08,  # 8% annual savings
                    is_dismissed=False,
                    created_at=datetime.now().isoformat()
                ))

        # CIBIL score building (always relevant for Indian users)
        recommendations.append(AIRecommendation(
            id=str(uuid4()),
            user_id=user_id,
            recommendation_type="cibil_building",
            title="सिबिल सुधार: Optimize CIBIL Score for Future Loans",
            description="Maintain payment history, keep credit utilization below 30%, and avoid closing old credit cards. Target CIBIL score of 750+ to access lowest interest rates (7-9%) for future home loans, saving ₹5-8 lakh over loan tenure compared to poor credit rates.",
            priority_score=8,
            potential_savings=500000,  # Long-term savings from better credit
            is_dismissed=False,
            created_at=datetime.now().isoformat()
        ))

        # Indian payment automation
        recommendations.append(AIRecommendation(
            id=str(uuid4()),
            user_id=user_id,
            recommendation_type="automation",
            title="स्वचालन: Setup Indian Digital Payment Systems",
            description="Configure UPI auto-pay, NEFT standing instructions, and EMI auto-debit aligned with salary dates. Enable payment reminders through bank apps (HDFC NetBanking, ICICI iMobile). This prevents late fees (₹500-1,500 per instance) and may qualify for interest rate discounts.",
            priority_score=6,
            potential_savings=12000,  # Annual late fee prevention
            is_dismissed=False,
            created_at=datetime.now().isoformat()
        ))

        return RecommendationSet(
            recommendations=recommendations[:5],
            overall_strategy="comprehensive_indian_approach",
            priority_order=list(range(len(recommendations))),
            estimated_impact={
                "fallback_used": True,
                "recommendation_count": len(recommendations),
                "total_potential_savings": sum(r.potential_savings or 0 for r in recommendations),
                "indian_banking_integrated": True,
                "cibil_optimization": True,
                "cultural_considerations": "Indian family financial planning integrated"
            },
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
        """Robust method with improved AI + fallback strategy."""
        # Strategy 1: Try improved AI approach with JSON parsing
        try:
            self.fallback_stats["pydantic_attempts"] += 1
            return await self.generate_recommendations_with_ai(debts, analysis)
        except Exception as e:
            print(f"Enhanced AI approach failed: {e}")

        # Strategy 2: Try simple string output approach
        try:
            return await self.generate_recommendations_simple_string(debts, analysis)
        except Exception as e:
            print(f"Simple AI approach failed: {e}")

        # Strategy 3: Use calculation fallback (always works)
        print("Using calculation fallback for recommendations")
        return self.generate_recommendations_calculation_fallback(debts, analysis)

    async def generate_recommendations_with_ai(self, debts: List[DebtInDB], analysis: DebtAnalysisResult) -> RecommendationSet:
        """Generate recommendations using AI with proper JSON parsing."""
        if not debts:
            return self._create_empty_recommendations("unknown")

        try:
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
                "context": "professional_debt_consultation"
            }

            # Add rate limiting delay to prevent Groq rate limit errors
            import asyncio
            await asyncio.sleep(1)  # 1 second delay for recommendations

            # Generate recommendations using main AI agent
            result = await self.agent.run(json.dumps(input_data, default=str))
            ai_response = result.output

            # Clean and parse JSON response
            try:
                # Remove any markdown formatting
                json_text = ai_response.strip()
                if json_text.startswith("```json"):
                    json_text = json_text[7:]
                if json_text.endswith("```"):
                    json_text = json_text[:-3]
                json_text = json_text.strip()

                # Parse JSON
                parsed_data = json.loads(json_text)

                # Convert to RecommendationSet
                return self._convert_ai_response_to_recommendation_set(parsed_data, str(debts[0].user_id))

            except json.JSONDecodeError as e:
                print(f"AI JSON parsing failed: {e}")
                print(f"Raw response: {ai_response[:500]}...")
                # Fall back to simple string approach
                return await self.generate_recommendations_simple_string(debts, analysis)

        except Exception as e:
            print(f"AI recommendation generation failed: {e}")
            # Fall back to calculation method
            return self.generate_recommendations_calculation_fallback(debts, analysis)

    def _convert_ai_response_to_recommendation_set(self, parsed_data: dict, user_id: str) -> RecommendationSet:
        """Convert AI response to proper RecommendationSet format."""
        recommendations = []

        for i, rec_data in enumerate(parsed_data.get("recommendations", [])):
            recommendation = AIRecommendation(
                id=str(uuid4()),
                user_id=user_id,
                recommendation_type=rec_data.get("recommendation_type", "behavioral"),
                title=rec_data.get("title", "Professional Recommendation"),
                description=rec_data.get("description", "Professional debt management guidance"),
                potential_savings=rec_data.get("potential_savings"),
                priority_score=rec_data.get("priority_score", 5),
                is_dismissed=False,
                created_at=datetime.now().isoformat()
            )
            recommendations.append(recommendation)

        return RecommendationSet(
            recommendations=recommendations,
            overall_strategy=parsed_data.get("overall_strategy", "comprehensive_approach"),
            priority_order=parsed_data.get("priority_order", list(range(len(recommendations)))),
            estimated_impact=parsed_data.get("estimated_impact", {}),
            generated_at=datetime.now().isoformat()
        )

    def _create_empty_recommendations(self, user_id: str) -> RecommendationSet:
        """Create recommendations for debt-free users."""
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
        user_profile: Optional[Dict[str, Any]] = None,
        user_goals: Optional[List[UserGoalResponse]] = None
    ) -> RecommendationSet:
        """
        Generate personalized AI recommendations with robust fallback strategies.

        Args:
            debts: List of user's debts
            analysis: Debt analysis results
            user_profile: Optional user profile information
            user_goals: Optional list of user's financial goals

        Returns:
            RecommendationSet with personalized recommendations
        """
        return await self.generate_recommendations_robust(debts, analysis)
    
    def generate_recommendations_sync(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        user_profile: Optional[Dict[str, Any]] = None,
        user_goals: Optional[List[UserGoalResponse]] = None
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
