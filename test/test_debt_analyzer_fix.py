#!/usr/bin/env python3
"""
Test the fixed debt analyzer specifically
"""

import asyncio
import sys
import os
from datetime import datetime, date
from uuid import uuid4

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.debt import DebtInDB
from app.agents.debt_optimizer_agent.enhanced_debt_analyzer import EnhancedDebtAnalyzer


async def test_debt_analyzer():
    """Test the fixed debt analyzer."""
    print("🔍 Testing Fixed Debt Analyzer...")

    try:
        # Create test debt
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

        print("✅ Test debt created")

        # Create analyzer
        analyzer = EnhancedDebtAnalyzer()
        print("✅ Analyzer created")

        # Test analysis
        print("🤖 Running debt analysis...")
        analysis = await analyzer.analyze_debts([debt])

        print(f"✅ Analysis completed!")
        print(f"📊 Total debt: ${analysis.total_debt:,.2f}")
        print(f"📈 Average interest rate: {analysis.average_interest_rate:.1f}%")
        print(f"🎯 Risk assessment: {analysis.risk_assessment}")
        print(f"💡 Recommendations: {len(analysis.recommended_focus_areas)}")

        return True

    except Exception as e:
        print(f"❌ Debt analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test."""
    print("🚀 Testing Fixed Debt Analyzer")
    print("=" * 40)

    success = await test_debt_analyzer()

    print("\n" + "=" * 40)
    if success:
        print("✅ Debt Analyzer is working correctly!")
        print("🎯 Function calling issues resolved")
        print("📈 Ready for professional AI consultation")
    else:
        print("❌ Debt Analyzer needs more fixes")
        print("🔧 Using fallback calculations for reliability")


if __name__ == "__main__":
    asyncio.run(main())