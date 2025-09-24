"""
Tests for AI agents and LangGraph orchestration.
Tests AI functionality, recommendations, and agent responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.agents.debt_optimizer_agent.langgraph_orchestrator import (
    LangGraphOrchestrator,
    WorkflowResult,
    OrchestrationState
)
from app.agents.debt_optimizer_agent.enhanced_debt_analyzer import (
    EnhancedDebtAnalyzer,
    DebtAnalysisResult
)
from app.agents.debt_optimizer_agent.enhanced_debt_optimizer import (
    EnhancedDebtOptimizer,
    RepaymentPlan
)
from app.agents.debt_optimizer_agent.ai_recommendation_agent import (
    AIRecommendationAgent,
    RecommendationSet
)
from app.models.debt import DebtInDB, DebtType, PaymentFrequency


@pytest.mark.ai
class TestDebtAnalyzerAgent:
    """Test the Enhanced Debt Analyzer agent."""

    def setup_method(self):
        """Setup test fixtures."""
        self.analyzer = EnhancedDebtAnalyzer()

    @patch('app.agents.debt_optimizer_agent.enhanced_debt_analyzer.logger')
    async def test_analyze_debts_basic(self, mock_logger):
        """Test basic debt analysis functionality."""
        # Create mock debts
        mock_debts = [
            DebtInDB(
                id=uuid4(),
                user_id=uuid4(),
                name="Credit Card",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=5000.0,
                current_balance=3000.0,
                interest_rate=18.99,
                minimum_payment=150.0,
                due_date="2025-02-15",
                lender="Test Bank",
                payment_frequency=PaymentFrequency.MONTHLY
            ),
            DebtInDB(
                id=uuid4(),
                user_id=uuid4(),
                name="Personal Loan",
                debt_type=DebtType.PERSONAL_LOAN,
                principal_amount=10000.0,
                current_balance=8000.0,
                interest_rate=12.5,
                minimum_payment=250.0,
                due_date="2025-03-01",
                lender="Test Lender",
                payment_frequency=PaymentFrequency.MONTHLY
            )
        ]

        result = await self.analyzer.analyze_debts(mock_debts)

        assert isinstance(result, DebtAnalysisResult)
        assert result.total_debt == 11000.0  # 3000 + 8000
        assert result.debt_count == 2
        assert result.average_interest_rate > 0
        assert result.total_minimum_payments == 400.0  # 150 + 250

    async def test_analyze_empty_debts(self):
        """Test debt analysis with empty debt list."""
        result = await self.analyzer.analyze_debts([])

        assert isinstance(result, DebtAnalysisResult)
        assert result.total_debt == 0
        assert result.debt_count == 0
        assert result.average_interest_rate == 0
        assert result.total_minimum_payments == 0

    async def test_analyze_high_interest_debts(self):
        """Test analysis of high-interest debts."""
        high_interest_debts = [
            DebtInDB(
                id=uuid4(),
                user_id=uuid4(),
                name="High Interest Card",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=5000.0,
                current_balance=4000.0,
                interest_rate=24.99,  # Very high
                minimum_payment=200.0,
                due_date="2025-02-15",
                lender="High Rate Bank",
                payment_frequency=PaymentFrequency.MONTHLY
            )
        ]

        result = await self.analyzer.analyze_debts(high_interest_debts)

        assert result.average_interest_rate == 24.99
        assert result.total_minimum_payments == 200.0


@pytest.mark.ai
class TestRecommendationAgent:
    """Test the AI Recommendation Agent."""

    def setup_method(self):
        """Setup test fixtures."""
        self.recommender = AIRecommendationAgent()

    async def test_generate_recommendations_basic(self):
        """Test basic recommendation generation."""
        mock_debts = [
            DebtInDB(
                id=uuid4(),
                user_id=uuid4(),
                name="High Rate Card",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=5000.0,
                current_balance=4000.0,
                interest_rate=22.99,
                minimum_payment=200.0,
                due_date="2025-02-15",
                lender="Expensive Bank",
                payment_frequency=PaymentFrequency.MONTHLY
            )
        ]

        mock_analysis = DebtAnalysisResult(
            total_debt=4000.0,
            debt_count=1,
            average_interest_rate=22.99,
            total_minimum_payments=200.0
        )

        recommendations = await self.recommender.generate_recommendations(mock_debts, mock_analysis)

        assert isinstance(recommendations, RecommendationSet)
        assert len(recommendations.recommendations) > 0

        # Should include avalanche recommendation for high interest debt
        rec_types = [rec.recommendation_type for rec in recommendations.recommendations]
        assert "avalanche" in rec_types

    async def test_generate_recommendations_multiple_strategies(self):
        """Test recommendations for different debt scenarios."""
        # Create diverse debt portfolio
        mock_debts = [
            DebtInDB(  # High interest credit card
                id=uuid4(),
                user_id=uuid4(),
                name="High Rate Card",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=5000.0,
                current_balance=4000.0,
                interest_rate=22.99,
                minimum_payment=200.0,
                due_date="2025-02-15",
                lender="Expensive Bank",
                payment_frequency=PaymentFrequency.MONTHLY
            ),
            DebtInDB(  # Student loan
                id=uuid4(),
                user_id=uuid4(),
                name="Student Loan",
                debt_type=DebtType.EDUCATION_LOAN,
                principal_amount=20000.0,
                current_balance=18000.0,
                interest_rate=4.5,
                minimum_payment=150.0,
                due_date="2025-03-01",
                lender="Federal Student Aid",
                payment_frequency=PaymentFrequency.MONTHLY
            ),
            DebtInDB(  # Low interest personal loan
                id=uuid4(),
                user_id=uuid4(),
                name="Personal Loan",
                debt_type=DebtType.PERSONAL_LOAN,
                principal_amount=5000.0,
                current_balance=2000.0,
                interest_rate=8.5,
                minimum_payment=100.0,
                due_date="2025-03-15",
                lender="Local Bank",
                payment_frequency=PaymentFrequency.MONTHLY
            )
        ]

        mock_analysis = DebtAnalysisResult(
            total_debt=24000.0,
            debt_count=3,
            average_interest_rate=11.996666666666666,
            total_minimum_payments=450.0
        )

        recommendations = await self.recommender.generate_recommendations(mock_debts, mock_analysis)

        assert isinstance(recommendations, RecommendationSet)
        assert len(recommendations.recommendations) >= 1

        # Should include multiple recommendation types
        rec_types = [rec.recommendation_type for rec in recommendations.recommendations]
        assert "avalanche" in rec_types  # For high interest debt


@pytest.mark.ai
class TestLangGraphOrchestrator:
    """Test the LangGraph Orchestrator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.orchestrator = LangGraphOrchestrator()

    @patch('app.agents.debt_optimizer_agent.langgraph_orchestrator.logger')
    async def test_analyze_user_debts_workflow(self, mock_logger):
        """Test the complete debt analysis workflow."""
        user_id = uuid4()

        # Mock the workflow execution
        mock_result = WorkflowResult(
            debt_analysis=DebtAnalysisResult(
                total_debt=10000.0,
                debt_count=2,
                average_interest_rate=15.5,
                total_minimum_payments=300.0
            ),
            recommendations=RecommendationSet(recommendations=[]),
            dti_analysis=None,
            repayment_plan=None,
            user_id=str(user_id),
            processing_time=1.5,
            fallback_used=False,
            errors=[]
        )

        with patch.object(self.orchestrator, 'workflow') as mock_workflow:
            mock_workflow.ainvoke.return_value = OrchestrationState(
                user_id=str(user_id),
                debt_analysis=mock_result.debt_analysis,
                recommendations=mock_result.recommendations,
                dti_analysis=mock_result.dti_analysis,
                repayment_plan=mock_result.repayment_plan,
                processing_time=mock_result.processing_time,
                fallback_used=mock_result.fallback_used,
                errors=mock_result.errors
            )

            result = await self.orchestrator.analyze_user_debts(user_id)

            assert isinstance(result, WorkflowResult)
            assert result.user_id == str(user_id)
            assert result.debt_analysis.total_debt == 10000.0
            assert result.processing_time == 1.5

    async def test_workflow_error_handling(self):
        """Test workflow error handling."""
        user_id = uuid4()

        # Mock workflow failure
        with patch.object(self.orchestrator, 'workflow') as mock_workflow:
            mock_workflow.ainvoke.side_effect = Exception("Workflow failed")

            result = await self.orchestrator.analyze_user_debts(user_id)

            # Should return fallback result
            assert isinstance(result, WorkflowResult)
            assert result.fallback_used is True
            assert len(result.errors) > 0

    async def test_workflow_status_check(self):
        """Test workflow status checking."""
        user_id = uuid4()

        status = await self.orchestrator.get_workflow_status(str(user_id))

        assert isinstance(status, dict)
        assert "status" in status
        assert "user_id" in status


@pytest.mark.ai
@pytest.mark.slow
class TestAIAgentIntegration:
    """Integration tests for AI agents working together."""

    async def test_complete_ai_workflow(self, ai_agent_config):
        """Test complete AI workflow with real agents."""
        # This is a slow test that actually calls AI models
        # Only run when explicitly requested
        pytest.skip("Skipping slow AI integration test")

        orchestrator = LangGraphOrchestrator()

        # Create test user and debts in database
        # This would require setting up real database state
        # For now, just test the orchestration setup

        user_id = uuid4()

        # Mock the workflow to return a real result
        with patch.object(orchestrator, 'workflow') as mock_workflow:
            mock_workflow.ainvoke.return_value = OrchestrationState(
                user_id=str(user_id),
                debt_analysis=DebtAnalysisResult(
                    total_debt=15000.0,
                    debt_count=3,
                    average_interest_rate=12.5,
                    total_minimum_payments=450.0
                ),
                recommendations=RecommendationSet(recommendations=[]),
                processing_time=2.1
            )

            result = await orchestrator.analyze_user_debts(user_id)

            assert result.debt_analysis.total_debt == 15000.0
            assert result.debt_analysis.debt_count == 3
            assert result.processing_time >= 0


@pytest.mark.ai
class TestAIPerformance:
    """Test AI agent performance and caching."""

    async def test_ai_caching_behavior(self):
        """Test that AI results are cached appropriately."""
        from app.services.ai_service import SimpleCache

        cache = SimpleCache()

        # Test cache operations
        test_key = "test_ai_result"
        test_data = {"analysis": "cached_result"}

        # Initially not cached
        assert cache.get(test_key) is None

        # Cache the data
        cache.set(test_key, test_data, ttl_seconds=60)

        # Now should be cached
        cached_result = cache.get(test_key)
        assert cached_result == test_data

        # Test cache expiration (simulate by setting old timestamp)
        cache._cache[test_key].timestamp = 0  # Very old
        expired_result = cache.get(test_key)
        assert expired_result is None  # Should be expired

    async def test_ai_service_caching_integration(self):
        """Test AI service caching integration."""
        from app.services.ai_service import AIService

        # Mock dependencies
        mock_debt_repo = MagicMock()
        mock_user_repo = MagicMock()
        mock_analytics_repo = MagicMock()

        service = AIService(mock_debt_repo, mock_user_repo, mock_analytics_repo)

        # Mock the orchestrator
        with patch.object(service.orchestrator, 'analyze_user_debts') as mock_analyze:
            mock_analyze.return_value = MagicMock(
                debt_analysis=MagicMock(total_debt=10000.0),
                recommendations=MagicMock(recommendations=[]),
                dti_analysis=None,
                repayment_plan=None,
                processing_time=1.0,
                fallback_used=False,
                errors=[]
            )

            user_id = uuid4()

            # First call - should compute
            result1 = await service.get_ai_insights(user_id)
            assert result1 is not None

            # Second call with same parameters - should use cache
            result2 = await service.get_ai_insights(user_id)
            assert result2 == result1

            # Orchestrator should only be called once due to caching
            assert mock_analyze.call_count == 1

            # Clear cache and verify it's called again
            service.invalidate_user_cache(user_id)
            result3 = await service.get_ai_insights(user_id)
            assert mock_analyze.call_count == 2
