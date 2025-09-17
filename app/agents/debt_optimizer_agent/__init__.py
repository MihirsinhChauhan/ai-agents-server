"""
Debt Optimizer Agent package for DebtEase server.
Enhanced with Pydantic AI agents for comprehensive debt analysis and optimization.
"""

# Legacy agents (for backward compatibility)
from .debt_analyzer_agent import DebtAnalyzingAgent as DebtAnalyzerAgent
from .debt_optimizer_agent import DebtOptimizerAgent
# Note: Legacy orchestrator commented out due to Supabase dependency
# from .orchestrator import DebtOptimizerOrchestrator

# Enhanced Pydantic AI agents
from .enhanced_debt_analyzer import EnhancedDebtAnalyzer, DebtAnalysisResult
from .enhanced_debt_optimizer import EnhancedDebtOptimizer, RepaymentPlan
from .ai_recommendation_agent import AIRecommendationAgent, RecommendationSet
from .dti_calculator_agent import DTICalculatorAgent, DTIAnalysis
from .enhanced_orchestrator import EnhancedAIOrchestrator, AIOrchestrationResult
from .langgraph_orchestrator import LangGraphOrchestrator, WorkflowResult, OrchestrationState

__all__ = [
    # Legacy agents
    'DebtAnalyzerAgent',
    'DebtOptimizerAgent',

    # Enhanced Pydantic AI agents
    'EnhancedDebtAnalyzer',
    'DebtAnalysisResult',
    'EnhancedDebtOptimizer',
    'RepaymentPlan',
    'AIRecommendationAgent',
    'RecommendationSet',
    'DTICalculatorAgent',
    'DTIAnalysis',
    'EnhancedAIOrchestrator',
    'AIOrchestrationResult',

    # LangGraph Orchestration (NEW)
    'LangGraphOrchestrator',
    'WorkflowResult',
    'OrchestrationState',
]
