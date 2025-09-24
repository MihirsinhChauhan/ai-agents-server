"""
Comprehensive tests for enhanced debt models with frontend compatibility.
Tests all validation, serialization, and frontend compatibility features.
"""

import pytest
from datetime import datetime, date
from uuid import UUID, uuid4
from pydantic import ValidationError

from app.models.debt import (
    DebtType, PaymentFrequency, DebtSource,
    DebtCreate, DebtInDB, DebtResponse, DebtUpdate
)
from app.models.payment import (
    PaymentStatus, PaymentCreate, PaymentInDB, 
    PaymentHistoryResponse, PaymentUpdate
)
from app.models.user import (
    UserCreate, UserInDB, UserProfileResponse, UserUpdate
)
from app.models.analytics import (
    DTIMetricsResponse, DebtSummaryResponse, 
    UserStreakResponse, AIRecommendationResponse,
    UserStreakInDB, AIRecommendationInDB,
    convert_user_streak_to_response, convert_ai_recommendation_to_response
)


class TestDebtModels:
    """Test debt model validation and frontend compatibility"""

    def test_debt_type_enum_values(self):
        """Test that DebtType enum matches frontend exactly"""
        expected_values = {
            "credit_card", "personal_loan", "home_loan", "vehicle_loan",
            "education_loan", "business_loan", "gold_loan", "overdraft", "emi", "other"
        }
        actual_values = {dt.value for dt in DebtType}
        assert actual_values == expected_values

    def test_payment_frequency_enum_values(self):
        """Test that PaymentFrequency enum matches frontend exactly"""
        expected_values = {"weekly", "biweekly", "monthly", "quarterly"}
        actual_values = {pf.value for pf in PaymentFrequency}
        assert actual_values == expected_values

    def test_debt_create_validation(self):
        """Test DebtCreate model validation"""
        user_id = uuid4()
        
        # Valid debt creation
        valid_debt = DebtCreate(
            name="Test Credit Card",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            is_variable_rate=False,
            minimum_payment=150.0,
            due_date="2024-01-15",
            lender="Test Bank",
            remaining_term_months=24,
            is_tax_deductible=False,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=True,
            notes="Test notes",
            user_id=user_id
        )
        assert valid_debt.name == "Test Credit Card"
        assert valid_debt.debt_type == DebtType.CREDIT_CARD
        assert valid_debt.principal_amount == 5000.0
        assert valid_debt.current_balance == 3000.0
        assert valid_debt.due_date == "2024-01-15"

    def test_debt_create_validation_errors(self):
        """Test DebtCreate validation failures"""
        user_id = uuid4()
        
        # Test negative principal amount
        with pytest.raises(ValidationError) as exc_info:
            DebtCreate(
                name="Test",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=-1000.0,
                current_balance=3000.0,
                interest_rate=18.5,
                minimum_payment=150.0,
                lender="Test Bank",
                user_id=user_id
            )
        assert "greater than 0" in str(exc_info.value)

        # Test negative current balance
        with pytest.raises(ValidationError) as exc_info:
            DebtCreate(
                name="Test",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=5000.0,
                current_balance=-1000.0,
                interest_rate=18.5,
                minimum_payment=150.0,
                lender="Test Bank",
                user_id=user_id
            )
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test invalid interest rate
        with pytest.raises(ValidationError) as exc_info:
            DebtCreate(
                name="Test",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=5000.0,
                current_balance=3000.0,
                interest_rate=150.0,  # > 100%
                minimum_payment=150.0,
                lender="Test Bank",
                user_id=user_id
            )
        assert "less than or equal to 100" in str(exc_info.value)

        # Test invalid date format
        with pytest.raises(ValidationError) as exc_info:
            DebtCreate(
                name="Test",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=5000.0,
                current_balance=3000.0,
                interest_rate=18.5,
                minimum_payment=150.0,
                due_date="15/01/2024",  # Wrong format
                lender="Test Bank",
                user_id=user_id
            )
        assert "string_pattern_mismatch" in str(exc_info.value)

    def test_debt_response_frontend_compatibility(self):
        """Test DebtResponse compatibility fields"""
        debt_response = DebtResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            is_variable_rate=False,
            minimum_payment=150.0,
            due_date="2024-01-15",
            lender="Test Bank",
            is_tax_deductible=False,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=True
        )
        
        # Test compatibility fields
        assert debt_response.amount == debt_response.principal_amount
        assert debt_response.remainingAmount == debt_response.current_balance

    def test_debt_response_days_past_due_calculation(self):
        """Test days past due calculation"""
        # Past due debt
        past_due_debt = DebtResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Past Due Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            is_variable_rate=False,
            minimum_payment=150.0,
            due_date="2020-01-01",  # Way past due
            lender="Test Bank",
            is_tax_deductible=False,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=True
        )
        assert past_due_debt.days_past_due > 0

        # Not past due debt
        future_debt = DebtResponse(
            id="123e4567-e89b-12d3-a456-426614174001",
            name="Future Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            is_variable_rate=False,
            minimum_payment=150.0,
            due_date="2030-12-31",  # Future date
            lender="Test Bank",
            is_tax_deductible=False,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=False
        )
        assert future_debt.days_past_due == 0

    def test_debt_response_from_debt_in_db(self):
        """Test conversion from DebtInDB to DebtResponse"""
        debt_in_db = DebtInDB(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Debt",
            debt_type=DebtType.PERSONAL_LOAN,
            principal_amount=10000.0,
            current_balance=7500.0,
            interest_rate=12.5,
            is_variable_rate=True,
            minimum_payment=300.0,
            due_date="2024-02-15",
            lender="Test Lender",
            remaining_term_months=18,
            is_tax_deductible=True,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=False,
            notes="Test notes",
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            updated_at=datetime(2023, 1, 2, 15, 30, 0)
        )
        
        response = DebtResponse.from_debt_in_db(debt_in_db)
        
        assert response.id == str(debt_in_db.id)
        assert response.name == debt_in_db.name
        assert response.debt_type == debt_in_db.debt_type
        assert response.principal_amount == debt_in_db.principal_amount
        assert response.current_balance == debt_in_db.current_balance
        assert response.created_at == "2023-01-01T10:00:00"
        assert response.updated_at == "2023-01-02T15:30:00"


class TestPaymentModels:
    """Test payment model validation and frontend compatibility"""

    def test_payment_create_validation(self):
        """Test PaymentCreate model validation"""
        debt_id = uuid4()
        user_id = uuid4()
        
        valid_payment = PaymentCreate(
            debt_id=debt_id,
            amount=250.0,
            payment_date="2024-01-15",
            principal_portion=200.0,
            interest_portion=50.0,
            notes="Monthly payment",
            user_id=user_id
        )
        
        assert valid_payment.debt_id == debt_id
        assert valid_payment.amount == 250.0
        assert valid_payment.payment_date == "2024-01-15"
        assert valid_payment.principal_portion == 200.0
        assert valid_payment.interest_portion == 50.0

    def test_payment_validation_errors(self):
        """Test PaymentCreate validation failures"""
        debt_id = uuid4()
        user_id = uuid4()
        
        # Test negative amount
        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                debt_id=debt_id,
                amount=-250.0,
                payment_date="2024-01-15",
                user_id=user_id
            )
        assert "greater than 0" in str(exc_info.value)

        # Test invalid date format
        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                debt_id=debt_id,
                amount=250.0,
                payment_date="15/01/2024",  # Wrong format
                user_id=user_id
            )
        assert "string_pattern_mismatch" in str(exc_info.value)

        # Test negative principal portion
        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                debt_id=debt_id,
                amount=250.0,
                payment_date="2024-01-15",
                principal_portion=-100.0,
                user_id=user_id
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_payment_history_response_compatibility(self):
        """Test PaymentHistoryResponse compatibility fields"""
        payment_response = PaymentHistoryResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            debt_id="123e4567-e89b-12d3-a456-426614174001",
            amount=250.0,
            payment_date="2024-01-15",
            principal_portion=200.0,
            interest_portion=50.0,
            notes="Test payment"
        )
        
        # Test compatibility field
        assert payment_response.date == payment_response.payment_date

    def test_payment_history_response_from_payment_in_db(self):
        """Test conversion from PaymentInDB to PaymentHistoryResponse"""
        payment_in_db = PaymentInDB(
            id=uuid4(),
            debt_id=uuid4(),
            user_id=uuid4(),
            amount=300.0,
            payment_date="2024-01-15",
            principal_portion=250.0,
            interest_portion=50.0,
            notes="Test payment",
            status=PaymentStatus.CONFIRMED,
            created_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        
        response = PaymentHistoryResponse.from_payment_in_db(payment_in_db)
        
        assert response.id == str(payment_in_db.id)
        assert response.debt_id == str(payment_in_db.debt_id)
        assert response.amount == payment_in_db.amount
        assert response.payment_date == payment_in_db.payment_date
        assert response.principal_portion == payment_in_db.principal_portion
        assert response.interest_portion == payment_in_db.interest_portion
        assert response.notes == payment_in_db.notes


class TestUserModels:
    """Test user model validation and frontend compatibility"""

    def test_user_create_validation(self):
        """Test UserCreate model validation"""
        valid_user = UserCreate(
            email="test@example.com",
            full_name="Test User",
            monthly_income=5000.0,
            phone_number="+1234567890",
            hashed_password="hashed_password_here"
        )
        
        assert valid_user.email == "test@example.com"
        assert valid_user.full_name == "Test User"
        assert valid_user.monthly_income == 5000.0

    def test_user_validation_errors(self):
        """Test UserCreate validation failures"""
        # Test negative monthly income
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                full_name="Test User",
                monthly_income=-1000.0,
                hashed_password="hashed_password_here"
            )
        assert "greater than or equal to 0" in str(exc_info.value)

        # Test invalid email
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="invalid_email",
                full_name="Test User",
                hashed_password="hashed_password_here"
            )
        assert "email" in str(exc_info.value).lower()

    def test_user_profile_response_from_user_in_db(self):
        """Test conversion from UserInDB to UserProfileResponse"""
        user_in_db = UserInDB(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            monthly_income=5000.0,
            phone_number="+1234567890",
            hashed_password="hashed_password_here",
            is_verified=True,
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            updated_at=datetime(2023, 1, 2, 15, 30, 0)
        )
        
        response = UserProfileResponse.from_user_in_db(user_in_db)
        
        assert response.id == str(user_in_db.id)
        assert response.email == user_in_db.email
        assert response.full_name == user_in_db.full_name
        assert response.monthly_income == user_in_db.monthly_income
        assert response.created_at == "2023-01-01T10:00:00"
        assert response.updated_at == "2023-01-02T15:30:00"


class TestAnalyticsModels:
    """Test analytics model validation and frontend compatibility"""

    def test_dti_metrics_response_validation(self):
        """Test DTIMetricsResponse model validation"""
        valid_dti = DTIMetricsResponse(
            frontend_dti=25.5,
            backend_dti=35.2,
            total_monthly_debt_payments=1760.0,
            monthly_income=5000.0,
            is_healthy=True
        )
        
        assert valid_dti.frontend_dti == 25.5
        assert valid_dti.backend_dti == 35.2
        assert valid_dti.is_healthy is True

    def test_dti_metrics_validation_errors(self):
        """Test DTIMetricsResponse validation failures"""
        # Test negative values
        with pytest.raises(ValidationError) as exc_info:
            DTIMetricsResponse(
                frontend_dti=-5.0,
                backend_dti=35.2,
                total_monthly_debt_payments=1760.0,
                monthly_income=5000.0,
                is_healthy=False
            )
        assert "cannot be negative" in str(exc_info.value)

    def test_debt_summary_response_validation(self):
        """Test DebtSummaryResponse model validation"""
        valid_summary = DebtSummaryResponse(
            total_debt=15000.0,
            total_interest_paid=2500.0,
            total_minimum_payments=650.0,
            average_interest_rate=16.8,
            debt_count=3,
            high_priority_count=1,
            upcomingPaymentsCount=2
        )
        
        assert valid_summary.total_debt == 15000.0
        assert valid_summary.debt_count == 3
        assert valid_summary.high_priority_count == 1

    def test_user_streak_response_validation(self):
        """Test UserStreakResponse model validation"""
        valid_streak = UserStreakResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="123e4567-e89b-12d3-a456-426614174001",
            current_streak=15,
            longest_streak=30,
            last_check_in="2024-01-15",
            total_payments_logged=45,
            milestones_achieved=["7_day_streak", "30_payments"],
            created_at="2023-01-01T10:00:00",
            updated_at="2024-01-15T15:30:00"
        )
        
        assert valid_streak.current_streak == 15
        assert valid_streak.longest_streak == 30
        assert len(valid_streak.milestones_achieved) == 2

    def test_user_streak_validation_errors(self):
        """Test UserStreakResponse validation failures"""
        # Test negative streak values
        with pytest.raises(ValidationError) as exc_info:
            UserStreakResponse(
                id="123e4567-e89b-12d3-a456-426614174000",
                user_id="123e4567-e89b-12d3-a456-426614174001",
                current_streak=-5,
                longest_streak=30,
                total_payments_logged=45,
                milestones_achieved=[]
            )
        assert "cannot be negative" in str(exc_info.value)

    def test_ai_recommendation_response_validation(self):
        """Test AIRecommendationResponse model validation"""
        valid_recommendation = AIRecommendationResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="123e4567-e89b-12d3-a456-426614174001",
            recommendation_type="avalanche",
            title="Pay off high-interest debt first",
            description="Focus on paying off your credit card debt to save on interest.",
            potential_savings=1500.0,
            priority_score=8,
            is_dismissed=False,
            created_at="2024-01-15T10:00:00"
        )
        
        assert valid_recommendation.recommendation_type == "avalanche"
        assert valid_recommendation.priority_score == 8
        assert valid_recommendation.potential_savings == 1500.0

    def test_ai_recommendation_validation_errors(self):
        """Test AIRecommendationResponse validation failures"""
        # Test invalid recommendation type
        with pytest.raises(ValidationError) as exc_info:
            AIRecommendationResponse(
                id="123e4567-e89b-12d3-a456-426614174000",
                user_id="123e4567-e89b-12d3-a456-426614174001",
                recommendation_type="invalid_type",
                title="Test",
                description="Test description",
                priority_score=5,
                is_dismissed=False
            )
        assert "must be one of" in str(exc_info.value)

        # Test invalid priority score
        with pytest.raises(ValidationError) as exc_info:
            AIRecommendationResponse(
                id="123e4567-e89b-12d3-a456-426614174000",
                user_id="123e4567-e89b-12d3-a456-426614174001",
                recommendation_type="snowball",
                title="Test",
                description="Test description",
                priority_score=15,  # > 10
                is_dismissed=False
            )
        assert "less than or equal to 10" in str(exc_info.value)

    def test_conversion_functions(self):
        """Test conversion functions between DB and response models"""
        # Test UserStreak conversion
        streak_in_db = UserStreakInDB(
            id=uuid4(),
            user_id=uuid4(),
            current_streak=10,
            longest_streak=25,
            last_check_in="2024-01-15",
            total_payments_logged=35,
            milestones_achieved=["7_day_streak"],
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            updated_at=datetime(2024, 1, 15, 15, 30, 0)
        )
        
        streak_response = convert_user_streak_to_response(streak_in_db)
        assert streak_response.id == str(streak_in_db.id)
        assert streak_response.current_streak == streak_in_db.current_streak
        assert streak_response.created_at == "2023-01-01T10:00:00"

        # Test AIRecommendation conversion
        recommendation_in_db = AIRecommendationInDB(
            id=uuid4(),
            user_id=uuid4(),
            recommendation_type="avalanche",
            title="Test Recommendation",
            description="Test description",
            potential_savings=500.0,
            priority_score=7,
            is_dismissed=False,
            created_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        
        recommendation_response = convert_ai_recommendation_to_response(recommendation_in_db)
        assert recommendation_response.id == str(recommendation_in_db.id)
        assert recommendation_response.recommendation_type == recommendation_in_db.recommendation_type
        assert recommendation_response.potential_savings == recommendation_in_db.potential_savings
        assert recommendation_response.created_at == "2024-01-15T10:00:00"


class TestModelIntegration:
    """Test model integration and serialization"""

    def test_model_serialization(self):
        """Test that all models serialize correctly to JSON"""
        # Test DebtResponse serialization
        debt_response = DebtResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            is_variable_rate=False,
            minimum_payment=150.0,
            due_date="2024-01-15",
            lender="Test Bank",
            is_tax_deductible=False,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=True
        )
        
        serialized = debt_response.model_dump()
        assert "id" in serialized
        assert "amount" in serialized  # Compatibility field
        assert "remainingAmount" in serialized  # Compatibility field
        assert serialized["amount"] == serialized["principal_amount"]
        assert serialized["remainingAmount"] == serialized["current_balance"]

    def test_model_deserialization(self):
        """Test that models can be created from dict data"""
        debt_data = {
            "name": "Test Debt",
            "debt_type": "credit_card",
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 18.5,
            "is_variable_rate": False,
            "minimum_payment": 150.0,
            "due_date": "2024-01-15",
            "lender": "Test Bank",
            "is_tax_deductible": False,
            "payment_frequency": "monthly",
            "is_high_priority": True,
            "user_id": str(uuid4())
        }
        
        debt_create = DebtCreate(**debt_data)
        assert debt_create.name == "Test Debt"
        assert debt_create.debt_type == DebtType.CREDIT_CARD
        assert debt_create.payment_frequency == PaymentFrequency.MONTHLY

    def test_field_aliases_and_compatibility(self):
        """Test that field aliases work correctly"""
        # Test DebtResponse compatibility fields
        debt_response = DebtResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            is_variable_rate=False,
            minimum_payment=150.0,
            due_date="2024-01-15",
            lender="Test Bank",
            is_tax_deductible=False,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=True
        )
        
        # Ensure compatibility fields are computed correctly
        assert debt_response.amount == 5000.0
        assert debt_response.remainingAmount == 3000.0
        
        # Test PaymentHistoryResponse compatibility field
        payment_response = PaymentHistoryResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            debt_id="123e4567-e89b-12d3-a456-426614174001",
            amount=250.0,
            payment_date="2024-01-15"
        )
        
        assert payment_response.date == "2024-01-15"
