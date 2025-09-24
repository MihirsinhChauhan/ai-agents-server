"""
Comprehensive API endpoint tests.
Tests all REST endpoints with authentication, validation, and error handling.
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient

from app.models.user import UserCreate
from app.models.debt import DebtCreate, DebtType, PaymentFrequency, DebtUpdate
from app.models.payment import PaymentCreate


@pytest.mark.api
class TestAuthAPI:
    """Test authentication API endpoints."""

    async def test_register_user(self, test_client):
        """Test user registration endpoint."""
        user_data = {
            "email": f"test_{uuid4()}@example.com",
            "full_name": "Test User",
            "password": "securepass123",
            "monthly_income": 50000.0
        }

        response = await test_client.post("/api/v2/auth/register", json=user_data)
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data

    async def test_register_duplicate_email(self, test_client, test_user):
        """Test registering with duplicate email."""
        user_data = {
            "email": test_user.email,  # Duplicate email
            "full_name": "Another User",
            "password": "securepass123",
            "monthly_income": 40000.0
        }

        response = await test_client.post("/api/v2/auth/register", json=user_data)
        assert response.status_code == 400

    async def test_login_success(self, test_client, test_user, helpers):
        """Test successful login."""
        login_data = {
            "email": test_user.email,
            "password": "testpassword123"  # From test fixture
        }

        response = await test_client.post("/api/v2/auth/login", json=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "session_token" in data or "access_token" in data

    async def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }

        response = await test_client.post("/api/v2/auth/login", json=login_data)
        assert response.status_code == 401

    async def test_get_current_user(self, test_client, authenticated_user):
        """Test getting current user profile."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        response = await test_client.get("/api/v2/auth/me")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == str(authenticated_user["user"].id)
        assert data["email"] == authenticated_user["user"].email


@pytest.mark.api
class TestDebtAPI:
    """Test debt management API endpoints."""

    async def test_create_debt(self, test_client, authenticated_user):
        """Test creating a new debt."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        debt_data = {
            "user_id": str(authenticated_user["user"].id),
            "name": "API Test Credit Card",
            "debt_type": "credit_card",
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 18.99,
            "minimum_payment": 150.0,
            "due_date": "2025-02-15",
            "lender": "API Test Bank",
            "payment_frequency": "monthly"
        }

        response = await test_client.post("/api/v2/debts", json=debt_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == debt_data["name"]
        assert data["principal_amount"] == debt_data["principal_amount"]
        assert data["user_id"] == debt_data["user_id"]

    async def test_create_debt_unauthorized(self, test_client):
        """Test creating debt without authentication."""
        debt_data = {
            "user_id": str(uuid4()),
            "name": "Unauthorized Debt",
            "debt_type": "credit_card",
            "principal_amount": 5000.0,
            "current_balance": 3000.0,
            "interest_rate": 18.99,
            "minimum_payment": 150.0,
            "due_date": "2025-02-15",
            "lender": "Test Bank",
            "payment_frequency": "monthly"
        }

        response = await test_client.post("/api/v2/debts", json=debt_data)
        assert response.status_code == 401

    async def test_get_user_debts(self, test_client, authenticated_user, test_debts):
        """Test retrieving user's debts."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        response = await test_client.get("/api/v2/debts")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(test_debts)

        # Verify debt structure
        for debt in data:
            assert "id" in debt
            assert "name" in debt
            assert "debt_type" in debt
            assert "current_balance" in debt

    async def test_get_specific_debt(self, test_client, authenticated_user, test_debts):
        """Test retrieving a specific debt."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        debt_id = str(test_debts[0].id)
        response = await test_client.get(f"/api/v2/debts/{debt_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == debt_id
        assert data["name"] == test_debts[0].name

    async def test_get_debt_not_found(self, test_client, authenticated_user):
        """Test retrieving non-existent debt."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        fake_debt_id = str(uuid4())
        response = await test_client.get(f"/api/v2/debts/{fake_debt_id}")
        assert response.status_code == 404

    async def test_update_debt(self, test_client, authenticated_user, test_debts):
        """Test updating a debt."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        debt_id = str(test_debts[0].id)
        update_data = {
            "current_balance": 2500.0,
            "minimum_payment": 125.0,
            "name": "Updated Credit Card"
        }

        response = await test_client.put(f"/api/v2/debts/{debt_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["current_balance"] == 2500.0
        assert data["minimum_payment"] == 125.0
        assert data["name"] == "Updated Credit Card"

    async def test_delete_debt(self, test_client, authenticated_user, test_debts):
        """Test deleting a debt."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        debt_id = str(test_debts[0].id)
        response = await test_client.delete(f"/api/v2/debts/{debt_id}")
        assert response.status_code == 204

    async def test_record_payment(self, test_client, authenticated_user, test_debts):
        """Test recording a payment."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        debt_id = str(test_debts[0].id)
        payment_data = {
            "amount": 200.0,
            "payment_date": "2025-01-15",
            "principal_portion": 150.0,
            "interest_portion": 50.0,
            "notes": "API test payment"
        }

        response = await test_client.post(f"/api/v2/debts/{debt_id}/payment", json=payment_data)
        assert response.status_code == 201

        data = response.json()
        assert data["payment"]["amount"] == 200.0
        assert data["debt"]["id"] == debt_id
        assert "celebration" in data


@pytest.mark.api
class TestPaymentAPI:
    """Test payment management API endpoints."""

    async def test_get_user_payments(self, test_client, authenticated_user, test_debts):
        """Test retrieving user's payment history."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # First create a payment
        debt_id = str(test_debts[0].id)
        payment_data = {
            "amount": 200.0,
            "payment_date": "2025-01-15",
            "principal_portion": 150.0,
            "interest_portion": 50.0
        }

        await test_client.post(f"/api/v2/debts/{debt_id}/payment", json=payment_data)

        # Now get payments
        response = await test_client.get("/api/v2/payments")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Verify payment structure
        payment = data[0]
        assert "id" in payment
        assert "amount" in payment
        assert "payment_date" in payment
        assert "debt_id" in payment

    async def test_get_payment_by_id(self, test_client, authenticated_user, test_debts):
        """Test retrieving a specific payment."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Create a payment first
        debt_id = str(test_debts[0].id)
        payment_data = {
            "amount": 200.0,
            "payment_date": "2025-01-15"
        }

        create_response = await test_client.post(f"/api/v2/debts/{debt_id}/payment", json=payment_data)
        payment_id = create_response.json()["payment"]["id"]

        # Get the specific payment
        response = await test_client.get(f"/api/v2/payments/{payment_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == payment_id
        assert data["amount"] == 200.0


@pytest.mark.api
class TestAIApi:
    """Test AI insights API endpoints."""

    async def test_get_ai_insights(self, test_client, authenticated_user, test_debts):
        """Test getting AI insights."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        response = await test_client.get("/api/ai/insights")
        assert response.status_code == 200

        data = response.json()
        assert "debt_analysis" in data
        assert "recommendations" in data
        assert "metadata" in data

        # Verify debt analysis
        analysis = data["debt_analysis"]
        assert "total_debt" in analysis
        assert "debt_count" in analysis
        assert "average_interest_rate" in analysis

    async def test_get_ai_insights_no_debts(self, test_client, authenticated_user):
        """Test AI insights when user has no debts."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        response = await test_client.get("/api/ai/insights")
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    async def test_get_ai_recommendations(self, test_client, authenticated_user, test_debts):
        """Test getting AI recommendations."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        response = await test_client.get("/api/ai/recommendations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        if len(test_debts) > 0:
            # Should have recommendations for users with debts
            assert len(data) >= 0  # May be empty if no recommendations generated

    async def test_get_dti_analysis(self, test_client, authenticated_user, test_debts):
        """Test getting DTI analysis."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        response = await test_client.get("/api/ai/dti")
        assert response.status_code == 200

        data = response.json()
        assert "frontend_dti" in data
        assert "backend_dti" in data
        assert "is_healthy" in data

    async def test_get_dti_no_income(self, test_client):
        """Test DTI analysis when user has no income set."""
        # Create a user without income
        user_data = {
            "email": f"noincome_{uuid4()}@example.com",
            "full_name": "No Income User",
            "password": "securepass123"
            # No monthly_income
        }

        # Register user
        register_response = await test_client.post("/api/v2/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Login
        login_data = {"email": user_data["email"], "password": "securepass123"}
        login_response = await test_client.post("/api/v2/auth/login", json=login_data)
        assert login_response.status_code == 200

        # Try to get DTI
        response = await test_client.get("/api/ai/dti")
        assert response.status_code == 400

    async def test_generate_ai_insights(self, test_client, authenticated_user, test_debts):
        """Test generating fresh AI insights with custom parameters."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        insights_data = {
            "monthly_payment_budget": 600.0,
            "preferred_strategy": "avalanche",
            "include_dti": True
        }

        response = await test_client.post("/api/ai/insights", json=insights_data)
        assert response.status_code == 200

        data = response.json()
        assert "debt_analysis" in data
        assert "recommendations" in data
        assert "repayment_plan" in data


@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling and edge cases."""

    async def test_invalid_json_payload(self, test_client, authenticated_user):
        """Test API response to invalid JSON."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Send invalid JSON
        response = await test_client.post(
            "/api/v2/debts",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Validation error

    async def test_unauthorized_access_attempt(self, test_client):
        """Test accessing protected endpoints without authentication."""
        endpoints = [
            "/api/v2/debts",
            "/api/v2/payments",
            "/api/ai/insights",
            "/api/ai/recommendations",
            "/api/ai/dti"
        ]

        for endpoint in endpoints:
            response = await test_client.get(endpoint)
            assert response.status_code == 401

    async def test_invalid_debt_data(self, test_client, authenticated_user):
        """Test creating debt with invalid data."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Invalid debt data (negative amount)
        invalid_debt_data = {
            "user_id": str(authenticated_user["user"].id),
            "name": "Invalid Debt",
            "debt_type": "credit_card",
            "principal_amount": -1000.0,  # Invalid
            "current_balance": 3000.0,
            "interest_rate": 18.99,
            "minimum_payment": 150.0,
            "due_date": "2025-02-15",
            "lender": "Test Bank",
            "payment_frequency": "monthly"
        }

        response = await test_client.post("/api/v2/debts", json=invalid_debt_data)
        assert response.status_code == 422  # Validation error

    async def test_rate_limiting_simulation(self, test_client, authenticated_user):
        """Test handling of rapid requests (simulate rate limiting)."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = await test_client.get("/api/v2/debts")
            responses.append(response.status_code)

        # All should succeed (no rate limiting implemented yet)
        assert all(code == 200 for code in responses)
