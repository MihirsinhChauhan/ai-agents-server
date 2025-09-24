#!/usr/bin/env python3
import requests
import json

# Test with session
base_url = "http://localhost:8000/api"

def test_with_session():
    # Create a session to maintain cookies
    session = requests.Session()

    # Login
    login_data = {
        "email": "test_professional@debtease.com",
        "password": "TestSecure123!"
    }

    print("Testing login with session...")
    response = session.post(f"{base_url}/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Cookies: {session.cookies}")

    if response.status_code == 200:
        # Test accessing a protected endpoint
        print("\nTesting protected endpoint...")
        debts_response = session.get(f"{base_url}/debts")
        print(f"Debts Status: {debts_response.status_code}")
        print(f"Debts Response: {debts_response.text[:200] if debts_response.text else 'empty'}")

        # Test AI insights
        print("\nTesting AI insights endpoint...")
        insights_response = session.get(f"{base_url}/ai/insights")
        print(f"Insights Status: {insights_response.status_code}")
        if insights_response.status_code == 200:
            data = insights_response.json()
            print(f"Insights keys: {list(data.keys())}")
        else:
            print(f"Insights Error: {insights_response.text}")

if __name__ == "__main__":
    test_with_session()