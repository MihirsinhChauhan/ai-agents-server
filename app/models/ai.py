"""
AI-related Pydantic models for API responses
Ensures frontend compatibility with TypeScript interfaces
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class DebtAnalysisResponse(BaseModel):
    """Debt analysis results for dashboard"""
    total_debt: float
    debt_count: int
    average_interest_rate: float
    total_minimum_payments: float
    high_priority_count: int
    generated_at: str


class AIRecommendationResponse(BaseModel):
    """AI recommendation response model"""
    id: str
    user_id: str
    recommendation_type: str = Field(..., description="avalanche, snowball, refinance, etc.")
    title: str
    description: str
    potential_savings: Optional[float] = None
    priority_score: int = Field(default=0, ge=0, le=10)
    is_dismissed: bool = False
    created_at: Optional[str] = None


class DTIAnalysisResponse(BaseModel):
    """Debt-to-Income analysis response"""
    frontend_dti: float = Field(..., description="Housing costs only DTI ratio")
    backend_dti: float = Field(..., description="All debt payments DTI ratio")
    total_monthly_debt_payments: float
    monthly_income: float
    is_healthy: bool = Field(..., description="Whether DTI is in healthy range")


class RepaymentPlanResponse(BaseModel):
    """Repayment plan response model"""
    strategy: str = Field(..., description="avalanche, snowball, custom")
    monthly_payment_amount: float
    total_interest_saved: float
    expected_completion_date: Optional[str] = None
    debt_order: List[str] = Field(default_factory=list, description="Ordered list of debt IDs")
    payment_schedule: Dict[str, Any] = Field(default_factory=dict)


class AIMetadataResponse(BaseModel):
    """Metadata about AI processing"""
    processing_time: float
    fallback_used: bool
    errors: List[str] = Field(default_factory=list)
    generated_at: str


class AIInsightsResponse(BaseModel):
    """Complete AI insights response for dashboard"""
    debt_analysis: DebtAnalysisResponse
    recommendations: List[AIRecommendationResponse]
    dti_analysis: Optional[DTIAnalysisResponse] = None
    repayment_plan: Optional[RepaymentPlanResponse] = None
    metadata: AIMetadataResponse


class AIInsightsRequest(BaseModel):
    """Request model for AI insights generation"""
    monthly_payment_budget: Optional[float] = None
    preferred_strategy: Optional[str] = Field(None, description="avalanche or snowball")
    include_dti: bool = True


class AIErrorResponse(BaseModel):
    """Error response for AI operations"""
    error: str
    error_type: str = "ai_processing_error"
    details: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# New models for enhanced AI Insights functionality

class PaymentTimelineEntry(BaseModel):
    """Single entry in payment timeline"""
    month: int
    total_debt: float
    monthly_payment: float
    interest_paid: float
    principal_paid: float
    remaining_debts: int = 0


class StrategyDetails(BaseModel):
    """Details about a specific debt repayment strategy"""
    name: str
    time_to_debt_free: int = Field(..., description="Months to debt freedom")
    total_interest_paid: float
    total_amount_paid: float
    debt_free_date: str
    description: str
    payment_timeline: List[PaymentTimelineEntry] = Field(default_factory=list)


class ComparisonSummary(BaseModel):
    """Summary comparing two strategies"""
    time_difference_months: float
    interest_savings_avalanche: float
    psychological_benefit_snowball: bool
    recommended_strategy: str
    recommendation_reason: str


class OptimizationSavings(BaseModel):
    """Savings metrics from optimization"""
    time_months: float
    interest_amount: float
    percentage_improvement: float


class StrategyPlan(BaseModel):
    """Plan details for a strategy"""
    strategy: str
    monthly_payment: float
    time_to_debt_free: int
    total_interest_paid: float
    debt_free_date: str


class SingleScenario(BaseModel):
    """Single payment scenario for simulation"""
    monthly_payment: float
    strategy: str = Field(..., description="avalanche or snowball")
    extra_payment_target: Optional[str] = None


class PaymentScenarioRequest(BaseModel):
    """Request model for payment scenario simulation"""
    scenarios: List[SingleScenario]


class SimulationResult(BaseModel):
    """Result of a single scenario simulation"""
    scenario_id: int
    time_to_debt_free: int
    total_interest_paid: float
    total_amount_paid: float
    debt_free_date: str
    debts_paid_off_count: int
    payment_timeline: List[PaymentTimelineEntry]
    strategy_used: str
    monthly_payment_used: float
    valid: bool
    error: Optional[str] = None


class SimulationResultsResponse(BaseModel):
    """Response model for payment scenario simulation"""
    user_id: str
    simulation_results: List[SimulationResult]
    generated_at: str


class StrategyComparisonResponse(BaseModel):
    """Response model for strategy comparison"""
    user_id: str
    comparison_amount: float
    avalanche_strategy: StrategyDetails
    snowball_strategy: StrategyDetails
    comparison_summary: ComparisonSummary
    generated_at: str


class PaymentTimelineResponse(BaseModel):
    """Response model for payment timeline"""
    user_id: str
    strategy: str
    monthly_payment: float
    timeline: List[PaymentTimelineEntry]
    summary: Dict[str, Any]
    generated_at: str


class OptimizationMetricsResponse(BaseModel):
    """Response model for optimization metrics"""
    user_id: str
    current_plan: StrategyPlan
    optimized_plan: StrategyPlan
    optimization_savings: OptimizationSavings
    is_improvement: bool
    generated_at: str


# Enhanced AI Insights Response matching frontend expectations

class CurrentStrategy(BaseModel):
    """Current strategy details for AI Insights"""
    name: str
    time_to_debt_free: int
    total_interest_saved: float
    monthly_payment: float
    debt_free_date: str


class AlternativeStrategy(BaseModel):
    """Alternative strategy suggestion"""
    name: str
    time_to_debt_free: int
    total_interest_saved: float
    description: str


class SimulationResults(BaseModel):
    """Simulation results comparing original vs optimized plans"""
    original_plan: StrategyDetails
    optimized_plan: StrategyDetails
    savings: OptimizationSavings


class EnhancedAIInsightsResponse(BaseModel):
    """Enhanced AI insights response matching frontend TypeScript interface"""
    current_strategy: CurrentStrategy
    payment_timeline: List[PaymentTimelineEntry]
    alternative_strategies: List[AlternativeStrategy]
    simulation_results: SimulationResults
