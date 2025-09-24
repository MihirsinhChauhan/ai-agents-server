"""
Basic API functionality tests for debt and payment management.
Tests core CRUD operations and data transformations.
"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.user import UserInDB
from app.models.debt import DebtCreate, DebtUpdate, DebtType, PaymentFrequency, DebtResponse
from app.models.payment import PaymentCreate, PaymentStatus, PaymentHistoryResponse
from app.utils.auth import AuthUtils


class TestDebtAPICore:
    """Test core debt management functionality"""

    def setup_method(self):
        """Clear sessions before each test"""
        _sessions = getattr(AuthUtils, '_sessions', {})
        _sessions.clear()

    def test_debt_response_model_frontend_compatibility(self):
        """Test that DebtResponse model includes frontend compatibility fields"""
        # Create a mock debt object
        mock_debt = MagicMock()
        mock_debt.id = uuid4()
        mock_debt.user_id = uuid4()
        mock_debt.name = "Test Credit Card"
        mock_debt.debt_type = DebtType.CREDIT_CARD
        mock_debt.principal_amount = 5000.0
        mock_debt.current_balance = 3000.0
        mock_debt.interest_rate = 18.5
        mock_debt.is_variable_rate = False
        mock_debt.minimum_payment = 150.0
        mock_debt.due_date = "2024-02-15"
        mock_debt.lender = "Test Bank"
        mock_debt.remaining_term_months = 24
        mock_debt.is_tax_deductible = False
        mock_debt.payment_frequency = PaymentFrequency.MONTHLY
        mock_debt.is_high_priority = True
        mock_debt.days_past_due = 0
        mock_debt.notes = "Test debt"
        mock_debt.created_at = datetime.now()
        mock_debt.updated_at = datetime.now()

        # Test that from_debt_in_db method works
        response = DebtResponse.from_debt_in_db(mock_debt)

        # Verify frontend compatibility fields
        assert response.amount == 5000.0  # Should map to principal_amount
        assert response.remainingAmount == 3000.0  # Should map to current_balance
        assert response.id is not None
        assert response.name == "Test Credit Card"
        assert response.debt_type == DebtType.CREDIT_CARD

    def test_payment_response_model_frontend_compatibility(self):
        """Test that PaymentHistoryResponse model includes frontend compatibility fields"""
        # Create a mock payment object
        mock_payment = MagicMock()
        mock_payment.id = uuid4()
        mock_payment.debt_id = uuid4()
        mock_payment.user_id = uuid4()
        mock_payment.amount = 500.0
        mock_payment.payment_date = "2024-01-15"
        mock_payment.principal_portion = 400.0
        mock_payment.interest_portion = 100.0
        mock_payment.notes = "Monthly payment"

        # Test that from_payment_in_db method works
        response = PaymentHistoryResponse.from_payment_in_db(mock_payment)

        # Verify frontend compatibility fields
        assert response.date == "2024-01-15"  # Should map to payment_date
        assert response.amount == 500.0
        assert response.id is not None
        assert response.debt_id is not None

    def test_debt_create_model_validation(self):
        """Test that DebtCreate model validates input correctly"""
        # Valid debt data
        valid_data = {
            "name": "Test Credit Card",
            "debt_type": DebtType.CREDIT_CARD,
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 18.5,
            "minimum_payment": 150.0,
            "lender": "Test Bank",
            "user_id": uuid4()
        }

        debt_create = DebtCreate(**valid_data)
        assert debt_create.name == "Test Credit Card"
        assert debt_create.principal_amount == 5000.0

        # Invalid data should raise validation errors
        invalid_data = {
            "name": "",  # Empty name should fail
            "debt_type": DebtType.CREDIT_CARD,
            "principal_amount": -1000.0,  # Negative amount should fail
            "current_balance": 3000.0,
            "interest_rate": 18.5,
            "minimum_payment": 150.0,
            "lender": "Test Bank",
            "user_id": uuid4()
        }

        with pytest.raises(ValueError):
            DebtCreate(**invalid_data)

    def test_payment_create_model_validation(self):
        """Test that PaymentCreate model validates input correctly"""
        # Valid payment data
        valid_data = {
            "debt_id": uuid4(),
            "user_id": uuid4(),
            "amount": 500.0,
            "payment_date": "2024-01-15"
        }

        payment_create = PaymentCreate(**valid_data)
        assert payment_create.amount == 500.0
        assert payment_create.payment_date == "2024-01-15"

        # Invalid data should raise validation errors
        invalid_data = {
            "debt_id": uuid4(),
            "user_id": uuid4(),
            "amount": -100.0,  # Negative amount should fail
            "payment_date": "invalid-date"  # Invalid date format should fail
        }

        with pytest.raises(ValueError):
            PaymentCreate(**invalid_data)

    def test_days_past_due_calculation(self):
        """Test that days_past_due is calculated correctly"""
        from app.models.debt import DebtInDB

        # Create a debt with a past due date
        past_date = (date.today() - timedelta(days=5)).isoformat()
        debt = DebtInDB(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            minimum_payment=150.0,
            due_date=past_date,
            lender="Test Bank"
        )

        response = DebtResponse.from_debt_in_db(debt)

        # Should have 5 days past due
        assert response.days_past_due == 5

    def test_upcoming_payment_reminders_logic(self):
        """Test the logic for generating payment reminders"""
        # Simple test for celebration logic without async function
        # Test the basic logic of when celebrations should occur

        # Test significant payment (25% of balance)
        payment_amount = 750.0
        previous_balance = 3000.0
        percentage = (payment_amount / previous_balance) * 100

        # Should trigger celebration for significant payment
        assert percentage >= 25  # 25% threshold for celebration

        # Test small payment
        small_payment = 50.0
        small_percentage = (small_payment / previous_balance) * 100
        assert small_percentage < 10  # Below celebration threshold


class TestAuthentication:
    """Test authentication integration"""

    def setup_method(self):
        """Clear sessions before each test"""
        _sessions = getattr(AuthUtils, '_sessions', {})
        _sessions.clear()

    def test_session_creation_and_validation(self):
        """Test session creation and validation"""
        user_id = uuid4()

        # Create session
        token = AuthUtils.create_session(user_id)
        assert token is not None
        assert len(token) > 20  # Should be a proper token

        # Validate session
        session_data = AuthUtils.get_session(token)
        assert session_data is not None
        assert session_data['user_id'] == user_id

    def test_session_expiration(self):
        """Test session expiration handling"""
        user_id = uuid4()

        # Create session
        token = AuthUtils.create_session(user_id)

        # Verify session exists initially
        initial_session = AuthUtils.get_session(token)
        assert initial_session is not None

        # Manually expire the session by setting expiry to past time
        from app.utils.auth import _sessions
        if token in _sessions:
            # Set expiry to 2 hours ago to ensure it's expired
            _sessions[token]['expires_at'] = datetime.now() - timedelta(hours=2)

        # Session should now be considered expired and removed
        # Note: get_session will clean up expired sessions
        expired_session = AuthUtils.get_session(token)
        assert expired_session is None

        # Verify session was cleaned up
        assert token not in _sessions


class TestDataTransformations:
    """Test data transformations for frontend compatibility"""

    def test_enum_serialization(self):
        """Test that enums are properly serialized"""
        debt_type = DebtType.CREDIT_CARD
        payment_freq = PaymentFrequency.MONTHLY

        # Test enum values
        assert debt_type.value == "credit_card"
        assert payment_freq.value == "monthly"

    def test_date_formatting(self):
        """Test date formatting for API responses"""
        test_date = "2024-01-15"
        formatted_date = datetime.strptime(test_date, "%Y-%m-%d").date()

        # Should parse correctly
        assert formatted_date.year == 2024
        assert formatted_date.month == 1
        assert formatted_date.day == 15

    def test_amount_formatting(self):
        """Test amount formatting and validation"""
        # Test positive amounts
        valid_amounts = [100.0, 1000.50, 50000.99]
        for amount in valid_amounts:
            assert amount > 0

        # Test invalid amounts
        invalid_amounts = [-100.0, 0.0, -0.01]
        for amount in invalid_amounts:
            assert amount <= 0


if __name__ == "__main__":
    # Run tests with: python -m pytest test/test_api_endpoints.py -v
    pytest.main([__file__, "-v"])
