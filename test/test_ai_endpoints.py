"""
Basic tests for AI API endpoints.
Tests core AI functionality and response formats.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.user import UserInDB
from app.models.ai import (
    AIInsightsResponse,
    AIRecommendationResponse,
    DTIAnalysisResponse,
    DebtAnalysisResponse
)
from app.services.ai_service import AIService, SimpleCache


class TestAIService:
    """Test AI service functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = uuid4()
        self.mock_debt_repo = MagicMock()
        self.mock_user_repo = MagicMock()
        self.mock_analytics_repo = MagicMock()

        self.ai_service = AIService(
            debt_repo=self.mock_debt_repo,
            user_repo=self.mock_user_repo,
            analytics_repo=self.mock_analytics_repo
        )

    def test_simple_cache_operations(self):
        """Test basic cache operations"""
        cache = SimpleCache()

        # Test cache set and get
        cache.set("test_key", {"data": "value"}, ttl_seconds=60)
        result = cache.get("test_key")
        assert result == {"data": "value"}

        # Test cache miss
        result = cache.get("nonexistent_key")
        assert result is None

        # Test cache expiration (simulate by setting old timestamp)
        cache._cache["test_key"].timestamp = 0  # Very old timestamp
        result = cache.get("test_key")
        assert result is None  # Should be expired and removed

    def test_cache_invalidation(self):
        """Test cache invalidation for users"""
        cache = SimpleCache()

        # Set some cache entries
        cache.set("user_123_insights_None_None_True", {"insights": "data"})
        cache.set("user_123_recommendations", {"recommendations": "data"})
        cache.set("user_456_insights_None_None_True", {"other_user": "data"})

        # Invalidate user 123's cache
        cache.clear_user_cache("123")

        # Check that user 123's entries are gone
        assert cache.get("user_123_insights_None_None_True") is None
        assert cache.get("user_123_recommendations") is None

        # Check that user 456's entries remain
        assert cache.get("user_456_insights_None_None_True") == {"other_user": "data"}

    @patch('app.services.ai_service.logger')
    async def test_ai_service_error_handling(self, mock_logger):
        """Test AI service error handling"""
        # Mock the orchestrator to raise an exception
        with patch.object(self.ai_service, 'orchestrator') as mock_orch:
            mock_orch.analyze_user_debts.side_effect = Exception("Test error")

            # Test that exceptions are properly raised
            with pytest.raises(Exception):
                await self.ai_service.get_ai_insights(self.user_id)

            # Verify logging was called
            mock_logger.error.assert_called()


class TestAIModels:
    """Test AI response models"""

    def test_debt_analysis_response(self):
        """Test DebtAnalysisResponse model"""
        data = {
            "total_debt": 10000.0,
            "debt_count": 3,
            "average_interest_rate": 12.5,
            "total_minimum_payments": 450.0,
            "high_priority_count": 1,
            "generated_at": "2024-01-01T00:00:00"
        }

        response = DebtAnalysisResponse(**data)

        assert response.total_debt == 10000.0
        assert response.debt_count == 3
        assert response.average_interest_rate == 12.5
        assert response.total_minimum_payments == 450.0
        assert response.high_priority_count == 1

    def test_ai_recommendation_response(self):
        """Test AIRecommendationResponse model"""
        data = {
            "id": "rec_1",
            "user_id": str(uuid4()),
            "recommendation_type": "avalanche",
            "title": "Pay high interest debt first",
            "description": "Focus on your credit card with 18% interest",
            "potential_savings": 500.0,
            "priority_score": 9,
            "is_dismissed": False,
            "created_at": "2024-01-01T00:00:00"
        }

        response = AIRecommendationResponse(**data)

        assert response.recommendation_type == "avalanche"
        assert response.potential_savings == 500.0
        assert response.priority_score == 9
        assert response.is_dismissed is False

    def test_dti_analysis_response(self):
        """Test DTIAnalysisResponse model"""
        data = {
            "frontend_dti": 25.5,
            "backend_dti": 35.2,
            "total_monthly_debt_payments": 2500.0,
            "monthly_income": 8000.0,
            "is_healthy": True
        }

        response = DTIAnalysisResponse(**data)

        assert response.frontend_dti == 25.5
        assert response.backend_dti == 35.2
        assert response.is_healthy is True

    def test_ai_insights_response(self):
        """Test complete AIInsightsResponse model"""
        debt_analysis = {
            "total_debt": 10000.0,
            "debt_count": 3,
            "average_interest_rate": 12.5,
            "total_minimum_payments": 450.0,
            "high_priority_count": 1,
            "generated_at": "2024-01-01T00:00:00"
        }

        recommendations = [{
            "id": "rec_1",
            "user_id": str(uuid4()),
            "recommendation_type": "avalanche",
            "title": "Pay high interest debt first",
            "description": "Focus on your credit card with 18% interest",
            "potential_savings": 500.0,
            "priority_score": 9,
            "is_dismissed": False,
            "created_at": "2024-01-01T00:00:00"
        }]

        dti_analysis = {
            "frontend_dti": 25.5,
            "backend_dti": 35.2,
            "total_monthly_debt_payments": 2500.0,
            "monthly_income": 8000.0,
            "is_healthy": True
        }

        metadata = {
            "processing_time": 2.5,
            "fallback_used": False,
            "errors": [],
            "generated_at": "2024-01-01T00:00:00"
        }

        data = {
            "debt_analysis": debt_analysis,
            "recommendations": recommendations,
            "dti_analysis": dti_analysis,
            "repayment_plan": None,
            "metadata": metadata
        }

        response = AIInsightsResponse(**data)

        assert response.debt_analysis.total_debt == 10000.0
        assert len(response.recommendations) == 1
        assert response.dti_analysis.frontend_dti == 25.5
        assert response.metadata.processing_time == 2.5


class TestAIEndpoints:
    """Test AI API endpoints"""

    def setup_method(self):
        """Setup test client"""
        from fastapi.testclient import TestClient
        from app.main import app

        self.client = TestClient(app)
        self.test_user_id = str(uuid4())

    def test_ai_endpoints_require_authentication(self):
        """Test that AI endpoints require authentication"""
        # Test insights endpoint
        response = self.client.get("/api/ai/insights")
        assert response.status_code == 401

        # Test recommendations endpoint
        response = self.client.get("/api/ai/recommendations")
        assert response.status_code == 401

        # Test DTI endpoint
        response = self.client.get("/api/ai/dti")
        assert response.status_code == 401

        # Test debt summary endpoint
        response = self.client.get("/api/ai/debt-summary")
        assert response.status_code == 401
