# Debt Repayment Optimizer

A smart system that helps users manage and efficiently pay off their debts using AI optimization and blockchain security.

## Features

- **Debt Management**: Analyze and track both manual and bank-linked debts
- **AI Optimization**: Get customized repayment plans using avalanche or snowball methods
- **Payment Reminders**: Receive notifications for upcoming payments
- **Blockchain Security**: Store debt records securely and transparently
- **Progress Tracking**: Visualize your debt repayment journey
# Debt Repayment Optimizer: Updated Project Setup

## Technology Stack

The project now uses the following technologies based on your requirements:

### Backend
- **FastAPI**: Modern, high-performance web framework
- **Supabase**: Combined database and vector storage
- **LangGraph**: AI agent orchestration framework
- **Pydantic AI**: Structured data models for AI
- **OpenAI**: API for AI agent capabilities

### AI Components
- **DebtAnalyzerAgent**: Analyzes debt information and provides insights
- **DebtOptimizerAgent**: Creates optimized repayment plans
- **Agent Orchestration**: Manages flow between AI agents using LangGraph

### Database
- **Supabase PostgreSQL**: Relational database for all data
- **pgvector**: Vector database extension for AI embeddings

### Blockchain Integration
- Interface for your teammate to implement blockchain components

## Project Structure

```
DebtEase/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── config.py                  # Configuration settings
│   │   ├── database.py                # Supabase database client
│   │   ├── dependencies.py            # FastAPI dependencies
│   │   ├── routes/                    # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── debts.py
│   │   │   ├── repayment_plans.py
│   │   │   └── notifications.py
│   │   ├── models/                    # Data models
│   │   │   ├── user.py
│   │   │   ├── debt.py
│   │   │   ├── payment.py
│   │   │   └── repayment_plan.py
│   │   ├── blockchain_interface.py    # Interface to blockchain
│   │   └── ai_module/                 # AI agent system
│   │       ├── agent_base.py          # Base agent class
│   │       ├── debt_analyzer_agent.py # Financial analysis agent
│   │       ├── debt_optimizer_agent.py # Optimization agent
│   │       └── orchestrator.py        # LangGraph workflow
│   ├── tests/                         # Unit and integration tests
│   │   ├── test_routes/
│   │   ├── test_ai_module/
│   │   └── test_services/
│   ├── requirements.txt               # Python dependencies
│   └── Dockerfile                     # Backend container config
├── blockchain/                        # Your teammate's responsibility
│   ├── contracts/                     # Smart contracts
│   ├── migrations/                    # Contract migrations
│   ├── scripts/                       # Deployment scripts
│   └── tests/                         # Blockchain tests
└── docs/                              # Documentation
    ├── architecture.md
    ├── api.md
    └── database.md
```

## Implementation Details

### AI Agents System

The AI system works as follows:

1. **Debt Analyzer Agent**: 
   - Analyzes user's debts to identify patterns and insights
   - Identifies highest impact debts and areas of concern
   - Provides financial analysis of debt situation

2. **Debt Optimizer Agent**:
   - Creates optimized repayment strategies
   - Compares multiple approaches (avalanche, snowball, etc.)
   - Provides customized recommendations

3. **Orchestration with LangGraph**:
   - Manages the workflow between agents
   - Handles state transitions and data passing
   - Provides a structured pipeline for optimization

### Supabase Database

The Supabase database includes:

1. **Relational Tables**:
   - Users
   - Debts
   - Payments
   - Repayment Plans
   - Notifications

2. **Vector Database**:
   - Embeddings table for vector similarity search
   - Custom function for matching similar financial scenarios
   - Indexes for efficient querying

3. **Security**:
   - Row-Level Security (RLS) policies
   - User authentication integration
   - Data encryption for sensitive information


## Getting Started

### Prerequisites

- Python 3.11
- Node.js 14+
- Docker and Docker Compose (optional)

### Installation

1. Clone the repository:
   ```
   git clone git@github.com:MihirsinhChauhan/DebtEase.git
   cd DebtEase
   ```

2. Set up the backend:
   ```
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up the blockchain component:
   ```
   cd ../blockchain
   npm install
   ```

4. Set up the frontend:
   ```
   cd ../frontend
   npm install
   ```

### Running the Application

1. Start the backend:
   ```
   cd backend
   uvicorn app.main:app --reload
   ```

2. Start the blockchain node:
   ```
   cd blockchain
   npm run node
   ```

3. Start the frontend:
   ```
   cd frontend
   npm start
   ```

## API Documentation

API documentation is available at `/docs` when the backend server is running.


## Contributors

- [Your Name] - Backend and AI
- [Teammate's Name] - Blockchain