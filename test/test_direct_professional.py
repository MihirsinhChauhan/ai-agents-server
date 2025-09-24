#!/usr/bin/env python3
"""Test professional consultation directly"""

import asyncio
import json
import sys
import os
from uuid import UUID

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.debt_optimizer_agent.enhanced_debt_analyzer import EnhancedDebtAnalyzer
from app.agents.debt_optimizer_agent.ai_recommendation_agent import AIRecommendationAgent
from app.agents.debt_optimizer_agent.enhanced_debt_optimizer import EnhancedDebtOptimizer
from app.repositories.debt_repository import DebtRepository
from app.repositories.user_repository import UserRepository

async def test_professional_consultation():
    """Test the professional consultation flow directly"""

    print("Testing Professional Consultation Flow")
    print("=" * 60)

    # Initialize repositories
    debt_repo = DebtRepository()
    user_repo = UserRepository()

    # Get test user
    users = await user_repo.get_all()
    test_user = None
    for user in users:
        if user.email == "test_professional@debtease.com":
            test_user = user
            break

    if not test_user:
        print("✗ Test user not found")
        return False

    print(f"✓ Found test user: {test_user.email}")
    print(f"  User ID: {test_user.id}")

    # Get user debts
    debts = await debt_repo.get_debts_by_user_id(test_user.id)
    print(f"✓ Found {len(debts)} debts")

    if not debts:
        print("✗ No debts found - cannot test professional consultation")
        return False

    # Initialize professional agents
    print("\nInitializing Professional Agents...")
    analyzer = EnhancedDebtAnalyzer()
    recommender = AIRecommendationAgent()
    optimizer = EnhancedDebtOptimizer()
    print("✓ All agents initialized")

    # Step 1: Enhanced Debt Analysis
    print("\n1. Enhanced Debt Analysis")
    print("-" * 40)
    try:
        analysis = await analyzer.analyze_debts(debts)
        print(f"  Total Debt: ₹{analysis.total_debt:,.2f}")
        print(f"  Debt Count: {analysis.debt_count}")
        print(f"  Average Interest Rate: {analysis.average_interest_rate:.2f}%")
        print(f"  High Priority Debts: {len(analysis.high_priority_debts)}")
        print(f"  Risk Assessment: {analysis.risk_assessment}")
        print("  ✓ Analysis successful")
    except Exception as e:
        print(f"  ✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 2: Professional Recommendations
    print("\n2. Professional AI Recommendations")
    print("-" * 40)
    try:
        user_profile = await user_repo.get_by_id(test_user.id)
        recommendations = await recommender.generate_recommendations(
            debts=debts,
            analysis=analysis,
            user_profile=user_profile.model_dump() if user_profile else None
        )
        print(f"  Generated {len(recommendations.recommendations)} recommendations")

        if recommendations.recommendations:
            rec = recommendations.recommendations[0]
            print(f"\n  Sample Recommendation:")
            print(f"    Title: {rec.title}")
            print(f"    Type: {rec.recommendation_type}")
            print(f"    Priority: {rec.priority_score}")

            # Check for enhanced fields
            has_action_steps = hasattr(rec, 'action_steps') and rec.action_steps
            has_benefits = hasattr(rec, 'benefits') and rec.benefits
            has_risks = hasattr(rec, 'risks') and rec.risks

            print(f"\n  Enhanced Fields:")
            print(f"    Action Steps: {'✓' if has_action_steps else '✗'}")
            print(f"    Benefits: {'✓' if has_benefits else '✗'}")
            print(f"    Risks: {'✓' if has_risks else '✗'}")

        print("  ✓ Recommendations successful")
    except Exception as e:
        print(f"  ✗ Recommendations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Enhanced Repayment Plan
    print("\n3. Enhanced Repayment Plan")
    print("-" * 40)
    try:
        repayment_plan = await optimizer.optimize_repayment(
            debts=debts,
            analysis=analysis,
            monthly_payment_budget=2000.0,
            preferred_strategy="avalanche"
        )
        print(f"  Strategy: {repayment_plan.strategy}")
        print(f"  Monthly Payment: ₹{repayment_plan.monthly_payment_amount:,.2f}")
        print(f"  Time to Debt Free: {repayment_plan.time_to_debt_free} months")
        print(f"  Total Interest Saved: ₹{repayment_plan.total_interest_saved:,.2f}")

        # Check for enhanced fields
        has_primary_strategy = hasattr(repayment_plan, 'primary_strategy') and repayment_plan.primary_strategy
        has_alternatives = hasattr(repayment_plan, 'alternative_strategies') and repayment_plan.alternative_strategies
        has_insights = hasattr(repayment_plan, 'key_insights') and repayment_plan.key_insights
        has_action_items = hasattr(repayment_plan, 'action_items') and repayment_plan.action_items

        print(f"\n  Enhanced Fields:")
        print(f"    Primary Strategy: {'✓' if has_primary_strategy else '✗'}")
        print(f"    Alternative Strategies: {'✓' if has_alternatives else '✗'}")
        print(f"    Key Insights: {'✓' if has_insights else '✗'}")
        print(f"    Action Items: {'✓' if has_action_items else '✗'}")

        print("  ✓ Repayment plan successful")
    except Exception as e:
        print(f"  ✗ Repayment plan failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ Professional Consultation Components Working!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = asyncio.run(test_professional_consultation())
    sys.exit(0 if success else 1)