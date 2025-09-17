from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import sys
from pathlib import Path

# Add project root to Python path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.models.transaction import Transaction
    from app.models.budget import Budget, BudgetCategory
    from app.models.financial_goal import FinancialGoal
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(project_root / "app"))
    from models.transaction import Transaction
    from models.budget import Budget, BudgetCategory
    from models.financial_goal import FinancialGoal

class BudgetDataFormatter:
    """Utility to format parsed financial data for budget tracking agents."""
    
    def __init__(self):
        """Initialize the budget data formatter."""
        pass
    
    def format_for_expense_tracker(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """
        Format transactions for the expense tracker agent.
        
        Args:
            transactions: List of Transaction objects
            
        Returns:
            Dictionary formatted for ExpenseTrackerAgent
        """
        formatted_transactions = []
        
        for transaction in transactions:
            formatted_transaction = {
                'id': transaction.id,
                'amount': transaction.amount,
                'description': transaction.description or '',
                'date': transaction.date.isoformat(),
                'type': transaction.type
            }
            formatted_transactions.append(formatted_transaction)
        
        return {
            'transactions': formatted_transactions,
            'total_count': len(formatted_transactions)
        }
    
    def format_for_budget_planner(self, 
                                transactions: List[Transaction], 
                                income_frequency: str = 'monthly',
                                budget_period_months: int = 1) -> Dict[str, Any]:
        """
        Format transaction data for the budget planner agent.
        
        Args:
            transactions: List of Transaction objects
            income_frequency: Frequency of income ('monthly', 'bi-weekly', 'weekly')
            budget_period_months: Number of months to analyze for planning
            
        Returns:
            Dictionary formatted for BudgetPlannerAgent
        """
        # Calculate income sources from transactions
        income_transactions = [t for t in transactions if t.type == 'income']
        income_by_source = defaultdict(list)
        
        for transaction in income_transactions:
            # Group by description to identify income sources
            source_name = self._categorize_income_source(transaction.description)
            income_by_source[source_name].append(transaction.amount)
        
        # Calculate average income per source
        income_sources = []
        for source, amounts in income_by_source.items():
            avg_amount = sum(amounts) / len(amounts) if amounts else 0
            income_sources.append({
                'name': source,
                'amount': round(avg_amount, 2),
                'frequency': income_frequency
            })
        
        # Calculate fixed expenses from transactions
        expense_transactions = [t for t in transactions if t.type == 'expense']
        fixed_expenses = self._identify_fixed_expenses(expense_transactions)
        
        # Generate desired categories based on transaction patterns
        desired_categories = self._generate_budget_categories(expense_transactions)
        
        return {
            'income_sources': income_sources,
            'fixed_expenses': fixed_expenses,
            'desired_categories': desired_categories
        }
    
    def format_for_alert_notification(self, 
                                    transactions: List[Transaction],
                                    current_budget: Optional[Budget] = None,
                                    days_lookback: int = 30) -> Dict[str, Any]:
        """
        Format data for the alert notification agent.
        
        Args:
            transactions: List of Transaction objects
            current_budget: Optional current budget
            days_lookback: Number of days to look back for recent transactions
            
        Returns:
            Dictionary formatted for AlertNotificationAgent
        """
        # Filter recent transactions
        cutoff_date = datetime.now() - timedelta(days=days_lookback)
        recent_transactions = [
            t for t in transactions 
            if t.date >= cutoff_date
        ]
        
        # Format recent transactions
        formatted_transactions = []
        for transaction in recent_transactions:
            formatted_transactions.append({
                'id': transaction.id,
                'amount': transaction.amount,
                'type': transaction.type,
                'category': transaction.category,
                'description': transaction.description,
                'date': transaction.date.isoformat(),
                'details': transaction.details
            })
        
        # Generate historical spending patterns
        historical_patterns = self._calculate_spending_patterns(transactions)
        
        # Identify upcoming bills from transaction patterns
        upcoming_bills = self._predict_upcoming_bills(transactions)
        
        return {
            'recent_transactions': formatted_transactions,
            'current_budget': current_budget.model_dump() if current_budget else None,
            'upcoming_bills': upcoming_bills,
            'historical_spending_patterns': historical_patterns
        }
    
    def format_for_savings_goal_tracker(self, 
                                      transactions: List[Transaction],
                                      financial_goals: List[FinancialGoal],
                                      current_budget: Optional[Budget] = None) -> Dict[str, Any]:
        """
        Format data for the savings goal tracker agent.
        
        Args:
            transactions: List of Transaction objects
            financial_goals: List of FinancialGoal objects
            current_budget: Optional current budget
            
        Returns:
            Dictionary formatted for SavingsGoalTrackerAgent
        """
        # Calculate available income for savings
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        
        # If we have a budget, use its discretionary income calculation
        if current_budget:
            allocated_total = sum(cat.allocated_amount for cat in current_budget.categories)
            available_income = current_budget.total_income - allocated_total
        else:
            # Estimate based on transactions
            available_income = max(0, total_income - total_expenses)
        
        # Format financial goals
        formatted_goals = []
        for goal in financial_goals:
            formatted_goals.append(goal.model_dump())
        
        return {
            'financial_goals': formatted_goals,
            'available_income_for_savings': round(available_income, 2)
        }
    
    def format_for_insight_analysis(self, 
                                  transactions: List[Transaction],
                                  historical_budgets: List[Budget],
                                  financial_goals: List[FinancialGoal]) -> Dict[str, Any]:
        """
        Format data for the insight analysis agent.
        
        Args:
            transactions: List of Transaction objects
            historical_budgets: List of historical Budget objects
            financial_goals: List of FinancialGoal objects
            
        Returns:
            Dictionary formatted for InsightAnalysisAgent
        """
        # Format transactions
        formatted_transactions = []
        for transaction in transactions:
            formatted_transactions.append({
                'id': transaction.id,
                'user_id': transaction.user_id,
                'amount': transaction.amount,
                'type': transaction.type,
                'category': transaction.category,
                'description': transaction.description,
                'date': transaction.date.isoformat(),
                'source': transaction.source,
                'details': transaction.details
            })
        
        # Format budgets
        formatted_budgets = []
        for budget in historical_budgets:
            formatted_budgets.append(budget.model_dump())
        
        # Format goals
        formatted_goals = []
        for goal in financial_goals:
            formatted_goals.append(goal.model_dump())
        
        return {
            'historical_budgets': formatted_budgets,
            'historical_transactions': formatted_transactions,
            'current_financial_goals': formatted_goals
        }
    
    def _categorize_income_source(self, description: str) -> str:
        """Categorize income source based on transaction description."""
        if not description:
            return "Unknown Income"
        
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ['salary', 'payroll', 'wages']):
            return "Salary"
        elif any(keyword in description_lower for keyword in ['freelance', 'consulting', 'contract']):
            return "Freelance/Consulting"
        elif any(keyword in description_lower for keyword in ['interest', 'dividend']):
            return "Investment Income"
        elif any(keyword in description_lower for keyword in ['rent', 'rental']):
            return "Rental Income"
        elif any(keyword in description_lower for keyword in ['refund', 'return']):
            return "Refunds"
        else:
            return "Other Income"
    
    def _identify_fixed_expenses(self, expense_transactions: List[Transaction]) -> List[Dict[str, Any]]:
        """Identify fixed expenses from transaction history."""
        # Group expenses by description and amount to find recurring payments
        expense_patterns = defaultdict(list)
        
        for transaction in expense_transactions:
            # Create a key based on similar description and amount
            key = self._normalize_expense_description(transaction.description)
            expense_patterns[key].append({
                'amount': transaction.amount,
                'date': transaction.date,
                'description': transaction.description
            })
        
        fixed_expenses = []
        for pattern, transactions in expense_patterns.items():
            if len(transactions) >= 2:  # Appears at least twice
                # Check if amounts are similar (within 10% variance)
                amounts = [t['amount'] for t in transactions]
                avg_amount = sum(amounts) / len(amounts)
                variance = max(amounts) - min(amounts)
                
                if variance / avg_amount <= 0.1:  # Low variance indicates fixed expense
                    # Estimate frequency based on date intervals
                    dates = sorted([t['date'] for t in transactions])
                    if len(dates) >= 2:
                        intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                        avg_interval = sum(intervals) / len(intervals)
                        
                        if 25 <= avg_interval <= 35:  # Monthly
                            frequency = 'monthly'
                        elif 12 <= avg_interval <= 16:  # Bi-weekly
                            frequency = 'bi-weekly'
                        elif 6 <= avg_interval <= 8:  # Weekly
                            frequency = 'weekly'
                        else:
                            frequency = 'monthly'  # Default
                    else:
                        frequency = 'monthly'
                    
                    fixed_expenses.append({
                        'name': pattern,
                        'amount': round(avg_amount, 2),
                        'frequency': frequency,
                        'due_date': None  # Could be estimated from transaction dates
                    })
        
        return fixed_expenses
    
    def _normalize_expense_description(self, description: str) -> str:
        """Normalize expense description for pattern matching."""
        if not description:
            return "Unknown Expense"
        
        # Remove common variations and numbers
        normalized = description.lower()
        normalized = normalized.replace('*', '').replace('#', '').replace('-', ' ')
        
        # Extract main merchant/service name (first few words)
        words = normalized.split()[:3]  # Take first 3 words
        return ' '.join(words).strip()
    
    def _generate_budget_categories(self, expense_transactions: List[Transaction]) -> List[str]:
        """Generate budget categories based on transaction patterns."""
        # Extract unique categories from transactions
        categories = set()
        
        for transaction in expense_transactions:
            if transaction.category and transaction.category != 'Uncategorized':
                categories.add(transaction.category)
        
        # If we have transaction categories, use them
        if categories:
            return list(categories)
        
        # Otherwise, return standard budget categories
        return [
            'Housing', 'Transportation', 'Food', 'Utilities', 'Insurance',
            'Healthcare', 'Debt Payments', 'Savings', 'Entertainment',
            'Shopping', 'Education', 'Miscellaneous'
        ]
    
    def _calculate_spending_patterns(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Calculate historical spending patterns by category."""
        patterns = defaultdict(list)
        
        for transaction in transactions:
            if transaction.type == 'expense':
                patterns[transaction.category].append(transaction.amount)
        
        # Calculate statistics for each category
        spending_patterns = {}
        for category, amounts in patterns.items():
            if amounts:
                spending_patterns[category] = {
                    'average': round(sum(amounts) / len(amounts), 2),
                    'min': round(min(amounts), 2),
                    'max': round(max(amounts), 2),
                    'total': round(sum(amounts), 2),
                    'count': len(amounts)
                }
        
        return spending_patterns
    
    def _predict_upcoming_bills(self, transactions: List[Transaction]) -> List[Dict[str, Any]]:
        """Predict upcoming bills based on transaction history."""
        # This is a simplified prediction - in a real implementation,
        # you might use more sophisticated pattern recognition
        
        fixed_expenses = self._identify_fixed_expenses(
            [t for t in transactions if t.type == 'expense']
        )
        
        upcoming_bills = []
        current_date = datetime.now()
        
        for expense in fixed_expenses:
            # Estimate next due date based on frequency
            if expense['frequency'] == 'monthly':
                next_due = current_date + timedelta(days=30)
            elif expense['frequency'] == 'bi-weekly':
                next_due = current_date + timedelta(days=14)
            elif expense['frequency'] == 'weekly':
                next_due = current_date + timedelta(days=7)
            else:
                next_due = current_date + timedelta(days=30)
            
            upcoming_bills.append({
                'name': expense['name'],
                'amount': expense['amount'],
                'due_date': next_due.isoformat()
            })
        
        return upcoming_bills

# Convenience functions
def format_transactions_for_agent(transactions: List[Transaction], 
                                agent_type: str, 
                                **kwargs) -> Dict[str, Any]:
    """
    Convenience function to format transactions for a specific agent.
    
    Args:
        transactions: List of Transaction objects
        agent_type: Type of agent ('expense_tracker', 'budget_planner', 'alert_notification', 
                   'savings_goal_tracker', 'insight_analysis')
        **kwargs: Additional arguments specific to each agent
        
    Returns:
        Formatted data dictionary
    """
    formatter = BudgetDataFormatter()
    
    if agent_type == 'expense_tracker':
        return formatter.format_for_expense_tracker(transactions)
    elif agent_type == 'budget_planner':
        return formatter.format_for_budget_planner(transactions, **kwargs)
    elif agent_type == 'alert_notification':
        return formatter.format_for_alert_notification(transactions, **kwargs)
    elif agent_type == 'savings_goal_tracker':
        return formatter.format_for_savings_goal_tracker(transactions, **kwargs)
    elif agent_type == 'insight_analysis':
        return formatter.format_for_insight_analysis(transactions, **kwargs)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}") 