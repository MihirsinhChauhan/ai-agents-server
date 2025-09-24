#!/usr/bin/env python3
"""Test importing professional AI agents"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing professional agent imports...")

try:
    from app.agents.debt_optimizer_agent.enhanced_debt_analyzer import EnhancedDebtAnalyzer, DebtAnalysisResult
    print("✓ EnhancedDebtAnalyzer imported successfully")
except ImportError as e:
    print(f"✗ Failed to import EnhancedDebtAnalyzer: {e}")

try:
    from app.agents.debt_optimizer_agent.ai_recommendation_agent import AIRecommendationAgent, RecommendationSet, AIRecommendation
    print("✓ AIRecommendationAgent imported successfully")
except ImportError as e:
    print(f"✗ Failed to import AIRecommendationAgent: {e}")

try:
    from app.agents.debt_optimizer_agent.enhanced_debt_optimizer import EnhancedDebtOptimizer, RepaymentPlan
    print("✓ EnhancedDebtOptimizer imported successfully")
except ImportError as e:
    print(f"✗ Failed to import EnhancedDebtOptimizer: {e}")

print("\nTrying to initialize agents...")
try:
    analyzer = EnhancedDebtAnalyzer()
    print("✓ EnhancedDebtAnalyzer initialized")

    recommender = AIRecommendationAgent()
    print("✓ AIRecommendationAgent initialized")

    optimizer = EnhancedDebtOptimizer()
    print("✓ EnhancedDebtOptimizer initialized")

    print("\n✅ All professional agents are available!")

except Exception as e:
    print(f"\n✗ Failed to initialize agents: {e}")
    import traceback
    traceback.print_exc()