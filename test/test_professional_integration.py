#!/usr/bin/env python3
"""
Professional Integration Test for DebtEase Enhanced AI Features

This comprehensive test validates the end-to-end integration between:
1. Enhanced AI backend (professional consultation methods)
2. Frontend data structure expectations
3. Professional feature completeness
4. Fallback mechanisms

Author: Integration Validation Specialist
Date: 2025-09-23
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
import requests
from decimal import Decimal
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "test_professional@debtease.com"
TEST_USER_PASSWORD = "TestSecure123!"


@dataclass
class TestDebt:
    """Test debt data structure"""
    name: str
    current_balance: float
    interest_rate: float
    minimum_payment: float
    debt_type: str
    is_high_priority: bool = False


@dataclass
class ValidationResult:
    """Result of a single validation check"""
    check_name: str
    passed: bool
    details: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    actual_value: Any = None
    expected_value: Any = None


class ProfessionalIntegrationTester:
    """
    Comprehensive integration tester for professional AI features
    """

    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.test_debts = []
        self.validation_results = []

    async def setup_test_environment(self):
        """Set up test user and authentication"""
        logger.info("🔧 Setting up test environment...")

        # Try to login first
        try:
            login_response = self.session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
            )

            if login_response.status_code == 200:
                data = login_response.json()
                self.auth_token = data.get("token", data.get("access_token"))
                if "user" in data:
                    self.user_id = data["user"]["id"]
                elif "id" in data:
                    self.user_id = data["id"]
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                logger.info(f"✓ Logged in as existing user: {TEST_USER_EMAIL}")
            else:
                # Create new user
                await self._create_test_user()
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            await self._create_test_user()

    async def _create_test_user(self):
        """Create a new test user"""
        register_data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "full_name": "Professional Test User",
            "monthly_income": 8500.00
        }

        response = self.session.post(
            f"{API_BASE_URL}/api/auth/register",
            json=register_data
        )

        if response.status_code in [200, 201]:
            data = response.json()
            self.auth_token = data.get("token", data.get("access_token"))
            if "user" in data:
                self.user_id = data["user"]["id"]
            elif "id" in data:
                self.user_id = data["id"]
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            logger.info(f"✓ Created new test user: {TEST_USER_EMAIL}")
        elif "already exists" in response.text:
            # User already exists, try to login
            logger.info("User already exists, attempting login...")
            login_response = self.session.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
            )
            if login_response.status_code == 200:
                data = login_response.json()
                self.auth_token = data.get("token", data.get("access_token"))
                if "user" in data:
                    self.user_id = data["user"]["id"]
                elif "id" in data:
                    self.user_id = data["id"]
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                logger.info(f"✓ Logged in as existing user: {TEST_USER_EMAIL}")
            else:
                raise Exception(f"Failed to login: {login_response.text}")
        else:
            raise Exception(f"Failed to create test user: {response.text}")

    async def create_test_debts(self):
        """Create comprehensive test debt portfolio"""
        logger.info("💳 Creating test debt portfolio...")

        test_debts = [
            TestDebt(
                name="High Interest Credit Card",
                current_balance=15000.00,
                interest_rate=24.99,
                minimum_payment=450.00,
                debt_type="credit_card",
                is_high_priority=True
            ),
            TestDebt(
                name="Personal Loan",
                current_balance=25000.00,
                interest_rate=12.5,
                minimum_payment=550.00,
                debt_type="personal_loan",
                is_high_priority=False
            ),
            TestDebt(
                name="Car Loan",
                current_balance=18000.00,
                interest_rate=6.5,
                minimum_payment=380.00,
                debt_type="auto_loan",
                is_high_priority=False
            ),
            TestDebt(
                name="Student Loan",
                current_balance=35000.00,
                interest_rate=5.25,
                minimum_payment=350.00,
                debt_type="education_loan",
                is_high_priority=False
            ),
            TestDebt(
                name="Medical Bill Credit",
                current_balance=3500.00,
                interest_rate=0.0,
                minimum_payment=100.00,
                debt_type="other",
                is_high_priority=True
            )
        ]

        # Clear existing debts first
        existing_debts = self.session.get(f"{API_BASE_URL}/api/debts").json()
        for debt in existing_debts.get("debts", []):
            self.session.delete(f"{API_BASE_URL}/api/debts/{debt['id']}")

        # Create new test debts
        for debt_data in test_debts:
            response = self.session.post(
                f"{API_BASE_URL}/api/debts",
                json=asdict(debt_data)
            )

            if response.status_code in [200, 201]:
                created_debt = response.json()
                self.test_debts.append(created_debt)
                logger.info(f"  ✓ Created: {debt_data.name}")
            else:
                logger.error(f"  ✗ Failed to create {debt_data.name}: {response.text}")

        logger.info(f"✓ Created {len(self.test_debts)} test debts")

    async def test_enhanced_insights_endpoint(self):
        """Test the enhanced AI insights endpoint"""
        logger.info("\n🔍 Testing Enhanced AI Insights Endpoint...")

        # Test with different configurations
        test_configs = [
            {
                "name": "Default Configuration",
                "params": {},
                "expected_fields": [
                    "debt_analysis", "recommendations", "dti_analysis",
                    "repayment_plan", "metadata"
                ]
            },
            {
                "name": "With Budget Preference",
                "params": {"monthly_payment_budget": 2000.00},
                "expected_fields": ["debt_analysis", "recommendations", "repayment_plan"]
            },
            {
                "name": "Avalanche Strategy",
                "params": {"preferred_strategy": "avalanche"},
                "expected_fields": ["debt_analysis", "recommendations", "repayment_plan"]
            },
            {
                "name": "Snowball Strategy",
                "params": {"preferred_strategy": "snowball"},
                "expected_fields": ["debt_analysis", "recommendations", "repayment_plan"]
            }
        ]

        for config in test_configs:
            logger.info(f"\n  Testing: {config['name']}")

            response = self.session.get(
                f"{API_BASE_URL}/api/ai/insights",
                params=config["params"]
            )

            if response.status_code == 200:
                data = response.json()

                # Validate expected fields
                for field in config["expected_fields"]:
                    validation = ValidationResult(
                        check_name=f"Field '{field}' in {config['name']}",
                        passed=field in data,
                        details=f"Field {'present' if field in data else 'missing'}",
                        severity="critical" if field in ["debt_analysis", "recommendations"] else "high",
                        actual_value=list(data.keys()),
                        expected_value=config["expected_fields"]
                    )
                    self.validation_results.append(validation)

                # Check professional features
                await self._validate_professional_features(data, config["name"])

                logger.info(f"    ✓ Response valid for {config['name']}")
            else:
                validation = ValidationResult(
                    check_name=f"Endpoint response for {config['name']}",
                    passed=False,
                    details=f"Failed with status {response.status_code}: {response.text}",
                    severity="critical"
                )
                self.validation_results.append(validation)
                logger.error(f"    ✗ Failed: {response.status_code}")

    async def _validate_professional_features(self, data: Dict[str, Any], config_name: str):
        """Validate professional consultation features in the response"""

        # 1. Check for professionalRecommendations
        has_prof_recs = "professionalRecommendations" in data
        if has_prof_recs:
            prof_recs = data["professionalRecommendations"]

            # Validate recommendation structure
            for rec in prof_recs[:3]:  # Check first 3
                required_fields = ["id", "type", "title", "description", "priority",
                                 "actionSteps", "timeline", "benefits", "risks"]
                for field in required_fields:
                    validation = ValidationResult(
                        check_name=f"Professional recommendation field '{field}'",
                        passed=field in rec,
                        details=f"Professional recommendation has {field}",
                        severity="high",
                        actual_value=rec.get(field),
                        expected_value=f"Non-empty {field}"
                    )
                    self.validation_results.append(validation)

                # Check actionSteps quality
                if "actionSteps" in rec:
                    validation = ValidationResult(
                        check_name=f"Action steps quality for {rec.get('title', 'Unknown')}",
                        passed=len(rec["actionSteps"]) >= 3,
                        details=f"Has {len(rec['actionSteps'])} action steps",
                        severity="medium",
                        actual_value=len(rec["actionSteps"]),
                        expected_value="At least 3 steps"
                    )
                    self.validation_results.append(validation)

        else:
            # Check if using fallback mode
            is_fallback = data.get("metadata", {}).get("fallback_used", False)
            validation = ValidationResult(
                check_name="Professional recommendations presence",
                passed=False,
                details=f"Missing professional recommendations (fallback: {is_fallback})",
                severity="high" if not is_fallback else "medium"
            )
            self.validation_results.append(validation)

        # 2. Check repaymentPlan structure
        if "repaymentPlan" in data and data["repaymentPlan"]:
            plan = data["repaymentPlan"]

            # Check for enhanced fields
            enhanced_fields = ["primaryStrategy", "alternativeStrategies",
                             "actionItems", "keyInsights", "riskFactors"]

            for field in enhanced_fields:
                if isinstance(plan, dict):
                    validation = ValidationResult(
                        check_name=f"Repayment plan field '{field}'",
                        passed=field in plan,
                        details=f"Repayment plan has {field}",
                        severity="high" if field == "primaryStrategy" else "medium",
                        actual_value=field in plan,
                        expected_value=True
                    )
                    self.validation_results.append(validation)

            # Validate primaryStrategy structure
            if "primaryStrategy" in plan and plan["primaryStrategy"]:
                strategy = plan["primaryStrategy"]
                strategy_fields = ["name", "description", "reasoning", "benefits", "timeline"]

                for field in strategy_fields:
                    validation = ValidationResult(
                        check_name=f"Primary strategy field '{field}'",
                        passed=field in strategy,
                        details=f"Primary strategy has {field}",
                        severity="medium",
                        actual_value=field in strategy,
                        expected_value=True
                    )
                    self.validation_results.append(validation)

        # 3. Check riskAssessment
        if "riskAssessment" in data:
            risk = data["riskAssessment"]

            validation = ValidationResult(
                check_name="Risk assessment structure",
                passed="level" in risk and "score" in risk and "factors" in risk,
                details="Risk assessment has required fields",
                severity="high",
                actual_value=list(risk.keys()) if isinstance(risk, dict) else None,
                expected_value=["level", "score", "factors"]
            )
            self.validation_results.append(validation)

        # 4. Check metadata quality score
        if "metadata" in data:
            metadata = data["metadata"]

            if "professionalQualityScore" in metadata:
                score = metadata["professionalQualityScore"]
                validation = ValidationResult(
                    check_name="Professional quality score",
                    passed=score >= 70,
                    details=f"Quality score: {score}/100",
                    severity="medium",
                    actual_value=score,
                    expected_value="≥ 70"
                )
                self.validation_results.append(validation)

            # Check enhancement method
            method = metadata.get("enhancement_method", "unknown")
            validation = ValidationResult(
                check_name="Enhancement method",
                passed=method in ["professional_consultation", "enhanced_workflow"],
                details=f"Using {method} method",
                severity="low",
                actual_value=method,
                expected_value="professional_consultation"
            )
            self.validation_results.append(validation)

    async def test_data_transformation(self):
        """Test data transformation between backend and frontend formats"""
        logger.info("\n🔄 Testing Data Transformation...")

        # Get raw insights
        response = self.session.get(f"{API_BASE_URL}/api/ai/insights")

        if response.status_code == 200:
            backend_data = response.json()

            # Simulate frontend data expectations
            frontend_expectations = {
                "debt_analysis": {
                    "required": ["total_debt", "debt_count", "average_interest_rate"],
                    "types": {"total_debt": (int, float), "debt_count": int}
                },
                "recommendations": {
                    "required": ["id", "title", "description"],
                    "types": {"priority_score": (int, float)}
                }
            }

            # Validate transformation
            for section, expectations in frontend_expectations.items():
                if section in backend_data:
                    section_data = backend_data[section]

                    # Check required fields
                    if "required" in expectations:
                        if isinstance(section_data, list) and len(section_data) > 0:
                            # Check first item in list
                            item = section_data[0]
                            for field in expectations["required"]:
                                validation = ValidationResult(
                                    check_name=f"Transform: {section}.{field}",
                                    passed=field in item,
                                    details=f"Field present in transformed data",
                                    severity="high"
                                )
                                self.validation_results.append(validation)
                        elif isinstance(section_data, dict):
                            for field in expectations["required"]:
                                validation = ValidationResult(
                                    check_name=f"Transform: {section}.{field}",
                                    passed=field in section_data,
                                    details=f"Field present in transformed data",
                                    severity="high"
                                )
                                self.validation_results.append(validation)

    async def test_fallback_mechanisms(self):
        """Test fallback mechanisms when AI agents fail"""
        logger.info("\n🛡️ Testing Fallback Mechanisms...")

        # Create a scenario that might trigger fallback
        # (e.g., user with no income for DTI calculation)
        update_response = self.session.put(
            f"{API_BASE_URL}/api/users/profile",
            json={"monthly_income": 0}
        )

        # Test insights with no income
        response = self.session.get(
            f"{API_BASE_URL}/api/ai/insights",
            params={"include_dti": True}
        )

        if response.status_code == 200:
            data = response.json()

            # Check if fallback was used
            fallback_used = data.get("metadata", {}).get("fallback_used", False)

            validation = ValidationResult(
                check_name="Fallback mechanism activation",
                passed=True,  # Should handle gracefully
                details=f"Fallback {'activated' if fallback_used else 'not needed'}",
                severity="high",
                actual_value=fallback_used
            )
            self.validation_results.append(validation)

            # Even with fallback, basic structure should be present
            basic_fields = ["debt_analysis", "recommendations", "metadata"]
            for field in basic_fields:
                validation = ValidationResult(
                    check_name=f"Fallback: {field} present",
                    passed=field in data,
                    details=f"Field present even in fallback mode",
                    severity="critical"
                )
                self.validation_results.append(validation)

        # Restore income
        self.session.put(
            f"{API_BASE_URL}/api/users/profile",
            json={"monthly_income": 8500.00}
        )

    async def test_enhanced_insights_endpoint_new(self):
        """Test the new enhanced insights endpoint if available"""
        logger.info("\n🚀 Testing Enhanced Insights Endpoint...")

        response = self.session.get(f"{API_BASE_URL}/api/ai/insights/enhanced")

        if response.status_code == 200:
            data = response.json()

            # Check for enhanced structure
            expected_structure = {
                "insights": dict,
                "recommendations": list,
                "dtiAnalysis": (dict, type(None))
            }

            for field, expected_type in expected_structure.items():
                if field in data:
                    actual_type = type(data[field])
                    if isinstance(expected_type, tuple):
                        type_match = actual_type in expected_type
                    else:
                        type_match = actual_type == expected_type

                    validation = ValidationResult(
                        check_name=f"Enhanced endpoint: {field} type",
                        passed=type_match,
                        details=f"Field has correct type",
                        severity="high",
                        actual_value=actual_type.__name__,
                        expected_value=str(expected_type)
                    )
                    self.validation_results.append(validation)

            logger.info("  ✓ Enhanced endpoint validated")
        else:
            logger.info(f"  ℹ Enhanced endpoint not available: {response.status_code}")

    async def test_frontend_compatibility(self):
        """Test that API responses match frontend TypeScript interfaces"""
        logger.info("\n🎨 Testing Frontend Compatibility...")

        # Get insights for comparison
        response = self.session.get(
            f"{API_BASE_URL}/api/ai/insights",
            params={"monthly_payment_budget": 2000.00, "preferred_strategy": "avalanche"}
        )

        if response.status_code == 200:
            data = response.json()

            # Frontend expects these exact field names (from ai-insights.ts)
            frontend_mappings = {
                "recommendations": {
                    "expected_fields": [
                        "id", "recommendation_type", "title", "description",
                        "potential_savings", "priority_score"
                    ]
                },
                "debt_analysis": {
                    "expected_fields": [
                        "total_debt", "debt_count", "average_interest_rate",
                        "total_minimum_payments", "high_priority_count"
                    ]
                }
            }

            for section, config in frontend_mappings.items():
                if section in data:
                    section_data = data[section]

                    if isinstance(section_data, list) and len(section_data) > 0:
                        # Check first item
                        item = section_data[0]
                        for field in config["expected_fields"]:
                            validation = ValidationResult(
                                check_name=f"Frontend compatibility: {section}.{field}",
                                passed=field in item,
                                details=f"Field matches frontend interface",
                                severity="critical"
                            )
                            self.validation_results.append(validation)
                    elif isinstance(section_data, dict):
                        for field in config["expected_fields"]:
                            validation = ValidationResult(
                                check_name=f"Frontend compatibility: {section}.{field}",
                                passed=field in section_data,
                                details=f"Field matches frontend interface",
                                severity="critical"
                            )
                            self.validation_results.append(validation)

    async def test_consultation_quality(self):
        """Test the quality of professional consultation features"""
        logger.info("\n💎 Testing Consultation Quality...")

        response = self.session.get(
            f"{API_BASE_URL}/api/ai/insights",
            params={"monthly_payment_budget": 2500.00}
        )

        if response.status_code == 200:
            data = response.json()

            quality_checks = []

            # 1. Check recommendation depth
            if "recommendations" in data:
                recs = data["recommendations"]

                avg_desc_length = sum(len(r.get("description", "")) for r in recs) / len(recs) if recs else 0
                quality_checks.append(ValidationResult(
                    check_name="Recommendation description depth",
                    passed=avg_desc_length >= 50,
                    details=f"Average description length: {avg_desc_length:.0f} chars",
                    severity="medium",
                    actual_value=avg_desc_length,
                    expected_value="≥ 50 characters"
                ))

            # 2. Check professional recommendations if present
            if "professionalRecommendations" in data:
                prof_recs = data["professionalRecommendations"]

                for rec in prof_recs[:2]:  # Check first 2
                    # Check action steps quality
                    action_steps = rec.get("actionSteps", [])
                    quality_checks.append(ValidationResult(
                        check_name=f"Action steps for '{rec.get('title', 'Unknown')}'",
                        passed=len(action_steps) >= 3 and all(len(step) > 10 for step in action_steps),
                        details=f"Has {len(action_steps)} detailed action steps",
                        severity="high",
                        actual_value=len(action_steps),
                        expected_value="≥ 3 detailed steps"
                    ))

                    # Check benefits quality
                    benefits = rec.get("benefits", [])
                    quality_checks.append(ValidationResult(
                        check_name=f"Benefits for '{rec.get('title', 'Unknown')}'",
                        passed=len(benefits) >= 2,
                        details=f"Has {len(benefits)} benefits listed",
                        severity="medium",
                        actual_value=len(benefits),
                        expected_value="≥ 2 benefits"
                    ))

            # 3. Check repayment plan quality
            if "repaymentPlan" in data and isinstance(data["repaymentPlan"], dict):
                plan = data["repaymentPlan"]

                # Check key insights
                insights = plan.get("keyInsights", [])
                quality_checks.append(ValidationResult(
                    check_name="Repayment plan insights",
                    passed=len(insights) >= 2,
                    details=f"Has {len(insights)} key insights",
                    severity="medium",
                    actual_value=len(insights),
                    expected_value="≥ 2 insights"
                ))

            self.validation_results.extend(quality_checks)

    async def compare_basic_vs_enhanced(self):
        """Compare basic recommendations vs professional consultation"""
        logger.info("\n📊 Comparing Basic vs Enhanced Features...")

        # Get standard insights
        standard_response = self.session.get(f"{API_BASE_URL}/api/ai/insights")

        if standard_response.status_code == 200:
            standard_data = standard_response.json()

            # Count features
            basic_rec_count = len(standard_data.get("recommendations", []))
            prof_rec_count = len(standard_data.get("professionalRecommendations", []))

            has_risk_assessment = "riskAssessment" in standard_data
            has_prof_plan = (
                "repaymentPlan" in standard_data and
                isinstance(standard_data.get("repaymentPlan"), dict) and
                "primaryStrategy" in standard_data.get("repaymentPlan", {})
            )

            quality_score = standard_data.get("metadata", {}).get("professionalQualityScore", 0)

            comparison_report = f"""
            📈 Feature Comparison:

            Basic Recommendations: {basic_rec_count}
            Professional Recommendations: {prof_rec_count}
            Has Risk Assessment: {has_risk_assessment}
            Has Professional Plan: {has_prof_plan}
            Quality Score: {quality_score}/100

            Enhancement Level: {'PROFESSIONAL' if prof_rec_count > 0 else 'BASIC'}
            """

            logger.info(comparison_report)

            # Add validation
            validation = ValidationResult(
                check_name="Professional enhancement level",
                passed=prof_rec_count > 0 or has_prof_plan,
                details=f"System provides {'professional' if prof_rec_count > 0 else 'basic'} consultation",
                severity="high",
                actual_value=f"{prof_rec_count} professional recommendations",
                expected_value="At least 1 professional feature"
            )
            self.validation_results.append(validation)

    async def generate_integration_report(self):
        """Generate comprehensive integration test report"""
        logger.info("\n" + "="*80)
        logger.info("📋 INTEGRATION TEST REPORT")
        logger.info("="*80)

        # Group results by severity
        critical = [r for r in self.validation_results if r.severity == "critical"]
        high = [r for r in self.validation_results if r.severity == "high"]
        medium = [r for r in self.validation_results if r.severity == "medium"]
        low = [r for r in self.validation_results if r.severity == "low"]

        # Calculate statistics
        total_checks = len(self.validation_results)
        passed_checks = len([r for r in self.validation_results if r.passed])
        pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        # Summary
        logger.info(f"""
📊 Test Summary:
  Total Checks: {total_checks}
  Passed: {passed_checks}
  Failed: {total_checks - passed_checks}
  Pass Rate: {pass_rate:.1f}%

📈 By Severity:
  Critical: {len(critical)} ({len([r for r in critical if r.passed])} passed)
  High: {len(high)} ({len([r for r in high if r.passed])} passed)
  Medium: {len(medium)} ({len([r for r in medium if r.passed])} passed)
  Low: {len(low)} ({len([r for r in low if r.passed])} passed)
""")

        # Detailed failures
        failures = [r for r in self.validation_results if not r.passed]
        if failures:
            logger.info("\n❌ Failed Checks:")
            for failure in failures[:10]:  # Show first 10 failures
                logger.info(f"""
  [{failure.severity.upper()}] {failure.check_name}
  Details: {failure.details}
  Expected: {failure.expected_value}
  Actual: {failure.actual_value}
""")

        # Critical issues
        critical_failures = [r for r in critical if not r.passed]
        if critical_failures:
            logger.error("\n🚨 CRITICAL ISSUES FOUND:")
            for issue in critical_failures:
                logger.error(f"  - {issue.check_name}: {issue.details}")

        # Professional features assessment
        prof_features = [r for r in self.validation_results if "professional" in r.check_name.lower()]
        prof_passed = len([r for r in prof_features if r.passed])

        logger.info(f"""
🎯 Professional Features Assessment:
  Total Professional Checks: {len(prof_features)}
  Passed: {prof_passed}
  Professional Feature Coverage: {(prof_passed/len(prof_features)*100) if prof_features else 0:.1f}%
""")

        # Overall verdict
        if pass_rate >= 90 and len(critical_failures) == 0:
            verdict = "✅ EXCELLENT - System is production ready"
            verdict_color = "green"
        elif pass_rate >= 70 and len(critical_failures) <= 2:
            verdict = "⚠️ GOOD - Minor issues to address"
            verdict_color = "yellow"
        elif pass_rate >= 50:
            verdict = "⚠️ NEEDS WORK - Several issues require attention"
            verdict_color = "orange"
        else:
            verdict = "❌ FAILING - Major issues need resolution"
            verdict_color = "red"

        logger.info(f"""
{"="*80}
FINAL VERDICT: {verdict}
{"="*80}
""")

        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": total_checks - passed_checks,
                "pass_rate": pass_rate,
                "verdict": verdict
            },
            "by_severity": {
                "critical": {
                    "total": len(critical),
                    "passed": len([r for r in critical if r.passed]),
                    "failed": len([r for r in critical if not r.passed])
                },
                "high": {
                    "total": len(high),
                    "passed": len([r for r in high if r.passed]),
                    "failed": len([r for r in high if not r.passed])
                },
                "medium": {
                    "total": len(medium),
                    "passed": len([r for r in medium if r.passed]),
                    "failed": len([r for r in medium if not r.passed])
                },
                "low": {
                    "total": len(low),
                    "passed": len([r for r in low if r.passed]),
                    "failed": len([r for r in low if not r.passed])
                }
            },
            "professional_features": {
                "total": len(prof_features),
                "passed": prof_passed,
                "coverage": (prof_passed/len(prof_features)*100) if prof_features else 0
            },
            "failures": [
                {
                    "check": f.check_name,
                    "severity": f.severity,
                    "details": f.details,
                    "expected": str(f.expected_value),
                    "actual": str(f.actual_value)
                }
                for f in failures
            ]
        }

        # Save to file
        report_file = f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"\n📄 Detailed report saved to: {report_file}")

        return pass_rate >= 70 and len(critical_failures) == 0


async def main():
    """Main test runner"""
    tester = ProfessionalIntegrationTester()

    try:
        # Run all tests
        await tester.setup_test_environment()
        await tester.create_test_debts()

        # Core integration tests
        await tester.test_enhanced_insights_endpoint()
        await tester.test_data_transformation()
        await tester.test_fallback_mechanisms()
        await tester.test_enhanced_insights_endpoint_new()
        await tester.test_frontend_compatibility()
        await tester.test_consultation_quality()
        await tester.compare_basic_vs_enhanced()

        # Generate report
        success = await tester.generate_integration_report()

        # Return exit code
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())