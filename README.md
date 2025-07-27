# DebtEase

DebtEase is a smart, mobile-first financial wellness app tailored for the Indian market, helping users **manage debts** and **grow wealth** through AI-driven guidance, gamification, and secure integrations. It aggregates financial data from banks, credit institutions, and investment accounts, providing personalized repayment and wealth-building strategies. The current focus is on building the AI-agent server to power intelligent financial recommendations.

## 🌟 Features

- **User Onboarding & KYC**: RBI-compliant eKYC with PAN/Aadhaar verification via DigiLocker, XML, or QR, with consent capture for Account Aggregator (AA).
- **Debt Management**:
  - Aggregates loan and credit data (banks, NBFCs, credit cards, BNPL, gold loans) via AA.
  - EMI dashboard with real-time status (Paid, Upcoming, Overdue).
  - Manual debt entry for personal or family loans.
  - AI-powered repayment plans (Snowball/Avalanche) with interest savings forecasts and DPD/bouncing risk alerts.
  - Gamified experience with debt-free streaks, milestone celebrations, leaderboards, and daily nudges.
- **Wealth Management**:
  - Aggregates assets (mutual funds, stocks, FDs, gold, insurance, EPF) via BSEStar, MF Central, or broker APIs (Zerodha, Groww).
  - Net worth calculation with graphical trends and high debt-to-net-worth ratio alerts.
  - Goal planning for major life events (home, car, wedding, education) with auto-suggestions.
  - Smart alerts for SIPs, insurance premiums, and portfolio rebalancing.
- **AI-Driven Insights**: Analyzes spending vs. debt, identifies high-interest burdens, suggests debt consolidation, and provides budgeting recommendations.
- **Security & Compliance**: AES-256 encryption, TLS for data in transit, India-based cloud hosting (Mumbai), and RBI/UIDAI-compliant KYC and consent withdrawal.
- **Advanced Metrics**: Tracks DTI, credit utilization, EMI-to-income ratio, DPD, CEI, net worth growth, and portfolio diversification score.
- **Admin Dashboard**: Tracks user performance, behavior segmentation, cohort stats, and onboarding funnel metrics.

## 🚀 Unique Value Proposition (USP)

1. 🇮🇳 Tailored for the Indian financial ecosystem.
2. 🎮 Gamified approach to debt repayment and wealth management.
3. 🔄 Real-time debt and asset sync via Account Aggregator.
4. 🧠 Intelligent nudges for stress-free financial planning.
5. 🏛️ RBI-compliant from day one.

## 📦 Monetization

- **Premium Tier**: Auto AI payoff scheduling, PDF export reports, advisor chat.
- **Referrals**: Partnerships with loan consolidators and mutual fund platforms.
- **Financial Literacy**: In-app courses.
- **Partnered Offers**: Zero processing fees for early payers.

## ⚙️ Technology Stack

| Component            | Technology                                    |
|----------------------|-----------------------------------------------|
| **Mobile App**       | Flutter or React Native                       |
| **AI-Agent Server**  | FastAPI (Python)                              |
| **AI Engine**        | Python (Sklearn, XGBoost, LangGraph, OpenAI) |
| **Database**         | Supabase PostgreSQL (user, KYC, payments), MongoDB (statements, assets), pgvector (AI embeddings) |
| **AA Integration**   | Sahamati FIU APIs                            |
| **KYC**              | UIDAI offline Aadhaar, NSDL PAN APIs          |

### AI Components
- **DebtAnalyzerAgent**: Analyzes debt patterns and provides insights.
- **DebtOptimizerAgent**: Generates optimized repayment plans (Snowball/Avalanche).
- **Orchestration**: Manages AI agent workflows using LangGraph.

## 📂 Project Structure

```
DebtEase/
├── ai-agent-server/
│   ├── main.py                        # FastAPI application entry point
│   ├── config.py                      # Configuration settings
│   ├── database.py                    # Supabase database client
│   ├── dependencies.py                # FastAPI dependencies
│   ├── routes/                        # API endpoints
│   │   ├── auth.py                    # User authentication and KYC
│   │   ├── debts.py                   # Debt management endpoints
│   │   ├── repayment_plans.py         # AI-driven repayment plans
│   │   ├── notifications.py           # Payment and goal reminders
│   │   ├── wealth.py                  # Wealth management endpoints
│   ├── models/                        # Data models
│   │   ├── user.py
│   │   ├── debt.py
│   │   ├── payment.py
│   │   ├── repayment_plan.py
│   │   ├── asset.py
│   └── ai_module/                     # AI agent system
│       ├── agent_base.py              # Base agent class
│       ├── debt_analyzer_agent.py     # Financial analysis agent
│       ├── debt_optimizer_agent.py    # Optimization agent
│       ├── orchestrator.py            # LangGraph workflow
│   ├── tests/                         # Unit and integration tests
│   │   ├── test_routes/
│   │   ├── test_ai_module/
│   │   ├── test_services/
│   ├── requirements.txt               # Python dependencies
│   └── Dockerfile                     # AI-agent server container config
├── frontend/                          # Mobile app (Flutter/React Native)
└── docs/                              # Documentation
    ├── architecture.md
    ├── api.md
    └── database.md
```

## 🔐 Security & Compliance

| Area                  | Implementation                              |
|-----------------------|---------------------------------------------|
| **KYC & Consent**     | RBI/UIDAI-compliant eKYC and consent        |
| **Account Aggregator**| Sahamati FIU integration                   |
| **Data Hosting**      | India-based cloud (Mumbai region)          |
| **Encryption**        | AES-256 (at rest), TLS (in-transit)        |
| **Consent Withdrawal**| Users can revoke access anytime            |
| **Database Security** | Row-Level Security (RLS), user auth        |

## 📈 Metrics Tracked

- Debt-to-Income Ratio (DTI)
- Credit Utilization Rate
- EMI-to-Income %
- Days Past Due (DPD)
- Collection Effectiveness Index (CEI)
- Net Worth Growth Rate
- Portfolio Diversification Score

## 🛠️ Getting Started

### Prerequisites
- Python 3.11
- Node.js 14+
- Flutter or React Native (for frontend)
- Docker and Docker Compose (optional)

### Installation
1. Clone the repository:
   ```
   git clone git@github.com:MihirsinhChauhan/DebtEase.git
   cd DebtEase
   ```

2. Set up the AI-agent server:
   ```
   cd ai-agent-server
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up the frontend:
   ```
   cd ../frontend
   npm install  # or flutter pub get
   ```

### Running the Application
1. Start the AI-agent server:
   ```
   cd ai-agent-server
   uvicorn main:app --reload
   ```

2. Start the frontend:
   ```
   cd frontend
   npm start  # or flutter run
   ```

## 📚 API Documentation
Available at `/docs` when the AI-agent server is running.

## 👥 Contributors
- [Your Name] - AI-Agent Server, AI, and Mobile App