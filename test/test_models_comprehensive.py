"""
Comprehensive unit tests for all Pydantic models.
Tests validation, serialization, and business logic.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from app.models.user import UserCreate, UserInDB, UserResponse, UserProfileResponse
from app.models.debt import (
    DebtCreate, DebtUpdate, DebtResponse, DebtInDB,
    DebtType, PaymentFrequency, DebtSummaryResponse
)
from app.models.payment import (
    PaymentCreate, PaymentHistoryResponse, PaymentStatus, PaymentInDB
)
from app.models.ai import (
    AIInsightsResponse, AIRecommendationResponse,
    DTIAnalysisResponse, DebtAnalysisResponse
)


class TestUserModels:
    """Test user-related models."""

    def test_user_create_validation(self):
        """Test UserCreate model validation."""
        # Valid user data (with hashed password as expected by UserCreate model)
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "hashed_password_123",
            "monthly_income": 50000.0
        }
        user = UserCreate(**user_data)
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.hashed_password == "hashed_password_123"
        assert user.monthly_income == 50000.0

    def test_user_create_invalid_email(self):
        """Test UserCreate with invalid email."""
        with pytest.raises(ValueError):
            UserCreate(
                email="invalid-email",
                full_name="Test User",
                hashed_password="securepass123"
            )

    def test_user_create_required_fields(self):
        """Test UserCreate requires all necessary fields."""
        # Missing email
        with pytest.raises(ValueError):
            UserCreate(
                full_name="Test User",
                hashed_password="hashed_password_123"
            )

        # Missing hashed_password
        with pytest.raises(ValueError):
            UserCreate(
                email="test@example.com",
                full_name="Test User"
            )

    def test_user_response_serialization(self):
        """Test UserResponse model serialization."""
        user_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "full_name": "Test User",
            "monthly_income": 50000.0,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        user = UserResponse(**user_data)
        assert user.id == user_data["id"]
        assert user.email == user_data["email"]


class TestDebtModels:
    """Test debt-related models."""

    def test_debt_type_enum(self):
        """Test DebtType enum values."""
        assert DebtType.CREDIT_CARD == "credit_card"
        assert DebtType.PERSONAL_LOAN == "personal_loan"
        assert DebtType.HOME_LOAN == "home_loan"
        assert DebtType.VEHICLE_LOAN == "vehicle_loan"

    def test_payment_frequency_enum(self):
        """Test PaymentFrequency enum values."""
        assert PaymentFrequency.MONTHLY == "monthly"
        assert PaymentFrequency.BIWEEKLY == "biweekly"
        assert PaymentFrequency.WEEKLY == "weekly"

    def test_debt_create_validation(self):
        """Test DebtCreate model validation."""
        user_id = str(uuid4())
        debt_data = {
            "user_id": user_id,
            "name": "Test Credit Card",
            "debt_type": DebtType.CREDIT_CARD,
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 18.99,
            "minimum_payment": 150.0,
            "due_date": "2025-02-15",
            "lender": "Test Bank",
            "payment_frequency": PaymentFrequency.MONTHLY
        }
        debt = DebtCreate(**debt_data)
        assert debt.name == "Test Credit Card"
        assert debt.principal_amount == 5000.0
        assert debt.current_balance == 3000.0

    def test_debt_create_negative_amounts(self):
        """Test DebtCreate with negative amounts."""
        user_id = str(uuid4())
        with pytest.raises(ValueError):
            DebtCreate(
                user_id=user_id,
                name="Test Debt",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=-1000.0,  # Negative
                current_balance=3000.0,
                interest_rate=15.0,
                minimum_payment=150.0,
                due_date="2025-02-15",
                lender="Test Bank",
                payment_frequency=PaymentFrequency.MONTHLY
            )

    def test_debt_response_frontend_compatibility(self):
        """Test DebtResponse frontend compatibility fields."""
        debt_data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "name": "Test Credit Card",
            "debt_type": DebtType.CREDIT_CARD,
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 18.99,
            "is_variable_rate": False,
            "minimum_payment": 150.0,
            "due_date": "2025-02-15",
            "lender": "Test Bank",
            "remaining_term_months": 24,
            "is_tax_deductible": False,
            "payment_frequency": PaymentFrequency.MONTHLY,
            "is_high_priority": True,
            "days_past_due": 0,
            "notes": "Test notes",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        debt = DebtResponse(**debt_data)

        # Test frontend compatibility fields
        assert debt.amount == debt.principal_amount  # amount field
        assert debt.remainingAmount == debt.current_balance  # remainingAmount field
        assert debt.date == debt.due_date  # date field

    def test_debt_update_partial(self):
        """Test DebtUpdate with partial data."""
        update_data = {
            "current_balance": 2500.0,
            "minimum_payment": 125.0
        }
        update = DebtUpdate(**update_data)
        assert update.current_balance == 2500.0
        assert update.minimum_payment == 125.0
        # Other fields should be None (not set)
        assert update.name is None


class TestPaymentModels:
    """Test payment-related models."""

    def test_payment_status_enum(self):
        """Test PaymentStatus enum values."""
        assert PaymentStatus.CONFIRMED == "confirmed"
        assert PaymentStatus.PENDING == "pending"
        assert PaymentStatus.FAILED == "failed"

    def test_payment_create_validation(self):
        """Test PaymentCreate model validation."""
        debt_id = str(uuid4())
        user_id = str(uuid4())

        payment_data = {
            "debt_id": debt_id,
            "user_id": user_id,
            "amount": 200.0,
            "payment_date": "2025-01-15",
            "principal_portion": 150.0,
            "interest_portion": 50.0,
            "notes": "Extra payment"
        }
        payment = PaymentCreate(**payment_data)
        assert payment.amount == 200.0
        assert payment.principal_portion == 150.0
        assert payment.interest_portion == 50.0

    def test_payment_create_negative_amount(self):
        """Test PaymentCreate with negative amount."""
        with pytest.raises(ValueError):
            PaymentCreate(
                debt_id=str(uuid4()),
                user_id=str(uuid4()),
                amount=-100.0,  # Negative amount
                payment_date="2025-01-15"
            )

    def test_payment_history_response_frontend_compatibility(self):
        """Test PaymentHistoryResponse frontend compatibility."""
        payment_data = {
            "id": str(uuid4()),
            "debt_id": str(uuid4()),
            "amount": 200.0,
            "payment_date": "2025-01-15",
            "principal_portion": 150.0,
            "interest_portion": 50.0,
            "notes": "Extra payment"
        }
        payment = PaymentHistoryResponse(**payment_data)

        # Test frontend compatibility field
        assert payment.date == payment.payment_date  # date field


class TestAIModels:
    """Test AI-related models."""

    def test_ai_recommendation_response(self):
        """Test AIRecommendationResponse model."""
        rec_data = {
            "id": "rec_1",
            "user_id": str(uuid4()),
            "recommendation_type": "avalanche",
            "title": "Pay high interest debt first",
            "description": "Focus on credit card with 18.99% interest",
            "potential_savings": 500.0,
            "priority_score": 9,
            "is_dismissed": False,
            "created_at": datetime.now().isoformat()
        }
        rec = AIRecommendationResponse(**rec_data)
        assert rec.recommendation_type == "avalanche"
        assert rec.potential_savings == 500.0
        assert rec.priority_score == 9

    def test_dti_analysis_response(self):
        """Test DTIAnalysisResponse model."""
        dti_data = {
            "frontend_dti": 25.5,
            "backend_dti": 35.2,
            "total_monthly_debt_payments": 2500.0,
            "monthly_income": 8000.0,
            "is_healthy": True
        }
        dti = DTIAnalysisResponse(**dti_data)
        assert dti.frontend_dti == 25.5
        assert dti.backend_dti == 35.2
        assert dti.is_healthy is True

    def test_debt_analysis_response(self):
        """Test DebtAnalysisResponse model."""
        analysis_data = {
            "total_debt": 15000.0,
            "debt_count": 3,
            "average_interest_rate": 12.5,
            "total_minimum_payments": 450.0,
            "high_priority_count": 1,
            "generated_at": datetime.now().isoformat()
        }
        analysis = DebtAnalysisResponse(**analysis_data)
        assert analysis.total_debt == 15000.0
        assert analysis.debt_count == 3
        assert analysis.average_interest_rate == 12.5

    def test_ai_insights_response_complete(self):
        """Test complete AIInsightsResponse model."""
        insights_data = {
            "debt_analysis": {
                "total_debt": 15000.0,
                "debt_count": 3,
                "average_interest_rate": 12.5,
                "total_minimum_payments": 450.0,
                "high_priority_count": 1,
                "generated_at": datetime.now().isoformat()
            },
            "recommendations": [{
                "id": "rec_1",
                "user_id": str(uuid4()),
                "recommendation_type": "avalanche",
                "title": "Pay high interest debt first",
                "description": "Focus on credit card",
                "potential_savings": 500.0,
                "priority_score": 9,
                "is_dismissed": False,
                "created_at": datetime.now().isoformat()
            }],
            "dti_analysis": {
                "frontend_dti": 25.5,
                "backend_dti": 35.2,
                "total_monthly_debt_payments": 2500.0,
                "monthly_income": 8000.0,
                "is_healthy": True
            },
            "repayment_plan": {
                "strategy": "avalanche",
                "monthly_payment_amount": 600.0,
                "total_interest_saved": 1200.0,
                "expected_completion_date": "2026-01-15",
                "debt_order": ["debt1", "debt2"],
                "payment_schedule": {"month1": 600.0}
            },
            "metadata": {
                "processing_time": 2.5,
                "fallback_used": False,
                "errors": [],
                "generated_at": datetime.now().isoformat()
            }
        }
        insights = AIInsightsResponse(**insights_data)
        assert insights.debt_analysis.total_debt == 15000.0
        assert len(insights.recommendations) == 1
        assert insights.dti_analysis.frontend_dti == 25.5
        assert insights.repayment_plan.strategy == "avalanche"
        assert insights.metadata.processing_time == 2.5


class TestModelIntegration:
    """Test model integration and business logic."""

    def test_debt_summary_calculation(self):
        """Test debt summary response calculation."""
        summary_data = {
            "total_debt": 15000.0,
            "total_interest_paid": 1200.0,
            "total_minimum_payments": 450.0,
            "average_interest_rate": 12.5,
            "debt_count": 3,
            "high_priority_count": 1,
            "upcoming_payments_count": 2
        }
        summary = DebtSummaryResponse(**summary_data)
        assert summary.total_debt == 15000.0
        assert summary.average_interest_rate == 12.5

    def test_user_profile_response(self):
        """Test UserProfileResponse model."""
        profile_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "full_name": "Test User",
            "monthly_income": 50000.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        profile = UserProfileResponse(**profile_data)
        assert profile.email == "test@example.com"
        assert profile.monthly_income == 50000.0
