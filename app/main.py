from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.configs.config import settings
from app.routes import auth, debt_new, payment_new, ai
from app.routes.onboarding import router as onboarding_router
# from app.databases.database import get_supabase  # Not using Supabase
from app.databases.database import db_manager
from app.services.ai_processing_worker import start_ai_worker, stop_ai_worker

# Initialize FastAPI app
app = FastAPI(
    title="Debt Repayment Optimizer API",
    description="API for managing debts and optimizing repayment strategies using AI",
    version="0.1.0",
)

# Add CORS middleware to allow frontend access
cors_origins = [
    "http://localhost:8080",  # Vite frontend
    "http://127.0.0.1:8080",  # Alternative localhost
    "http://localhost:8081",  # Current Vite frontend port
    "http://127.0.0.1:8081",  # Alternative localhost
    "http://localhost:3000",  # Alternative frontend port
    "http://127.0.0.1:3000",  # Alternative localhost
]

# Add production origins if available
if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
    cors_origins.extend(settings.CORS_ORIGINS.split(','))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Database startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database connection pool and background services on startup"""
    try:
        await db_manager.create_pool()
        print("✅ Database connection pool initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        # In production, this should fail fast
        if settings.ENVIRONMENT == "production":
            raise e
        else:
            print("⚠️  Continuing without database in development mode...")

    # Initialize SQLAlchemy engine for AI cache service
    try:
        await db_manager.create_sqlalchemy_engine()
        print("✅ SQLAlchemy engine initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize SQLAlchemy engine: {e}")
        if settings.ENVIRONMENT == "production":
            raise e

    # Start AI processing worker (only after SQLAlchemy tables are ready)
    try:
        await start_ai_worker(max_workers=2, poll_interval=30)
        print("✅ AI processing worker started successfully")
    except Exception as e:
        print(f"⚠️  Failed to start AI processing worker: {e}")
        # In production, log the error but don't crash the entire app
        # The worker will be retried and tables should be created by now
        print("⚠️  Continuing without AI worker - it can be restarted once tables are ready")

# Include routers - Using updated routes with proper models
try:
    app.include_router(auth, prefix="/api/auth", tags=["Authentication"])
    print("✅ Auth routes loaded")
    app.include_router(debt_new, prefix="/api/debts", tags=["Debt Management"])
    print("✅ Debt routes loaded")
    app.include_router(payment_new, prefix="/api/payments", tags=["Payment Management"])
    print("✅ Payment routes loaded")
    app.include_router(ai, prefix="/api/ai", tags=["AI Insights"])
    print("✅ AI routes loaded")
    app.include_router(onboarding_router, prefix="/api/onboarding", tags=["Onboarding"])
    print("✅ Onboarding routes loaded")
except Exception as e:
    print(f"❌ Error loading routes: {e}")
    import traceback
    traceback.print_exc()

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint that confirms the API is running
    """
    return {
        "message": "DebtEase API is running",
        "docs": "/docs",
        "version": app.version,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify API is operational
    """
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    # Stop AI processing worker
    try:
        await stop_ai_worker()
        print("✅ AI processing worker stopped successfully")
    except Exception as e:
        print(f"⚠️  Error stopping AI processing worker: {e}")

    try:
        # Close database connections
        await db_manager.close_pool()
        print("✅ Database connection pool closed successfully")
    except Exception as e:
        print(f"❌ Error closing database connections: {e}")






if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting DebtEase API server...")
    print("📍 Server will be available at: http://127.0.0.1:8000")
    print("📚 API Documentation: http://127.0.0.1:8000/docs")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, log_level="info")