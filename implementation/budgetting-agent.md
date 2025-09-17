# Budget Tracking Multi-Agent System: Implementation Plan

This document outlines a step-by-step plan to implement a multi-AI agent system for budgeting and expense tracking, leveraging the existing `debt-optimizer-agent` structure as a reference. The system will be built using `pydantic_ai` for individual agents and `LangGraph` for orchestration.

## 1. Agent to File Mapping

Based on the proposed architecture, here's how the agents will map to Python files within the `app/agents/budget-tracking-agent/` directory:

*   **Core Coordinator Agent:** `orchestrator.py`
*   **Budget Planner Agent:** `budget_planner_agent.py`
*   **Expense Tracker Agent:** `expense_tracker_agent.py`
*   **Alert & Notification Agent:** `alert_notification_agent.py`
*   **Savings & Goal Tracker Agent:** `savings_goal_tracker_agent.py`
*   **Insight & Analysis Agent:** `insight_analysis_agent.py`

## 2. Step-by-Step Implementation Plan

### Step 1: Define Core Data Models (`app/models/`)

Create Pydantic models to represent the core entities for budgeting and expense tracking. These models will be used by all agents and for database interactions.

*   `app/models/budget.py`:
    *   `Budget`: Represents a user's budget, including categories, limits, and period.
    *   `BudgetCategory`: Defines a specific spending category.
*   `app/models/transaction.py`:
    *   `Transaction`: Represents an individual expense or income transaction.
*   `app/models/financial_goal.py`:
    *   `FinancialGoal`: Represents a user's savings or financial goal.
*   `app/models/user_profile.py`: (If not already existing)
    *   `UserProfile`: Extend the existing user model to include budgeting preferences.

### Step 2: Implement Individual AI Agents (`app/agents/budget-tracking-agent/`)

Each agent will be a Python class using `pydantic_ai.Agent`, similar to `DebtAnalyzingAgent` and `DebtOptimizerAgent`. They will define their specific `result_type` (Pydantic model for output) and `system_prompt`.

#### 2.1. `budget_planner_agent.py`

*   **Purpose:** Create and manage budgets.
*   **Input:** User income, fixed expenses, desired budget categories, financial goals.
*   **Output:** `Budget` object with suggested allocations.
*   **Tasks:**
    *   Analyze income and fixed expenses.
    *   Suggest budget allocations for categories.
    *   Adjust budgets based on user feedback or changes.

#### 2.2. `expense_tracker_agent.py`

*   **Purpose:** Categorize and track expenses.
*   **Input:** Raw transaction data (from manual input or external sources).
*   **Output:** Categorized `Transaction` objects.
*   **Tasks:**
    *   Automatically categorize transactions based on descriptions.
    *   Allow manual categorization and corrections.
    *   Summarize spending by category.

#### 2.3. `alert_notification_agent.py`

*   **Purpose:** Generate alerts and notifications.
*   **Input:** Current spending data, budget limits, upcoming bills.
*   **Output:** Notification messages.
*   **Tasks:**
    *   Monitor spending against budget limits.
    *   Identify unusual spending patterns.
    *   Track upcoming bill due dates.

#### 2.4. `savings_goal_tracker_agent.py`

*   **Purpose:** Track progress towards financial goals.
*   **Input:** Financial goals, current savings, income.
*   **Output:** `FinancialGoal` status updates, savings recommendations.
*   **Tasks:**
    *   Calculate progress towards goals.
    *   Suggest strategies to accelerate savings.

#### 2.5. `insight_analysis_agent.py`

*   **Purpose:** Provide deeper financial insights and recommendations.
*   **Input:** Historical budget and transaction data.
*   **Output:** `FinancialInsight` object (new Pydantic model) with trends, forecasts, and recommendations.
*   **Tasks:**
    *   Identify spending trends over time.
    *   Compare spending to budget and benchmarks.
    *   Forecast future expenses.
    *   Suggest cost-saving measures.

### Step 3: Develop the Orchestrator (`app/agents/budget-tracking-agent/orchestrator.py`)

This will be the central `LangGraph` workflow, similar to `orchestrator.py` in the debt optimizer.

*   **Define `GraphState`:** A TypedDict to hold the state of the budgeting process (e.g., `user_input`, `current_budget`, `transactions`, `alerts`, `insights`).
*   **Add Nodes:** Each agent's `run` method will be a node in the graph.
*   **Define Edges:**
    *   Conditional edges to route requests to the appropriate agent based on user input or system state.
    *   Sequential edges to pass data between agents (e.g., `ExpenseTracker` output to `BudgetPlanner` and `AlertNotification`).
*   **Entry Point:** Define the starting point of the workflow.
*   **Integration with Supabase:** Implement functions to save and retrieve budget data, transactions, and goals from Supabase, similar to how `repayment_plans` are handled.

### Step 4: Integration and Utilities

*   **Database Integration:**
    *   Update `app/databases/__init__.py` or create new modules for budget and transaction storage in Supabase.
    *   Ensure data models from Step 1 can be easily stored and retrieved.
*   **External Data Sources (Optional but Recommended):**
    *   If integrating with bank accounts (e.g., Plaid), create a utility module (`app/utils/financial_data_connector.py`) to handle API calls and data parsing. This would feed raw transaction data to the `ExpenseTrackerAgent`.
*   **Helper Functions:** Create any necessary helper functions for date calculations, financial calculations, etc., in `app/utils/`.

### Step 5: API Endpoints (`app/routes/`)

Create FastAPI routes to expose the functionality of the budget tracking system.

*   `app/routes/budget.py`:
    *   Endpoints for creating, updating, and retrieving budgets.
    *   Endpoint to trigger the `BudgetPlannerAgent`.
*   `app/routes/transactions.py`:
    *   Endpoints for logging and retrieving transactions.
    *   Endpoint to trigger the `ExpenseTrackerAgent`.
*   `app/routes/goals.py`:
    *   Endpoints for managing financial goals.
*   `app/routes/insights.py`:
    *   Endpoints to retrieve insights and analysis from the `InsightAnalysisAgent`.

### Step 6: Testing (`test/`)

*   **Unit Tests:** Write unit tests for each individual agent to ensure their `system_prompt` and `result_type` work as expected with `pydantic_ai`.
*   **Integration Tests:** Write integration tests for the `orchestrator.py` to verify the flow between agents and correct data passing.
*   **API Tests:** Test the FastAPI endpoints to ensure they correctly interact with the orchestrator and return expected results.

### Step 7: Documentation and Configuration

*   Update `README.md` with instructions on how to set up and run the new budget tracking system.
*   Add any new environment variables (e.g., for external financial APIs) to `app/configs/config.py` and document them.
*   Add agent-specific documentation within the code.

This plan provides a structured approach to building the multi-agent budgeting system, leveraging the existing patterns in your project.