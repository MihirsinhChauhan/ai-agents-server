#!/usr/bin/env python3
"""
Comprehensive test suite for Enhanced AI Insights functionality
Tests all new simulation methods, endpoints, and response formats
"""

import asyncio
import sys
import json
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime

# Add the server directory to the Python path
sys.path.append('/home/mihir/Desktop/Work/projects/DebtEase/debtease-demo/server')

from app.services.ai_service import AIService
from app.repositories.debt_repository import DebtRepository
from app.repositories.user_repository import UserRepository
from app.repositories.analytics_repository import AnalyticsRepository


class AIEnhancementsTestSuite:
    """Comprehensive test suite for AI enhancements"""

    def __init__(self):
        self.debt_repo = DebtRepository()
        self.user_repo = UserRepository()
        self.analytics_repo = AnalyticsRepository()
        self.ai_service = AIService(self.debt_repo, self.user_repo, self.analytics_repo)
        self.test_user_id = uuid4()

        # Mock debts for testing
        self.mock_debts = [
            MockDebt(
                id=uuid4(),
                debt_name="Credit Card 1",
                current_balance=5000.0,
                interest_rate=18.5,
                minimum_payment=150.0,
                debt_type=MockDebtType("credit_card")
            ),
            MockDebt(
                id=uuid4(),
                debt_name="Credit Card 2",
                current_balance=3000.0,
                interest_rate=22.0,
                minimum_payment=90.0,
                debt_type=MockDebtType("credit_card")
            ),
            MockDebt(
                id=uuid4(),
                debt_name="Student Loan",
                current_balance=15000.0,
                interest_rate=6.5,
                minimum_payment=200.0,
                debt_type=MockDebtType("student_loan")
            ),
            MockDebt(
                id=uuid4(),
                debt_name="Car Loan",
                current_balance=12000.0,
                interest_rate=4.8,
                minimum_payment=280.0,
                debt_type=MockDebtType("auto_loan")
            )
        ]

        self.test_results = {}

    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Enhanced AI Insights Test Suite")
        print("=" * 60)

        # Test 1: Simulation Engine
        await self.test_simulation_engine()

        # Test 2: Strategy Comparison
        await self.test_strategy_comparison()

        # Test 3: Payment Timeline Generation
        await self.test_payment_timeline()

        # Test 4: Optimization Metrics
        await self.test_optimization_metrics()

        # Test 5: Enhanced AI Insights
        await self.test_enhanced_ai_insights()

        # Test 6: Payment Scenario Simulation
        await self.test_payment_scenarios()

        # Test 7: Error Handling
        await self.test_error_handling()

        # Print Summary
        self.print_test_summary()

    async def test_simulation_engine(self):
        """Test the core simulation engine"""
        print("\n🔧 Testing Simulation Engine...")

        try:
            # Test avalanche strategy
            avalanche_scenario = {
                "monthly_payment": 1000.0,
                "strategy": "avalanche"
            }

            avalanche_result = await self.ai_service._simulate_single_scenario(
                self.mock_debts, avalanche_scenario
            )

            # Validate result structure
            required_fields = [
                "time_to_debt_free", "total_interest_paid", "total_amount_paid",
                "debt_free_date", "debts_paid_off_count", "payment_timeline",
                "strategy_used", "monthly_payment_used", "valid"
            ]

            missing_fields = [field for field in required_fields if field not in avalanche_result]

            if missing_fields:
                self.test_results["simulation_engine"] = f"❌ FAILED - Missing fields: {missing_fields}"
                return

            # Test snowball strategy
            snowball_scenario = {
                "monthly_payment": 1000.0,
                "strategy": "snowball"
            }

            snowball_result = await self.ai_service._simulate_single_scenario(
                self.mock_debts, snowball_scenario
            )

            # Validate strategies produce different results
            if avalanche_result["time_to_debt_free"] == snowball_result["time_to_debt_free"]:
                self.test_results["simulation_engine"] = "⚠️  WARNING - Strategies produced identical results"
            else:
                self.test_results["simulation_engine"] = "✅ PASSED - Simulation engine working correctly"

            print(f"   Avalanche: {avalanche_result['time_to_debt_free']} months, ${avalanche_result['total_interest_paid']:.2f} interest")
            print(f"   Snowball: {snowball_result['time_to_debt_free']} months, ${snowball_result['total_interest_paid']:.2f} interest")

        except Exception as e:
            self.test_results["simulation_engine"] = f"❌ FAILED - {str(e)}"
            print(f"   Error: {e}")

    async def test_strategy_comparison(self):
        """Test strategy comparison functionality"""
        print("\n📊 Testing Strategy Comparison...")

        try:
            # Mock the debt repo method for testing
            original_method = self.ai_service.debt_repo.get_debts_by_user_id

            async def mock_get_debts(user_id):
                return self.mock_debts

            self.ai_service.debt_repo.get_debts_by_user_id = mock_get_debts

            comparison = await self.ai_service.compare_strategies(
                user_id=self.test_user_id,
                monthly_payment=1000.0
            )

            # Restore original method
            self.ai_service.debt_repo.get_debts_by_user_id = original_method

            # Validate comparison structure
            required_fields = [
                "user_id", "comparison_amount", "avalanche_strategy",
                "snowball_strategy", "comparison_summary", "generated_at"
            ]

            missing_fields = [field for field in required_fields if field not in comparison]

            if missing_fields:
                self.test_results["strategy_comparison"] = f"❌ FAILED - Missing fields: {missing_fields}"
                return

            # Validate strategy details
            for strategy_key in ["avalanche_strategy", "snowball_strategy"]:
                strategy = comparison[strategy_key]
                strategy_fields = ["name", "time_to_debt_free", "total_interest_paid", "description"]
                missing_strategy_fields = [field for field in strategy_fields if field not in strategy]

                if missing_strategy_fields:
                    self.test_results["strategy_comparison"] = f"❌ FAILED - Missing {strategy_key} fields: {missing_strategy_fields}"
                    return

            self.test_results["strategy_comparison"] = "✅ PASSED - Strategy comparison working correctly"
            print(f"   Avalanche: {comparison['avalanche_strategy']['time_to_debt_free']} months")
            print(f"   Snowball: {comparison['snowball_strategy']['time_to_debt_free']} months")
            print(f"   Recommended: {comparison['comparison_summary']['recommended_strategy']}")

        except Exception as e:
            self.test_results["strategy_comparison"] = f"❌ FAILED - {str(e)}"
            print(f"   Error: {e}")

    async def test_payment_timeline(self):
        """Test payment timeline generation"""
        print("\n📅 Testing Payment Timeline Generation...")

        try:
            # Mock the debt repo method for testing
            original_method = self.ai_service.debt_repo.get_debts_by_user_id

            async def mock_get_debts(user_id):
                return self.mock_debts

            self.ai_service.debt_repo.get_debts_by_user_id = mock_get_debts

            timeline = await self.ai_service.generate_payment_timeline(
                user_id=self.test_user_id,
                monthly_payment=1000.0,
                strategy="avalanche"
            )

            # Restore original method
            self.ai_service.debt_repo.get_debts_by_user_id = original_method

            # Validate timeline structure
            required_fields = ["user_id", "strategy", "monthly_payment", "timeline", "summary", "generated_at"]
            missing_fields = [field for field in required_fields if field not in timeline]

            if missing_fields:
                self.test_results["payment_timeline"] = f"❌ FAILED - Missing fields: {missing_fields}"
                return

            # Validate timeline entries
            if not timeline["timeline"]:
                self.test_results["payment_timeline"] = "❌ FAILED - Empty timeline"
                return

            first_entry = timeline["timeline"][0]
            entry_fields = ["month", "total_debt", "monthly_payment", "interest_paid", "principal_paid"]
            missing_entry_fields = [field for field in entry_fields if field not in first_entry]

            if missing_entry_fields:
                self.test_results["payment_timeline"] = f"❌ FAILED - Missing timeline entry fields: {missing_entry_fields}"
                return

            self.test_results["payment_timeline"] = "✅ PASSED - Payment timeline generation working correctly"
            print(f"   Timeline length: {len(timeline['timeline'])} months")
            print(f"   First month debt: ${first_entry['total_debt']:.2f}")
            print(f"   Summary: {timeline['summary']['time_to_debt_free']} months to freedom")

        except Exception as e:
            self.test_results["payment_timeline"] = f"❌ FAILED - {str(e)}"
            print(f"   Error: {e}")

    async def test_optimization_metrics(self):
        """Test optimization metrics calculation"""
        print("\n⚡ Testing Optimization Metrics...")

        try:
            # Mock the debt repo method for testing
            original_method = self.ai_service.debt_repo.get_debts_by_user_id

            async def mock_get_debts(user_id):
                return self.mock_debts

            self.ai_service.debt_repo.get_debts_by_user_id = mock_get_debts

            current_strategy = {"monthly_payment": 800.0, "strategy": "snowball"}
            optimized_strategy = {"monthly_payment": 1000.0, "strategy": "avalanche"}

            metrics = await self.ai_service.calculate_optimization_metrics(
                user_id=self.test_user_id,
                current_strategy=current_strategy,
                optimized_strategy=optimized_strategy
            )

            # Restore original method
            self.ai_service.debt_repo.get_debts_by_user_id = original_method

            # Validate metrics structure
            required_fields = [
                "user_id", "current_plan", "optimized_plan",
                "optimization_savings", "is_improvement", "generated_at"
            ]
            missing_fields = [field for field in required_fields if field not in metrics]

            if missing_fields:
                self.test_results["optimization_metrics"] = f"❌ FAILED - Missing fields: {missing_fields}"
                return

            # Validate savings structure
            savings = metrics["optimization_savings"]
            savings_fields = ["time_months", "interest_amount", "percentage_improvement"]
            missing_savings_fields = [field for field in savings_fields if field not in savings]

            if missing_savings_fields:
                self.test_results["optimization_metrics"] = f"❌ FAILED - Missing savings fields: {missing_savings_fields}"
                return

            self.test_results["optimization_metrics"] = "✅ PASSED - Optimization metrics working correctly"
            print(f"   Time saved: {savings['time_months']} months")
            print(f"   Interest saved: ${savings['interest_amount']:.2f}")
            print(f"   Improvement: {savings['percentage_improvement']}%")

        except Exception as e:
            self.test_results["optimization_metrics"] = f"❌ FAILED - {str(e)}"
            print(f"   Error: {e}")

    async def test_enhanced_ai_insights(self):
        """Test enhanced AI insights functionality"""
        print("\n🧠 Testing Enhanced AI Insights...")

        try:
            # Mock the debt repo method for testing
            original_method = self.ai_service.debt_repo.get_debts_by_user_id

            async def mock_get_debts(user_id):
                return self.mock_debts

            self.ai_service.debt_repo.get_debts_by_user_id = mock_get_debts

            insights = await self.ai_service.get_enhanced_ai_insights(
                user_id=self.test_user_id,
                monthly_payment_budget=1000.0,
                preferred_strategy="avalanche"
            )

            # Restore original method
            self.ai_service.debt_repo.get_debts_by_user_id = original_method

            # Validate insights structure (matches frontend interface)
            required_fields = [
                "current_strategy", "payment_timeline",
                "alternative_strategies", "simulation_results"
            ]
            missing_fields = [field for field in required_fields if field not in insights]

            if missing_fields:
                self.test_results["enhanced_ai_insights"] = f"❌ FAILED - Missing fields: {missing_fields}"
                return

            # Validate current strategy structure
            current_strategy = insights["current_strategy"]
            strategy_fields = ["name", "time_to_debt_free", "total_interest_saved", "monthly_payment", "debt_free_date"]
            missing_strategy_fields = [field for field in strategy_fields if field not in current_strategy]

            if missing_strategy_fields:
                self.test_results["enhanced_ai_insights"] = f"❌ FAILED - Missing current strategy fields: {missing_strategy_fields}"
                return

            # Validate alternative strategies
            if not insights["alternative_strategies"]:
                self.test_results["enhanced_ai_insights"] = "⚠️  WARNING - No alternative strategies provided"
            else:
                alt_strategy = insights["alternative_strategies"][0]
                alt_fields = ["name", "time_to_debt_free", "total_interest_saved", "description"]
                missing_alt_fields = [field for field in alt_fields if field not in alt_strategy]

                if missing_alt_fields:
                    self.test_results["enhanced_ai_insights"] = f"❌ FAILED - Missing alternative strategy fields: {missing_alt_fields}"
                    return

            # Validate simulation results
            sim_results = insights["simulation_results"]
            sim_fields = ["original_plan", "optimized_plan", "savings"]
            missing_sim_fields = [field for field in sim_fields if field not in sim_results]

            if missing_sim_fields:
                self.test_results["enhanced_ai_insights"] = f"❌ FAILED - Missing simulation result fields: {missing_sim_fields}"
                return

            self.test_results["enhanced_ai_insights"] = "✅ PASSED - Enhanced AI insights working correctly"
            print(f"   Current strategy: {current_strategy['name']}")
            print(f"   Timeline entries: {len(insights['payment_timeline'])}")
            print(f"   Alternative strategies: {len(insights['alternative_strategies'])}")

        except Exception as e:
            self.test_results["enhanced_ai_insights"] = f"❌ FAILED - {str(e)}"
            print(f"   Error: {e}")

    async def test_payment_scenarios(self):
        """Test payment scenario simulation"""
        print("\n🎯 Testing Payment Scenario Simulation...")

        try:
            # Mock the debt repo method for testing
            original_method = self.ai_service.debt_repo.get_debts_by_user_id

            async def mock_get_debts(user_id):
                return self.mock_debts

            self.ai_service.debt_repo.get_debts_by_user_id = mock_get_debts

            scenarios = [
                {"monthly_payment": 800.0, "strategy": "avalanche"},
                {"monthly_payment": 1000.0, "strategy": "snowball"},
                {"monthly_payment": 1200.0, "strategy": "avalanche"}
            ]

            results = await self.ai_service.simulate_payment_scenarios(
                user_id=self.test_user_id,
                scenarios=scenarios
            )

            # Restore original method
            self.ai_service.debt_repo.get_debts_by_user_id = original_method

            # Validate results structure
            required_fields = ["user_id", "simulation_results", "generated_at"]
            missing_fields = [field for field in required_fields if field not in results]

            if missing_fields:
                self.test_results["payment_scenarios"] = f"❌ FAILED - Missing fields: {missing_fields}"
                return

            # Validate simulation results
            if len(results["simulation_results"]) != len(scenarios):
                self.test_results["payment_scenarios"] = f"❌ FAILED - Expected {len(scenarios)} results, got {len(results['simulation_results'])}"
                return

            # Validate each result
            for i, result in enumerate(results["simulation_results"]):
                result_fields = ["scenario_id", "time_to_debt_free", "total_interest_paid", "valid"]
                missing_result_fields = [field for field in result_fields if field not in result]

                if missing_result_fields:
                    self.test_results["payment_scenarios"] = f"❌ FAILED - Missing result {i} fields: {missing_result_fields}"
                    return

            self.test_results["payment_scenarios"] = "✅ PASSED - Payment scenario simulation working correctly"
            print(f"   Scenarios tested: {len(scenarios)}")
            for i, result in enumerate(results["simulation_results"]):
                print(f"   Scenario {i+1}: {result['time_to_debt_free']} months, ${result['total_interest_paid']:.2f} interest")

        except Exception as e:
            self.test_results["payment_scenarios"] = f"❌ FAILED - {str(e)}"
            print(f"   Error: {e}")

    async def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n🛡️  Testing Error Handling...")

        try:
            # Test with empty debts
            original_method = self.ai_service.debt_repo.get_debts_by_user_id

            async def mock_empty_debts(user_id):
                return []

            self.ai_service.debt_repo.get_debts_by_user_id = mock_empty_debts

            error_caught = False
            try:
                await self.ai_service.get_enhanced_ai_insights(
                    user_id=self.test_user_id,
                    monthly_payment_budget=1000.0
                )
            except ValueError as e:
                if "No debts found" in str(e):
                    error_caught = True

            # Restore original method
            self.ai_service.debt_repo.get_debts_by_user_id = original_method

            if not error_caught:
                self.test_results["error_handling"] = "❌ FAILED - No error raised for empty debts"
                return

            # Test with invalid monthly payment
            error_caught = False
            try:
                await self.ai_service._simulate_single_scenario(
                    self.mock_debts,
                    {"monthly_payment": 100.0, "strategy": "avalanche"}  # Below minimum payments
                )
            except ValueError as e:
                if "less than minimum payments" in str(e):
                    error_caught = True

            if not error_caught:
                self.test_results["error_handling"] = "❌ FAILED - No error raised for insufficient payment"
                return

            self.test_results["error_handling"] = "✅ PASSED - Error handling working correctly"
            print("   ✓ Empty debts validation")
            print("   ✓ Insufficient payment validation")

        except Exception as e:
            self.test_results["error_handling"] = f"❌ FAILED - {str(e)}"
            print(f"   Error: {e}")

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)

        passed = 0
        failed = 0
        warnings = 0

        for test_name, result in self.test_results.items():
            print(f"{test_name.replace('_', ' ').title()}: {result}")
            if "✅ PASSED" in result:
                passed += 1
            elif "❌ FAILED" in result:
                failed += 1
            elif "⚠️  WARNING" in result:
                warnings += 1

        print("\n" + "-" * 60)
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")

        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! Enhanced AI Insights is ready for production.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please review and fix issues before deployment.")

        print("=" * 60)


class MockDebt:
    """Mock debt object for testing"""
    def __init__(self, id, debt_name, current_balance, interest_rate, minimum_payment, debt_type):
        self.id = id
        self.debt_name = debt_name
        self.current_balance = current_balance
        self.interest_rate = interest_rate
        self.minimum_payment = minimum_payment
        self.debt_type = debt_type


class MockDebtType:
    """Mock debt type object for testing"""
    def __init__(self, value):
        self.value = value


async def main():
    """Run the comprehensive test suite"""
    test_suite = AIEnhancementsTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())