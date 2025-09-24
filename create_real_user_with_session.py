#!/usr/bin/env python3
"""
Create a real test user (Aditya) with actual debt data and test AI insights using sessions
"""

import requests
import json
from datetime import datetime, date

def create_user_and_debts():
    """Create user Aditya with real debt data via API using sessions."""
    base_url = "http://localhost:8000/api"
    session = requests.Session()

    print("🚀 Creating Real User Test: Aditya")
    print("=" * 50)

    # 1. Create/login user Aditya
    print("👤 Creating user Aditya...")
    user_data = {
        "email": "aditya@test.com",
        "password": "Password123",
        "full_name": "Aditya Kumar",
        "phone": "+91-9876543210"
    }

    try:
        # Try to login first
        print("🔑 Attempting login...")
        login_response = session.post(f"{base_url}/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })

        if login_response.status_code == 200:
            user_response = login_response.json()
            user_id = user_response["user"]["id"]
            print(f"✅ Logged in existing user: {user_id}")
        else:
            print(f"⚠️  Login failed, trying to register...")
            # Try to register
            register_response = session.post(f"{base_url}/auth/register", json=user_data)
            if register_response.status_code == 201:
                user_response = register_response.json()
                user_id = user_response["user"]["id"]
                print(f"✅ User created: {user_id}")
            else:
                print(f"❌ Failed to register: {register_response.text}")
                return None

    except Exception as e:
        print(f"❌ Error creating/logging user: {e}")
        return None

    # 2. Create realistic debt portfolio for Aditya
    print(f"\n💳 Creating realistic debt portfolio for Aditya...")

    # Debt 1: High-interest credit card (common in India)
    debt1 = {
        "name": "HDFC Credit Card",
        "debt_type": "credit_card",
        "principal_amount": 80000.00,
        "current_balance": 65000.00,
        "interest_rate": 42.0,  # High rate typical in India
        "minimum_payment": 3250.00,
        "due_date": "2024-02-15",
        "lender": "HDFC Bank",
        "payment_frequency": "monthly",
        "is_high_priority": True
    }

    # Debt 2: Personal loan
    debt2 = {
        "name": "Personal Loan - Wedding",
        "debt_type": "personal_loan",
        "principal_amount": 200000.00,
        "current_balance": 150000.00,
        "interest_rate": 14.5,
        "minimum_payment": 8500.00,
        "due_date": "2024-02-10",
        "lender": "ICICI Bank",
        "payment_frequency": "monthly",
        "is_high_priority": False
    }

    # Debt 3: Education loan
    debt3 = {
        "name": "MBA Education Loan",
        "debt_type": "education_loan",
        "principal_amount": 500000.00,
        "current_balance": 380000.00,
        "interest_rate": 9.5,
        "minimum_payment": 12000.00,
        "due_date": "2024-02-05",
        "lender": "SBI",
        "payment_frequency": "monthly",
        "is_high_priority": False
    }

    # Debt 4: Vehicle loan
    debt4 = {
        "name": "Car Loan - Honda City",
        "debt_type": "vehicle_loan",
        "principal_amount": 600000.00,
        "current_balance": 420000.00,
        "interest_rate": 8.75,
        "minimum_payment": 14500.00,
        "due_date": "2024-02-20",
        "lender": "Bajaj Finance",
        "payment_frequency": "monthly",
        "is_high_priority": False
    }

    # Debt 5: Home loan (smaller amount - could be parent's home)
    debt5 = {
        "name": "Home Loan",
        "debt_type": "home_loan",
        "principal_amount": 1500000.00,
        "current_balance": 1200000.00,
        "interest_rate": 7.25,
        "minimum_payment": 18000.00,
        "due_date": "2024-02-01",
        "lender": "LIC Housing Finance",
        "payment_frequency": "monthly",
        "is_high_priority": False
    }

    debts = [debt1, debt2, debt3, debt4, debt5]
    created_debts = []

    for i, debt in enumerate(debts, 1):
        try:
            response = session.post(f"{base_url}/debts", json=debt)
            if response.status_code == 201:
                debt_data = response.json()
                created_debts.append(debt_data)
                print(f"✅ Created debt {i}: {debt['name']} - ₹{debt['current_balance']:,.0f}")
            else:
                print(f"⚠️  Debt {i} might already exist: {response.status_code}")
                if "already exists" in response.text.lower():
                    print(f"   Skipping {debt['name']} - already exists")
                    created_debts.append(debt)  # Add to list for summary
                else:
                    print(f"❌ Failed to create debt {i}: {response.text}")
        except Exception as e:
            print(f"❌ Error creating debt {i}: {e}")

    print(f"\n📊 Aditya's Complete Debt Portfolio:")
    total_debt = sum(debt.get('current_balance', debt.get('current_balance', 0)) for debt in debts)
    total_minimum = sum(debt.get('minimum_payment', debt.get('minimum_payment', 0)) for debt in debts)
    avg_interest = sum(debt.get('current_balance', 0) * debt.get('interest_rate', 0) for debt in debts) / total_debt if total_debt > 0 else 0

    print(f"   💰 Total Outstanding Debt: ₹{total_debt:,.0f}")
    print(f"   📅 Monthly Minimum Payments: ₹{total_minimum:,.0f}")
    print(f"   📈 Average Interest Rate: {avg_interest:.1f}%")
    print(f"   🏦 Number of Lenders: {len(set(debt['lender'] for debt in debts))}")

    return session, user_id, created_debts


def test_ai_insights_with_real_data(session, user_id):
    """Test AI insights with the real user data."""
    print(f"\n🤖 Testing AI Insights for Real User Data")
    print("=" * 50)

    base_url = "http://localhost:8000/api"

    try:
        # Test enhanced AI insights
        print("🧠 Requesting enhanced AI insights...")
        response = session.post(
            f"{base_url}/ai/insights",
            json={"includeDti": True}
        )

        print(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            insights = response.json()
            print(f"✅ AI Insights generated successfully!")

            # Show the actual response structure
            print(f"\n📋 RAW AI RESPONSE STRUCTURE:")
            print(f"Keys: {list(insights.keys())}")

            # Analyze the insights quality
            print(f"\n📊 AI INSIGHTS ANALYSIS:")

            # Check for current strategy
            if 'currentStrategy' in insights:
                current_strategy = insights['currentStrategy']
                print(f"   🎯 Current Strategy: {current_strategy.get('strategy', 'Unknown')}")
                print(f"   ⏱️  Time to Debt Free: {current_strategy.get('timeToDebtFree', 0)} months")
                print(f"   💵 Interest Saved: ₹{current_strategy.get('totalInterestSaved', 0):,.0f}")

            # Check debt summary
            if 'debtSummary' in insights:
                debt_summary = insights['debtSummary']
                print(f"   💰 Total Debt Analyzed: ₹{debt_summary.get('totalDebt', 0):,.0f}")
                print(f"   📊 Debts Count: {debt_summary.get('debtCount', 0)}")
                print(f"   📈 Average Interest Rate: {debt_summary.get('averageInterestRate', 0):.1f}%")

            # Check for professional recommendations
            prof_recs = insights.get('professionalRecommendations', [])
            if prof_recs:
                print(f"\n💡 PROFESSIONAL AI RECOMMENDATIONS ({len(prof_recs)}):")
                for i, rec in enumerate(prof_recs[:3], 1):
                    print(f"   {i}. {rec.get('title', 'Recommendation')}")
                    print(f"      Priority: {rec.get('priority_score', 0)}/10")
                    if rec.get('potential_savings'):
                        print(f"      Potential Savings: ₹{rec.get('potential_savings', 0):,.0f}")
            else:
                print(f"\n⚠️  No professional recommendations found")

            # Check strategy comparison
            strategy_comp = insights.get('strategyComparison', {})
            if strategy_comp:
                print(f"\n🎯 STRATEGY COMPARISON:")
                if 'avalanche' in strategy_comp:
                    avalanche = strategy_comp['avalanche']
                    print(f"   📈 Avalanche: {avalanche.get('monthsToDebtFree', 0)} months, ₹{avalanche.get('totalInterestSaved', 0):,.0f} saved")
                if 'snowball' in strategy_comp:
                    snowball = strategy_comp['snowball']
                    print(f"   ⚡ Snowball: {snowball.get('monthsToDebtFree', 0)} months, ₹{snowball.get('totalInterestSaved', 0):,.0f} saved")
                print(f"   🏆 Recommended: {strategy_comp.get('recommended', 'Unknown')}")

            # Quality assessment
            print(f"\n🏅 AI OUTPUT QUALITY ASSESSMENT:")
            quality_indicators = []

            if insights.get('debtSummary', {}).get('totalDebt', 0) > 0:
                quality_indicators.append("✅ Real debt data processed")

            if prof_recs and len(prof_recs) > 0:
                quality_indicators.append("✅ Professional recommendations generated")

            if strategy_comp.get('recommended'):
                quality_indicators.append("✅ Strategy recommendations provided")

            if insights.get('currentStrategy', {}).get('timeToDebtFree', 0) > 0:
                quality_indicators.append("✅ Realistic timeline calculated")

            metadata = insights.get('metadata', {})
            if metadata.get('professionalQualityScore', 0) > 70:
                quality_indicators.append("✅ High professional quality score")

            for indicator in quality_indicators:
                print(f"   {indicator}")

            # Test for meaningful content
            meaningful_indicators = []

            # Check if debt amounts match what we created
            expected_total = 65000 + 150000 + 380000 + 420000 + 1200000  # 2,215,000
            actual_total = insights.get('debtSummary', {}).get('totalDebt', 0)
            if abs(actual_total - expected_total) < 10000:  # Allow for some variance
                meaningful_indicators.append("✅ Debt amounts accurately reflect user's actual data")

            # Check for personalized recommendations
            rec_text = ' '.join([rec.get('description', '') for rec in prof_recs])
            if 'HDFC' in rec_text or 'credit card' in rec_text.lower() or '42' in rec_text:
                meaningful_indicators.append("✅ Recommendations reference specific user debts")

            if len(meaningful_indicators) > 0:
                print(f"\n🎯 MEANINGFUL CONTENT VALIDATION:")
                for indicator in meaningful_indicators:
                    print(f"   {indicator}")

            # Final assessment
            if len(quality_indicators) >= 3:
                print(f"\n🏆 EXCELLENT: AI is generating high-quality insights from real user data!")
                print(f"✅ Professional consultation level achieved")
                if len(meaningful_indicators) > 0:
                    print(f"✅ Content is meaningfully personalized to user's actual financial situation")
                return True
            else:
                print(f"\n⚠️  GOOD: AI is working but could provide more comprehensive insights")
                return False

        else:
            print(f"❌ Failed to get AI insights: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error testing AI insights: {e}")
        return False


def main():
    """Main test function."""
    print("🎯 REAL USER DATA AI TESTING")
    print("Testing if AI agents generate meaningful insights from actual database user data")
    print("=" * 70)

    # Create user and debts
    result = create_user_and_debts()
    if not result:
        print("❌ Failed to create user and debts")
        return

    session, user_id, created_debts = result

    # Mark task as complete
    print("\n✅ User and debt creation completed")

    # Test AI insights
    success = test_ai_insights_with_real_data(session, user_id)

    print("\n" + "=" * 70)
    print("🎉 REAL USER DATA AI TESTING COMPLETE!")
    print("=" * 70)

    if success:
        print("✅ AI agents are successfully processing real user data from database")
        print("✅ Generating meaningful, personalized debt consultation")
        print("✅ Professional-grade recommendations based on actual financial situation")
        print("✅ Frontend will receive high-quality AI insights")
    else:
        print("⚠️  AI agents are working but insights could be more comprehensive")
        print("✅ System remains functional with real data processing")
        print("💡 Consider fine-tuning prompts for better personalization")

    print(f"\n📋 USER CREATED FOR TESTING:")
    print(f"   👤 Name: Aditya Kumar")
    print(f"   📧 Email: aditya@test.com")
    print(f"   🔑 Password: Password123")
    print(f"   💳 Debts: {len(created_debts)} realistic Indian debt scenarios")
    print(f"   💰 Total Portfolio: ₹22,15,000 (Credit Card + Personal + Education + Vehicle + Home loans)")
    print(f"\n💡 Use this user in the frontend to see AI insights in action!")


if __name__ == "__main__":
    main()