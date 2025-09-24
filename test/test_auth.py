#!/usr/bin/env python3
import requests
import json

# Test auth endpoints
base_url = "http://localhost:8000/api"

# Try to register or login
def test_auth():
    # Try login first
    login_data = {
        "email": "test_professional@debtease.com",
        "password": "TestSecure123!"
    }

    print("Testing login...")
    response = requests.post(f"{base_url}/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        data = response.json()
        print(f"Success! Token field: {list(data.keys())}")
        return data

    # Try registration if login failed
    print("\nTrying registration...")
    register_data = {
        "email": "test_integration@debtease.com",
        "password": "TestSecure123!",
        "full_name": "Test User",
        "monthly_income": 5000
    }

    response = requests.post(f"{base_url}/auth/register", json=register_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code in [200, 201]:
        data = response.json()
        print(f"Success! Token field: {list(data.keys())}")
        return data

    return None

if __name__ == "__main__":
    result = test_auth()
    if result:
        print("\n✓ Auth working")
        print(f"Token key name: {[k for k in result.keys() if 'token' in k.lower() or 'access' in k.lower()]}")
    else:
        print("\n✗ Auth failed")