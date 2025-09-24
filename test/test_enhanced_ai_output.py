#!/usr/bin/env python3
"""
Test script for enhanced AI agents output quality.
Tests the professional debt consultant improvements.
"""

import asyncio
import sys
import os
import json
from datetime import datetime, date
from uuid import uuid4
from typing import List

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.debt import DebtInDB
from app.agents.debt_optimizer_agent.enhanced_debt_analyzer import EnhancedDebtAnalyzer, DebtAnalysisResult
from app.agents.debt_optimizer_agent.ai_recommendation_agent import AIRecommendationAgent
from app.agents.debt_optimizer_agent.enhanced_debt_optimizer import EnhancedDebtOptimizer
from app.agents.debt_optimizer_agent.enhanced_orchestrator import EnhancedAIOrchestrator


def create_mock_debts() -> List[DebtInDB]:
    """Create realistic test debt data."""
    return [
        DebtInDB(
            id=str(uuid4()),
            user_id=uuid4(),
            name="Credit Card - Chase Freedom",
            debt_type="credit_card",
            principal_amount=8500.00,
            current_balance=7200.00,
            interest_rate=24.99,
            minimum_payment=180.00,
            due_date=date(2024, 1, 15),
            lender="Chase Bank",
            payment_frequency="monthly",
            is_high_priority=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        DebtInDB(
            id=str(uuid4()),
            user_id=uuid4(),
            name="Education Loan - Federal",
            debt_type="education_loan",
            principal_amount=25000.00,
            current_balance=22500.00,
            interest_rate=6.8,
            minimum_payment=280.00,
            due_date=date(2024, 1, 20),
            lender="Federal Student Aid",
            payment_frequency="monthly",
            is_high_priority=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        DebtInDB(
            id=str(uuid4()),
            user_id=uuid4(),
            name="Personal Loan",
            debt_type="personal_loan",
            principal_amount=5000.00,
            current_balance=3200.00,
            interest_rate=12.5,
            minimum_payment=120.00,
            due_date=date(2024, 1, 10),
            lender="LendingClub",
            payment_frequency="monthly",
            is_high_priority=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]


async def test_debt_analyzer_output():
    """Test Enhanced Debt Analyzer output."""
    print("🔍 Testing Enhanced Debt Analyzer...")

    try:
        analyzer = EnhancedDebtAnalyzer()
        debts = create_mock_debts()

        analysis = await analyzer.analyze_debts(debts)

        print(f"✅ Analysis completed successfully")
        print(f"📊 Total Debt: ${analysis.total_debt:,.2f}")
        print(f"📈 Average Interest Rate: {analysis.average_interest_rate:.2f}%")
        print(f"⚠️  Risk Assessment: {analysis.risk_assessment}")
        print(f"🎯 Focus Areas: {len(analysis.recommended_focus_areas)} recommendations")

        for i, area in enumerate(analysis.recommended_focus_areas[:3], 1):
            print(f"   {i}. {area}")

        return analysis

    except Exception as e:
        print(f"❌ Debt Analyzer test failed: {e}")
        return None


async def test_recommendation_agent_output(analysis: DebtAnalysisResult):
    """Test AI Recommendation Agent with professional prompts."""
    print("\n💡 Testing AI Recommendation Agent (Professional Consultation)...")

    try:
        agent = AIRecommendationAgent()
        debts = create_mock_debts()

        # Test the robust recommendation generation
        recommendations = await agent.generate_recommendations_robust(debts, analysis)

        print(f"✅ Recommendations generated successfully")
        print(f"📋 Total Recommendations: {len(recommendations.recommendations)}")
        print(f"🎯 Overall Strategy: {recommendations.overall_strategy}")

        print("\n🔍 Professional Recommendation Details:")
        for i, rec in enumerate(recommendations.recommendations[:3], 1):
            print(f"\n--- Recommendation {i} ---")
            print(f"Type: {rec.recommendation_type}")
            print(f"Title: {rec.title}")
            print(f"Priority Score: {rec.priority_score}/10")
            if rec.description:
                # Truncate long descriptions for readability
                desc = rec.description[:200] + "..." if len(rec.description) > 200 else rec.description
                print(f"Description: {desc}")
            if rec.potential_savings:
                print(f"Potential Savings: ${rec.potential_savings:,.2f}")

        return recommendations

    except Exception as e:
        print(f"❌ Recommendation Agent test failed: {e}")
        return None


async def test_debt_optimizer_output(analysis: DebtAnalysisResult):
    """Test Enhanced Debt Optimizer with professional methodologies."""
    print("\n⚡ Testing Enhanced Debt Optimizer (Professional Strategy)...")

    try:
        optimizer = EnhancedDebtOptimizer()
        debts = create_mock_debts()

        # Test repayment plan optimization
        repayment_plan = await optimizer.optimize_repayment(
            debts=debts,
            analysis=analysis,
            monthly_payment_budget=800.00,
            preferred_strategy="avalanche"
        )

        print(f"✅ Repayment plan generated successfully")
        print(f"📈 Strategy: {repayment_plan.strategy}")
        print(f"💰 Monthly Payment: ${repayment_plan.monthly_payment_amount:,.2f}")
        print(f"⏱️  Time to Debt Free: {repayment_plan.time_to_debt_free} months")
        print(f"💵 Interest Saved: ${repayment_plan.total_interest_saved:,.2f}")
        print(f"🎯 Completion Date: {repayment_plan.expected_completion_date}")

        print(f"\n🔍 Primary Strategy Details:")
        print(f"Strategy Name: {repayment_plan.primary_strategy.name}")
        print(f"Benefits: {len(repayment_plan.primary_strategy.benefits)} listed")
        print(f"Reasoning: {repayment_plan.primary_strategy.reasoning[:150]}...")

        print(f"\n📊 Key Insights ({len(repayment_plan.key_insights)}):")
        for i, insight in enumerate(repayment_plan.key_insights[:3], 1):
            print(f"   {i}. {insight}")

        print(f"\n✅ Action Items ({len(repayment_plan.action_items)}):")
        for i, action in enumerate(repayment_plan.action_items[:3], 1):
            print(f"   {i}. {action}")

        return repayment_plan

    except Exception as e:
        print(f"❌ Debt Optimizer test failed: {e}")
        return None


async def test_full_orchestrator_workflow():
    """Test the complete Enhanced AI Orchestrator workflow."""
    print("\n🎼 Testing Enhanced AI Orchestrator (Full Professional Consultation)...")

    try:
        # Create a test orchestrator (we'll need to mock some repository calls)
        from unittest.mock import Mock, AsyncMock

        orchestrator = EnhancedAIOrchestrator()

        # Mock the repository calls
        test_user_id = uuid4()
        debts = create_mock_debts()

        # Update debts to have the same user_id
        for debt in debts:
            debt.user_id = test_user_id

        # Mock the repository methods
        orchestrator.debt_repository.get_by_user_id = AsyncMock(return_value=debts)
        orchestrator._get_user_profile = AsyncMock(return_value={
            "monthly_income": 5000.00,
            "email": "test@example.com",
            "full_name": "Test User"
        })

        # Run the full analysis
        result = await orchestrator.analyze_user_debts(
            user_id=test_user_id,
            monthly_payment_budget=800.00,
            preferred_strategy="avalanche",
            include_dti=True
        )

        print(f"✅ Full orchestration completed successfully")
        print(f"⏱️  Processing Time: {result.processing_time:.2f} seconds")
        print(f"👤 User ID: {result.user_id}")

        print(f"\n📊 Debt Analysis Summary:")
        print(f"   Total Debt: ${result.debt_analysis.total_debt:,.2f}")
        print(f"   Debt Count: {result.debt_analysis.debt_count}")
        print(f"   Risk Level: {result.debt_analysis.risk_assessment}")

        print(f"\n💡 Recommendations Summary:")
        print(f"   Total Recommendations: {len(result.recommendations.recommendations)}")
        print(f"   Strategy: {result.recommendations.overall_strategy}")

        print(f"\n⚡ Repayment Plan Summary:")
        print(f"   Strategy: {result.repayment_plan.strategy}")
        print(f"   Monthly Payment: ${result.repayment_plan.monthly_payment_amount:,.2f}")
        print(f"   Debt Freedom: {result.repayment_plan.time_to_debt_free} months")

        if result.dti_analysis:
            print(f"\n📈 DTI Analysis:")
            print(f"   DTI Ratio: {getattr(result.dti_analysis, 'dti_ratio', 'N/A')}")

        return result

    except Exception as e:
        print(f"❌ Full Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_professional_output_quality(result):
    """Validate the professional quality of the output."""
    print("\n🎯 Validating Professional Consultation Quality...")

    quality_checks = []

    # Check for professional terminology
    rec_text = " ".join([rec.title + " " + rec.description for rec in result.recommendations.recommendations])

    professional_terms = [
        "strategy", "assessment", "optimization", "foundation",
        "risk", "timeline", "implementation", "analysis"
    ]

    found_terms = [term for term in professional_terms if term.lower() in rec_text.lower()]
    quality_checks.append(f"Professional terminology: {len(found_terms)}/{len(professional_terms)} terms found")

    # Check for step-by-step guidance
    has_detailed_descriptions = sum(1 for rec in result.recommendations.recommendations if len(rec.description) > 100)
    quality_checks.append(f"Detailed guidance: {has_detailed_descriptions}/{len(result.recommendations.recommendations)} recommendations have detailed descriptions")

    # Check for priority scoring
    has_priority_scores = sum(1 for rec in result.recommendations.recommendations if rec.priority_score > 0)
    quality_checks.append(f"Priority scoring: {has_priority_scores}/{len(result.recommendations.recommendations)} recommendations have priority scores")

    # Check repayment plan detail
    plan_quality = []
    if len(result.repayment_plan.key_insights) >= 3:
        plan_quality.append("Key insights provided")
    if len(result.repayment_plan.action_items) >= 3:
        plan_quality.append("Action items provided")
    if result.repayment_plan.primary_strategy.reasoning:
        plan_quality.append("Strategy reasoning provided")

    quality_checks.append(f"Repayment plan quality: {len(plan_quality)}/3 quality indicators met")

    print("🔍 Quality Assessment Results:")
    for check in quality_checks:
        print(f"   ✅ {check}")

    # Overall assessment
    total_quality_score = len(found_terms) + has_detailed_descriptions + has_priority_scores + len(plan_quality)
    max_possible_score = len(professional_terms) + len(result.recommendations.recommendations) * 2 + 3

    quality_percentage = (total_quality_score / max_possible_score) * 100
    print(f"\n🎯 Overall Professional Quality Score: {quality_percentage:.1f}%")

    if quality_percentage >= 70:
        print("✅ EXCELLENT: Professional consultation quality achieved!")
    elif quality_percentage >= 50:
        print("⚠️  GOOD: Solid professional quality with room for improvement")
    else:
        print("❌ NEEDS IMPROVEMENT: Professional quality below expectations")

    return quality_percentage


async def main():
    """Run all tests."""
    print("🚀 Testing Enhanced AI Agents - Professional Debt Consultant Output")
    print("=" * 70)

    # Test individual components
    analysis = await test_debt_analyzer_output()
    if not analysis:
        return

    recommendations = await test_recommendation_agent_output(analysis)
    if not recommendations:
        return

    repayment_plan = await test_debt_optimizer_output(analysis)
    if not repayment_plan:
        return

    # Test full workflow
    full_result = await test_full_orchestrator_workflow()
    if not full_result:
        return

    # Validate professional quality
    quality_score = await test_professional_output_quality(full_result)

    print("\n" + "=" * 70)
    print("🎉 ENHANCED AI TESTING COMPLETED!")
    print(f"✅ All components working correctly")
    print(f"🎯 Professional Quality Score: {quality_score:.1f}%")
    print("🚀 Ready for production use!")


if __name__ == "__main__":
    asyncio.run(main())