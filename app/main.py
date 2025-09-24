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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Vite frontend
        "http://127.0.0.1:8080",  # Alternative localhost
        "http://localhost:8081",  # Current Vite frontend port
        "http://127.0.0.1:8081",  # Alternative localhost
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
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
        print("⚠️  Continuing without database for debugging...")
        # Don't raise exception for now

    # AI processing worker temporarily disabled due to database compatibility issues
    print("⚠️  AI processing worker disabled for testing")

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
    # AI worker disabled - no cleanup needed
    print("⚠️  AI processing worker was disabled - no cleanup needed")

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