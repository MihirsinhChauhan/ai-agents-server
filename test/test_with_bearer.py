#!/usr/bin/env python3
"""
Test with Bearer token from session cookie
"""
import requests
import json
import sys

base_url = "http://localhost:8000/api"

def main():
    # Create session
    session = requests.Session()

    # Step 1: Login to get session token
    print("Step 1: Login to get session token")
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

    # Get session token from cookie
    session_token = session.cookies.get('session_token')
    print(f"✓ Login successful")
    print(f"Session token: {session_token[:20]}...")

    # Use Bearer token instead of cookies
    headers = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    }

    # Step 2: Test with Bearer token
    print("\nStep 2: Testing with Bearer token")

    # Get debts
    debts_response = requests.get(f"{base_url}/debts", headers=headers)
    print(f"Get debts status: {debts_response.status_code}")

    if debts_response.status_code == 200:
        print("✓ Bearer token authentication working")
        existing_debts = debts_response.json()
        # Handle both list and dict response formats
        if isinstance(existing_debts, list):
            debts_list = existing_debts
        else:
            debts_list = existing_debts.get('debts', [])

        print(f"Found {len(debts_list)} existing debts")

        # Clear existing debts
        for debt in debts_list:
            del_response = requests.delete(
                f"{base_url}/debts/{debt['id']}",
                headers=headers
            )
            if del_response.status_code == 200:
                print(f"✓ Deleted debt: {debt['name']}")

        # Create test debts with all required fields
        test_debts = [
            {
                "name": "High Interest Card",
                "lender": "Bank ABC",
                "principal_amount": 15000,
                "current_balance": 15000,
                "interest_rate": 24.99,
                "minimum_payment": 450,
                "debt_type": "credit_card",
                "is_high_priority": True
            },
            {
                "name": "Personal Loan",
                "lender": "Finance Corp",
                "principal_amount": 25000,
                "current_balance": 25000,
                "interest_rate": 12.5,
                "minimum_payment": 550,
                "debt_type": "personal_loan",
                "is_high_priority": False
            },
            {
                "name": "Car Loan",
                "lender": "Auto Finance",
                "principal_amount": 20000,
                "current_balance": 18000,
                "interest_rate": 6.5,
                "minimum_payment": 380,
                "debt_type": "vehicle_loan",  # Fixed from auto_loan
                "is_high_priority": False
            }
        ]

        for debt_data in test_debts:
            create_response = requests.post(
                f"{base_url}/debts",
                json=debt_data,
                headers=headers
            )
            if create_response.status_code in [200, 201]:
                print(f"✓ Created debt: {debt_data['name']}")
            else:
                print(f"✗ Failed to create {debt_data['name']}: {create_response.text}")

        # Step 3: Test AI insights
        print("\nStep 3: Testing AI insights")
        insights_response = requests.get(
            f"{base_url}/ai/insights",
            headers=headers
        )

        print(f"AI insights status: {insights_response.status_code}")

        if insights_response.status_code == 200:
            insights = insights_response.json()
            print("✓ AI insights retrieved successfully")
            print(f"\nKeys in response: {list(insights.keys())}")

            # Check for professional features
            has_prof_recs = "professionalRecommendations" in insights
            has_repayment_plan = "repaymentPlan" in insights and isinstance(insights["repaymentPlan"], dict)
            has_risk_assessment = "riskAssessment" in insights

            print(f"\n🎯 Professional Features Check:")
            print(f"  Professional Recommendations: {'✓ PRESENT' if has_prof_recs else '✗ MISSING'}")
            print(f"  Enhanced Repayment Plan: {'✓ PRESENT' if has_repayment_plan else '✗ MISSING'}")
            print(f"  Risk Assessment: {'✓ PRESENT' if has_risk_assessment else '✗ MISSING'}")

            if has_prof_recs and insights["professionalRecommendations"]:
                rec = insights["professionalRecommendations"][0]
                print(f"\n📋 Sample Professional Recommendation:")
                print(f"  Title: {rec.get('title', 'N/A')}")
                print(f"  Type: {rec.get('type', 'N/A')}")
                print(f"  Priority: {rec.get('priority', 'N/A')}")
                print(f"  Action Steps: {len(rec.get('actionSteps', []))} steps")
                if rec.get('actionSteps'):
                    print(f"    - {rec['actionSteps'][0][:50]}...")
                print(f"  Benefits: {len(rec.get('benefits', []))} benefits")
                print(f"  Risks: {len(rec.get('risks', []))} risks")
                print(f"  Timeline: {rec.get('timeline', 'N/A')}")

            if has_repayment_plan and insights["repaymentPlan"]:
                plan = insights["repaymentPlan"]
                if "primaryStrategy" in plan:
                    print(f"\n💰 Repayment Plan:")
                    print(f"  Strategy: {plan.get('strategy', 'N/A')}")
                    print(f"  Monthly Payment: ₹{plan.get('monthlyPayment', 0):,.2f}")
                    print(f"  Time to Freedom: {plan.get('timeToFreedom', 0)} months")
                    print(f"  Total Savings: ₹{plan.get('totalSavings', 0):,.2f}")

                    if "primaryStrategy" in plan:
                        primary = plan["primaryStrategy"]
                        print(f"  Primary Strategy: {primary.get('name', 'N/A')}")
                        print(f"    Benefits: {len(primary.get('benefits', []))} listed")
                        print(f"    Reasoning: {primary.get('reasoning', 'N/A')[:100]}...")

            if has_risk_assessment and insights["riskAssessment"]:
                risk = insights["riskAssessment"]
                print(f"\n⚠️ Risk Assessment:")
                print(f"  Level: {risk.get('level', 'N/A')}")
                print(f"  Score: {risk.get('score', 'N/A')}/10")
                print(f"  Factors: {len(risk.get('factors', []))} identified")
                if risk.get('factors'):
                    factor = risk['factors'][0]
                    print(f"    - {factor.get('category', 'N/A')}: {factor.get('impact', 'N/A')[:50]}...")

            # Check metadata
            if "metadata" in insights:
                metadata = insights["metadata"]
                print(f"\n📊 Quality Metrics:")
                print(f"  Enhancement Method: {metadata.get('enhancement_method', 'unknown')}")
                print(f"  Professional Quality Score: {metadata.get('professionalQualityScore', 'N/A')}/100")
                print(f"  Fallback Used: {metadata.get('fallback_used', False)}")
                print(f"  Processing Time: {metadata.get('processing_time', 'N/A')}s")

            # Overall assessment
            professional_features = sum([has_prof_recs, has_repayment_plan, has_risk_assessment])
            print(f"\n{'='*60}")
            print(f"✅ PROFESSIONAL FEATURES SCORE: {professional_features}/3")

            if professional_features == 3:
                print("🎯 EXCELLENT: Full professional consultation features active!")
            elif professional_features >= 2:
                print("✓ GOOD: Most professional features are working")
            elif professional_features >= 1:
                print("⚠️ PARTIAL: Some professional features active")
            else:
                print("❌ BASIC: No professional features detected")
            print(f"{'='*60}")

            return professional_features >= 2
        else:
            print(f"✗ Failed to get insights: {insights_response.text}")
            return False
    else:
        print(f"✗ Bearer token not working: {debts_response.text}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)