from typing import Dict, Any, List, TypedDict, Optional
import json
from langgraph.graph import StateGraph, END
from pydantic import ValidationError

from app.models.debt import Debt
from app.models.repayment_plan import RepaymentPlanCreate
from .debt_analyzer_agent import DebtAnalyzingAgent, DebtAnalysis
from .debt_optimizer_agent import DebtOptimizerAgent, RepaymentPlanSummary
from app.configs.config import settings
from supabase import create_client
from uuid import UUID


class GraphState(TypedDict):
    """
    State object for the LangGraph workflow.
    """
    debts: List[Debt]
    monthly_payment: float
    preferred_strategy: Optional[str]
    analysis_file: Optional[str]
    debt_analysis: Optional[DebtAnalysis]
    repayment_plan: Optional[RepaymentPlanSummary]
    error: Optional[str]


class DebtOptimizerOrchestrator:
    """
    Orchestrates the AI agents using LangGraph to analyze debts and generate an optimized repayment plan.
    """
    
    def __init__(self):
        """Initialize the orchestrator with the workflow graph."""
        self.workflow = self._build_workflow()
        
    def optimize_debt_repayment(
        self,
        debts: List[Dict[str, Any]],
        monthly_payment: float,
        preferred_strategy: Optional[str] = None,
        analysis_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the debt optimization workflow.

        Args:
            debts: List of debt dictionaries (with '_id' for debt IDs).
            monthly_payment: Monthly payment amount for repayment.
            preferred_strategy: Optional preferred strategy ('avalanche', 'snowball', 'custom').
            analysis_file: Optional path to a DebtAnalysis JSON file.

        Returns:
            Dictionary with optimization results (analysis, repayment plan).

        Raises:
            ValueError: If an error occurs during the workflow.
        """
        # Convert debt dictionaries to Debt objects
        try:
            debt_objects = [Debt.model_validate(debt) for debt in debts]
        except ValidationError as e:
            raise ValueError(f"Invalid debt data: {str(e)}")

        # Initialize the state
        initial_state: GraphState = {
            "debts": debt_objects,
            "monthly_payment": monthly_payment,
            "preferred_strategy": preferred_strategy,
            "analysis_file": analysis_file,
            "debt_analysis": None,
            "repayment_plan": None,
            "error": None
        }

        # Run the workflow
        result = self.workflow.invoke(initial_state)

        # Check for errors
        if result["error"]:
            raise ValueError(result["error"])

        # Save repayment plan to Supabase
        if result["repayment_plan"]:
            user_id = str(debt_objects[0].user_id)  # Assume all debts belong to one user
            repayment_plan = self._save_to_repayment_plans(result["repayment_plan"], user_id)
            result["repayment_plan"] = repayment_plan.dict()

        return {
            "debt_analysis": result["debt_analysis"].dict() if result["debt_analysis"] else None,
            "repayment_plan": result["repayment_plan"]
        }
        
    def _build_workflow(self) -> StateGraph:
        """
        Build the workflow graph.

        Returns:
            Compiled StateGraph instance.
        """
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("load_analysis", self._load_analysis)
        workflow.add_node("analyze_debts", self._analyze_debts)
        workflow.add_node("optimize_repayment", self._optimize_repayment)

        # Define edges
        workflow.add_conditional_edges(
            "load_analysis",
            self._decide_analysis_path,
            {
                "analyze_debts": "analyze_debts",
                "optimize_repayment": "optimize_repayment"
            }
        )
        workflow.add_edge("analyze_debts", "optimize_repayment")
        workflow.add_edge("optimize_repayment", END)

        # Set entry point
        workflow.set_entry_point("load_analysis")

        return workflow.compile()

    def _decide_analysis_path(self, state: GraphState) -> str:
        """
        Decide whether to load an analysis file or run debt analysis.

        Args:
            state: Current workflow state.

        Returns:
            Next node name ('analyze_debts' or 'optimize_repayment').
        """
        if state["analysis_file"] and not state["error"]:
            return "optimize_repayment"
        return "analyze_debts"

    def _load_analysis(self, state: GraphState) -> GraphState:
        """
        Load DebtAnalysis from a file if provided.

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state.
        """
        if not state["analysis_file"]:
            return state

        try:
            with open(state["analysis_file"], 'r') as f:
                analysis_data = json.load(f)
            state["debt_analysis"] = DebtAnalysis.model_validate(analysis_data)
        except Exception as e:
            state["error"] = f"Error loading analysis file: {str(e)}"

        return state

    def _analyze_debts(self, state: GraphState) -> GraphState:
        """
        Analyze debts using DebtAnalyzerAgent.

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state.
        """
        if state["error"]:
            return state

        try:
            analyzer = DebtAnalyzingAgent()
            analysis = analyzer.analyze(state["debts"])
            state["debt_analysis"] = analysis
        except Exception as e:
            state["error"] = f"Error analyzing debts: {str(e)}"

        return state

    def _optimize_repayment(self, state: GraphState) -> GraphState:
        """
        Optimize repayment plan using DebtOptimizerAgent.

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state.
        """
        if state["error"] or not state["debt_analysis"]:
            state["error"] = state["error"] or "No debt analysis available"
            return state

        try:
            optimizer = DebtOptimizerAgent()
            # Adjust recommended_monthly_payment if preferred_strategy is set
            analysis = state["debt_analysis"]
            monthly_payment = state["monthly_payment"]
            if state["preferred_strategy"]:
                monthly_payment = max(monthly_payment, analysis.min_payment_sum * 1.5)
            repayment_plan = optimizer.optimize(state["debts"], analysis)
            state["repayment_plan"] = repayment_plan
        except Exception as e:
            state["error"] = f"Error optimizing repayment: {str(e)}"

        return state

    def _save_to_repayment_plans(self, repayment_plan: RepaymentPlanSummary, user_id: str) -> RepaymentPlanCreate:
        """
        Save repayment plan to Supabase repayment_plans table.

        Args:
            repayment_plan: RepaymentPlanSummary object.
            user_id: User UUID as string.

        Returns:
            RepaymentPlanCreate object saved to Supabase.
        """
        try:
            plan = RepaymentPlanCreate(
                user_id=UUID(user_id),
                strategy=repayment_plan.recommended_strategy,
                monthly_payment_amount=repayment_plan.recommended_monthly_payment,
                debt_order=[UUID(debt_id) for debt_id in repayment_plan.alternative_strategies[0].debt_order],
                total_interest_saved=repayment_plan.total_interest_saved,
                expected_completion_date=repayment_plan.expected_completion_date,
                payment_schedule=[
                    {"debt_id": debt_id, "payoff_date": date}
                    for debt_id, date in repayment_plan.milestone_dates.items()
                ]
            )
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            supabase.table("repayment_plans").insert(plan.model_dump(by_alias=True)).execute()
            return plan
        except Exception as e:
            raise ValueError(f"Error saving repayment plan to Supabase: {str(e)}")