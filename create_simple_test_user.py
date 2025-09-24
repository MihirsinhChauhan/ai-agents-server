#!/usr/bin/env python3
"""
Create a simple test user with verified credentials for frontend testing
"""

import requests
import json

def create_and_verify_user():
    """Create a simple test user and verify login works."""
    base_url = "http://localhost:8000/api"

    print("🚀 Creating Simple Test User for Frontend")
    print("=" * 50)

    # User data
    user_data = {
        "email": "test@debtease.com",
        "password": "Test123!",
        "full_name": "Test User",
        "phone": "+91-9999999999"
    }

    try:
        # Try to register
        print("👤 Creating user...")
        register_response = requests.post(f"{base_url}/auth/register", json=user_data)

        if register_response.status_code == 201:
            user_info = register_response.json()
            print(f"✅ User created successfully!")
            print(f"   User ID: {user_info['user']['id']}")
            print(f"   Email: {user_info['user']['email']}")
        else:
            print(f"⚠️  Registration response: {register_response.status_code}")
            print(f"   Message: {register_response.text}")

        # Test login immediately
        print("\n🔑 Testing login...")
        login_response = requests.post(f"{base_url}/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })

        if login_response.status_code == 200:
            login_info = login_response.json()
            print(f"✅ Login successful!")
            print(f"   User ID: {login_info['user']['id']}")
            print(f"   Session expires: {login_info['session_expires_at']}")

            # Create a simple debt for testing
            session = requests.Session()
            session.post(f"{base_url}/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            })

            print("\n💳 Creating test debt...")
            debt_data = {
                "name": "Test Credit Card",
                "debt_type": "credit_card",
                "principal_amount": 50000.00,
                "current_balance": 35000.00,
                "interest_rate": 24.0,
                "minimum_payment": 1500.00,
                "due_date": "2024-03-15",
                "lender": "Test Bank",
                "payment_frequency": "monthly",
                "is_high_priority": True
            }

            debt_response = session.post(f"{base_url}/debts/", json=debt_data)
            if debt_response.status_code == 201:
                debt_info = debt_response.json()
                print(f"✅ Test debt created!")
                print(f"   Debt: {debt_info['name']}")
                print(f"   Amount: ₹{debt_info['current_balance']:,.0f}")
            else:
                print(f"⚠️  Debt creation: {debt_response.status_code} - {debt_response.text}")

            # Test AI insights
            print("\n🤖 Testing AI insights...")
            insights_response = session.post(f"{base_url}/ai/insights", json={"includeDti": True})
            if insights_response.status_code == 200:
                insights = insights_response.json()
                debt_analysis = insights.get('debt_analysis', {})
                recommendations = insights.get('recommendations', [])

                print(f"✅ AI insights generated!")
                print(f"   Total debt analyzed: ₹{debt_analysis.get('total_debt', 0):,.0f}")
                print(f"   Recommendations: {len(recommendations)}")

                if recommendations:
                    print(f"   Top recommendation: {recommendations[0].get('title', 'Unknown')}")

                return True
            else:
                print(f"⚠️  AI insights: {insights_response.status_code} - {insights_response.text}")
                return False

        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function."""
    print("🎯 SIMPLE TEST USER CREATION")
    print("Creating a verified test user for frontend login testing")
    print("=" * 60)

    success = create_and_verify_user()

    print("\n" + "=" * 60)
    print("🎉 TEST USER CREATION COMPLETE!")
    print("=" * 60)

    if success:
        print("✅ Test user created and verified successfully!")
        print("✅ Login credentials tested and working")
        print("✅ AI insights generating properly")
        print("\n📋 FRONTEND LOGIN CREDENTIALS:")
        print("   📧 Email: test@debtease.com")
        print("   🔑 Password: Test123!")
        print("   👤 Name: Test User")
        print("\n💡 Use these credentials to log into the frontend and test AI insights!")
    else:
        print("⚠️  Issues encountered during user creation")
        print("💡 Try the alternative credentials:")
        print("   📧 Email: aditya@test.com")
        print("   🔑 Password: Password123")

if __name__ == "__main__":
    main()