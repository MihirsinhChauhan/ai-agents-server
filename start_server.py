#!/usr/bin/env python3
"""
Simple server starter script for DebtEase API
This script ensures clean startup and proper configuration
"""

import os
import sys
import subprocess
import signal
import time

def kill_existing_servers():
    """Kill any existing uvicorn processes"""
    try:
        subprocess.run(["pkill", "-f", "uvicorn"], check=False)
        print("🧹 Cleaned up existing server processes")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️  Warning during cleanup: {e}")

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting DebtEase API Server...")
    print("📍 Server will be available at: http://127.0.0.1:8000")
    print("📚 API Documentation: http://127.0.0.1:8000/docs")
    print("❤️  Health Check: http://127.0.0.1:8000/health")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Change to server directory
    server_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(server_dir)
    
    # Start uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload",
        "--log-level", "info"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    kill_existing_servers()
    start_server()







