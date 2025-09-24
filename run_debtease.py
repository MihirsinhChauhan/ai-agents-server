#!/usr/bin/env python3
"""
Fixed DebtEase server startup script
This version ensures proper initialization and avoids startup issues
"""

import os
import sys
import uvicorn
import subprocess

def cleanup_processes():
    """Clean up any existing uvicorn processes"""
    try:
        subprocess.run(["pkill", "-f", "uvicorn"], check=False, capture_output=True)
        print("🧹 Cleaned up existing processes")
    except:
        pass

def main():
    # Change to server directory
    server_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(server_dir)
    
    # Add server directory to Python path
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    
    print("🚀 Starting DebtEase API Server...")
    print("📂 Working directory:", os.getcwd())
    print("🐍 Python path includes server directory")
    print("-" * 50)
    
    # Import and start the app
    try:
        from app.main import app
        print("✅ Application imported successfully")
        
        print("🌐 Server starting at: http://127.0.0.1:8000")
        print("📚 API Documentation: http://127.0.0.1:8000/docs")
        print("❤️  Health Check: http://127.0.0.1:8000/health")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 50)
        
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=True,
            reload=False  # Disable reload to avoid issues
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Falling back to minimal server...")
        
        # Fallback to minimal server
        from simple_server import app as simple_app
        uvicorn.run(
            simple_app,
            host="127.0.0.1", 
            port=8000,
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_processes()
    main()







