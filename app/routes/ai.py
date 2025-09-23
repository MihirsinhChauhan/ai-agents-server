"""
AI API endpoints for dashboard insights and recommendations.
Provides AI-powered analytics that work with frontend dashboard components.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from app.services.ai_service import AIService
from app.repositories.debt_repository import DebtRepository
from app.repositories.user_repository import UserRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.models.ai import (
    AIInsightsResponse,
    AIRecommendationResponse,
    DTIAnalysisResponse,
    DebtAnalysisResponse,
    AIInsightsRequest,
    AIErrorResponse,
    PaymentScenarioRequest,
    StrategyComparisonResponse,
    PaymentTimelineResponse,
    OptimizationMetricsResponse,
    SimulationResultsResponse,
    EnhancedAIInsightsResponse
)
from app.middleware.auth import CurrentUser
from app.models.user import UserInDB

# Dependency injection for repositories
def get_debt_repository() -> DebtRepository:
    """Get debt repository instance"""
    return DebtRepository()

def get_user_repository() -> UserRepository:
    """Get user repository instance"""
    return UserRepository()

def get_analytics_repository() -> AnalyticsRepository:
    """Get analytics repository instance"""
    return AnalyticsRepository()

# Dependency injection for AI service
async def get_ai_service(
    debt_repo: DebtRepository = Depends(get_debt_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    analytics_repo: AnalyticsRepository = Depends(get_analytics_repository)
) -> AIService:
    """Get AI service instance with dependencies"""
    return AIService(
        debt_repo=debt_repo,
        user_repo=user_repo,
        analytics_repo=analytics_repo
    )

router = APIRouter()


@router.get("/insights", response_model=AIInsightsResponse)
async def get_ai_insights(
    current_user: CurrentUser,
    monthly_payment_budget: Optional[float] = None,
    preferred_strategy: Optional[str] = None,
    include_dti: bool = True,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Get comprehensive AI insights for dashboard including:
    - Debt analysis
    - AI recommendations
    - DTI calculations
    - Repayment plan suggestions

    Query Parameters:
    - monthly_payment_budget: Optional preferred monthly payment amount
    - preferred_strategy: Optional strategy preference (avalanche/snowball)
    - include_dti: Whether to include DTI analysis (default: true)
    """
    try:
        # Validate inputs
        if monthly_payment_budget is not None and monthly_payment_budget <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payment budget must be greater than 0"
            )

        if preferred_strategy is not None and preferred_strategy not in ["avalanche", "snowball"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preferred strategy must be either 'avalanche' or 'snowball'"
            )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for analysis. Please add some debts first."
            )

        insights = await ai_service.get_ai_insights(
            user_id=current_user.id,
            monthly_payment_budget=monthly_payment_budget,
            preferred_strategy=preferred_strategy,
            include_dti=include_dti
        )

        return AIInsightsResponse(**insights)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate AI insights for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI insights. Please try again later."
        )


@router.post("/simulate", response_model=SimulationResultsResponse)
async def simulate_payment_scenarios(
    request: PaymentScenarioRequest,
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Simulate different payment scenarios for real-time "what-if" analysis.
    Allows users to test various monthly payment amounts and strategies.

    Request Body:
    - scenarios: List of scenarios to simulate, each containing monthly_payment, strategy, etc.
    """
    try:
        # Validate scenarios
        if not request.scenarios:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one scenario is required"
            )

        for i, scenario in enumerate(request.scenarios):
            if scenario.monthly_payment <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Scenario {i+1}: Monthly payment must be greater than 0"
                )

            if scenario.strategy not in ["avalanche", "snowball"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Scenario {i+1}: Strategy must be either 'avalanche' or 'snowball'"
                )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for simulation. Please add some debts first."
            )

        # Convert scenarios to dict format
        scenarios_dict = []
        for scenario in request.scenarios:
            scenario_dict = {
                "monthly_payment": scenario.monthly_payment,
                "strategy": scenario.strategy
            }
            if scenario.extra_payment_target:
                scenario_dict["extra_payment_target"] = scenario.extra_payment_target
            scenarios_dict.append(scenario_dict)

        results = await ai_service.simulate_payment_scenarios(
            user_id=current_user.id,
            scenarios=scenarios_dict
        )

        return SimulationResultsResponse(**results)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to simulate payment scenarios for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to simulate payment scenarios. Please try again later."
        )


@router.get("/strategies/compare", response_model=StrategyComparisonResponse)
async def compare_strategies(
    monthly_payment: float,
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Compare Avalanche vs Snowball strategies side-by-side.
    Shows detailed metrics for both strategies with the same monthly payment amount.

    Query Parameters:
    - monthly_payment: Monthly payment amount to use for comparison
    """
    try:
        # Validate input
        if monthly_payment <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payment must be greater than 0"
            )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for comparison. Please add some debts first."
            )

        comparison = await ai_service.compare_strategies(
            user_id=current_user.id,
            monthly_payment=monthly_payment
        )

        return StrategyComparisonResponse(**comparison)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to compare strategies for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare strategies. Please try again later."
        )


@router.get("/timeline", response_model=PaymentTimelineResponse)
async def get_payment_timeline(
    monthly_payment: float,
    current_user: CurrentUser,
    strategy: str = "avalanche",
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Generate detailed month-by-month payment timeline for a specific strategy.
    Shows how debts will be paid off over time.

    Query Parameters:
    - monthly_payment: Monthly payment amount
    - strategy: Payment strategy (avalanche or snowball, default: avalanche)
    """
    try:
        # Validate inputs
        if monthly_payment <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payment must be greater than 0"
            )

        if strategy not in ["avalanche", "snowball"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strategy must be either 'avalanche' or 'snowball'"
            )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for timeline generation. Please add some debts first."
            )

        timeline = await ai_service.generate_payment_timeline(
            user_id=current_user.id,
            monthly_payment=monthly_payment,
            strategy=strategy
        )

        return PaymentTimelineResponse(**timeline)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate payment timeline for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate payment timeline. Please try again later."
        )


@router.post("/optimize", response_model=OptimizationMetricsResponse)
async def calculate_optimization_metrics(
    request: dict,
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Calculate optimization metrics comparing current vs optimized strategies.
    Shows potential savings and improvements.

    Request Body:
    - current_strategy: Current payment strategy details (monthly_payment, strategy)
    - optimized_strategy: Optimized payment strategy details (monthly_payment, strategy)
    """
    try:
        # Extract strategies from request
        current_strategy = request.get("current_strategy", {})
        optimized_strategy = request.get("optimized_strategy", {})

        # Validate inputs
        required_fields = ["monthly_payment", "strategy"]

        for field in required_fields:
            if field not in current_strategy:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Current strategy missing required field: {field}"
                )
            if field not in optimized_strategy:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Optimized strategy missing required field: {field}"
                )

        if current_strategy["monthly_payment"] <= 0 or optimized_strategy["monthly_payment"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payments must be greater than 0"
            )

        for strategy in [current_strategy["strategy"], optimized_strategy["strategy"]]:
            if strategy not in ["avalanche", "snowball"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Strategy must be either 'avalanche' or 'snowball'"
                )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for optimization calculation. Please add some debts first."
            )

        metrics = await ai_service.calculate_optimization_metrics(
            user_id=current_user.id,
            current_strategy=current_strategy,
            optimized_strategy=optimized_strategy
        )

        return OptimizationMetricsResponse(**metrics)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to calculate optimization metrics for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate optimization metrics. Please try again later."
        )


@router.get("/recommendations", response_model=List[AIRecommendationResponse])
async def get_ai_recommendations(
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Get AI-generated recommendations for debt optimization strategies.
    Returns personalized suggestions based on user's debt profile.
    """
    try:
        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            return []  # Return empty list instead of error for recommendations

        recommendations = await ai_service.get_recommendations(user_id=current_user.id)
        return [AIRecommendationResponse(**rec) for rec in recommendations]

    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get AI recommendations for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get AI recommendations. Please try again later."
        )


@router.get("/dti", response_model=DTIAnalysisResponse)
async def get_dti_analysis(
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Calculate and return Debt-to-Income (DTI) ratios for the user.
    Includes both frontend DTI (housing only) and backend DTI (all debts).
    """
    try:
        # Check if user has monthly income set
        user_profile = await ai_service.user_repo.get_by_id(current_user.id)
        if not user_profile or not user_profile.monthly_income or user_profile.monthly_income <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly income is required for DTI calculation. Please update your profile."
            )

        dti_analysis = await ai_service.calculate_dti(user_id=current_user.id)

        # Check if there's an error in the analysis
        if "error" in dti_analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=dti_analysis["error"]
            )

        return DTIAnalysisResponse(**dti_analysis)

    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to calculate DTI for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate DTI. Please try again later."
        )


@router.get("/debt-summary", response_model=DebtAnalysisResponse)
async def get_debt_summary(
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Get debt summary statistics for dashboard widgets.
    Provides key metrics about user's debt portfolio.
    """
    try:
        summary = await ai_service.get_debt_summary(user_id=current_user.id)
        return DebtAnalysisResponse(**summary)

    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get debt summary for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get debt summary. Please try again later."
        )


@router.post("/insights", response_model=AIInsightsResponse)
async def generate_ai_insights(
    request: AIInsightsRequest,
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Generate fresh AI insights based on current debt data.
    Allows customization of analysis parameters.

    Request Body:
    - monthly_payment_budget: Optional preferred monthly payment amount
    - preferred_strategy: Optional strategy preference (avalanche/snowball)
    - include_dti: Whether to include DTI analysis (default: true)
    """
    try:
        # Validate inputs
        if request.monthly_payment_budget is not None and request.monthly_payment_budget <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payment budget must be greater than 0"
            )

        if request.preferred_strategy is not None and request.preferred_strategy not in ["avalanche", "snowball"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preferred strategy must be either 'avalanche' or 'snowball'"
            )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for analysis. Please add some debts first."
            )

        insights = await ai_service.get_ai_insights(
            user_id=current_user.id,
            monthly_payment_budget=request.monthly_payment_budget,
            preferred_strategy=request.preferred_strategy,
            include_dti=request.include_dti
        )

        return AIInsightsResponse(**insights)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate AI insights for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI insights. Please try again later."
        )


@router.post("/simulate", response_model=SimulationResultsResponse)
async def simulate_payment_scenarios(
    request: PaymentScenarioRequest,
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Simulate different payment scenarios for real-time "what-if" analysis.
    Allows users to test various monthly payment amounts and strategies.

    Request Body:
    - scenarios: List of scenarios to simulate, each containing monthly_payment, strategy, etc.
    """
    try:
        # Validate scenarios
        if not request.scenarios:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one scenario is required"
            )

        for i, scenario in enumerate(request.scenarios):
            if scenario.monthly_payment <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Scenario {i+1}: Monthly payment must be greater than 0"
                )

            if scenario.strategy not in ["avalanche", "snowball"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Scenario {i+1}: Strategy must be either 'avalanche' or 'snowball'"
                )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for simulation. Please add some debts first."
            )

        # Convert scenarios to dict format
        scenarios_dict = []
        for scenario in request.scenarios:
            scenario_dict = {
                "monthly_payment": scenario.monthly_payment,
                "strategy": scenario.strategy
            }
            if scenario.extra_payment_target:
                scenario_dict["extra_payment_target"] = scenario.extra_payment_target
            scenarios_dict.append(scenario_dict)

        results = await ai_service.simulate_payment_scenarios(
            user_id=current_user.id,
            scenarios=scenarios_dict
        )

        return SimulationResultsResponse(**results)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to simulate payment scenarios for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to simulate payment scenarios. Please try again later."
        )


@router.get("/strategies/compare", response_model=StrategyComparisonResponse)
async def compare_strategies(
    monthly_payment: float,
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Compare Avalanche vs Snowball strategies side-by-side.
    Shows detailed metrics for both strategies with the same monthly payment amount.

    Query Parameters:
    - monthly_payment: Monthly payment amount to use for comparison
    """
    try:
        # Validate input
        if monthly_payment <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payment must be greater than 0"
            )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for comparison. Please add some debts first."
            )

        comparison = await ai_service.compare_strategies(
            user_id=current_user.id,
            monthly_payment=monthly_payment
        )

        return StrategyComparisonResponse(**comparison)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to compare strategies for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare strategies. Please try again later."
        )


@router.get("/timeline", response_model=PaymentTimelineResponse)
async def get_payment_timeline(
    monthly_payment: float,
    current_user: CurrentUser,
    strategy: str = "avalanche",
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Generate detailed month-by-month payment timeline for a specific strategy.
    Shows how debts will be paid off over time.

    Query Parameters:
    - monthly_payment: Monthly payment amount
    - strategy: Payment strategy (avalanche or snowball, default: avalanche)
    """
    try:
        # Validate inputs
        if monthly_payment <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payment must be greater than 0"
            )

        if strategy not in ["avalanche", "snowball"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Strategy must be either 'avalanche' or 'snowball'"
            )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for timeline generation. Please add some debts first."
            )

        timeline = await ai_service.generate_payment_timeline(
            user_id=current_user.id,
            monthly_payment=monthly_payment,
            strategy=strategy
        )

        return PaymentTimelineResponse(**timeline)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate payment timeline for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate payment timeline. Please try again later."
        )


@router.post("/optimize", response_model=OptimizationMetricsResponse)
async def calculate_optimization_metrics(
    request: dict,
    current_user: CurrentUser,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Calculate optimization metrics comparing current vs optimized strategies.
    Shows potential savings and improvements.

    Request Body:
    - current_strategy: Current payment strategy details (monthly_payment, strategy)
    - optimized_strategy: Optimized payment strategy details (monthly_payment, strategy)
    """
    try:
        # Extract strategies from request
        current_strategy = request.get("current_strategy", {})
        optimized_strategy = request.get("optimized_strategy", {})

        # Validate inputs
        required_fields = ["monthly_payment", "strategy"]

        for field in required_fields:
            if field not in current_strategy:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Current strategy missing required field: {field}"
                )
            if field not in optimized_strategy:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Optimized strategy missing required field: {field}"
                )

        if current_strategy["monthly_payment"] <= 0 or optimized_strategy["monthly_payment"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payments must be greater than 0"
            )

        for strategy in [current_strategy["strategy"], optimized_strategy["strategy"]]:
            if strategy not in ["avalanche", "snowball"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Strategy must be either 'avalanche' or 'snowball'"
                )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for optimization calculation. Please add some debts first."
            )

        metrics = await ai_service.calculate_optimization_metrics(
            user_id=current_user.id,
            current_strategy=current_strategy,
            optimized_strategy=optimized_strategy
        )

        return OptimizationMetricsResponse(**metrics)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to calculate optimization metrics for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate optimization metrics. Please try again later."
        )


@router.get("/insights/enhanced")
async def get_enhanced_ai_insights(
    current_user: CurrentUser,
    monthly_payment_budget: Optional[float] = None,
    preferred_strategy: Optional[str] = None,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Get enhanced AI insights in the exact format expected by the frontend.
    This endpoint provides the complete AIInsightsData structure for the React components.

    Query Parameters:
    - monthly_payment_budget: Optional preferred monthly payment amount
    - preferred_strategy: Optional strategy preference (avalanche/snowball)
    """
    try:
        # Validate inputs
        if monthly_payment_budget is not None and monthly_payment_budget <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Monthly payment budget must be greater than 0"
            )

        if preferred_strategy is not None and preferred_strategy not in ["avalanche", "snowball"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preferred strategy must be either 'avalanche' or 'snowball'"
            )

        # Check if user has debts
        user_debts = await ai_service.debt_repo.get_debts_by_user_id(current_user.id)
        if not user_debts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No debts found for analysis. Please add some debts first."
            )

        insights = await ai_service.get_enhanced_ai_insights(
            user_id=current_user.id,
            monthly_payment_budget=monthly_payment_budget,
            preferred_strategy=preferred_strategy
        )

        # Return in the format expected by the frontend EnhancedInsightsResponse
        return {
            "insights": insights,
            "recommendations": insights.get("alternative_strategies", []),
            "dtiAnalysis": None  # Add DTI analysis if needed
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate enhanced AI insights for user {current_user.id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate enhanced AI insights. Please try again later."
        )
