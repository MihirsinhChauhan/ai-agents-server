#!/usr/bin/env python3
"""
Debug script for AI insights issues
"""

import asyncio
import logging
import traceback
from uuid import UUID

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_ai_insights():
    """Test the AI insights functionality step by step"""

    try:
        # Import required modules
        from app.services.ai_service import AIService
        from app.repositories.debt_repository import DebtRepository
        from app.repositories.user_repository import UserRepository
        from app.repositories.analytics_repository import AnalyticsRepository

        print("✅ Imports successful")

        # Initialize repositories
        debt_repo = DebtRepository()
        user_repo = UserRepository()
        analytics_repo = AnalyticsRepository()

        print("✅ Repositories initialized")

        # Initialize AI service
        ai_service = AIService(debt_repo, user_repo, analytics_repo)
        print("✅ AI service initialized")

        # Test with a mock user ID (we'll use a test UUID)
        test_user_id = UUID("12345678-1234-5678-9012-123456789012")

        print(f"🔍 Testing with user ID: {test_user_id}")

        # Step 1: Check if user has debts
        print("\n1. Checking for user debts...")
        try:
            user_debts = await debt_repo.get_debts_by_user_id(test_user_id)
            print(f"   Found {len(user_debts) if user_debts else 0} debts")

            if not user_debts:
                print("   ⚠️ No debts found - this will cause the enhanced insights to fail")
                print("   Let's check what the method does with no debts...")

        except Exception as e:
            print(f"   ❌ Error getting debts: {e}")
            traceback.print_exc()

        # Step 2: Try to call enhanced AI insights
        print("\n2. Testing enhanced AI insights...")
        try:
            result = await ai_service.get_enhanced_ai_insights(
                user_id=test_user_id,
                monthly_payment_budget=1000,
                preferred_strategy="avalanche"
            )
            print("   ✅ Enhanced AI insights succeeded!")
            print(f"   Result keys: {list(result.keys())}")

        except ValueError as e:
            if "No debts found" in str(e):
                print(f"   ⚠️ Expected error (no debts): {e}")
            else:
                print(f"   ❌ ValueError: {e}")
                traceback.print_exc()
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            traceback.print_exc()

        # Step 3: Test individual methods
        print("\n3. Testing individual AI service methods...")

        # Test _simulate_single_scenario if we have debts
        if user_debts:
            print("   Testing _simulate_single_scenario...")
            try:
                scenario = {"monthly_payment": 1000, "strategy": "avalanche"}
                result = await ai_service._simulate_single_scenario(user_debts, scenario)
                print(f"   ✅ Simulation successful: {list(result.keys())}")
            except Exception as e:
                print(f"   ❌ Simulation failed: {e}")
                traceback.print_exc()

        print("\n4. Testing other methods...")

        # Test compare_strategies
        try:
            comparison = await ai_service.compare_strategies(test_user_id, 1000)
            print("   ✅ Strategy comparison succeeded!")
        except Exception as e:
            print(f"   ❌ Strategy comparison failed: {e}")

        # Test generate_payment_timeline
        try:
            timeline = await ai_service.generate_payment_timeline(test_user_id, 1000, "avalanche")
            print("   ✅ Payment timeline succeeded!")
        except Exception as e:
            print(f"   ❌ Payment timeline failed: {e}")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Unexpected error during initialization: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Starting AI Insights Debug Session...")
    print("=" * 50)

    try:
        asyncio.run(test_ai_insights())
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        traceback.print_exc()

    print("=" * 50)
    print("🔍 Debug session complete")