from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.configs.config import settings
from app.routes import auth, debts, repayment_plans, notifications
from app.database import get_supabase

# Initialize FastAPI app
app = FastAPI(
    title="Debt Repayment Optimizer API",
    description="API for managing debts and optimizing repayment strategies using AI",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(debts.router, prefix="/api/debts", tags=["Debt Management"])
app.include_router(repayment_plans.router, prefix="/api/repayment-plans", tags=["Repayment Plans"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize connections on startup
    """
    # Initialize Supabase connection
    get_supabase()
    print(f"Connected to Supabase at {settings.SUPABASE_URL}")


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint that confirms the API is running
    """
    return {
        "message": "Debt Repayment Optimizer API is running",
        "docs": "/docs",
        "version": app.version,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify API is operational
    """
    # Get Supabase client
    supabase = get_supabase()
    
    # Check database connection
    try:
        response = await supabase.rpc("health_check").execute()
        db_status = "healthy" if response else "unhealthy"
    except Exception:
        db_status = "unhealthy"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)