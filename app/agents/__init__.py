"""
AI Agents package for DebtEase server.
"""

# Import all agent modules to make them available
try:
    from .budget_tracking_agent import *
except ImportError:
    pass

try:
    from .debt_optimizer_agent import *
except ImportError:
    pass

try:
    from .wealth_management_agent import *
except ImportError:
    pass

__all__ = [
    # Budget tracking agent
    'BudgetTrackingOrchestrator',
    'BudgetPlannerAgent',
    'ExpenseTrackerAgent',
    'AlertNotificationAgent',
    'SavingsGoalTrackerAgent',
    'InsightAnalysisAgent',
    
    # Debt optimizer agent
    'DebtAnalyzerAgent',
    'DebtOptimizerAgent',
    'DebtOptimizerOrchestrator',
    
    # Wealth management agent
    # Add wealth management agent classes here when implemented
] 