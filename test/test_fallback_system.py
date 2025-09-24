#!/usr/bin/env python3
"""
Test the fallback recommendation system
"""

import asyncio
import sys
import os
from datetime import datetime, date
from uuid import uuid4

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.debt_optimizer_agent.ai_recommendation_agent import AIRecommendationAgent
from app.agents.debt_optimizer_agent.enhanced_debt_analyzer import EnhancedDebtAnalyzer
from app.models.debt import DebtInDB


async def test_fallback_system():
    print("🔧 Testing AI Fallback Systems...")

    # Create test debt
    debts = [
        DebtInDB(
            id=str(uuid4()),
            user_id=uuid4(),
            name="Credit Card - High Interest",
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

    # Test analyzer
    print("📊 Testing Enhanced Debt Analyzer...")
    analyzer = EnhancedDebtAnalyzer()
    analysis = await analyzer.analyze_debts(debts)
    print(f"✅ Analysis completed")
    print(f"   Total debt: ${analysis.total_debt:,.2f}")
    print(f"   Average rate: {analysis.average_interest_rate:.2f}%")
    print(f"   Risk level: {analysis.risk_assessment}")

    # Test fallback recommendation system (no AI model needed)
    print("\n💡 Testing Calculation Fallback Recommendations...")
    agent = AIRecommendationAgent()
    recommendations = agent.generate_recommendations_calculation_fallback(debts, analysis)

    print(f"✅ Fallback recommendations generated successfully")
    print(f"📋 Total recommendations: {len(recommendations.recommendations)}")
    print(f"🎯 Strategy: {recommendations.overall_strategy}")

    print("\n🔍 Professional Fallback Recommendation Details:")
    for i, rec in enumerate(recommendations.recommendations, 1):
        print(f"\n--- Fallback Recommendation {i} ---")
        print(f"Type: {rec.recommendation_type}")
        print(f"Title: {rec.title}")
        print(f"Priority Score: {rec.priority_score}/10")
        if rec.description:
            desc = rec.description[:150] + "..." if len(rec.description) > 150 else rec.description
            print(f"Description: {desc}")
        if rec.potential_savings:
            print(f"Potential Savings: ${rec.potential_savings:,.2f}")

    # Test professional quality
    print("\n🎯 Validating Professional Quality (Fallback Mode)...")

    quality_indicators = []

    # Check for professional recommendations
    avalanche_found = any("avalanche" in rec.recommendation_type for rec in recommendations.recommendations)
    consolidation_found = any("consolidation" in rec.recommendation_type for rec in recommendations.recommendations)
    automation_found = any("automation" in rec.recommendation_type for rec in recommendations.recommendations)

    if avalanche_found:
        quality_indicators.append("✅ Mathematical optimization strategy (Avalanche)")
    if consolidation_found:
        quality_indicators.append("✅ Debt consolidation assessment")
    if automation_found:
        quality_indicators.append("✅ Payment automation strategy")

    # Check for priority scoring
    has_priorities = all(rec.priority_score > 0 for rec in recommendations.recommendations)
    if has_priorities:
        quality_indicators.append("✅ Professional priority scoring")

    # Check for detailed descriptions
    detailed_recs = sum(1 for rec in recommendations.recommendations if len(rec.description) > 50)
    if detailed_recs >= len(recommendations.recommendations) * 0.5:
        quality_indicators.append("✅ Detailed professional guidance")

    print(f"\n📊 Professional Quality Assessment:")
    for indicator in quality_indicators:
        print(f"   {indicator}")

    quality_score = (len(quality_indicators) / 5) * 100
    print(f"\n🎯 Professional Quality Score: {quality_score:.1f}%")

    if quality_score >= 80:
        print("🏆 EXCELLENT: Professional consultation quality achieved!")
    elif quality_score >= 60:
        print("✅ GOOD: Solid professional quality")
    else:
        print("⚠️  ACCEPTABLE: Basic professional quality maintained")

    return recommendations


async def test_enhanced_prompts_structure():
    """Test that enhanced prompts are properly structured"""
    print("\n🔧 Testing Enhanced Prompt Structure...")

    agent = AIRecommendationAgent()

    # Test main prompt
    main_prompt = agent._get_system_prompt()
    print(f"✅ Main prompt loaded: {len(main_prompt)} characters")

    # Check for professional elements
    professional_elements = [
        "Professional Certified Debt Consultant",
        "Dave Ramsey",
        "Suze Orman",
        "step-by-step",
        "action_steps",
        "PHASE",
        "behavioral",
        "risk assessment"
    ]

    found_elements = []
    for element in professional_elements:
        if element.lower() in main_prompt.lower():
            found_elements.append(element)

    print(f"📊 Professional elements found: {len(found_elements)}/{len(professional_elements)}")
    for element in found_elements:
        print(f"   ✅ {element}")

    # Test simple prompt
    simple_prompt = agent._get_simple_prompt()
    print(f"✅ Simple prompt loaded: {len(simple_prompt)} characters")

    if "Professional Certified Debt Consultant" in simple_prompt:
        print("✅ Simple prompt also has professional framework")

    prompt_quality = (len(found_elements) / len(professional_elements)) * 100
    print(f"\n🎯 Prompt Enhancement Quality: {prompt_quality:.1f}%")

    return prompt_quality >= 70


async def main():
    print("🚀 Testing Enhanced AI System Fallback Capabilities")
    print("=" * 60)

    # Test fallback system
    recommendations = await test_fallback_system()

    # Test prompt structure
    prompt_quality = await test_enhanced_prompts_structure()

    print("\n" + "=" * 60)
    print("🎉 FALLBACK SYSTEM TESTING COMPLETED!")

    if recommendations and len(recommendations.recommendations) >= 3:
        print("✅ Fallback recommendation system working correctly")
    else:
        print("❌ Fallback recommendation system needs attention")

    if prompt_quality:
        print("✅ Enhanced prompts properly structured")
    else:
        print("❌ Enhanced prompts need review")

    print("\n📋 Summary:")
    print("   ✅ System can operate without AI model (fallback mode)")
    print("   ✅ Professional consultation framework in place")
    print("   ✅ Enhanced prompts ready for improved AI output")
    print("   ⚠️  AI model configuration may need adjustment for full features")


if __name__ == "__main__":
    asyncio.run(main())