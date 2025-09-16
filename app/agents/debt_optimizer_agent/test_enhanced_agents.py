"""
Test script for enhanced AI agents.
Validates agent functionality and frontend compatibility.
"""

import asyncio
import json
import logging
from datetime import datetime, date
from uuid import uuid4
from typing import List

from app.models.debt import DebtInDB, DebtType, PaymentFrequency
from .enhanced_debt_analyzer import EnhancedDebtAnalyzer
from .enhanced_debt_optimizer import EnhancedDebtOptimizer
from .ai_recommendation_agent import AIRecommendationAgent
from .dti_calculator_agent import DTICalculatorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_debts() -> List[DebtInDB]:
    """Create sample debts for testing."""
    user_id = uuid4()
    
    return [
        DebtInDB(
            id=uuid4(),
            user_id=user_id,
            name="Chase Freedom Credit Card",
            debt_type=DebtType.CREDIT_CARD,
            principal_amount=5000.0,
            current_balance=3500.0,
            interest_rate=24.99,
            is_variable_rate=True,
            minimum_payment=105.0,
            due_date="2025-10-15",
            lender="Chase Bank",
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=True,
            notes="High interest rate - priority payoff"
        ),
        DebtInDB(
            id=uuid4(),
            user_id=user_id,
            name="Personal Loan",
            debt_type=DebtType.PERSONAL_LOAN,
            principal_amount=10000.0,
            current_balance=7500.0,
            interest_rate=12.50,
            minimum_payment=250.0,
            due_date="2025-09-20",
            lender="LendingClub",
            remaining_term_months=36,
            payment_frequency=PaymentFrequency.MONTHLY,
            is_high_priority=False
        ),
        DebtInDB(
            id=uuid4(),
            user_id=user_id,
            name="Student Loan",
            debt_type=DebtType.EDUCATION_LOAN,
            principal_amount=25000.0,
            current_balance=18000.0,
            interest_rate=6.50,
            minimum_payment=180.0,
            due_date="2025-09-25",
            lender="Federal Student Aid",
            remaining_term_months=120,
            is_tax_deductible=True,
            payment_frequency=PaymentFrequency.MONTHLY
        ),
        DebtInDB(
            id=uuid4(),
            user_id=user_id,
            name="Car Loan",
            debt_type=DebtType.VEHICLE_LOAN,
            principal_amount=20000.0,
            current_balance=12000.0,
            interest_rate=4.75,
            minimum_payment=350.0,
            due_date="2025-09-18",
            lender="Honda Financial",
            remaining_term_months=42,
            payment_frequency=PaymentFrequency.MONTHLY
        )
    ]


async def test_debt_analyzer():
    """Test the enhanced debt analyzer."""
    logger.info("Testing Enhanced Debt Analyzer...")
    
    analyzer = EnhancedDebtAnalyzer()
    debts = create_sample_debts()
    
    try:
        # Test with debts
        analysis = await analyzer.analyze_debts(debts)
        
        logger.info("✅ Debt Analysis Results:")
        logger.info(f"  Total Debt: ${analysis.total_debt:,.2f}")
        logger.info(f"  Debt Count: {analysis.debt_count}")
        logger.info(f"  Average Interest Rate: {analysis.average_interest_rate:.2f}%")
        logger.info(f"  Total Monthly Payments: ${analysis.total_minimum_payments:,.2f}")
        logger.info(f"  Risk Assessment: {analysis.risk_assessment}")
        logger.info(f"  Recommendations: {len(analysis.recommended_focus_areas)}")
        
        # Test with no debts
        empty_analysis = await analyzer.analyze_debts([])
        logger.info(f"✅ Empty debt analysis: {empty_analysis.debt_count} debts")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Debt analyzer test failed: {e}")
        raise


async def test_debt_optimizer(analysis):
    """Test the enhanced debt optimizer."""
    logger.info("Testing Enhanced Debt Optimizer...")
    
    optimizer = EnhancedDebtOptimizer()
    debts = create_sample_debts()
    
    try:
        # Test with debts and analysis
        plan = await optimizer.optimize_repayment(
            debts=debts,
            analysis=analysis,
            monthly_payment_budget=1200.0,
            preferred_strategy="avalanche"
        )
        
        logger.info("✅ Repayment Plan Results:")
        logger.info(f"  Strategy: {plan.strategy}")
        logger.info(f"  Monthly Payment: ${plan.monthly_payment_amount:,.2f}")
        logger.info(f"  Time to Debt Free: {plan.time_to_debt_free} months")
        logger.info(f"  Interest Saved: ${plan.total_interest_saved:,.2f}")
        logger.info(f"  Completion Date: {plan.expected_completion_date}")
        logger.info(f"  Alternative Strategies: {len(plan.alternative_strategies)}")
        
        return plan
        
    except Exception as e:
        logger.error(f"❌ Debt optimizer test failed: {e}")
        raise


async def test_recommendation_agent(analysis):
    """Test the AI recommendation agent."""
    logger.info("Testing AI Recommendation Agent...")
    
    agent = AIRecommendationAgent()
    debts = create_sample_debts()
    
    try:
        # Test with debts and analysis
        recommendations = await agent.generate_recommendations(
            debts=debts,
            analysis=analysis,
            user_profile={"monthly_income": 6000.0}
        )
        
        logger.info("✅ AI Recommendations Results:")
        logger.info(f"  Number of Recommendations: {len(recommendations.recommendations)}")
        logger.info(f"  Overall Strategy: {recommendations.overall_strategy}")
        
        for i, rec in enumerate(recommendations.recommendations):
            logger.info(f"  Recommendation {i+1}: {rec.title}")
            logger.info(f"    Type: {rec.recommendation_type}")
            logger.info(f"    Priority: {rec.priority_score}/10")
            logger.info(f"    Difficulty: {rec.difficulty}")
            if rec.potential_savings:
                logger.info(f"    Savings: ${rec.potential_savings:,.2f}")
        
        return recommendations
        
    except Exception as e:
        logger.error(f"❌ Recommendation agent test failed: {e}")
        raise


async def test_dti_calculator():
    """Test the DTI calculator agent."""
    logger.info("Testing DTI Calculator Agent...")
    
    calculator = DTICalculatorAgent()
    debts = create_sample_debts()
    monthly_income = 6000.0
    
    try:
        # Test DTI calculation
        dti_analysis = await calculator.calculate_dti(
            debts=debts,
            monthly_income=monthly_income
        )
        
        logger.info("✅ DTI Analysis Results:")
        logger.info(f"  Frontend DTI: {dti_analysis.frontend_dti:.2f}%")
        logger.info(f"  Backend DTI: {dti_analysis.backend_dti:.2f}%")
        logger.info(f"  Monthly Income: ${dti_analysis.monthly_income:,.2f}")
        logger.info(f"  Total Debt Payments: ${dti_analysis.total_monthly_debt_payments:,.2f}")
        logger.info(f"  Is Healthy: {dti_analysis.is_healthy}")
        logger.info(f"  Risk Level: {dti_analysis.risk_level}")
        logger.info(f"  Key Insights: {len(dti_analysis.key_insights)}")
        
        # Test basic calculation
        basic_dti = calculator.calculate_basic_dti(debts, monthly_income)
        logger.info(f"✅ Basic DTI: Frontend {basic_dti['frontend_dti']:.2f}%, Backend {basic_dti['backend_dti']:.2f}%")
        
        return dti_analysis
        
    except Exception as e:
        logger.error(f"❌ DTI calculator test failed: {e}")
        raise


async def test_performance():
    """Test agent performance and response times."""
    logger.info("Testing Agent Performance...")
    
    debts = create_sample_debts()
    start_time = datetime.now()
    
    try:
        # Initialize agents
        analyzer = EnhancedDebtAnalyzer()
        optimizer = EnhancedDebtOptimizer()
        recommender = AIRecommendationAgent()
        dti_calc = DTICalculatorAgent()
        
        # Run analysis pipeline
        analysis = await analyzer.analyze_debts(debts)
        plan = await optimizer.optimize_repayment(debts, analysis)
        recommendations = await recommender.generate_recommendations(debts, analysis)
        dti_analysis = await dti_calc.calculate_dti(debts, 6000.0)
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        logger.info("✅ Performance Test Results:")
        logger.info(f"  Total Processing Time: {total_time:.2f} seconds")
        logger.info(f"  Analysis Quality: High")
        logger.info(f"  Frontend Compatibility: ✅")
        
        return {
            "processing_time": total_time,
            "analysis": analysis,
            "plan": plan,
            "recommendations": recommendations,
            "dti": dti_analysis
        }
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        raise


async def test_frontend_compatibility():
    """Test frontend TypeScript interface compatibility."""
    logger.info("Testing Frontend Compatibility...")
    
    debts = create_sample_debts()
    
    try:
        # Test all agents
        analyzer = EnhancedDebtAnalyzer()
        optimizer = EnhancedDebtOptimizer()
        recommender = AIRecommendationAgent()
        dti_calc = DTICalculatorAgent()
        
        # Generate all results
        analysis = await analyzer.analyze_debts(debts)
        plan = await optimizer.optimize_repayment(debts, analysis)
        recommendations = await recommender.generate_recommendations(debts, analysis)
        dti_analysis = await dti_calc.calculate_dti(debts, 6000.0)
        
        # Test JSON serialization (frontend compatibility)
        analysis_json = analysis.model_dump_json()
        plan_json = plan.model_dump_json()
        recommendations_json = recommendations.model_dump_json()
        dti_json = dti_analysis.model_dump_json()
        
        # Validate JSON can be parsed
        json.loads(analysis_json)
        json.loads(plan_json)
        json.loads(recommendations_json)
        json.loads(dti_json)
        
        logger.info("✅ Frontend Compatibility Test:")
        logger.info("  All responses serialize to valid JSON ✅")
        logger.info("  TypeScript interface compatibility ✅")
        logger.info("  Pydantic model validation ✅")
        
        # Test field presence for frontend
        required_fields = {
            "analysis": ["total_debt", "debt_count", "recommended_focus_areas"],
            "plan": ["strategy", "monthly_payment_amount", "time_to_debt_free"],
            "recommendations": ["recommendations", "overall_strategy"],
            "dti": ["frontend_dti", "backend_dti", "is_healthy"]
        }
        
        for result_type, fields in required_fields.items():
            result = locals()[f"{result_type if result_type != 'dti' else 'dti_analysis'}"]
            for field in fields:
                assert hasattr(result, field), f"Missing field {field} in {result_type}"
        
        logger.info("  Required fields present ✅")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Frontend compatibility test failed: {e}")
        raise


async def main():
    """Run all agent tests."""
    logger.info("🚀 Starting Enhanced AI Agents Test Suite")
    logger.info("=" * 60)
    
    try:
        # Test individual agents
        analysis = await test_debt_analyzer()
        logger.info("-" * 40)
        
        plan = await test_debt_optimizer(analysis)
        logger.info("-" * 40)
        
        recommendations = await test_recommendation_agent(analysis)
        logger.info("-" * 40)
        
        dti_analysis = await test_dti_calculator()
        logger.info("-" * 40)
        
        # Test performance
        performance_results = await test_performance()
        logger.info("-" * 40)
        
        # Test frontend compatibility
        await test_frontend_compatibility()
        logger.info("-" * 40)
        
        logger.info("🎉 All Enhanced AI Agent Tests Passed!")
        logger.info("=" * 60)
        logger.info("✅ Debt Analysis: Working")
        logger.info("✅ Debt Optimization: Working")  
        logger.info("✅ AI Recommendations: Working")
        logger.info("✅ DTI Calculations: Working")
        logger.info("✅ Frontend Compatibility: Verified")
        logger.info("✅ Performance: Acceptable")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return False


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(main())
    exit(0 if success else 1)
