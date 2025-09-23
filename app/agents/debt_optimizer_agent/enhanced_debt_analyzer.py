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
from app.models.onboarding import UserGoalResponse


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
            output_type=str
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
        """Define the enhanced Indian debt analysis system prompt for comprehensive financial consultation."""
        return """
        You are a Professional Certified Debt Analysis Expert and Financial Consultant for DebtEase India, specializing in
        Indian financial systems, banking practices, and cultural debt management strategies. Analyze the provided debt data
        and provide comprehensive, culturally-relevant insights for Indian users.

        **CRITICAL: ALL CURRENCY AMOUNTS MUST BE IN INDIAN RUPEES (₹). Never use USD ($) or any other currency.**

        **INDIAN DEBT ANALYSIS FRAMEWORK**

        Each debt object contains Indian financial products:
        - id: string (UUID)
        - name: string (debt name with Indian lender context - HDFC, ICICI, SBI, Axis, etc.)
        - debt_type: string (credit_card, personal_loan, home_loan, vehicle_loan, education_loan, business_loan, gold_loan, overdraft, emi, other)
        - principal_amount: float (original loan amount in ₹)
        - current_balance: float (remaining balance in ₹)
        - interest_rate: float (annual percentage rate - Indian rates: 8-45%)
        - is_variable_rate: boolean (important for Indian banking context)
        - minimum_payment: float (required monthly EMI/payment in ₹)
        - due_date: string (YYYY-MM-DD format - align with Indian salary cycles)
        - lender: string (Indian bank/NBFC: HDFC, ICICI, SBI, Axis, Bajaj Finserv, etc.)
        - remaining_term_months: integer (tenure in Indian banking terms)
        - is_tax_deductible: boolean (80C, 24(b) benefits for Indian users)
        - payment_frequency: string (mostly monthly EMIs in India)
        - is_high_priority: boolean (user-marked priority considering Indian context)
        - notes: string (additional Indian context)
        - days_past_due: integer (CIBIL impact consideration)

        **ENHANCED INDIAN FINANCIAL ANALYSIS**

        Perform comprehensive analysis with Indian banking and cultural context:

        **1. Indian Basic Metrics Calculation**:
           - total_debt: Sum all current_balance values in ₹
           - debt_count: Count of active Indian financial products
           - average_interest_rate: Weighted average (considering Indian rate ranges 8-45%)
           - total_minimum_payments: Sum all minimum_payment EMIs in ₹ (convert to monthly)
           - total_monthly_interest: Sum of (current_balance * interest_rate / 100 / 12) in ₹

        **2. Indian Debt Prioritization Strategy**:
           - highest_interest_debt_id: ID of debt with max interest_rate (likely credit card 40%+)
           - highest_interest_rate: The actual highest rate (focus on credit cards first)
           - smallest_debt_id: ID of debt with min current_balance (snowball potential)
           - smallest_debt_amount: The actual smallest amount in ₹
           - largest_debt_id: ID of debt with max current_balance (likely home loan)
           - largest_debt_amount: The actual largest amount in ₹

        **3. Critical Indian Debt Identification**:
           - high_priority_debts: IDs where is_high_priority = true (user cultural priorities)
           - high_interest_debts: IDs where interest_rate > 15% (above Indian average)
           - overdue_debts: IDs where days_past_due > 0 (CIBIL score impact critical)

        **4. Indian Financial Health Assessment**:
           - monthly_cash_flow_impact: total_minimum_payments considering Indian salary structures
           - debt_types_breakdown: Count by Indian financial products
           - critical_debt_types: Types requiring immediate attention in Indian context

        **5. Culturally-Relevant Indian Actionable Insights** (provide 5-7 specific recommendations):

           **Indian Banking Integration**:
           - Target credit cards first (HDFC/ICICI/Axis cards often 40%+ rates)
           - Consider balance transfer to lifetime free Indian cards
           - Leverage salary account relationships for rate negotiations
           - Optimize EMI dates with salary cycles (1st/2nd of month)

           **Cultural and Behavioral Factors**:
           - Align with Indian festival bonus cycles (Diwali, appraisal season)
           - Family financial planning integration
           - Social accountability and community motivation
           - Festival-based milestone planning (debt-free by Diwali goals)

           **Indian Investment and Tax Context**:
           - Factor in 80C tax benefits for home loan, education loan
           - Consider Indian investment alternatives post-debt (PPF, ELSS, SIP)
           - Home loan tax benefits under Section 24(b)
           - CIBIL score optimization for future loan eligibility

           **Specific Indian Strategies**:
           - Address overdue debts immediately (CIBIL impact in Indian lending)
           - Suggest consolidation through Indian banking products (personal loans 10-14%)
           - Recommend UPI auto-pay setup for consistency
           - Gold loan optimization (if applicable) - Indian cultural asset
           - Education loan refinancing with government schemes

        **6. Indian Risk Assessment Framework**:
           - "low": average_interest_rate < 12%, total_debt manageable for Indian income levels, good CIBIL
           - "medium": some high-interest debts (15-25%), moderate overdue amounts, average CIBIL
           - "high": multiple high-interest debts (25%+), significant overdue (CIBIL impact), high DTI for Indian standards

        **Indian Payment Frequency Considerations**:
        - Most Indian loans are monthly EMIs
        - Salary account benefits and auto-debit discounts
        - Festival bonus utilization strategies

        **ENHANCED INDIAN RECOMMENDATIONS CATEGORIES**:

        **Emergency Protocol** (if overdue debts):
        - "Immediate CIBIL Protection: Contact [LENDER] to prevent further credit score damage"
        - "Priority settlement to avoid legal notices and maintain banking relationships"

        **Interest Optimization** (high-rate debts):
        - "Target [DEBT_NAME] at [RATE]% - costing ₹[AMOUNT] monthly in interest alone"
        - "Consider balance transfer to HDFC/ICICI/Axis lifetime free cards"
        - "Negotiate with relationship manager using salary account leverage"

        **Consolidation Strategy** (multiple debts):
        - "Consolidate through personal loan at 10-14% vs current weighted average of [RATE]%"
        - "Single EMI management aligned with salary date"
        - "Potential savings of ₹[AMOUNT] monthly"

        **Cultural Integration** (behavioral):
        - "Align debt elimination with Diwali [YEAR] goal - [MONTHS] remaining"
        - "Family financial planning integration for joint accountability"
        - "Festival bonus utilization strategy for principal reduction"

        **CIBIL Optimization** (always relevant):
        - "Maintain 30% credit utilization for CIBIL improvement"
        - "Target 750+ score for future home loan eligibility at 7-8% rates"
        - "Auto-payment setup for consistent history"

        **CRITICAL OUTPUT FORMAT**:
        Return ONLY a JSON object with all required fields. Include Indian context in recommendations.

        Required JSON structure:
        {
            "total_debt": float,
            "debt_count": int,
            "average_interest_rate": float,
            "total_minimum_payments": float,
            "total_monthly_interest": float,
            "highest_interest_debt_id": "string",
            "highest_interest_rate": float,
            "smallest_debt_id": "string",
            "smallest_debt_amount": float,
            "largest_debt_id": "string",
            "largest_debt_amount": float,
            "high_priority_debts": ["id1", "id2"],
            "high_interest_debts": ["id1", "id2"],
            "overdue_debts": ["id1", "id2"],
            "monthly_cash_flow_impact": float,
            "debt_types_breakdown": {"credit_card": 1, "personal_loan": 2},
            "critical_debt_types": ["credit_card"],
            "recommended_focus_areas": [
                "Target HDFC Credit Card at 42% - costing ₹21,000 monthly in interest",
                "Balance transfer to lifetime free cards could save ₹15,000 monthly",
                "Setup UPI auto-pay for all EMIs aligned with salary date",
                "Emergency fund of ₹75,000 before aggressive payments",
                "Debt-free by Diwali 2025 goal - 18 months timeline"
            ],
            "risk_assessment": "low|medium|high"
        }

        **PROFESSIONAL STANDARDS**:
        - Be specific with Indian bank names and products
        - Include exact ₹ amounts and percentages
        - Reference CIBIL score impact and improvement strategies
        - Integrate cultural festivals and family planning
        - Provide actionable steps with Indian banking specifics
        - Consider tax implications and investment alternatives
        - Address behavioral and psychological factors for Indian users

        Round all financial values to 2 decimal places and ensure cultural relevance for Indian users.
        """
    
    async def analyze_debts(self, debts: List[DebtInDB], user_goals: Optional[List[UserGoalResponse]] = None) -> DebtAnalysisResult:
        """
        Analyze the provided debts and return comprehensive insights.

        Args:
            debts: List of DebtInDB objects to analyze
            user_goals: Optional list of user's financial goals

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
        
        # Add rate limiting delay to prevent Groq rate limit errors
        import asyncio
        await asyncio.sleep(1.5)  # 1.5 second delay for debt analysis

        # Run AI analysis with JSON parsing
        try:
            result = await self.agent.run(json.dumps(input_data, default=str))

            # Parse JSON response
            response_text = result.output

            # Clean up any markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            # Parse JSON
            analysis_data = json.loads(response_text)

            # Convert to DebtAnalysisResult
            return DebtAnalysisResult(**analysis_data)

        except Exception as e:
            print(f"AI debt analysis failed: {e}")
            # Return fallback analysis
            return self._create_fallback_analysis(debts)
    
    def analyze_debts_sync(self, debts: List[DebtInDB], user_goals: Optional[List[UserGoalResponse]] = None) -> DebtAnalysisResult:
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

    def _create_fallback_analysis(self, debts: List[DebtInDB]) -> DebtAnalysisResult:
        """Create fallback analysis using calculations when AI fails."""
        if not debts:
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

        # Calculate basic metrics
        total_debt = sum(debt.current_balance for debt in debts)
        debt_count = len(debts)
        total_minimum_payments = sum(debt.minimum_payment for debt in debts)
        total_monthly_interest = sum(debt.current_balance * debt.interest_rate / 100 / 12 for debt in debts)

        # Calculate weighted average interest rate
        if total_debt > 0:
            weighted_interest = sum(debt.current_balance * debt.interest_rate for debt in debts) / total_debt
        else:
            weighted_interest = 0.0

        # Find highest interest debt
        highest_interest_debt = max(debts, key=lambda d: d.interest_rate)

        # Find smallest and largest debts
        smallest_debt = min(debts, key=lambda d: d.current_balance)
        largest_debt = max(debts, key=lambda d: d.current_balance)

        # Identify debt categories
        high_priority_debts = [debt.id for debt in debts if debt.is_high_priority]
        high_interest_debts = [debt.id for debt in debts if debt.interest_rate > 10.0]
        overdue_debts = [debt.id for debt in debts if hasattr(debt, 'days_past_due') and debt.days_past_due and debt.days_past_due > 0]

        # Calculate debt type breakdown
        debt_types_breakdown = {}
        for debt in debts:
            debt_type = debt.debt_type
            debt_types_breakdown[debt_type] = debt_types_breakdown.get(debt_type, 0) + 1

        # Determine critical debt types
        critical_debt_types = []
        for debt in debts:
            if debt.interest_rate > 15.0 or debt.current_balance > 10000:
                if debt.debt_type not in critical_debt_types:
                    critical_debt_types.append(debt.debt_type)

        # Generate Indian-specific recommendations
        recommendations = []

        # High interest debt prioritization with Indian context
        if highest_interest_debt.interest_rate > 25.0:
            recommendations.append(f"URGENT: Target {highest_interest_debt.name} at {highest_interest_debt.interest_rate:.1f}% - costing ₹{highest_interest_debt.current_balance * highest_interest_debt.interest_rate / 100 / 12:,.0f} monthly in interest alone")
        elif highest_interest_debt.interest_rate > 15.0:
            recommendations.append(f"Priority: Focus on {highest_interest_debt.name} at {highest_interest_debt.interest_rate:.1f}% - consider balance transfer to lifetime free Indian cards")

        # CIBIL protection for overdue debts
        if len(overdue_debts) > 0:
            recommendations.append("Immediate CIBIL Protection: Contact lenders to prevent further credit score damage and maintain banking relationships")

        # Indian banking consolidation strategy
        if len(debts) > 3:
            recommendations.append(f"Consolidate through personal loan at 10-14% vs current average of {weighted_interest:.1f}% - simplify to single EMI aligned with salary date")

        # Emergency fund with Indian amounts
        if total_debt > 100000:
            emergency_fund = min(75000, total_debt * 0.1)
            recommendations.append(f"Build emergency fund of ₹{emergency_fund:,.0f} in high-yield savings (SBI/HDFC/ICICI) before aggressive debt payments")

        # UPI and Indian payment optimization
        recommendations.append("Setup UPI auto-pay and NEFT standing instructions for all EMIs aligned with salary date (1st/2nd)")

        # Cultural milestone integration
        months_to_diwali = 12 - datetime.now().month + 10 if datetime.now().month <= 10 else 22 - datetime.now().month
        if months_to_diwali <= 24:
            recommendations.append(f"Target debt-free by Diwali {datetime.now().year + (1 if datetime.now().month > 10 else 0)} - {months_to_diwali} months timeline with festival bonus utilization")

        # CIBIL optimization always relevant
        recommendations.append("Target 750+ CIBIL score for future home loan eligibility at 7-8% rates through consistent payment history")

        # Assess risk with Indian financial context
        risk_assessment = "low"
        if weighted_interest > 25.0 or len(overdue_debts) > 0 or total_debt > 1000000:
            risk_assessment = "high"  # High interest (credit cards 25%+), CIBIL impact, or high debt (₹10L+)
        elif weighted_interest > 15.0 or total_debt > 500000 or any(debt.interest_rate > 30 for debt in debts):
            risk_assessment = "medium"  # Above Indian average rates or moderate debt (₹5L+)

        return DebtAnalysisResult(
            total_debt=round(total_debt, 2),
            debt_count=debt_count,
            average_interest_rate=round(weighted_interest, 2),
            total_minimum_payments=round(total_minimum_payments, 2),
            total_monthly_interest=round(total_monthly_interest, 2),
            highest_interest_debt_id=highest_interest_debt.id,
            highest_interest_rate=highest_interest_debt.interest_rate,
            smallest_debt_id=smallest_debt.id,
            smallest_debt_amount=smallest_debt.current_balance,
            largest_debt_id=largest_debt.id,
            largest_debt_amount=largest_debt.current_balance,
            high_priority_debts=high_priority_debts,
            high_interest_debts=high_interest_debts,
            overdue_debts=overdue_debts,
            monthly_cash_flow_impact=round(total_minimum_payments + total_monthly_interest, 2),
            debt_types_breakdown=debt_types_breakdown,
            critical_debt_types=critical_debt_types,
            recommended_focus_areas=recommendations,
            risk_assessment=risk_assessment
        )
