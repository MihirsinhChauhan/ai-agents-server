#!/usr/bin/env python3
"""
Minimal FastAPI server for debugging
"""

import uvicorn
from fastapi import FastAPI

# Create minimal app
app = FastAPI(
    title="DebtEase API - Debug Mode",
    description="Minimal server for debugging connection issues",
    version="debug-1.0.0"
)

@app.get("/")
def read_root():
    return {
        "message": "DebtEase API is running in debug mode",
        "status": "success",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "mode": "debug"}

@app.get("/test")
def test_endpoint():
    return {"test": "working", "server": "debug"}

if __name__ == "__main__":
    print("🚀 Starting Debug Server...")
    print("🌐 Access at: http://127.0.0.1:8000")
    print("📚 Docs at: http://127.0.0.1:8000/docs")
    print("❤️  Health: http://127.0.0.1:8000/health")
    print("🔧 Test: http://127.0.0.1:8000/test")
    print("-" * 40)
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000, 
        log_level="info",
        access_log=True
    )







