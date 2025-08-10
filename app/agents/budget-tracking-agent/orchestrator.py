from typing import Dict, Any, List, TypedDict, Optional
import json
from langgraph.graph import StateGraph, END
from pydantic import ValidationError
from uuid import UUID

from app.configs.config import settings
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.financial_goal import FinancialGoal
from app.agents.budget_tracking_agent.budget_planner_agent import BudgetPlannerAgent, BudgetPlan
from app.agents.budget_tracking_agent.expense_tracker_agent import ExpenseTrackerAgent, ExpenseTrackingSummary
from app.agents.budget_tracking_agent.alert_notification_agent import AlertNotificationAgent, AlertNotificationSummary
from app.agents.budget_tracking_agent.savings_goal_tracker_agent import SavingsGoalTrackerAgent, SavingsGoalTrackingSummary
from app.agents.budget_tracking_agent.insight_analysis_agent import InsightAnalysisAgent, FinancialInsight

# Assuming Supabase client is available and configured in app.configs.config
# from supabase import create_client


class GraphState(TypedDict):
    """
    State object for the LangGraph workflow for budget tracking.
    """
    user_id: str
    user_input: Dict[str, Any]  # General input from the user
    current_budget: Optional[Budget]
    transactions: List[Transaction]
    financial_goals: List[FinancialGoal]
    budget_plan: Optional[BudgetPlan]
    expense_summary: Optional[ExpenseTrackingSummary]
    alerts: Optional[AlertNotificationSummary]
    savings_summary: Optional[SavingsGoalTrackingSummary]
    financial_insights: Optional[FinancialInsight]
    error: Optional[str]


class BudgetTrackingOrchestrator:
    """
    Orchestrates the AI agents using LangGraph to manage budgeting and expense tracking.
    """
    
    def __init__(self):
        """Initialize the orchestrator with the workflow graph."""
        self.workflow = self._build_workflow()
        
    def run_budget_workflow(
        self,
        user_id: str,
        user_input: Dict[str, Any],
        current_budget: Optional[Dict[str, Any]] = None,
        transactions: Optional[List[Dict[str, Any]]] = None,
        financial_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Run the budget tracking workflow.

        Args:
            user_id: UUID of the user.
            user_input: Dictionary containing user's request/data (e.g., income, expenses, new transaction).
            current_budget: Optional dictionary of the current budget data.
            transactions: Optional list of transaction dictionaries.
            financial_goals: Optional list of financial goal dictionaries.

        Returns:
            Dictionary with the results from various agents.

        Raises:
            ValueError: If an error occurs during the workflow.
        """
        # Convert input dictionaries to Pydantic models where applicable
        try:
            budget_obj = Budget.model_validate(current_budget) if current_budget else None
            transaction_objs = [Transaction.model_validate(t) for t in transactions] if transactions else []
            goal_objs = [FinancialGoal.model_validate(g) for g in financial_goals] if financial_goals else []
        except ValidationError as e:
            raise ValueError(f"Invalid input data: {str(e)}")

        # Initialize the state
        initial_state: GraphState = {
            "user_id": user_id,
            "user_input": user_input,
            "current_budget": budget_obj,
            "transactions": transaction_objs,
            "financial_goals": goal_objs,
            "budget_plan": None,
            "expense_summary": None,
            "alerts": None,
            "savings_summary": None,
            "financial_insights": None,
            "error": None
        }

        # Run the workflow
        result = self.workflow.invoke(initial_state)

        # Check for errors
        if result["error"]:
            raise ValueError(result["error"])

        # TODO: Save relevant data to Supabase (e.g., updated budget, new transactions, updated goals)
        # self._save_to_database(result)

        return {
            "budget_plan": result["budget_plan"].dict() if result["budget_plan"] else None,
            "expense_summary": result["expense_summary"].dict() if result["expense_summary"] else None,
            "alerts": result["alerts"].dict() if result["alerts"] else None,
            "savings_summary": result["savings_summary"].dict() if result["savings_summary"] else None,
            "financial_insights": result["financial_insights"].dict() if result["financial_insights"] else None,
        }
        
    def _build_workflow(self) -> StateGraph:
        """
        Build the workflow graph.

        Returns:
            Compiled StateGraph instance.
        """
        workflow = StateGraph(GraphState)

        # Add nodes for each agent
        workflow.add_node("plan_budget", self._call_budget_planner)
        workflow.add_node("track_expenses", self._call_expense_tracker)
        workflow.add_node("generate_alerts", self._call_alert_notification)
        workflow.add_node("track_savings_goals", self._call_savings_goal_tracker)
        workflow.add_node("analyze_insights", self._call_insight_analysis)

        # Define edges based on typical flow and user input
        # This is a simplified flow; real-world might have more complex conditionals
        workflow.set_entry_point("plan_budget") # Start with budget planning or expense tracking based on input

        # Example flow: Plan budget -> Track expenses -> Generate alerts -> Track savings -> Analyze insights
        workflow.add_edge("plan_budget", "track_expenses")
        workflow.add_edge("track_expenses", "generate_alerts")
        workflow.add_edge("generate_alerts", "track_savings_goals")
        workflow.add_edge("track_savings_goals", "analyze_insights")
        workflow.add_edge("analyze_insights", END)

        # TODO: Add more sophisticated conditional edges based on user_input or state
        # For example, if user_input is only about tracking expenses, skip budget planning.

        return workflow.compile()

    def _call_budget_planner(self, state: GraphState) -> GraphState:
        """
        Call the BudgetPlannerAgent.
        """
        if state["error"]:
            return state
        try:
            planner = BudgetPlannerAgent()
            # Dummy data for now, replace with actual user_input parsing
            income_sources = state["user_input"].get("income_sources", [])
            fixed_expenses = state["user_input"].get("fixed_expenses", [])
            desired_categories = state["user_input"].get("desired_categories", ['Housing', 'Transportation', 'Food', 'Utilities', 'Insurance', 'Healthcare', 'Debt Payments', 'Savings', 'Entertainment', 'Shopping', 'Education', 'Miscellaneous'])
            financial_goals = [g.model_dump() for g in state["financial_goals"]] if state["financial_goals"] else []
            current_budget_dict = state["current_budget"].model_dump() if state["current_budget"] else None

            budget_plan = planner.plan_budget(
                user_id=state["user_id"],
                income_sources=income_sources,
                fixed_expenses=fixed_expenses,
                desired_categories=desired_categories,
                financial_goals=financial_goals,
                current_budget=current_budget_dict
            )
            state["budget_plan"] = budget_plan
            state["current_budget"] = budget_plan.recommended_budget # Update current budget with the new plan
        except Exception as e:
            state["error"] = f"Error planning budget: {str(e)}"
        return state

    def _call_expense_tracker(self, state: GraphState) -> GraphState:
        """
        Call the ExpenseTrackerAgent.
        """
        if state["error"]:
            return state
        try:
            tracker = ExpenseTrackerAgent()
            # Dummy data for now, replace with actual user_input parsing or fetched transactions
            transactions_data = [t.model_dump() for t in state["transactions"]] if state["transactions"] else []
            available_categories = [c.name for c in state["current_budget"].categories] if state["current_budget"] else []
            if not available_categories: # Fallback if no budget is set yet
                available_categories = ['Groceries', 'Utilities', 'Transportation', 'Dining Out', 'Salary', 'Rent', 'Shopping', 'Entertainment', 'Healthcare', 'Education', 'Miscellaneous', 'Uncategorized']

            expense_summary = tracker.track_expenses(
                user_id=state["user_id"],
                transactions=transactions_data,
                available_categories=available_categories
            )
            state["expense_summary"] = expense_summary
            # Update budget spent amounts based on expense summary
            if state["current_budget"] and expense_summary:
                updated_categories = []
                for budget_cat in state["current_budget"].categories:
                    spent = expense_summary.spending_by_category.get(budget_cat.name, 0.0)
                    budget_cat.spent_amount = spent
                    budget_cat.limit_exceeded = spent > budget_cat.allocated_amount
                    updated_categories.append(budget_cat)
                state["current_budget"].categories = updated_categories
                state["current_budget"].updated_at = datetime.now()

        except Exception as e:
            state["error"] = f"Error tracking expenses: {str(e)}"
        return state

    def _call_alert_notification(self, state: GraphState) -> GraphState:
        """
        Call the AlertNotificationAgent.
        """
        if state["error"]:
            return state
        try:
            alerter = AlertNotificationAgent()
            # Dummy data for now, replace with actual fetched data
            current_budget_dict = state["current_budget"].model_dump() if state["current_budget"] else None
            recent_transactions_dict = [t.model_dump() for t in state["transactions"]] if state["transactions"] else []
            # TODO: Fetch upcoming bills and historical spending patterns from DB
            upcoming_bills = state["user_input"].get("upcoming_bills", [])
            historical_spending_patterns = state["user_input"].get("historical_spending_patterns", {})

            alerts = alerter.generate_alerts(
                user_id=state["user_id"],
                current_budget=current_budget_dict,
                recent_transactions=recent_transactions_dict,
                upcoming_bills=upcoming_bills,
                historical_spending_patterns=historical_spending_patterns
            )
            state["alerts"] = alerts
        except Exception as e:
            state["error"] = f"Error generating alerts: {str(e)}"
        return state

    def _call_savings_goal_tracker(self, state: GraphState) -> GraphState:
        """
        Call the SavingsGoalTrackerAgent.
        """
        if state["error"]:
            return state
        try:
            tracker = SavingsGoalTrackerAgent()
            financial_goals_dict = [g.model_dump() for g in state["financial_goals"]] if state["financial_goals"] else []
            # Available income for savings could come from budget plan or user input
            available_income_for_savings = state["budget_plan"].discretionary_income if state["budget_plan"] else 0.0

            savings_summary = tracker.track_goals(
                user_id=state["user_id"],
                financial_goals=financial_goals_dict,
                available_income_for_savings=available_income_for_savings
            )
            state["savings_summary"] = savings_summary
            # Update financial goals in state with potentially updated current_amount/is_achieved
            if savings_summary:
                state["financial_goals"] = savings_summary.goals
        except Exception as e:
            state["error"] = f"Error tracking savings goals: {str(e)}"
        return state

    def _call_insight_analysis(self, state: GraphState) -> GraphState:
        """
        Call the InsightAnalysisAgent.
        """
        if state["error"]:
            return state
        try:
            analyzer = InsightAnalysisAgent()
            # TODO: Fetch historical budgets and transactions from DB
            historical_budgets_dict = [state["current_budget"].model_dump()] if state["current_budget"] else [] # For now, just current budget
            historical_transactions_dict = [t.model_dump() for t in state["transactions"]] if state["transactions"] else [] # For now, just current transactions
            current_financial_goals_dict = [g.model_dump() for g in state["financial_goals"]] if state["financial_goals"] else []

            financial_insights = analyzer.analyze_financial_data(
                user_id=state["user_id"],
                historical_budgets=historical_budgets_dict,
                historical_transactions=historical_transactions_dict,
                current_financial_goals=current_financial_goals_dict
            )
            state["financial_insights"] = financial_insights
        except Exception as e:
            state["error"] = f"Error analyzing insights: {str(e)}"
        return state

    # TODO: Implement _save_to_database method to persist data to Supabase
    # def _save_to_database(self, state: GraphState):
    #     """
    #     Save relevant data from the workflow state to Supabase.
    #     """
    #     try:
    #         supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    #         # Example: Save/update budget
    #         if state["current_budget"]:
    #             # Logic to insert or update budget in Supabase
    #             pass
    #         # Example: Save new transactions
    #         # if state["new_transactions"]:
    #         #     # Logic to insert new transactions
    #         #     pass
    #         # Example: Update financial goals
    #         # if state["financial_goals"]:
    #         #     # Logic to update goals
    #         #     pass
    #     except Exception as e:
    #     raise ValueError(f"Error saving data to Supabase: {str(e)}")
