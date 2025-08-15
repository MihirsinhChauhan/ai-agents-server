import os
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Debt Repayment Optimizer"
    API_V1_STR: str = "/api"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # Frontend local development
        "http://localhost:8000",  # Backend local development
        "https://debt-optimizer.example.com",  # Production URL
    ]
    
    # Authentication
    SECRET_KEY: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # e.g., "openai", "groq", "ollama"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")   # Default model
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    LLM_BASE_URL: Optional[str] = os.getenv("LLM_BASE_URL", None)  # For custom endpoints (e.g., Ollama)
    
    # # Blockchain Integration
    # BLOCKCHAIN_NODE_URL: str = os.getenv("BLOCKCHAIN_NODE_URL", "http://localhost:8545")
    # BLOCKCHAIN_ENABLED: bool = os.getenv("BLOCKCHAIN_ENABLED", "true").lower() == "true"
    # CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    
    # External API Keys
    PLAID_CLIENT_ID: str = os.getenv("PLAID_CLIENT_ID", "")
    PLAID_SECRET: str = os.getenv("PLAID_SECRET", "")
    PLAID_ENVIRONMENT: str = os.getenv("PLAID_ENVIRONMENT", "sandbox")
    
    # Notification Services
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "noreply@debt-optimizer.example.com")
    
    # AI Module
    AI_STRATEGIES: List[str] = ["avalanche", "snowball", "custom", "ai_optimized"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"


# Create settings instance
settings = Settings()