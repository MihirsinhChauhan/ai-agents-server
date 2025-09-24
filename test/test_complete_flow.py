#!/usr/bin/env python3
"""
Test complete flow with proper session handling
"""
import requests
import json
import sys

base_url = "http://localhost:8000/api"

def main():
    # Create session
    session = requests.Session()

    # Step 1: Login
    print("Step 1: Login")
    login_response = session.post(
        f"{base_url}/auth/login",
        json={
            "email": "test_professional@debtease.com",
            "password": "TestSecure123!"
        }
    )

    if login_response.status_code != 200:
        print(f"✗ Login failed: {login_response.status_code}")
        print(login_response.text)
        sys.exit(1)

    print(f"✓ Login successful")
    print(f"Session cookie: {session.cookies.get('session_token')[:20]}...")

    # Check cookies are being sent correctly
    print(f"\nSession cookies: {dict(session.cookies)}")

    # Step 2: Test creating a debt
    print("\nStep 2: Creating test debt")

    # First clear existing debts
    debts_response = session.get(f"{base_url}/debts")
    print(f"Get debts status: {debts_response.status_code}")

    if debts_response.status_code == 200:
        existing_debts = debts_response.json()
        print(f"Found {len(existing_debts.get('debts', []))} existing debts")

        # Clear them
        for debt in existing_debts.get('debts', []):
            del_response = session.delete(f"{base_url}/debts/{debt['id']}")
            print(f"Deleted debt {debt['name']}: {del_response.status_code}")

    # Create a new debt
    debt_data = {
        "name": "Test Credit Card",
        "current_balance": 5000,
        "interest_rate": 18.99,
        "minimum_payment": 150,
        "debt_type": "credit_card",
        "is_high_priority": True
    }

    create_response = session.post(f"{base_url}/debts", json=debt_data)
    print(f"Create debt status: {create_response.status_code}")

    if create_response.status_code in [200, 201]:
        print("✓ Debt created successfully")
    else:
        print(f"✗ Failed to create debt: {create_response.text}")

    # Step 3: Test AI insights
    print("\nStep 3: Testing AI insights")
    insights_response = session.get(f"{base_url}/ai/insights")

    print(f"AI insights status: {insights_response.status_code}")

    if insights_response.status_code == 200:
        insights = insights_response.json()
        print("✓ AI insights retrieved successfully")
        print(f"Keys in response: {list(insights.keys())}")

        # Check for professional features
        has_prof_recs = "professionalRecommendations" in insights
        has_repayment_plan = "repaymentPlan" in insights
        has_risk_assessment = "riskAssessment" in insights

        print(f"\nProfessional Features:")
        print(f"  - Professional Recommendations: {'✓' if has_prof_recs else '✗'}")
        print(f"  - Repayment Plan: {'✓' if has_repayment_plan else '✗'}")
        print(f"  - Risk Assessment: {'✓' if has_risk_assessment else '✗'}")

        if has_prof_recs and insights["professionalRecommendations"]:
            rec = insights["professionalRecommendations"][0]
            print(f"\nSample Professional Recommendation:")
            print(f"  Title: {rec.get('title', 'N/A')}")
            print(f"  Action Steps: {len(rec.get('actionSteps', []))} steps")
            print(f"  Benefits: {len(rec.get('benefits', []))} benefits")
            print(f"  Risks: {len(rec.get('risks', []))} risks")

        # Check metadata
        if "metadata" in insights:
            metadata = insights["metadata"]
            print(f"\nMetadata:")
            print(f"  Enhancement Method: {metadata.get('enhancement_method', 'unknown')}")
            print(f"  Quality Score: {metadata.get('professionalQualityScore', 'N/A')}")
            print(f"  Fallback Used: {metadata.get('fallback_used', False)}")

        return True
    else:
        print(f"✗ Failed to get insights: {insights_response.text}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)