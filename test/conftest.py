"""
Pytest configuration and shared fixtures for comprehensive testing.
Provides database, API client, authentication, and AI agent fixtures.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from uuid import uuid4
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# from app.main import app  # Commented out to avoid import issues in unit tests
from app.configs.config import settings
from app.models.user import UserInDB, UserCreate
from app.models.debt import DebtCreate, DebtType, PaymentFrequency
from app.repositories.user_repository import UserRepository
from app.repositories.debt_repository import DebtRepository
from app.utils.auth import AuthUtils


# Test Database Configuration
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/debtease_test"

# Override settings for testing
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "postgres"
os.environ["DB_NAME"] = "debtease_test"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    from sqlalchemy import text

    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        echo=False,
    )

    # Create test database if it doesn't exist
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE DATABASE debtease_test"))
    except Exception:
        pass  # Database might already exist

    # Run migrations
    from app.databases.migrations.migration_runner import run_migrations
    async with engine.begin() as conn:
        await run_migrations(conn)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)

    async with async_session.begin() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="function")
async def test_app() -> FastAPI:
    """Create test FastAPI application."""
    # For unit tests, return a minimal app to avoid dependency issues
    # Full integration tests will use a different approach
    from fastapi import FastAPI
    test_app = FastAPI(title="Test App")
    return test_app


@pytest.fixture(scope="function")
async def test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
async def test_user(test_session) -> UserInDB:
    """Create a test user."""
    user_repo = UserRepository()

    user_data = UserCreate(
        email=f"test_{uuid4()}@example.com",
        full_name="Test User",
        password="testpassword123",
        monthly_income=50000.0
    )

    user = await user_repo.create_user(user_data)
    return user


@pytest.fixture(scope="function")
async def authenticated_user(test_user) -> Dict[str, Any]:
    """Create an authenticated user with session."""
    # Create a test session for the user
    session_token = AuthUtils.create_session_token(test_user.id)

    return {
        "user": test_user,
        "session_token": session_token
    }


@pytest.fixture(scope="function")
async def test_debts(test_user) -> list:
    """Create test debts for a user."""
    debt_repo = DebtRepository()

    debts_data = [
        DebtCreate(
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
        ),
        DebtCreate(
            user_id=test_user.id,
            name="Test Personal Loan",
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

    debts = []
    for debt_data in debts_data:
        debt = await debt_repo.create_debt(debt_data)
        debts.append(debt)

    return debts


@pytest.fixture(scope="session")
def ai_agent_config():
    """Configuration for AI agent testing."""
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", "test-key"),
        "model": "gpt-3.5-turbo",  # Use cheaper model for testing
        "temperature": 0.1,  # More deterministic for testing
        "max_tokens": 500
    }


@pytest.fixture(scope="function")
def mock_ai_response():
    """Mock AI agent response for testing."""
    return {
        "recommendations": [
            {
                "type": "avalanche",
                "title": "Pay high interest debt first",
                "description": "Focus on credit card with 18.99% interest",
                "savings": 500.0
            }
        ],
        "analysis": {
            "total_debt": 11000.0,
            "average_rate": 15.5,
            "recommendation": "avalanche"
        }
    }


# Custom markers for test organization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "ai: AI agent tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "database: Database related tests")


# Test utilities
class TestHelpers:
    """Helper functions for tests."""

    @staticmethod
    def create_test_user_data(email=None, password="testpass123"):
        """Create test user data."""
        return UserCreate(
            email=email or f"test_{uuid4()}@example.com",
            full_name="Test User",
            password=password,
            monthly_income=50000.0
        )

    @staticmethod
    def create_test_debt_data(user_id, **overrides):
        """Create test debt data."""
        defaults = {
            "user_id": user_id,
            "name": "Test Debt",
            "debt_type": DebtType.CREDIT_CARD,
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 15.0,
            "minimum_payment": 150.0,
            "due_date": "2025-02-15",
            "lender": "Test Bank",
            "payment_frequency": PaymentFrequency.MONTHLY
        }
        defaults.update(overrides)
        return DebtCreate(**defaults)

    @staticmethod
    async def authenticate_user(client: AsyncClient, email: str, password: str):
        """Authenticate a user and return session token."""
        response = await client.post(
            "/api/v2/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200

        # Extract session token from response or cookie
        # This depends on your auth implementation
        return response.cookies.get("session_token") or response.json().get("session_token")


# Make helpers available as fixture
@pytest.fixture(scope="session")
def helpers():
    """Test helper functions."""
    return TestHelpers()
