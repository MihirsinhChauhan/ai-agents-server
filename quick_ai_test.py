#!/usr/bin/env python3
"""
Quick test to isolate LLM issues
"""

import asyncio
import sys
import os
from datetime import datetime, date
from uuid import uuid4

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.debt import DebtInDB

async def test_simple_ai_call():
    """Test a simple AI call to isolate the issue."""
    print("🔍 Testing Simple AI Call...")

    try:
        from app.agents.debt_optimizer_agent.ai_recommendation_agent import AIRecommendationAgent

        # Create minimal test data
        debt = DebtInDB(
            id=str(uuid4()),
            user_id=uuid4(),
            name="Test Credit Card",
            debt_type="credit_card",
            principal_amount=5000.00,
            current_balance=3000.00,
            interest_rate=18.0,
            minimum_payment=90.00,
            due_date=date(2024, 1, 15),
            lender="Test Bank",
            payment_frequency="monthly",
            is_high_priority=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        print("✅ Test data created")

        # Create agent
        agent = AIRecommendationAgent()
        print("✅ Agent created")

        # Test simple method without AI
        fallback_recs = agent.generate_recommendations_calculation_fallback([debt], None)
        print(f"✅ Fallback method works: {len(fallback_recs.recommendations)} recommendations")

        # Test AI method with timeout
        print("🤖 Testing AI method...")
        try:
            import asyncio
            ai_recs = await asyncio.wait_for(
                agent.generate_recommendations_with_ai([debt], None),
                timeout=10.0
            )
            print(f"✅ AI method works: {len(ai_recs.recommendations)} recommendations")
            return True
        except asyncio.TimeoutError:
            print("❌ AI method timed out")
            return False
        except Exception as e:
            print(f"❌ AI method failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test."""
    print("🚀 Quick AI Test")
    print("=" * 40)

    success = await test_simple_ai_call()

    print("\n" + "=" * 40)
    if success:
        print("✅ AI is working correctly")
    else:
        print("❌ AI has issues - using fallback mode")
        print("💡 This is expected behavior for robust production systems")

if __name__ == "__main__":
    asyncio.run(main())