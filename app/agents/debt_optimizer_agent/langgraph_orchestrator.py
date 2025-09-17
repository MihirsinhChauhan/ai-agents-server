"""
LangGraph-Based AI Orchestrator for DebtEase
Enhanced workflow orchestration using LangGraph for robust AI agent coordination
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.models.debt import DebtInDB
from app.repositories.debt_repository import DebtRepository
from app.repositories.user_repository import UserRepository
from .enhanced_debt_analyzer import EnhancedDebtAnalyzer, DebtAnalysisResult
from .enhanced_debt_optimizer import EnhancedDebtOptimizer, RepaymentPlan
from .ai_recommendation_agent import AIRecommendationAgent, RecommendationSet
from .dti_calculator_agent import DTICalculatorAgent, DTIAnalysis

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationState:
    """State object for LangGraph workflow"""
    user_id: str
    debts: List[DebtInDB] = None
    user_profile: Optional[Dict[str, Any]] = None

    # Analysis results
    debt_analysis: Optional[DebtAnalysisResult] = None
    recommendations: Optional[RecommendationSet] = None
    dti_analysis: Optional[Dict[str, Any]] = None  # Using dict for direct calculation
    repayment_plan: Optional[RepaymentPlan] = None

    # Workflow control
    include_dti: bool = True
    monthly_payment_budget: Optional[float] = None
    preferred_strategy: Optional[str] = None

    # Error handling
    errors: List[str] = None
    fallback_used: bool = False

    # Metadata
    start_time: datetime = None
    processing_time: float = 0.0


class WorkflowResult(BaseModel):
    """Final result from LangGraph workflow"""

    # Analysis results
    debt_analysis: DebtAnalysisResult
    recommendations: RecommendationSet
    dti_analysis: Optional[Dict[str, Any]] = None
    repayment_plan: Optional[RepaymentPlan] = None

    # Workflow metadata
    user_id: str
    processing_time: float
    fallback_used: bool
    errors: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        arbitrary_types_allowed = True


class DataIngestionNode:
    """Node for loading user data"""

    def __init__(self, debt_repo: DebtRepository, user_repo: UserRepository):
        self.debt_repo = debt_repo
        self.user_repo = user_repo

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        """Load user debts and profile"""
        try:
            logger.info(f"Loading data for user {state.user_id}")

            # Load debts
            user_uuid = UUID(state.user_id)
            debts = await self.debt_repo.get_by_user_id(user_uuid)

            # Load user profile
            user_profile = await self._get_user_profile(user_uuid)

            state.debts = debts or []
            state.user_profile = user_profile

            logger.info(f"Loaded {len(state.debts)} debts for user {state.user_id}")

        except Exception as e:
            logger.error(f"Data ingestion failed: {e}")
            state.errors.append(f"Data ingestion failed: {str(e)}")

        return state

    async def _get_user_profile(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        try:
            user = await self.user_repo.get_by_id(user_id)
            if user:
                return {
                    "monthly_income": user.monthly_income,
                    "email": user.email,
                    "full_name": user.full_name
                }
        except Exception as e:
            logger.warning(f"Could not get user profile: {e}")
        return None


class DebtAnalysisNode:
    """Node for debt analysis using EnhancedDebtAnalyzer"""

    def __init__(self, analyzer: EnhancedDebtAnalyzer):
        self.analyzer = analyzer

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        """Analyze user debts"""
        try:
            if not state.debts:
                logger.info("No debts to analyze")
                return state

            logger.info(f"Analyzing {len(state.debts)} debts")
            analysis = await self.analyzer.analyze_debts(state.debts)

            state.debt_analysis = analysis
            logger.info("Debt analysis completed")

        except Exception as e:
            logger.error(f"Debt analysis failed: {e}")
            state.errors.append(f"Debt analysis failed: {str(e)}")

        return state


class RecommendationNode:
    """Node for generating AI recommendations"""

    def __init__(self, recommender: AIRecommendationAgent):
        self.recommender = recommender

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        """Generate AI recommendations"""
        try:
            if not state.debts or not state.debt_analysis:
                logger.info("Skipping recommendations - no debts or analysis")
                return state

            logger.info("Generating AI recommendations")
            recommendations = await self.recommender.generate_recommendations(
                debts=state.debts,
                analysis=state.debt_analysis,
                user_profile=state.user_profile
            )

            state.recommendations = recommendations
            logger.info("AI recommendations generated")

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            state.errors.append(f"Recommendation generation failed: {str(e)}")

        return state


class DTICalculationNode:
    """Node for DTI calculation using direct calculation approach"""

    def __init__(self):
        # Direct calculation - no AI agent needed
        pass

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        """Calculate DTI using direct calculation"""
        try:
            if not state.include_dti or not state.debts or not state.user_profile:
                logger.info("Skipping DTI calculation")
                return state

            monthly_income = state.user_profile.get("monthly_income")
            if not monthly_income or monthly_income <= 0:
                logger.info("No valid income data for DTI calculation")
                return state

            logger.info("Calculating DTI using direct calculation")

            # Direct DTI calculation (more efficient than AI)
            dti_result = self._calculate_dti_direct(state.debts, monthly_income)
            state.dti_analysis = dti_result

            logger.info("DTI calculation completed")

        except Exception as e:
            logger.error(f"DTI calculation failed: {e}")
            state.errors.append(f"DTI calculation failed: {str(e)}")

        return state

    def _calculate_dti_direct(self, debts: List[DebtInDB], monthly_income: float) -> Dict[str, Any]:
        """Direct DTI calculation without AI"""
        # Calculate housing payments (home loans only)
        housing_payments = sum(
            debt.minimum_payment for debt in debts
            if debt.debt_type.value == "home_loan"
        )

        # Calculate total debt payments
        total_payments = sum(debt.minimum_payment for debt in debts)

        # Calculate DTI ratios
        frontend_dti = (housing_payments / monthly_income) * 100 if housing_payments > 0 else 0.0
        backend_dti = (total_payments / monthly_income) * 100

        # Health assessment
        is_healthy = frontend_dti <= 28.0 and backend_dti <= 36.0

        # Risk level
        if frontend_dti <= 28.0 and backend_dti <= 36.0:
            risk_level = "low"
        elif frontend_dti <= 31.0 and backend_dti <= 43.0:
            risk_level = "medium"
        elif frontend_dti <= 35.0 or backend_dti <= 50.0:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Debt breakdown by type
        debt_breakdown = {}
        for debt in debts:
            debt_type = debt.debt_type.value
            if debt_type not in debt_breakdown:
                debt_breakdown[debt_type] = 0.0
            debt_breakdown[debt_type] += debt.minimum_payment

        return {
            "frontend_dti": round(frontend_dti, 2),
            "backend_dti": round(backend_dti, 2),
            "total_monthly_debt_payments": round(total_payments, 2),
            "monthly_income": monthly_income,
            "housing_payments": round(housing_payments, 2),
            "non_housing_payments": round(total_payments - housing_payments, 2),
            "debt_breakdown": {k: round(v, 2) for k, v in debt_breakdown.items()},
            "is_healthy": is_healthy,
            "risk_level": risk_level,
            "key_insights": self._generate_dti_insights(frontend_dti, backend_dti, debt_breakdown, monthly_income),
            "improvement_suggestions": self._generate_dti_suggestions(frontend_dti, backend_dti),
            "target_frontend_dti": 28.0,
            "target_backend_dti": 36.0,
            "monthly_reduction_needed": self._calculate_reduction_needed(total_payments, monthly_income, backend_dti, 36.0),
            "income_increase_needed": self._calculate_income_increase_needed(total_payments, monthly_income, backend_dti, 36.0),
            "calculated_at": datetime.now().isoformat(),
            "calculation_method": "direct_calculation"
        }

    def _generate_dti_insights(self, frontend_dti: float, backend_dti: float,
                              debt_breakdown: Dict[str, float], income: float) -> List[str]:
        """Generate insights about DTI"""
        insights = []

        if frontend_dti > 28.0:
            insights.append(f"Frontend DTI of {frontend_dti:.1f}% exceeds healthy limit of 28.0%")
        if backend_dti > 36.0:
            insights.append(f"Backend DTI of {backend_dti:.1f}% exceeds healthy limit of 36.0%")

        if debt_breakdown:
            highest_type = max(debt_breakdown.items(), key=lambda x: x[1])
            percentage = (highest_type[1] / sum(debt_breakdown.values())) * 100
            insights.append(f"{highest_type[0].replace('_', ' ').title()} debts account for {percentage:.1f}% of total payments")
        total_payments = sum(debt_breakdown.values())
        utilization = (total_payments / income) * 100
        if utilization > 50:
            insights.append(f"Debt payments consume {utilization:.1f}% of income - consider debt reduction")
        return insights[:3]

    def _generate_dti_suggestions(self, frontend_dti: float, backend_dti: float) -> List[str]:
        """Generate DTI improvement suggestions"""
        suggestions = []

        if backend_dti > 36.0:
            suggestions.append("Consider debt consolidation to reduce monthly payments")

        if frontend_dti > 28.0:
            suggestions.append("Review housing expenses and consider refinancing options")

        if not suggestions:
            suggestions.append("Maintain current DTI levels - you're in a healthy range")

        return suggestions[:3]

    def _calculate_reduction_needed(self, total_payments: float, income: float,
                                   current_dti: float, target_dti: float) -> float:
        """Calculate monthly payment reduction needed"""
        if current_dti <= target_dti:
            return 0.0
        target_payments = (target_dti / 100) * income
        return max(0, total_payments - target_payments)

    def _calculate_income_increase_needed(self, total_payments: float, income: float,
                                         current_dti: float, target_dti: float) -> float:
        """Calculate monthly income increase needed"""
        if current_dti <= target_dti:
            return 0.0
        target_income = total_payments / (target_dti / 100)
        return max(0, target_income - income)


class RepaymentOptimizationNode:
    """Node for repayment plan optimization"""

    def __init__(self, optimizer: EnhancedDebtOptimizer):
        self.optimizer = optimizer

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        """Generate repayment optimization plan"""
        try:
            if not state.debts or not state.debt_analysis:
                logger.info("Skipping repayment optimization - no debts or analysis")
                return state

            logger.info("Optimizing repayment strategy")
            plan = await self.optimizer.optimize_repayment(
                debts=state.debts,
                analysis=state.debt_analysis,
                monthly_payment_budget=state.monthly_payment_budget,
                preferred_strategy=state.preferred_strategy
            )

            state.repayment_plan = plan
            logger.info("Repayment optimization completed")

        except Exception as e:
            logger.error(f"Repayment optimization failed: {e}")
            state.errors.append(f"Repayment optimization failed: {str(e)}")

        return state


class ResultCompilationNode:
    """Node for compiling final results"""

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        """Compile all results into final output"""
        try:
            # Calculate processing time
            if state.start_time:
                state.processing_time = (datetime.now() - state.start_time).total_seconds()

            logger.info(f"Workflow completed in {state.processing_time:.2f} seconds")

            # Check if any fallbacks were used
            state.fallback_used = len(state.errors) > 0

            if state.errors:
                logger.warning(f"Workflow completed with {len(state.errors)} errors")
                for error in state.errors:
                    logger.warning(f"  - {error}")

        except Exception as e:
            logger.error(f"Result compilation failed: {e}")
            state.errors.append(f"Result compilation failed: {str(e)}")

        return state


class LangGraphOrchestrator:
    """LangGraph-based orchestrator for AI agents"""

    def __init__(self):
        # Initialize components
        self.debt_repo = DebtRepository()
        self.user_repo = UserRepository()

        self.debt_analyzer = EnhancedDebtAnalyzer()
        self.recommender = AIRecommendationAgent()
        self.optimizer = EnhancedDebtOptimizer()

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""

        # Create nodes
        data_ingestion = DataIngestionNode(self.debt_repo, self.user_repo)
        debt_analysis = DebtAnalysisNode(self.debt_analyzer)
        recommendation = RecommendationNode(self.recommender)
        dti_calculation = DTICalculationNode()
        repayment_optimization = RepaymentOptimizationNode(self.optimizer)
        result_compilation = ResultCompilationNode()

        # Build graph
        workflow = StateGraph(OrchestrationState)

        # Add nodes
        workflow.add_node("data_ingestion", data_ingestion.run)
        workflow.add_node("debt_analysis", debt_analysis.run)
        workflow.add_node("recommendation", recommendation.run)
        workflow.add_node("dti_calculation", dti_calculation.run)
        workflow.add_node("repayment_optimization", repayment_optimization.run)
        workflow.add_node("result_compilation", result_compilation.run)

        # Define edges (workflow flow)
        workflow.set_entry_point("data_ingestion")

        workflow.add_edge("data_ingestion", "debt_analysis")
        workflow.add_edge("debt_analysis", "recommendation")
        workflow.add_edge("recommendation", "dti_calculation")
        workflow.add_edge("dti_calculation", "repayment_optimization")
        workflow.add_edge("repayment_optimization", "result_compilation")

        workflow.add_edge("result_compilation", END)

        return workflow.compile()

    async def analyze_user_debts(
        self,
        user_id: UUID,
        monthly_payment_budget: Optional[float] = None,
        preferred_strategy: Optional[str] = None,
        include_dti: bool = True
    ) -> WorkflowResult:
        """
        Run complete debt analysis workflow using LangGraph

        Args:
            user_id: User's UUID
            monthly_payment_budget: Optional preferred monthly payment amount
            preferred_strategy: Optional preferred strategy
            include_dti: Whether to include DTI analysis

        Returns:
            WorkflowResult with complete analysis
        """
        # Initialize state
        initial_state = OrchestrationState(
            user_id=str(user_id),
            include_dti=include_dti,
            monthly_payment_budget=monthly_payment_budget,
            preferred_strategy=preferred_strategy,
            start_time=datetime.now(),
            errors=[]
        )

        try:
            logger.info(f"Starting LangGraph workflow for user {user_id}")

            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)

            # Convert to result format
            result = self._convert_to_workflow_result(final_state)

            logger.info(f"LangGraph workflow completed for user {user_id}")
            return result

        except Exception as e:
            logger.error(f"LangGraph workflow failed for user {user_id}: {e}")

            # Return minimal result on failure
            return WorkflowResult(
                debt_analysis=DebtAnalysisResult(
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
                    recommended_focus_areas=["Analysis failed - please try again"],
                    risk_assessment="unknown"
                ),
                recommendations=RecommendationSet(
                    recommendations=[],
                    overall_strategy="error_recovery",
                    priority_order=[],
                    estimated_impact={"error": True},
                    generated_at=datetime.now().isoformat()
                ),
                user_id=str(user_id),
                processing_time=final_state.processing_time if 'final_state' in locals() else 0.0,
                fallback_used=True,
                errors=[str(e)]
            )

    def _convert_to_workflow_result(self, state: OrchestrationState) -> WorkflowResult:
        """Convert final state to WorkflowResult"""
        return WorkflowResult(
            debt_analysis=state.debt_analysis,
            recommendations=state.recommendations,
            dti_analysis=state.dti_analysis,
            repayment_plan=state.repayment_plan,
            user_id=state.user_id,
            processing_time=state.processing_time,
            fallback_used=state.fallback_used,
            errors=state.errors or []
        )

    async def get_workflow_status(self, user_id: str) -> Dict[str, Any]:
        """Get current workflow status for monitoring"""
        # This would be enhanced with actual workflow state tracking
        return {
            "user_id": user_id,
            "status": "completed",  # In a real implementation, this would track actual state
            "last_updated": datetime.now().isoformat()
        }
