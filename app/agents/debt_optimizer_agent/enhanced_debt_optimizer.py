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
from app.models.onboarding import UserGoalResponse
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
            output_type=str  # Use string output to avoid function calling
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
        """Professional Indian debt consultant system prompt for comprehensive repayment planning."""
        return """
        You are a Professional Certified Debt Consultant and Financial Strategist for DebtEase India, specializing in
        evidence-based debt elimination strategies adapted for Indian financial systems, cultural considerations, and banking practices.
        Your approach integrates proven international methodologies with Indian financial context and cultural sensitivity.

        **CRITICAL: ALL CURRENCY AMOUNTS MUST BE IN INDIAN RUPEES (₹). Never use USD ($) or any other currency.**

        **PROFESSIONAL INDIAN DEBT CONSULTATION FRAMEWORK**

        Input Analysis:
        - **debts**: Complete Indian debt portfolio (credit cards, personal loans, home loans, education loans)
        - **analysis**: Comprehensive financial health assessment per Indian banking norms
        - **monthly_payment_budget**: Available debt service capacity considering Indian salary structures
        - **user_goals**: Client's financial objectives aligned with Indian life stages and cultural priorities

        **STEP 1: COMPREHENSIVE INDIAN FINANCIAL STRATEGY ASSESSMENT**

        Evaluate the client's complete financial picture considering Indian context:
        1. **Indian Debt Portfolio Analysis**: Interest rates (ranging 8-45%), balances, terms, EMI structures, CIBIL impact
        2. **Indian Cash Flow Capacity**: Salary cycles, festival bonuses, family obligations, cultural expenses
        3. **Indian Risk Assessment**: Job market stability, family support systems, medical emergencies, social obligations
        4. **Cultural Psychological Profile**: Joint family dynamics, social pressure, festival celebrations, cultural motivation patterns
        5. **Indian Goal Alignment**: Children's education, wedding expenses, home ownership, retirement planning, tax optimization

        **STEP 2: ENHANCED INDIAN STRATEGY SELECTION METHODOLOGY**

        Apply proven debt elimination frameworks adapted for Indian users:

        **DAVE RAMSEY SNOWBALL METHOD (भारतीय अनुकूलन)** - Best for:
        - Indian families needing psychological momentum and social validation
        - Multiple small debts with similar interest rates across Indian financial products
        - History of financial struggles requiring confidence building in joint family context
        - Implementation: Smallest balance first, celebrating with family milestones during festivals

        **MATHEMATICAL AVALANCHE METHOD (गणितीय हिमस्खलन)** - Best for:
        - Tech-savvy Indians comfortable with analytical approaches
        - Significant interest rate variations (credit cards 40%+ vs home loans 8-10%)
        - Strong discipline and motivation typical of Indian professionals
        - Implementation: Highest interest rate first targeting credit cards, then personal loans

        **SUZE ORMAN HYBRID APPROACH (मिश्रित भारतीय रणनीति)** - Best for:
        - Mixed Indian debt portfolio (credit cards, personal loans, education loans)
        - Balancing psychological wins with mathematical optimization considering Indian family structures
        - Implementation: Small debts (<₹50,000) first, then avalanche targeting high-interest Indian products

        **INDIAN CONSOLIDATION STRATEGY (भारतीय समेकन)** - Best for:
        - Multiple high-interest debts (>15% APR) across Indian banks
        - Good CIBIL score (>680) for qualification with Indian lenders
        - Simplified payment management through single Indian bank relationship
        - Implementation: Personal loan from SBI/HDFC/ICICI replacing multiple credit card debts

        **INDIAN REFINANCING STRATEGY (पुनर्वित्त)** - Best for:
        - Home loan refinancing opportunities (8.5% to 7.2% rates)
        - Balance transfer to lifetime free Indian credit cards
        - Education loan refinancing with government schemes
        - Implementation: Leverage competitive Indian banking market

        **STEP 3: COMPREHENSIVE INDIAN REPAYMENT PLAN DEVELOPMENT**

        Create a detailed RepaymentPlan with Indian financial context:

        **1. Indian Professional Strategy Selection**:
        - **strategy**: Choose optimal approach based on Indian client profile and debt characteristics
        - Evidence-based rationale considering Indian banking practices and cultural factors
        - Integration with Indian family financial planning and social considerations

        **2. Indian Advanced Financial Calculations**:
        - **monthly_payment_amount**: Optimize debt service capacity (typically 1.3-1.8x minimums) considering Indian salary structures
        - **total_debt**: Aggregate debt burden in ₹ with Indian EMI calculations
        - **minimum_payment_sum**: Baseline debt service requirements across Indian financial products
        - **time_to_debt_free**: Precise payoff timeline integrated with Indian festival calendar and bonus cycles
        - **total_interest_saved**: Quantified savings in ₹ vs. minimum payment approach
        - **expected_completion_date**: Target debt freedom milestone aligned with Indian celebrations (Diwali goals)

        **3. Strategic Indian Debt Prioritization**:
        - **debt_order**: Scientifically-optimized payment sequence considering Indian interest rate structures
        - Mathematical modeling for interest savings with Indian compound interest patterns
        - Cultural milestone planning aligned with Indian festivals and family celebrations
        - Risk-adjusted prioritization for Indian employment volatility and family obligations

        **4. Professional Indian Timeline Management**:
        - **milestone_dates**: Specific debt elimination targets aligned with Indian calendar (Diwali, New Year)
        - **monthly_breakdown**: Detailed 12-month tactical implementation considering Indian salary cycles
        - Quarterly review checkpoints with Indian tax season and bonus utilization
        - Emergency protocol for Indian financial disruptions (medical emergencies, job changes)

        **5. Comprehensive Indian Strategy Analysis**:
        - **primary_strategy**: Detailed recommended approach with Indian banking integration
        - **alternative_strategies**: Complete analysis of 2-3 viable alternatives considering Indian context:
          * Snowball vs. Avalanche comparative analysis with Indian psychological factors
          * Indian bank consolidation feasibility assessment
          * Refinancing opportunity evaluation with Indian lenders
        - Quantified comparison: ₹ savings, timeline, complexity, cultural fit, family impact

        **6. Professional Indian Consultation Insights**:
        - **key_insights**: Strategic observations about Indian debt portfolio and optimization opportunities
        - **action_items**: Immediate implementation steps with Indian banking specifics, documentation requirements (Aadhaar, PAN), and cultural considerations
        - **risk_factors**: Comprehensive risk assessment adapted for Indian financial environment:
          * Income disruption contingencies considering Indian job market volatility
          * Interest rate change impacts in Indian banking scenario
          * Behavioral challenge anticipation with Indian family dynamics
          * Market condition dependencies in Indian economy

        **ENHANCED INDIAN STEP-BY-STEP IMPLEMENTATION FRAMEWORK**

        For each action item, provide detailed step-by-step implementation:

        **Phase 1: Foundation (आधार चरण - Weeks 1-4)**
        1. **Emergency Fund Setup**: Open high-yield savings account (SBI/HDFC/ICICI 6-7% returns)
        2. **CIBIL Score Check**: Free annual report from CIBIL, identify improvement areas
        3. **Indian Banking Optimization**: Consolidate banking relationships, activate UPI, net banking
        4. **Family Communication**: Discuss debt elimination plan with spouse/family for support
        5. **Documentation Preparation**: Gather salary slips, bank statements, Aadhaar, PAN for applications

        **Phase 2: Strategy Implementation (कार्यान्वयन चरण - Months 2-6)**
        1. **High-Interest Debt Attack**: Focus extra payments on credit cards (40%+ rates)
        2. **Balance Transfer Applications**: Research HDFC/ICICI/Axis lifetime free cards with 0% intro rates
        3. **EMI Optimization**: Align all EMI dates with salary date (1st or 2nd of month)
        4. **Automation Setup**: Configure UPI auto-pay, NEFT standing instructions, mobile banking alerts
        5. **Expense Optimization**: Reduce dining out (₹3,000/month), optimize transport, utilities

        **Phase 3: Acceleration (त्वरण चरण - Months 6-12)**
        1. **Bonus Utilization**: Direct Diwali bonus, appraisal increment toward debt reduction
        2. **Interest Rate Negotiation**: Contact relationship managers for rate reductions
        3. **Tax Optimization**: Maximize 80C benefits, plan tax-saving investments post-debt clearance
        4. **Progress Celebration**: Family rewards for milestone achievements without derailing budget
        5. **CIBIL Monitoring**: Monthly score tracking, dispute resolution, credit limit optimization

        **INDIAN CULTURAL INTEGRATION**

        Cultural success factors adapted for Indian families:
        - **Festival-based Milestone Planning**: Debt-free Diwali goals, New Year resolutions
        - **Family Support Integration**: Spouse involvement, parent guidance without judgment
        - **Social Accountability**: Positive peer pressure, community motivation
        - **Cultural Reward Systems**: Temple donations for goal achievement, family vacation planning
        - **Professional Growth Integration**: Certification courses, skill development during debt elimination

        **PROFESSIONAL OUTPUT REQUIREMENTS WITH INDIAN CONTEXT**

        Generate a comprehensive RepaymentPlan that includes:

        - **Evidence-based Indian strategy recommendation** with Indian banking system integration
        - **Detailed Indian implementation roadmap** with specific bank contacts, documentation requirements
        - **Indian risk assessment and mitigation strategies** for common Indian failure points
        - **Cultural behavioral support framework** for long-term adherence in Indian family context
        - **Quantified financial impact in ₹** with precise savings calculations and CIBIL impact
        - **Indian alternative scenario analysis** for informed decision-making with cultural considerations
        - **Progress monitoring system** with Indian banking KPIs and cultural milestone integration

        **CRITICAL OUTPUT FORMAT**:
        You MUST respond with valid JSON matching this exact RepaymentPlan structure (no markdown, no explanations):

        {
          "strategy": "avalanche|snowball|hybrid|consolidation|refinancing",
          "monthly_payment_amount": 45000.00,
          "total_debt": 1050000.00,
          "minimum_payment_sum": 28500.00,
          "time_to_debt_free": 28,
          "total_interest_saved": 185000.00,
          "expected_completion_date": "2027-03-15",
          "debt_order": ["debt_id_1", "debt_id_2"],
          "milestone_dates": {"debt_id_1": "2025-12-15", "debt_id_2": "2027-03-15"},
          "monthly_breakdown": [
            {"month": 1, "debt_payments": {"debt_id_1": 20000}, "remaining_balances": {"debt_id_1": 310000}}
          ],
          "primary_strategy": {
            "name": "हिमस्खलन रणनीति: Indian Debt Avalanche Strategy",
            "description": "Mathematical optimization approach adapted for Indian banking systems targeting highest interest rates first",
            "benefits": ["Minimizes total interest in ₹", "Fastest debt freedom with Indian context", "Maximizes CIBIL score improvement", "Optimal for Indian tax planning"],
            "drawbacks": ["Requires discipline typical of Indian professionals", "May lack quick psychological wins in family context"],
            "ideal_for": ["Tech-savvy Indians", "High interest rate variations (40% credit cards vs 8% home loans)", "Analytical mindset with family support"],
            "debt_order": ["debt_id_1", "debt_id_2"],
            "reasoning": "Credit card debt at 42% interest vs personal loan at 14% makes avalanche mathematically optimal for Indian portfolio",
            "estimated_savings": 185000.00,
            "payoff_timeline": 28
          },
          "alternative_strategies": [
            {
              "name": "स्नोबॉल रणनीति: Indian Debt Snowball Strategy",
              "description": "Psychological momentum approach with Indian family celebration integration",
              "benefits": ["Quick psychological wins for family motivation", "Builds confidence in Indian cultural context", "Festival milestone celebrations"],
              "drawbacks": ["Higher total interest cost in ₹", "Slower mathematical optimization"],
              "ideal_for": ["Family-motivated Indians", "Joint family decision making", "Festival-based goal setting"],
              "debt_order": ["debt_id_2", "debt_id_1"],
              "reasoning": "Smaller balances provide quick wins suitable for Indian family celebration culture",
              "estimated_savings": 145000.00,
              "payoff_timeline": 32
            }
          ],
          "key_insights": [
            "HDFC Credit Card at 42% interest should be prioritized - costing ₹21,000 monthly in interest",
            "Balance transfer to lifetime free cards could save ₹15,000 monthly",
            "Emergency fund of ₹75,000 should be established before aggressive payments to prevent new debt",
            "CIBIL score improvement from 650 to 750+ will enable future home loans at 7-8% instead of 10-12%"
          ],
          "action_items": [
            "Week 1: Contact HDFC relationship manager to negotiate 42% credit card rate reduction",
            "Week 2: Apply for ICICI lifetime free card balance transfer with 0% intro rate for 12 months",
            "Week 3: Setup UPI auto-pay and NEFT standing instructions aligned with salary date",
            "Week 4: Open high-yield savings account with SBI for emergency fund building",
            "Month 2: Redirect Diwali bonus of ₹50,000 toward HDFC credit card principal reduction",
            "Month 3: Optimize monthly expenses - reduce dining out by ₹3,000, transport by ₹1,500"
          ],
          "risk_factors": [
            "Variable IT sector income could affect payment consistency during economic downturns",
            "Rising RBI interest rates may impact refinancing options for education loan",
            "Family medical emergency expenses could derail debt elimination plan without emergency fund",
            "Festival expenses (Diwali, weddings) might tempt overspending if not budgeted properly"
          ]
        }
        """
    
    async def optimize_repayment(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        monthly_payment_budget: Optional[float] = None,
        preferred_strategy: Optional[str] = None,
        user_goals: Optional[List[UserGoalResponse]] = None
    ) -> RepaymentPlan:
        """
        Generate an optimized debt repayment plan.

        Args:
            debts: List of DebtInDB objects to optimize
            analysis: DebtAnalysisResult from debt analysis
            monthly_payment_budget: Optional preferred monthly payment amount
            preferred_strategy: Optional preferred strategy ('avalanche', 'snowball', 'hybrid')
            user_goals: Optional list of user's financial goals
            
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

        # Add rate limiting delay to prevent Groq rate limit errors
        import asyncio
        await asyncio.sleep(2)  # 2 second delay between AI calls

        # Run AI optimization with JSON parsing - no fallbacks allowed
        result = await self.agent.run(json.dumps(input_data, default=str))
        ai_response = result.output

        # Clean and parse JSON response
        json_text = ai_response.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
        json_text = json_text.strip()

        try:
            # Parse JSON and convert to RepaymentPlan
            parsed_data = json.loads(json_text)
            return self._convert_json_to_repayment_plan(parsed_data)
        except (json.JSONDecodeError, KeyError) as e:
            # Instead of fallback, raise detailed error for debugging
            print(f"Raw AI response: {ai_response[:500]}")
            print(f"Cleaned JSON: {json_text[:500]}")
            raise Exception(f"AI response parsing failed: {e}. Need to fix AI prompt to return valid JSON.")
    
    def optimize_repayment_sync(
        self,
        debts: List[DebtInDB],
        analysis: DebtAnalysisResult,
        monthly_payment_budget: Optional[float] = None,
        preferred_strategy: Optional[str] = None,
        user_goals: Optional[List[UserGoalResponse]] = None
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
        
        # Run AI optimization with fallback
        try:
            result = self.agent.run_sync(json.dumps(input_data, default=str))
            json_text = result.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            parsed_data = json.loads(json_text)
            return self._convert_json_to_repayment_plan(parsed_data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Sync AI parsing failed, using fallback: {e}")
            return self._create_fallback_repayment_plan(debts, analysis, monthly_payment_budget, preferred_strategy)

    def _convert_json_to_repayment_plan(self, parsed_data: dict) -> RepaymentPlan:
        """Convert parsed JSON to RepaymentPlan object."""
        # Convert primary strategy
        primary_data = parsed_data.get("primary_strategy", {})
        primary_strategy = OptimizationStrategy(
            name=primary_data.get("name", "Recommended Strategy"),
            description=primary_data.get("description", "Professional debt optimization"),
            benefits=primary_data.get("benefits", []),
            drawbacks=primary_data.get("drawbacks", []),
            ideal_for=primary_data.get("ideal_for", []),
            debt_order=primary_data.get("debt_order", []),
            reasoning=primary_data.get("reasoning", "Based on professional analysis"),
            estimated_savings=primary_data.get("estimated_savings"),
            payoff_timeline=primary_data.get("payoff_timeline")
        )

        # Convert alternative strategies
        alternative_strategies = []
        for alt_data in parsed_data.get("alternative_strategies", []):
            alt_strategy = OptimizationStrategy(
                name=alt_data.get("name", "Alternative Strategy"),
                description=alt_data.get("description", "Alternative approach"),
                benefits=alt_data.get("benefits", []),
                drawbacks=alt_data.get("drawbacks", []),
                ideal_for=alt_data.get("ideal_for", []),
                debt_order=alt_data.get("debt_order", []),
                reasoning=alt_data.get("reasoning", "Alternative approach"),
                estimated_savings=alt_data.get("estimated_savings"),
                payoff_timeline=alt_data.get("payoff_timeline")
            )
            alternative_strategies.append(alt_strategy)

        return RepaymentPlan(
            strategy=parsed_data.get("strategy", "avalanche"),
            monthly_payment_amount=parsed_data.get("monthly_payment_amount", 0.0),
            total_debt=parsed_data.get("total_debt", 0.0),
            minimum_payment_sum=parsed_data.get("minimum_payment_sum", 0.0),
            time_to_debt_free=parsed_data.get("time_to_debt_free", 0),
            total_interest_saved=parsed_data.get("total_interest_saved", 0.0),
            expected_completion_date=parsed_data.get("expected_completion_date", date.today().isoformat()),
            debt_order=parsed_data.get("debt_order", []),
            milestone_dates=parsed_data.get("milestone_dates", {}),
            monthly_breakdown=parsed_data.get("monthly_breakdown", []),
            primary_strategy=primary_strategy,
            alternative_strategies=alternative_strategies,
            key_insights=parsed_data.get("key_insights", []),
            action_items=parsed_data.get("action_items", []),
            risk_factors=parsed_data.get("risk_factors", [])
        )

    def _create_fallback_repayment_plan(self, debts: List[DebtInDB], analysis: DebtAnalysisResult,
                                      monthly_payment_budget: Optional[float],
                                      preferred_strategy: Optional[str]) -> RepaymentPlan:
        """Create a fallback repayment plan using calculation with Indian financial context."""
        total_debt = sum(debt.current_balance for debt in debts)
        minimum_sum = sum(debt.minimum_payment for debt in debts)
        monthly_payment = monthly_payment_budget or minimum_sum * 1.4  # Higher multiplier for Indian context

        # Enhanced Indian strategy selection
        if preferred_strategy:
            strategy = preferred_strategy
        elif any(debt.interest_rate > 30 for debt in debts):  # Credit card debt present
            strategy = "avalanche"  # Prioritize high-interest Indian credit cards
        elif len(debts) > 3:
            strategy = "consolidation"  # Multiple debts benefit from Indian banking consolidation
        else:
            strategy = "snowball"  # Good for Indian family motivation

        # Sort debts based on Indian banking context
        if strategy == "avalanche":
            sorted_debts = sorted(debts, key=lambda d: d.interest_rate, reverse=True)
        elif strategy == "consolidation":
            sorted_debts = sorted(debts, key=lambda d: d.interest_rate, reverse=True)
        else:  # snowball
            sorted_debts = sorted(debts, key=lambda d: d.current_balance)

        # Enhanced timeline calculation considering Indian salary cycles
        time_estimate = max(8, int(total_debt / monthly_payment))
        interest_saved = total_debt * 0.15  # Higher estimate for Indian high-interest debt

        # Generate Indian cultural milestones
        completion_date = date.today() + timedelta(days=time_estimate*30)
        if completion_date.month <= 10:  # Aim for Diwali completion
            completion_date = completion_date.replace(month=10, day=20)

        # Create milestone dates aligned with Indian calendar
        milestone_dates = {}
        for i, debt in enumerate(sorted_debts):
            milestone_month = min(time_estimate, (i + 1) * (time_estimate // len(sorted_debts)))
            milestone_date = date.today() + timedelta(days=milestone_month*30)
            milestone_dates[str(debt.id)] = milestone_date.isoformat()

        # Enhanced Indian-specific strategies
        primary_strategy_data = {
            "avalanche": {
                "name": "हिमस्खलन रणनीति: Indian Debt Avalanche Strategy",
                "description": "Mathematical optimization targeting highest interest Indian debt first (credit cards 40%+)",
                "benefits": [
                    f"Minimizes total interest by ₹{interest_saved:,.0f}",
                    "Fastest debt freedom with Indian context",
                    "Maximizes CIBIL score improvement for future loans",
                    "Optimal for Indian tax planning integration"
                ],
                "drawbacks": [
                    "Requires discipline typical of Indian professionals",
                    "May lack quick psychological wins in family context"
                ],
                "ideal_for": [
                    "Tech-savvy Indians comfortable with analytics",
                    "High interest rate variations (40% credit cards vs 8% home loans)",
                    "Strong motivation with family support system"
                ]
            },
            "snowball": {
                "name": "स्नोबॉल रणनीति: Indian Debt Snowball Strategy",
                "description": "Psychological momentum approach with Indian family celebration integration",
                "benefits": [
                    "Quick psychological wins for family motivation",
                    "Builds confidence in Indian cultural context",
                    "Festival milestone celebrations (Diwali goals)",
                    f"Still saves ₹{interest_saved * 0.8:,.0f} in interest"
                ],
                "drawbacks": [
                    "Higher total interest cost compared to avalanche",
                    "Slower mathematical optimization"
                ],
                "ideal_for": [
                    "Family-motivated Indians seeking social validation",
                    "Joint family decision making requirements",
                    "Festival-based goal setting culture"
                ]
            },
            "consolidation": {
                "name": "समेकन रणनीति: Indian Debt Consolidation Strategy",
                "description": "Single loan approach using Indian banking relationships for simplified management",
                "benefits": [
                    f"Reduces complexity from {len(debts)} payments to 1",
                    "Potential rate reduction through Indian bank relationships",
                    f"Saves ₹{interest_saved:,.0f} through optimized interest rates",
                    "Simplified EMI management aligned with salary cycles"
                ],
                "drawbacks": [
                    "Requires good CIBIL score (650+) for Indian bank approval",
                    "May extend overall payment timeline"
                ],
                "ideal_for": [
                    "Multiple high-interest debts across Indian banks",
                    "Strong banking relationships (salary account holders)",
                    "Preference for simplified payment management"
                ]
            }
        }

        current_strategy = primary_strategy_data.get(strategy, primary_strategy_data["avalanche"])

        return RepaymentPlan(
            strategy=strategy,
            monthly_payment_amount=monthly_payment,
            total_debt=total_debt,
            minimum_payment_sum=minimum_sum,
            time_to_debt_free=time_estimate,
            total_interest_saved=interest_saved,
            expected_completion_date=completion_date.isoformat(),
            debt_order=[str(debt.id) for debt in sorted_debts],
            milestone_dates=milestone_dates,
            monthly_breakdown=[],
            primary_strategy=OptimizationStrategy(
                name=current_strategy["name"],
                description=current_strategy["description"],
                benefits=current_strategy["benefits"],
                drawbacks=current_strategy["drawbacks"],
                ideal_for=current_strategy["ideal_for"],
                debt_order=[str(debt.id) for debt in sorted_debts],
                reasoning=f"{strategy.title()} method selected based on Indian debt portfolio characteristics and cultural context",
                estimated_savings=interest_saved,
                payoff_timeline=time_estimate
            ),
            alternative_strategies=[],
            key_insights=[
                f"Total debt of ₹{total_debt:,.0f} can be eliminated in {time_estimate} months with disciplined approach",
                f"Monthly payment of ₹{monthly_payment:,.0f} recommended (including bonus utilization)",
                f"Potential interest savings of ₹{interest_saved:,.0f} compared to minimum payments",
                f"CIBIL score improvement expected from 650+ to 750+ enabling future low-interest loans",
                f"Target completion by Diwali {completion_date.year} for cultural milestone celebration"
            ],
            action_items=[
                "Week 1: Setup UPI auto-pay and NEFT standing instructions for all EMIs",
                "Week 2: Consolidate banking relationships and activate mobile banking alerts",
                "Week 3: Contact relationship managers for interest rate negotiation opportunities",
                "Month 2: Redirect Diwali bonus and appraisal increments toward debt principal",
                "Month 3: Optimize monthly expenses - reduce dining out by ₹3,000, transport by ₹1,500",
                "Quarterly: Review progress and celebrate milestones with family (without overspending)"
            ],
            risk_factors=[
                "Variable Indian income cycles could affect payment consistency during economic changes",
                "Festival expenses (Diwali, weddings) might tempt budget deviations if not planned",
                "Family medical emergency expenses common in India could derail plan without emergency fund",
                "Rising RBI interest rates may impact refinancing options for existing loans",
                "Job market volatility in Indian IT/service sectors could affect income stability"
            ]
        )
