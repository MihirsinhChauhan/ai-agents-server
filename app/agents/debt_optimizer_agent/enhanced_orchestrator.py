"""
Enhanced AI Agent Orchestrator for DebtEase.
Coordinates multiple AI agents and integrates with repository layer.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.debt import DebtInDB
from app.repositories.debt_repository import DebtRepository
from app.repositories.user_repository import UserRepository
from .enhanced_debt_analyzer import EnhancedDebtAnalyzer, DebtAnalysisResult
from .enhanced_debt_optimizer import EnhancedDebtOptimizer, RepaymentPlan
from .ai_recommendation_agent import AIRecommendationAgent, RecommendationSet
from .dti_calculator_agent import DTICalculatorAgent, DTIAnalysis

logger = logging.getLogger(__name__)


class AIOrchestrationResult(BaseModel):
    """Complete AI orchestration result."""
    
    # Analysis results
    debt_analysis: DebtAnalysisResult
    repayment_plan: RepaymentPlan
    recommendations: RecommendationSet
    dti_analysis: Optional[DTIAnalysis] = None
    
    # Metadata
    user_id: str
    processing_time: float
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        populate_by_name = True


class EnhancedAIOrchestrator:
    """
    Professional AI Debt Consultation Orchestrator.

    Coordinates multiple AI agents to provide comprehensive debt consultation services
    following proven methodologies from certified financial planners and debt counselors.

    Professional Consultation Workflow:
    1. Financial Health Assessment - Comprehensive debt and cash flow analysis
    2. Strategic Planning - Evidence-based strategy selection with behavioral considerations
    3. Implementation Planning - Detailed step-by-step action plans with timelines
    4. Risk Management - Scenario planning and contingency strategies
    5. Progress Monitoring - Success metrics and milestone tracking

    Integrates methodologies from:
    - Dave Ramsey (Debt Snowball, Emergency Fund Foundation)
    - Suze Orman (Hybrid Approach, Risk Assessment)
    - Mathematical Optimization (Debt Avalanche, Interest Rate Focus)
    - Behavioral Finance (Motivation, Habit Formation, Sustainability)
    """

    def __init__(self):
        """Initialize the professional consultation orchestrator with all specialized agents."""
        # Professional debt consultation agents
        self.debt_analyzer = EnhancedDebtAnalyzer()
        self.debt_optimizer = EnhancedDebtOptimizer()
        self.recommendation_agent = AIRecommendationAgent()
        self.dti_calculator = DTICalculatorAgent()

        # Data access repositories
        self.debt_repository = DebtRepository()
        self.user_repository = UserRepository()
    
    async def analyze_user_debts(
        self,
        user_id: UUID,
        monthly_payment_budget: Optional[float] = None,
        preferred_strategy: Optional[str] = None,
        include_dti: bool = True
    ) -> AIOrchestrationResult:
        """
        Perform comprehensive professional debt consultation analysis.

        Professional Consultation Process:
        1. Financial Health Assessment - Complete debt portfolio analysis
        2. Strategic Planning - Evidence-based strategy recommendation
        3. Implementation Planning - Detailed action plan with timelines
        4. Risk Assessment - Scenario planning and contingency strategies
        5. Progress Framework - Success metrics and monitoring system

        Args:
            user_id: Client's unique identifier
            monthly_payment_budget: Available debt service capacity
            preferred_strategy: Client's strategy preference (if any)
            include_dti: Include debt-to-income analysis for qualification assessment

        Returns:
            AIOrchestrationResult with professional consultation outcomes
        """
        start_time = datetime.now()

        try:
            logger.info(f"Initiating professional debt consultation for user {user_id}")

            # STAGE 1: FINANCIAL HEALTH ASSESSMENT
            debts = await self.debt_repository.get_by_user_id(user_id)

            if not debts:
                logger.info(f"No debts found for user {user_id} - providing wealth building guidance")
                return await self._create_debt_free_analysis(str(user_id), start_time)

            logger.info(f"Professional Analysis: Evaluating {len(debts)} debts for comprehensive consultation")

            # STAGE 2: COMPREHENSIVE DEBT ANALYSIS
            analysis = await self.debt_analyzer.analyze_debts(debts)
            logger.info("Professional Analysis: Financial health assessment completed")

            # STAGE 3: STRATEGIC REPAYMENT PLANNING
            repayment_plan = await self.debt_optimizer.optimize_repayment(
                debts=debts,
                analysis=analysis,
                monthly_payment_budget=monthly_payment_budget,
                preferred_strategy=preferred_strategy
            )
            logger.info("Professional Analysis: Strategic repayment plan developed")
            
            # STAGE 4: PROFESSIONAL RECOMMENDATION DEVELOPMENT
            user_profile = await self._get_user_profile(user_id)
            recommendations = await self.recommendation_agent.generate_recommendations(
                debts=debts,
                analysis=analysis,
                user_profile=user_profile
            )
            logger.info("Professional Analysis: Personalized recommendations developed")

            # STAGE 5: RISK ASSESSMENT & QUALIFICATION ANALYSIS
            dti_analysis = None
            if include_dti and user_profile and user_profile.get("monthly_income"):
                try:
                    dti_analysis = await self.dti_calculator.calculate_dti(
                        debts=debts,
                        monthly_income=user_profile["monthly_income"]
                    )
                    logger.info("Professional Analysis: Debt-to-income qualification assessment completed")
                except Exception as e:
                    logger.warning(f"DTI qualification analysis failed: {e}")

            # CONSULTATION COMPLETION
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Professional debt consultation completed in {processing_time:.2f} seconds")

            return AIOrchestrationResult(
                debt_analysis=analysis,
                repayment_plan=repayment_plan,
                recommendations=recommendations,
                dti_analysis=dti_analysis,
                user_id=str(user_id),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"AI orchestration failed for user {user_id}: {e}")
            raise
    
    def analyze_user_debts_sync(
        self,
        user_id: UUID,
        monthly_payment_budget: Optional[float] = None,
        preferred_strategy: Optional[str] = None,
        include_dti: bool = True
    ) -> AIOrchestrationResult:
        """
        Synchronous version of comprehensive AI analysis.
        
        Args:
            user_id: User's UUID
            monthly_payment_budget: Optional preferred monthly payment amount
            preferred_strategy: Optional preferred strategy
            include_dti: Whether to include DTI analysis
            
        Returns:
            AIOrchestrationResult with complete analysis
        """
        start_time = datetime.now()
        
        try:
            # Get user's debts from repository (sync version)
            debts = self.debt_repository.get_by_user_id_sync(user_id)
            
            if not debts:
                logger.info(f"No debts found for user {user_id}")
                # Return minimal analysis for debt-free user
                return self._create_debt_free_analysis_sync(str(user_id), start_time)
            
            logger.info(f"Analyzing {len(debts)} debts for user {user_id}")
            
            # Run debt analysis
            analysis = self.debt_analyzer.analyze_debts_sync(debts)
            logger.info("Debt analysis completed")
            
            # Generate repayment plan
            repayment_plan = self.debt_optimizer.optimize_repayment_sync(
                debts=debts,
                analysis=analysis,
                monthly_payment_budget=monthly_payment_budget,
                preferred_strategy=preferred_strategy
            )
            logger.info("Repayment optimization completed")
            
            # Generate AI recommendations
            user_profile = self._get_user_profile_sync(user_id)
            recommendations = self.recommendation_agent.generate_recommendations_sync(
                debts=debts,
                analysis=analysis,
                user_profile=user_profile
            )
            logger.info("AI recommendations generated")
            
            # Calculate DTI if requested and user has income data
            dti_analysis = None
            if include_dti and user_profile and user_profile.get("monthly_income"):
                try:
                    dti_analysis = self.dti_calculator.calculate_dti_sync(
                        debts=debts,
                        monthly_income=user_profile["monthly_income"]
                    )
                    logger.info("DTI analysis completed")
                except Exception as e:
                    logger.warning(f"DTI analysis failed: {e}")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AIOrchestrationResult(
                debt_analysis=analysis,
                repayment_plan=repayment_plan,
                recommendations=recommendations,
                dti_analysis=dti_analysis,
                user_id=str(user_id),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"AI orchestration failed for user {user_id}: {e}")
            raise
    
    async def analyze_specific_debts(
        self,
        debts: List[DebtInDB],
        monthly_income: Optional[float] = None,
        monthly_payment_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze specific debts without user repository lookup.
        
        Args:
            debts: List of debts to analyze
            monthly_income: Optional monthly income for DTI
            monthly_payment_budget: Optional payment budget
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Run debt analysis
            analysis = await self.debt_analyzer.analyze_debts(debts)
            
            # Generate repayment plan
            repayment_plan = await self.debt_optimizer.optimize_repayment(
                debts=debts,
                analysis=analysis,
                monthly_payment_budget=monthly_payment_budget
            )
            
            # Generate recommendations
            recommendations = await self.recommendation_agent.generate_recommendations(
                debts=debts,
                analysis=analysis
            )
            
            result = {
                "analysis": analysis.model_dump(),
                "repayment_plan": repayment_plan.model_dump(),
                "recommendations": recommendations.model_dump()
            }
            
            # Add DTI if income provided
            if monthly_income and monthly_income > 0:
                dti_analysis = await self.dti_calculator.calculate_dti(
                    debts=debts,
                    monthly_income=monthly_income
                )
                result["dti_analysis"] = dti_analysis.model_dump()
            
            return result
            
        except Exception as e:
            logger.error(f"Specific debt analysis failed: {e}")
            raise
    
    async def _get_user_profile(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user profile information."""
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user:
                return {
                    "monthly_income": user.monthly_income,
                    "email": user.email,
                    "full_name": user.full_name
                }
        except Exception as e:
            logger.warning(f"Could not get user profile for {user_id}: {e}")
        return None
    
    def _get_user_profile_sync(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Synchronous version of get user profile."""
        try:
            user = self.user_repository.get_by_id_sync(user_id)
            if user:
                return {
                    "monthly_income": user.monthly_income,
                    "email": user.email,
                    "full_name": user.full_name
                }
        except Exception as e:
            logger.warning(f"Could not get user profile for {user_id}: {e}")
        return None
    
    async def _create_debt_free_analysis(
        self,
        user_id: str,
        start_time: datetime
    ) -> AIOrchestrationResult:
        """Create professional wealth-building consultation for debt-free users."""
        logger.info(f"Professional Analysis: Providing wealth-building consultation for debt-free user {user_id}")

        # Create debt-free financial health analysis
        analysis = DebtAnalysisResult(
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
            recommended_focus_areas=[
                "Congratulations! You're debt-free and ready for wealth building.",
                "Focus on emergency fund completion (3-6 months expenses)",
                "Maximize retirement contributions and investment opportunities",
                "Explore advanced financial strategies for long-term wealth"
            ],
            risk_assessment="low"
        )
        
        # Create empty repayment plan
        repayment_plan = await self.debt_optimizer.optimize_repayment([], analysis)
        
        # Create recommendations for debt-free users
        recommendations = await self.recommendation_agent.generate_recommendations([], analysis)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AIOrchestrationResult(
            debt_analysis=analysis,
            repayment_plan=repayment_plan,
            recommendations=recommendations,
            user_id=user_id,
            processing_time=processing_time
        )
    
    def _create_debt_free_analysis_sync(
        self, 
        user_id: str, 
        start_time: datetime
    ) -> AIOrchestrationResult:
        """Synchronous version of debt-free analysis."""
        # Create empty analysis
        analysis = DebtAnalysisResult(
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
            recommended_focus_areas=["You're debt-free! Focus on building wealth."],
            risk_assessment="low"
        )
        
        # Create empty repayment plan
        repayment_plan = self.debt_optimizer.optimize_repayment_sync([], analysis)
        
        # Create recommendations for debt-free users
        recommendations = self.recommendation_agent.generate_recommendations_sync([], analysis)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AIOrchestrationResult(
            debt_analysis=analysis,
            repayment_plan=repayment_plan,
            recommendations=recommendations,
            user_id=user_id,
            processing_time=processing_time
        )
