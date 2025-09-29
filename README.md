# Debtease Backend - AI-Powered Debt Management API

The Debtease backend is a robust, AI-driven API server that powers intelligent debt management and financial wellness features. Built with FastAPI and Python, it provides the core intelligence behind personalized debt analysis, repayment optimization, and financial coaching.

## 🌟 Features

- **AI-Powered Debt Analysis**: Advanced algorithms that analyze debt patterns and provide personalized insights using machine learning models.
- **Intelligent Repayment Strategies**: Automated optimization using Snowball, Avalanche, and hybrid approaches to minimize interest and accelerate debt freedom.
- **Smart Payment Scheduling**: Dynamic payment plans that adapt to user's financial situation and cash flow patterns.
- **Financial Goal Planning**: AI-assisted goal setting and progress tracking for major life events and financial milestones.
- **Real-time Notifications**: Intelligent alerts for payment deadlines, goal achievements, and financial opportunities.
- **Comprehensive Analytics**: Visual dashboards with spending analysis, debt progression tracking, and financial health metrics.
- **Gamification Elements**: Achievement systems, progress celebrations, and motivational nudges to maintain user engagement.
- **Secure Authentication**: JWT-based user authentication with role-based access control and secure session management.
- **API-First Architecture**: RESTful APIs designed for scalability and integration with frontend applications and third-party services.

## 🚀 Unique Value Proposition (USP)

1. 🤖 **AI-First Approach**: Advanced machine learning algorithms for personalized financial guidance
2. 🎮 **Gamified Experience**: Engaging debt repayment journey with achievements and celebrations
3. 🔄 **Real-time Intelligence**: Dynamic adaptation to user's changing financial situation
4. 🧠 **Behavioral Coaching**: Psychology-based nudges for sustainable financial habits
5. 📊 **Comprehensive Analytics**: Deep insights into spending patterns and financial health

## 📦 Monetization

- **Premium Tier**: Auto AI payoff scheduling, PDF export reports, advisor chat.
- **Referrals**: Partnerships with loan consolidators and mutual fund platforms.
- **Financial Literacy**: In-app courses.
- **Partnered Offers**: Zero processing fees for early payers.

## ⚙️ Technology Stack

| Component            | Technology                                    |
|----------------------|-----------------------------------------------|
| **Backend Framework**| FastAPI (Python) with async/await support    |
| **AI Engine**        | LangGraph, OpenAI, Scikit-learn, XGBoost     |
| **Database**         | Supabase PostgreSQL with vector extensions   |
| **Authentication**   | JWT tokens with OAuth2 integration            |
| **API Documentation**| Auto-generated OpenAPI/Swagger docs          |
| **Deployment**       | Docker containerization, Render hosting      |

### AI Components
- **DebtAnalyzerAgent**: Analyzes debt patterns and provides insights.
- **DebtOptimizerAgent**: Generates optimized repayment plans (Snowball/Avalanche).
- **Orchestration**: Manages AI agent workflows using LangGraph.

## 📂 Project Structure

```
server/
├── app/
│   ├── main.py                        # FastAPI application entry point
│   ├── config.py                      # Configuration settings
│   ├── database.py                    # Supabase database client
│   ├── dependencies.py                # FastAPI dependencies
│   ├── middleware/                    # Authentication and CORS middleware
│   ├── routes/                        # API endpoint definitions
│   │   ├── auth.py                    # User authentication endpoints
│   │   ├── debts.py                   # Debt management endpoints
│   │   ├── payments.py                # Payment processing endpoints
│   │   ├── insights.py                # AI insights and analytics
│   │   └── onboarding.py              # User onboarding flow
│   ├── models/                        # Database models and schemas
│   │   ├── user.py                    # User model and schemas
│   │   ├── debt.py                    # Debt model and schemas
│   │   ├── payment.py                 # Payment model and schemas
│   │   └── ai_insights.py             # AI insights model
│   ├── agents/                        # AI agent implementations
│   │   ├── __init__.py
│   │   ├── budget_tracking_agent/     # Budget analysis agents
│   │   ├── debt_optimizer_agent/      # Debt optimization agents
│   │   └── wealth_management_agent/   # Wealth building agents
│   ├── repositories/                  # Data access layer
│   │   ├── user_repository.py
│   │   ├── debt_repository.py
│   │   ├── payment_repository.py
│   │   └── analytics_repository.py
│   ├── services/                      # Business logic services
│   │   ├── auth_service.py
│   │   ├── debt_service.py
│   │   ├── payment_service.py
│   │   └── ai_service.py
│   └── utils/                         # Utility functions and helpers
├── alembic/                           # Database migration management
├── test/                              # Test suite and fixtures
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project configuration
└── run_migrations.py                  # Database migration runner
```

## 🔐 Security & Privacy

| Area                  | Implementation                              |
|-----------------------|---------------------------------------------|
| **Authentication**    | JWT-based auth with secure session management|
| **Data Encryption**   | AES-256 encryption for sensitive data        |
| **API Security**      | Rate limiting, CORS protection             |
| **Database Security**| Row-Level Security (RLS) with Supabase      |
| **HTTPS Only**        | TLS encryption for all data in transit     |
| **Privacy First**     | User consent management and data minimization|

## 📈 Key Metrics & Analytics

- **Debt-to-Income Ratio (DTI)**: Financial health indicator
- **Payment Consistency**: Track on-time payment patterns
- **Interest Savings**: Monitor progress toward debt freedom
- **Goal Achievement Rate**: Success rate for financial milestones
- **Engagement Metrics**: User activity and feature utilization
- **Risk Assessment**: Early warning indicators for financial stress

## 🛠️ Getting Started

### Prerequisites
- **Python 3.11+** for the backend server
- **Git** for version control
- **Virtual environment** tool (venv, virtualenv, or conda)

### Backend Setup

1. **Navigate to the server directory**
   ```bash
   cd server
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**
   ```bash
   python run_migrations.py
   ```

6. **Start the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

### API Documentation
Once the server is running, visit:
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)

### Testing
Run the test suite:
```bash
pytest
```

## 🤝 Contributing

We welcome contributions to the Debtease backend! Here's how to get involved:

1. **Fork** the repository and create a feature branch
2. **Write tests** for new functionality
3. **Follow PEP 8** style guidelines for Python code
4. **Update documentation** for API changes
5. **Submit a pull request** with a clear description

### Development Guidelines
- Use type hints for all function signatures
- Write comprehensive docstrings
- Implement proper error handling
- Add tests for new endpoints and features
- Ensure all tests pass before submitting PRs

## 📄 License

This project is licensed under the MIT License.

## 📚 Additional Resources

- **[Main Project README](../README.md)** - Complete project overview
- **[Frontend Documentation](../client/README.md)** - Client-side development guide
- **[API Documentation](./docs/)** - Detailed API reference (when available)