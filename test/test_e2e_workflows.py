"""
End-to-end tests covering complete user workflows.
Tests full user journeys from registration to AI insights.
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient


@pytest.mark.e2e
class TestUserOnboardingWorkflow:
    """Test complete user onboarding workflow."""

    async def test_complete_user_onboarding_journey(self, test_client):
        """Test complete user journey from registration to dashboard."""
        # Step 1: User Registration
        user_email = f"e2e_{uuid4()}@example.com"
        user_data = {
            "email": user_email,
            "full_name": "E2E Test User",
            "password": "securepass123",
            "monthly_income": 75000.0
        }

        register_response = await test_client.post("/api/v2/auth/register", json=user_data)
        assert register_response.status_code == 201

        user_response = register_response.json()
        user_id = user_response["id"]

        # Step 2: User Login
        login_data = {
            "email": user_email,
            "password": "securepass123"
        }

        login_response = await test_client.post("/api/v2/auth/login", json=login_data)
        assert login_response.status_code == 200

        # Extract session token
        session_token = login_response.cookies.get("session_token")
        assert session_token is not None

        # Set session cookie for subsequent requests
        test_client.cookies.set("session_token", session_token)

        # Step 3: Get User Profile
        profile_response = await test_client.get("/api/v2/auth/me")
        assert profile_response.status_code == 200

        profile_data = profile_response.json()
        assert profile_data["email"] == user_email
        assert profile_data["monthly_income"] == 75000.0

        # Step 4: Create Debts
        debts_data = [
            {
                "user_id": user_id,
                "name": "Primary Credit Card",
                "debt_type": "credit_card",
                "principal_amount": 8000.0,
                "current_balance": 5500.0,
                "interest_rate": 19.99,
                "minimum_payment": 165.0,
                "due_date": "2025-02-15",
                "lender": "Chase Bank",
                "payment_frequency": "monthly"
            },
            {
                "user_id": user_id,
                "name": "Student Loan",
                "debt_type": "education_loan",
                "principal_amount": 25000.0,
                "current_balance": 22000.0,
                "interest_rate": 4.75,
                "minimum_payment": 275.0,
                "due_date": "2025-03-01",
                "lender": "Federal Student Aid",
                "payment_frequency": "monthly"
            }
        ]

        created_debts = []
        for debt_data in debts_data:
            debt_response = await test_client.post("/api/v2/debts", json=debt_data)
            assert debt_response.status_code == 201
            created_debts.append(debt_response.json())

        # Step 5: Get User's Debts
        debts_list_response = await test_client.get("/api/v2/debts")
        assert debts_list_response.status_code == 200

        debts_list = debts_list_response.json()
        assert len(debts_list) == 2

        # Verify debt data
        for debt in debts_list:
            assert debt["user_id"] == user_id
            assert "amount" in debt  # Frontend compatibility field
            assert "remainingAmount" in debt  # Frontend compatibility field

        # Step 6: Record Payments
        for debt in created_debts:
            payment_data = {
                "amount": debt["minimum_payment"],
                "payment_date": "2025-01-15",
                "principal_portion": debt["minimum_payment"] * 0.7,
                "interest_portion": debt["minimum_payment"] * 0.3,
                "notes": f"Minimum payment for {debt['name']}"
            }

            payment_response = await test_client.post(
                f"/api/v2/debts/{debt['id']}/payment",
                json=payment_data
            )
            assert payment_response.status_code == 201

            payment_result = payment_response.json()
            assert "celebration" in payment_result
            assert payment_result["message"] == "Payment recorded successfully!"

        # Step 7: Get Payment History
        payments_response = await test_client.get("/api/v2/payments")
        assert payments_response.status_code == 200

        payments_list = payments_response.json()
        assert len(payments_list) == 2

        # Verify payment data
        for payment in payments_list:
            assert payment["user_id"] == user_id
            assert "date" in payment  # Frontend compatibility field

        # Step 8: Get AI Insights
        insights_response = await test_client.get("/api/ai/insights")
        assert insights_response.status_code == 200

        insights_data = insights_response.json()
        assert "debt_analysis" in insights_data
        assert "recommendations" in insights_data
        assert "metadata" in insights_data

        # Verify debt analysis
        analysis = insights_data["debt_analysis"]
        expected_total_debt = sum(debt["current_balance"] for debt in created_debts)
        assert analysis["total_debt"] == expected_total_debt
        assert analysis["debt_count"] == 2

        # Step 9: Get AI Recommendations
        recommendations_response = await test_client.get("/api/ai/recommendations")
        assert recommendations_response.status_code == 200

        recommendations = recommendations_response.json()
        assert isinstance(recommendations, list)
        # May be empty if no recommendations generated, but should not error

        # Step 10: Get DTI Analysis
        dti_response = await test_client.get("/api/ai/dti")
        assert dti_response.status_code == 200

        dti_data = dti_response.json()
        assert "frontend_dti" in dti_data
        assert "backend_dti" in dti_data
        assert "is_healthy" in dti_data

        # Verify DTI calculation
        monthly_income = 75000.0
        housing_debt = sum(debt["minimum_payment"] for debt in created_debts
                          if debt["debt_type"] == "home_loan")  # None in this case
        total_debt = sum(debt["minimum_payment"] for debt in created_debts)

        expected_frontend_dti = round((housing_debt / monthly_income) * 100, 2)
        expected_backend_dti = round((total_debt / monthly_income) * 100, 2)

        assert dti_data["frontend_dti"] == expected_frontend_dti
        assert dti_data["backend_dti"] == expected_backend_dti

        # Step 11: Generate Custom AI Insights
        custom_insights_data = {
            "monthly_payment_budget": 600.0,
            "preferred_strategy": "avalanche",
            "include_dti": True
        }

        custom_insights_response = await test_client.post("/api/ai/insights", json=custom_insights_data)
        assert custom_insights_response.status_code == 200

        custom_insights = custom_insights_response.json()
        assert "repayment_plan" in custom_insights

        # Success! Complete workflow executed successfully
        print("✅ Complete user onboarding workflow executed successfully!")


@pytest.mark.e2e
class TestDebtManagementWorkflow:
    """Test debt management workflows."""

    async def test_debt_crud_workflow(self, test_client, authenticated_user):
        """Test complete debt CRUD workflow."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])
        user_id = str(authenticated_user["user"].id)

        # Create debt
        debt_data = {
            "user_id": user_id,
            "name": "CRUD Test Debt",
            "debt_type": "personal_loan",
            "principal_amount": 10000.0,
            "current_balance": 8000.0,
            "interest_rate": 10.5,
            "minimum_payment": 200.0,
            "due_date": "2025-03-15",
            "lender": "CRUD Bank",
            "payment_frequency": "monthly"
        }

        create_response = await test_client.post("/api/v2/debts", json=debt_data)
        assert create_response.status_code == 201

        created_debt = create_response.json()
        debt_id = created_debt["id"]

        # Read debt
        read_response = await test_client.get(f"/api/v2/debts/{debt_id}")
        assert read_response.status_code == 200

        read_debt = read_response.json()
        assert read_debt["name"] == "CRUD Test Debt"
        assert read_debt["current_balance"] == 8000.0

        # Update debt
        update_data = {
            "current_balance": 7500.0,
            "minimum_payment": 190.0,
            "name": "Updated CRUD Debt"
        }

        update_response = await test_client.put(f"/api/v2/debts/{debt_id}", json=update_data)
        assert update_response.status_code == 200

        updated_debt = update_response.json()
        assert updated_debt["name"] == "Updated CRUD Debt"
        assert updated_debt["current_balance"] == 7500.0

        # Delete debt
        delete_response = await test_client.delete(f"/api/v2/debts/{debt_id}")
        assert delete_response.status_code == 204

        # Verify debt is deleted
        read_after_delete = await test_client.get(f"/api/v2/debts/{debt_id}")
        assert read_after_delete.status_code == 404


@pytest.mark.e2e
class TestPaymentWorkflow:
    """Test payment recording and tracking workflows."""

    async def test_payment_recording_workflow(self, test_client, authenticated_user, test_debts):
        """Test complete payment recording workflow."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        debt = test_debts[0]
        debt_id = str(debt.id)
        original_balance = debt.current_balance

        # Record payment
        payment_data = {
            "amount": 300.0,
            "payment_date": "2025-01-20",
            "principal_portion": 250.0,
            "interest_portion": 50.0,
            "notes": "Extra payment towards debt"
        }

        payment_response = await test_client.post(
            f"/api/v2/debts/{debt_id}/payment",
            json=payment_data
        )
        assert payment_response.status_code == 201

        payment_result = payment_response.json()

        # Verify payment was recorded
        assert payment_result["payment"]["amount"] == 300.0
        assert payment_result["payment"]["debt_id"] == debt_id

        # Verify debt balance was updated
        updated_debt = payment_result["debt"]
        expected_balance = original_balance - payment_data["principal_portion"]
        assert updated_debt["current_balance"] == expected_balance

        # Verify celebration data is present
        assert "celebration" in payment_result
        celebration = payment_result["celebration"]
        assert "message" in celebration
        assert "confetti_trigger" in celebration

        # Get payment history
        payments_response = await test_client.get("/api/v2/payments")
        assert payments_response.status_code == 200

        payments = payments_response.json()
        assert len(payments) >= 1

        # Find our payment
        our_payment = next((p for p in payments if p["debt_id"] == debt_id), None)
        assert our_payment is not None
        assert our_payment["amount"] == 300.0


@pytest.mark.e2e
class TestAIWorkflow:
    """Test AI functionality workflows."""

    async def test_ai_insights_workflow(self, test_client, authenticated_user, test_debts):
        """Test complete AI insights workflow."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Get debt summary
        summary_response = await test_client.get("/api/ai/debt-summary")
        assert summary_response.status_code == 200

        summary = summary_response.json()
        assert "total_debt" in summary
        assert "debt_count" in summary

        # Get AI insights
        insights_response = await test_client.get("/api/ai/insights")
        assert insights_response.status_code == 200

        insights = insights_response.json()

        # Verify insights structure
        required_keys = ["debt_analysis", "recommendations", "metadata"]
        for key in required_keys:
            assert key in insights

        # Verify debt analysis matches our test debts
        analysis = insights["debt_analysis"]
        expected_total_debt = sum(debt.current_balance for debt in test_debts)
        assert analysis["total_debt"] == expected_total_debt
        assert analysis["debt_count"] == len(test_debts)

        # Verify recommendations (may be empty but should not error)
        recommendations = insights["recommendations"]
        assert isinstance(recommendations, list)

        # Verify metadata
        metadata = insights["metadata"]
        assert "processing_time" in metadata
        assert "generated_at" in metadata

        # Test DTI calculation
        dti_response = await test_client.get("/api/ai/dti")
        assert dti_response.status_code == 200

        dti_data = dti_response.json()
        assert all(key in dti_data for key in ["frontend_dti", "backend_dti", "is_healthy"])

    async def test_ai_caching_workflow(self, test_client, authenticated_user, test_debts):
        """Test AI caching behavior in workflow."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # First request - should generate fresh insights
        response1 = await test_client.get("/api/ai/insights")
        assert response1.status_code == 200
        insights1 = response1.json()

        # Immediate second request - should use cache
        response2 = await test_client.get("/api/ai/insights")
        assert response2.status_code == 200
        insights2 = response2.json()

        # Results should be identical (from cache)
        assert insights1 == insights2

        # Modify debt data (this should invalidate cache)
        debt_id = str(test_debts[0].id)
        update_data = {"current_balance": test_debts[0].current_balance - 100}

        update_response = await test_client.put(f"/api/v2/debts/{debt_id}", json=update_data)
        assert update_response.status_code == 200

        # Next AI request should generate fresh insights
        response3 = await test_client.get("/api/ai/insights")
        assert response3.status_code == 200
        insights3 = response3.json()

        # Results should be different now (cache invalidated)
        assert insights3 != insights1


@pytest.mark.e2e
class TestErrorHandlingWorkflow:
    """Test error handling in complete workflows."""

    async def test_workflow_error_recovery(self, test_client):
        """Test error handling and recovery in workflows."""
        # Try to access protected endpoints without authentication
        endpoints = [
            "/api/v2/debts",
            "/api/ai/insights",
            "/api/ai/dti"
        ]

        for endpoint in endpoints:
            response = await test_client.get(endpoint)
            assert response.status_code == 401

        # Try invalid operations
        invalid_debt_data = {
            "user_id": str(uuid4()),
            "name": "",
            "debt_type": "invalid_type",
            "principal_amount": -1000,
            "current_balance": 3000,
            "interest_rate": 18.99,
            "minimum_payment": 150,
            "due_date": "invalid-date",
            "lender": "Test Bank",
            "payment_frequency": "monthly"
        }

        # This should fail validation
        response = await test_client.post("/api/v2/debts", json=invalid_debt_data)
        assert response.status_code in [401, 422]  # Auth error or validation error

    async def test_ai_error_handling(self, test_client, authenticated_user):
        """Test AI error handling when user has no debts."""
        # Set session cookie
        test_client.cookies.set("session_token", authenticated_user["session_token"])

        # Try to get AI insights without debts
        insights_response = await test_client.get("/api/ai/insights")
        # Should return 400 error for no debts
        assert insights_response.status_code == 400

        error_data = insights_response.json()
        assert "detail" in error_data

        # Recommendations should return empty list (not error)
        rec_response = await test_client.get("/api/ai/recommendations")
        assert rec_response.status_code == 200
        assert rec_response.json() == []

        # DTI should fail without income
        dti_response = await test_client.get("/api/ai/dti")
        assert dti_response.status_code == 400
