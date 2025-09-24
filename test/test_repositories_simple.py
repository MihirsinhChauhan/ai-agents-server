"""
Simplified repository tests with proper mocking.
Tests basic functionality without complex async context manager setup.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch
import asyncpg

from app.repositories.user_repository import UserRepository
from app.repositories.debt_repository import DebtRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.base_repository import DatabaseError, DuplicateRecordError

from app.models.user import UserInDB, UserCreate
from app.models.debt import DebtInDB, DebtCreate, DebtType, PaymentFrequency
from app.models.payment import PaymentInDB, PaymentCreate
from app.models.analytics import AIRecommendationInDB, UserStreakInDB


class TestRepositoriesFunctionality:
    """Test repository core functionality with simplified mocking"""

    @pytest.mark.asyncio
    async def test_user_repository_methods_exist(self):
        """Test that UserRepository has all expected methods"""
        repo = UserRepository()
        
        # Check that all expected methods exist
        assert hasattr(repo, 'create_user')
        assert hasattr(repo, 'get_by_email')
        assert hasattr(repo, 'verify_user')
        assert hasattr(repo, 'deactivate_user')
        assert hasattr(repo, 'get_user_stats')
        assert hasattr(repo, 'search_users')
        assert hasattr(repo, 'get_users_for_notifications')

    @pytest.mark.asyncio
    async def test_debt_repository_methods_exist(self):
        """Test that DebtRepository has all expected methods"""
        repo = DebtRepository()
        
        # Check that all expected methods exist
        assert hasattr(repo, 'create_debt')
        assert hasattr(repo, 'get_user_debts')
        assert hasattr(repo, 'get_high_priority_debts')
        assert hasattr(repo, 'get_debts_by_interest_rate')
        assert hasattr(repo, 'get_debts_by_balance')
        assert hasattr(repo, 'get_overdue_debts')
        assert hasattr(repo, 'get_debt_summary')
        assert hasattr(repo, 'update_debt_balance')

    @pytest.mark.asyncio
    async def test_payment_repository_methods_exist(self):
        """Test that PaymentRepository has all expected methods"""
        repo = PaymentRepository()
        
        # Check that all expected methods exist
        assert hasattr(repo, 'create_payment')
        assert hasattr(repo, 'get_user_payments')
        assert hasattr(repo, 'get_debt_payments')
        assert hasattr(repo, 'get_payment_summary')
        assert hasattr(repo, 'get_payment_streaks')
        assert hasattr(repo, 'get_monthly_payment_trends')
        assert hasattr(repo, 'bulk_create_payments')

    @pytest.mark.asyncio
    async def test_analytics_repository_methods_exist(self):
        """Test that AnalyticsRepository has all expected methods"""
        repo = AnalyticsRepository()
        
        # Check that all expected methods exist
        assert hasattr(repo, 'create_ai_recommendation')
        assert hasattr(repo, 'get_user_recommendations')
        assert hasattr(repo, 'dismiss_recommendation')
        assert hasattr(repo, 'get_or_create_user_streak')
        assert hasattr(repo, 'update_user_streak')
        assert hasattr(repo, 'log_payment_for_streak')
        assert hasattr(repo, 'calculate_dti_metrics')

    @pytest.mark.asyncio
    @patch('app.repositories.user_repository.UserRepository._fetch_one_with_error_handling')
    @patch('app.repositories.user_repository.UserRepository.create')
    async def test_user_creation_logic(self, mock_create, mock_fetch_one):
        """Test user creation business logic"""
        repo = UserRepository()
        
        # Mock no existing user found
        mock_fetch_one.return_value = None
        
        # Mock successful creation
        mock_user_data = {
            'id': uuid4(),
            'email': 'test@example.com',
            'full_name': 'Test User',
            'monthly_income': 5000.0,
            'phone_number': None,
            'notification_preferences': {'email': True},
            'hashed_password': 'hashed_password',
            'is_verified': False,
            'is_active': True,
            'plaid_access_token': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mock_create.return_value = UserInDB(**mock_user_data)
        
        user_create = UserCreate(
            email='test@example.com',
            full_name='Test User',
            monthly_income=5000.0,
            hashed_password='hashed_password'
        )
        
        result = await repo.create_user(user_create)
        
        assert result.email == 'test@example.com'
        assert result.full_name == 'Test User'
        assert result.is_active is True
        assert result.is_verified is False
        
        # Verify that email check was called
        mock_fetch_one.assert_called_once()
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.repositories.user_repository.UserRepository.get_by_email')
    async def test_user_duplicate_email_check(self, mock_get_by_email):
        """Test duplicate email detection"""
        repo = UserRepository()
        
        # Mock existing user found - patch get_by_email directly
        existing_user_data = {
            'id': uuid4(),
            'email': 'existing@example.com',
            'full_name': 'Existing User',
            'monthly_income': None,
            'phone_number': None,
            'notification_preferences': {'email': True},
            'hashed_password': 'hashed_password',
            'is_verified': True,
            'is_active': True,
            'plaid_access_token': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mock_get_by_email.return_value = UserInDB(**existing_user_data)
        
        user_create = UserCreate(
            email='existing@example.com',
            full_name='New User',
            hashed_password='hashed_password'
        )
        
        with pytest.raises(DuplicateRecordError, match="already exists"):
            await repo.create_user(user_create)

    @pytest.mark.asyncio
    @patch('app.repositories.debt_repository.DebtRepository.create')
    async def test_debt_creation_logic(self, mock_create):
        """Test debt creation business logic"""
        repo = DebtRepository()
        
        # Mock successful creation
        mock_debt_data = {
            'id': uuid4(),
            'user_id': uuid4(),
            'name': 'Credit Card',
            'debt_type': DebtType.CREDIT_CARD,
            'principal_amount': 5000.0,
            'current_balance': 3000.0,
            'interest_rate': 18.5,
            'is_variable_rate': False,
            'minimum_payment': 150.0,
            'due_date': '2024-01-15',
            'lender': 'Test Bank',
            'remaining_term_months': 24,
            'is_tax_deductible': False,
            'payment_frequency': PaymentFrequency.MONTHLY,
            'is_high_priority': True,
            'notes': 'Test notes',
            'source': 'manual',
            'details': {},
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'blockchain_id': None,
            'is_active': True
        }
        
        mock_create.return_value = DebtInDB(**mock_debt_data)
        
        debt_create = DebtCreate(
            user_id=mock_debt_data['user_id'],
            name='Credit Card',
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.5,
            minimum_payment=150.0,
            due_date='2024-01-15',
            lender='Test Bank'
        )
        
        result = await repo.create_debt(debt_create)
        
        assert result.name == 'Credit Card'
        assert result.debt_type == DebtType.CREDIT_CARD
        assert result.principal_amount == 5000.0
        assert result.current_balance == 3000.0
        assert result.is_active is True
        
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.repositories.analytics_repository.AnalyticsRepository._fetch_one_with_error_handling')
    async def test_dti_calculation_logic(self, mock_fetch_one):
        """Test DTI calculation business logic"""
        repo = AnalyticsRepository()
        
        # Mock debt data
        mock_debt_data = {
            'total_monthly_payments': 1760.0,
            'housing_payments': 1200.0
        }
        mock_fetch_one.return_value = mock_debt_data
        
        result = await repo.calculate_dti_metrics(uuid4(), 5000.0)
        
        assert result.frontend_dti == 24.0  # 1200/5000 * 100
        assert result.backend_dti == 35.2   # 1760/5000 * 100
        assert result.monthly_income == 5000.0
        assert result.total_monthly_debt_payments == 1760.0
        assert result.is_healthy is True  # Both DTI ratios within healthy limits

    @pytest.mark.asyncio
    async def test_dti_calculation_validation(self):
        """Test DTI calculation input validation"""
        repo = AnalyticsRepository()
        
        # Test negative income validation
        with pytest.raises(ValueError, match="Monthly income must be positive"):
            await repo.calculate_dti_metrics(uuid4(), -1000.0)
        
        # Test zero income validation
        with pytest.raises(ValueError, match="Monthly income must be positive"):
            await repo.calculate_dti_metrics(uuid4(), 0.0)

    @pytest.mark.asyncio
    async def test_model_validation(self):
        """Test that models validate inputs correctly"""
        
        # Test UserCreate validation
        with pytest.raises(Exception):  # Pydantic validation error
            UserCreate(
                email="invalid-email",  # Invalid email
                full_name="",  # Empty name
                hashed_password="password"
            )
        
        # Test DebtCreate validation
        with pytest.raises(Exception):  # Pydantic validation error
            DebtCreate(
                user_id=uuid4(),
                name="",  # Empty name
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=-1000.0,  # Negative amount
                current_balance=3000.0,
                interest_rate=18.5,
                minimum_payment=150.0,
                lender="Test Bank"
            )
        
        # Test PaymentCreate validation
        with pytest.raises(Exception):  # Pydantic validation error
            PaymentCreate(
                debt_id=uuid4(),
                user_id=uuid4(),
                amount=-250.0,  # Negative amount
                payment_date="invalid-date"  # Invalid date format
            )

    @pytest.mark.asyncio
    @patch('app.repositories.analytics_repository.AnalyticsRepository._fetch_one_with_error_handling')
    @patch('app.repositories.analytics_repository.AnalyticsRepository.get_or_create_user_streak')
    @patch('app.repositories.analytics_repository.AnalyticsRepository.update_user_streak')
    async def test_payment_streak_logic(self, mock_update_streak, mock_get_streak, mock_fetch_one):
        """Test payment streak calculation logic"""
        repo = AnalyticsRepository()
        user_id = uuid4()
        
        # Mock existing streak
        existing_streak = UserStreakInDB(
            id=uuid4(),
            user_id=user_id,
            current_streak=5,
            longest_streak=10,
            last_check_in='2024-01-14',
            total_payments_logged=15,
            milestones_achieved=['7_day_streak']
        )
        
        mock_get_streak.return_value = existing_streak
        
        # Mock updated streak after logging payment
        updated_streak = UserStreakInDB(
            id=existing_streak.id,
            user_id=user_id,
            current_streak=6,  # Incremented
            longest_streak=10,
            last_check_in='2024-01-15',
            total_payments_logged=16,  # Incremented
            milestones_achieved=['7_day_streak']
        )
        
        mock_update_streak.return_value = updated_streak
        
        # Log a consecutive payment
        result = await repo.log_payment_for_streak(user_id, '2024-01-15')
        
        assert result.current_streak == 6
        assert result.total_payments_logged == 16
        assert result.last_check_in == '2024-01-15'
        
        mock_get_streak.assert_called_once_with(user_id)
        mock_update_streak.assert_called_once()

    @pytest.mark.asyncio
    async def test_repository_error_handling_structure(self):
        """Test that repository error handling is properly structured"""
        
        # Test that custom exceptions exist
        assert DatabaseError is not None
        assert DuplicateRecordError is not None
        
        # Test exception inheritance
        assert issubclass(DuplicateRecordError, DatabaseError)
        
        # Test that repositories have proper error handling methods
        repo = UserRepository()
        assert hasattr(repo, '_fetch_one_with_error_handling')
        assert hasattr(repo, '_fetch_all_with_error_handling')
        assert hasattr(repo, '_execute_with_error_handling')

    @pytest.mark.asyncio
    async def test_repository_inheritance(self):
        """Test that repositories properly inherit from BaseRepository"""
        from app.repositories.base_repository import BaseRepository
        
        # Test that all repositories inherit from BaseRepository
        assert issubclass(UserRepository, BaseRepository)
        assert issubclass(DebtRepository, BaseRepository)
        assert issubclass(PaymentRepository, BaseRepository)
        
        # Test that base methods are available
        user_repo = UserRepository()
        assert hasattr(user_repo, 'get_by_id')
        assert hasattr(user_repo, 'update')
        assert hasattr(user_repo, 'delete')
        assert hasattr(user_repo, 'exists')
        assert hasattr(user_repo, 'count')

    @pytest.mark.asyncio
    async def test_transaction_methods_exist(self):
        """Test that transaction methods are properly implemented"""
        
        # Test specific repository transaction usage (concrete repositories)
        payment_repo = PaymentRepository()
        user_repo = UserRepository()
        
        # Check that transaction methods are available
        assert hasattr(payment_repo, 'execute_transaction')
        assert hasattr(payment_repo, 'execute_raw_query')
        assert hasattr(user_repo, 'execute_transaction')
        assert hasattr(user_repo, 'execute_raw_query')
        
        # Test specific transaction methods
        assert hasattr(payment_repo, 'bulk_create_payments')
        assert hasattr(payment_repo, 'create_payment')  # Uses transactions

    @pytest.mark.asyncio
    async def test_health_check_methods(self):
        """Test that health check methods are implemented"""
        
        user_repo = UserRepository()
        analytics_repo = AnalyticsRepository()
        
        assert hasattr(user_repo, 'get_health_check')
        assert hasattr(analytics_repo, 'get_analytics_health_check')


if __name__ == "__main__":
    # Run tests with: python -m pytest test/test_repositories_simple.py -v
    pytest.main([__file__, "-v"])
