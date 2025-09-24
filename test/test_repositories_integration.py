"""
Integration tests for repository layer.
Tests database operations and repository functionality.
"""

import pytest
from uuid import uuid4

from app.repositories.user_repository import UserRepository
from app.repositories.debt_repository import DebtRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.models.user import UserCreate
from app.models.debt import DebtCreate, DebtType, PaymentFrequency, DebtUpdate
from app.models.payment import PaymentCreate, PaymentStatus


@pytest.mark.integration
@pytest.mark.database
class TestUserRepository:
    """Test UserRepository database operations."""

    async def test_create_and_get_user(self, test_session):
        """Test creating and retrieving a user."""
        repo = UserRepository()
        repo.session = test_session  # Override session for testing

        # Create user
        user_data = UserCreate(
            email=f"test_{uuid4()}@example.com",
            full_name="Test User",
            password="securepass123",
            monthly_income=50000.0
        )

        created_user = await repo.create_user(user_data)
        assert created_user.email == user_data.email
        assert created_user.full_name == user_data.full_name
        assert created_user.monthly_income == user_data.monthly_income

        # Retrieve user
        retrieved_user = await repo.get_user_by_id(created_user.id)
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    async def test_get_user_by_email(self, test_session):
        """Test retrieving user by email."""
        repo = UserRepository()
        repo.session = test_session

        user_data = UserCreate(
            email=f"test_{uuid4()}@example.com",
            full_name="Test User",
            password="securepass123",
            monthly_income=50000.0
        )

        created_user = await repo.create_user(user_data)

        # Get by email
        retrieved_user = await repo.get_user_by_email(user_data.email)
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == user_data.email

    async def test_update_user(self, test_session):
        """Test updating user information."""
        repo = UserRepository()
        repo.session = test_session

        # Create user
        user_data = UserCreate(
            email=f"test_{uuid4()}@example.com",
            full_name="Test User",
            password="securepass123",
            monthly_income=50000.0
        )
        user = await repo.create_user(user_data)

        # Update user
        updated_data = {"full_name": "Updated Name", "monthly_income": 60000.0}
        updated_user = await repo.update_user(user.id, updated_data)

        assert updated_user.full_name == "Updated Name"
        assert updated_user.monthly_income == 60000.0
        assert updated_user.email == user_data.email  # Unchanged

    async def test_delete_user(self, test_session):
        """Test soft deleting a user."""
        repo = UserRepository()
        repo.session = test_session

        # Create user
        user_data = UserCreate(
            email=f"test_{uuid4()}@example.com",
            full_name="Test User",
            password="securepass123",
            monthly_income=50000.0
        )
        user = await repo.create_user(user_data)

        # Delete user
        success = await repo.delete_user(user.id)
        assert success is True

        # Verify user is marked as inactive
        deleted_user = await repo.get_user_by_id(user.id)
        assert deleted_user.is_active is False


@pytest.mark.integration
@pytest.mark.database
class TestDebtRepository:
    """Test DebtRepository database operations."""

    async def test_create_and_get_debt(self, test_session, test_user):
        """Test creating and retrieving a debt."""
        repo = DebtRepository()
        repo.session = test_session

        debt_data = DebtCreate(
            user_id=test_user.id,
            name="Test Credit Card",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.99,
            minimum_payment=150.0,
            due_date="2025-02-15",
            lender="Test Bank",
            payment_frequency=PaymentFrequency.MONTHLY
        )

        created_debt = await repo.create_debt(debt_data)
        assert created_debt.name == debt_data.name
        assert created_debt.principal_amount == debt_data.principal_amount
        assert created_debt.user_id == test_user.id

        # Retrieve debt
        retrieved_debt = await repo.get_by_id(created_debt.id)
        assert retrieved_debt.id == created_debt.id
        assert retrieved_debt.name == debt_data.name

    async def test_get_debts_by_user_id(self, test_session, test_user):
        """Test retrieving all debts for a user."""
        repo = DebtRepository()
        repo.session = test_session

        # Create multiple debts
        debts_data = [
            DebtCreate(
                user_id=test_user.id,
                name=f"Debt {i}",
                debt_type=DebtType.CREDIT_CARD,
                principal_amount=1000.0 * (i + 1),
                current_balance=800.0 * (i + 1),
                interest_rate=15.0 + i,
                minimum_payment=50.0 * (i + 1),
                due_date=f"2025-02-{15 + i}",
                lender=f"Bank {i}",
                payment_frequency=PaymentFrequency.MONTHLY
            )
            for i in range(3)
        ]

        created_debts = []
        for debt_data in debts_data:
            debt = await repo.create_debt(debt_data)
            created_debts.append(debt)

        # Retrieve all debts for user
        user_debts = await repo.get_debts_by_user_id(test_user.id)
        assert len(user_debts) == 3

        # Verify debts belong to user
        for debt in user_debts:
            assert debt.user_id == test_user.id

    async def test_update_debt(self, test_session, test_user):
        """Test updating debt information."""
        repo = DebtRepository()
        repo.session = test_session

        # Create debt
        debt_data = DebtCreate(
            user_id=test_user.id,
            name="Original Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.99,
            minimum_payment=150.0,
            due_date="2025-02-15",
            lender="Test Bank",
            payment_frequency=PaymentFrequency.MONTHLY
        )
        debt = await repo.create_debt(debt_data)

        # Update debt
        update_data = DebtUpdate(
            current_balance=2500.0,
            minimum_payment=125.0,
            name="Updated Debt"
        )
        updated_debt = await repo.update_debt(debt.id, update_data.model_dump(exclude_unset=True))

        assert updated_debt.current_balance == 2500.0
        assert updated_debt.minimum_payment == 125.0
        assert updated_debt.name == "Updated Debt"
        assert updated_debt.principal_amount == debt_data.principal_amount  # Unchanged

    async def test_delete_debt(self, test_session, test_user):
        """Test soft deleting a debt."""
        repo = DebtRepository()
        repo.session = test_session

        # Create debt
        debt_data = DebtCreate(
            user_id=test_user.id,
            name="Test Debt",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.99,
            minimum_payment=150.0,
            due_date="2025-02-15",
            lender="Test Bank",
            payment_frequency=PaymentFrequency.MONTHLY
        )
        debt = await repo.create_debt(debt_data)

        # Delete debt
        success = await repo.delete(debt.id)
        assert success is True

        # Verify debt is marked as inactive
        deleted_debt = await repo.get_by_id(debt.id)
        assert deleted_debt.is_active is False


@pytest.mark.integration
@pytest.mark.database
class TestPaymentRepository:
    """Test PaymentRepository database operations."""

    async def test_create_and_get_payment(self, test_session, test_user, test_debts):
        """Test creating and retrieving a payment."""
        repo = PaymentRepository()
        repo.session = test_session

        debt = test_debts[0]
        payment_data = PaymentCreate(
            debt_id=debt.id,
            user_id=test_user.id,
            amount=200.0,
            payment_date="2025-01-15",
            principal_portion=150.0,
            interest_portion=50.0,
            notes="Test payment"
        )

        created_payment = await repo.create_payment(payment_data)
        assert created_payment.amount == payment_data.amount
        assert created_payment.debt_id == debt.id
        assert created_payment.user_id == test_user.id

        # Retrieve payment
        retrieved_payment = await repo.get_payment_by_id(created_payment.id)
        assert retrieved_payment.id == created_payment.id
        assert retrieved_payment.amount == payment_data.amount

    async def test_get_payments_by_debt_id(self, test_session, test_user, test_debts):
        """Test retrieving payments for a specific debt."""
        repo = PaymentRepository()
        repo.session = test_session

        debt = test_debts[0]

        # Create multiple payments
        payments_data = [
            PaymentCreate(
                debt_id=debt.id,
                user_id=test_user.id,
                amount=100.0 * (i + 1),
                payment_date=f"2025-01-{10 + i}",
                principal_portion=80.0 * (i + 1),
                interest_portion=20.0 * (i + 1),
                notes=f"Payment {i + 1}"
            )
            for i in range(3)
        ]

        created_payments = []
        for payment_data in payments_data:
            payment = await repo.create_payment(payment_data)
            created_payments.append(payment)

        # Retrieve payments for debt
        debt_payments = await repo.get_payments_by_debt_id(debt.id)
        assert len(debt_payments) == 3

        # Verify payments belong to debt
        for payment in debt_payments:
            assert payment.debt_id == debt.id

    async def test_update_payment(self, test_session, test_user, test_debts):
        """Test updating payment information."""
        repo = PaymentRepository()
        repo.session = test_session

        debt = test_debts[0]
        payment_data = PaymentCreate(
            debt_id=debt.id,
            user_id=test_user.id,
            amount=200.0,
            payment_date="2025-01-15",
            notes="Original payment"
        )
        payment = await repo.create_payment(payment_data)

        # Update payment
        update_data = {
            "amount": 250.0,
            "notes": "Updated payment"
        }
        updated_payment = await repo.update_payment(payment.id, update_data)

        assert updated_payment.amount == 250.0
        assert updated_payment.notes == "Updated payment"
        assert updated_payment.payment_date == payment_data.payment_date  # Unchanged

    async def test_delete_payment(self, test_session, test_user, test_debts):
        """Test deleting a payment."""
        repo = PaymentRepository()
        repo.session = test_session

        debt = test_debts[0]
        payment_data = PaymentCreate(
            debt_id=debt.id,
            user_id=test_user.id,
            amount=200.0,
            payment_date="2025-01-15"
        )
        payment = await repo.create_payment(payment_data)

        # Delete payment
        success = await repo.delete_payment(payment.id)
        assert success is True

        # Verify payment is deleted (soft delete)
        deleted_payment = await repo.get_payment_by_id(payment.id)
        assert deleted_payment is None  # Assuming soft delete removes from active queries


@pytest.mark.integration
@pytest.mark.database
class TestAnalyticsRepository:
    """Test AnalyticsRepository database operations."""

    async def test_calculate_debt_summary(self, test_session, test_user, test_debts):
        """Test calculating debt summary statistics."""
        repo = AnalyticsRepository()
        repo.session = test_session

        # Calculate summary
        summary = await repo.calculate_debt_summary(test_user.id)

        assert summary is not None
        assert "total_debt" in summary
        assert "debt_count" in summary
        assert "average_interest_rate" in summary

        # Verify calculations
        expected_total_debt = sum(debt.current_balance for debt in test_debts)
        assert summary["total_debt"] == expected_total_debt
        assert summary["debt_count"] == len(test_debts)

    async def test_calculate_payment_history(self, test_session, test_user, test_debts):
        """Test calculating payment history analytics."""
        repo = AnalyticsRepository()
        repo.session = test_session

        # Create some payments first
        payment_repo = PaymentRepository()
        payment_repo.session = test_session

        for debt in test_debts:
            payment_data = PaymentCreate(
                debt_id=debt.id,
                user_id=test_user.id,
                amount=debt.minimum_payment,
                payment_date="2025-01-15"
            )
            await payment_repo.create_payment(payment_data)

        # Calculate payment analytics
        analytics = await repo.calculate_payment_analytics(test_user.id)

        assert analytics is not None
        assert "total_payments" in analytics
        assert "total_amount_paid" in analytics

        # Verify calculations
        assert analytics["total_payments"] == len(test_debts)


@pytest.mark.integration
@pytest.mark.database
class TestRepositoryIntegration:
    """Test repository integration and cross-repository operations."""

    async def test_user_debt_payment_workflow(self, test_session):
        """Test complete workflow: user -> debt -> payment."""
        # Setup repositories
        user_repo = UserRepository()
        debt_repo = DebtRepository()
        payment_repo = PaymentRepository()

        user_repo.session = test_session
        debt_repo.session = test_session
        payment_repo.session = test_session

        # Create user
        user_data = UserCreate(
            email=f"workflow_{uuid4()}@example.com",
            full_name="Workflow User",
            password="securepass123",
            monthly_income=50000.0
        )
        user = await user_repo.create_user(user_data)

        # Create debt
        debt_data = DebtCreate(
            user_id=user.id,
            name="Workflow Credit Card",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3000.0,
            interest_rate=18.99,
            minimum_payment=150.0,
            due_date="2025-02-15",
            lender="Workflow Bank",
            payment_frequency=PaymentFrequency.MONTHLY
        )
        debt = await debt_repo.create_debt(debt_data)

        # Create payment
        payment_data = PaymentCreate(
            debt_id=debt.id,
            user_id=user.id,
            amount=200.0,
            payment_date="2025-01-15",
            principal_portion=150.0,
            interest_portion=50.0
        )
        payment = await payment_repo.create_payment(payment_data)

        # Verify relationships
        assert payment.user_id == user.id
        assert payment.debt_id == debt.id
        assert debt.user_id == user.id

        # Verify data integrity
        retrieved_user = await user_repo.get_user_by_id(user.id)
        retrieved_debt = await debt_repo.get_by_id(debt.id)
        retrieved_payment = await payment_repo.get_payment_by_id(payment.id)

        assert retrieved_user.email == user_data.email
        assert retrieved_debt.name == debt_data.name
        assert retrieved_payment.amount == payment_data.amount
