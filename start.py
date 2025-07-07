#!/usr/bin/env python3
"""
Quick start script for Tug-o-Chat
Runs both backend and frontend servers
"""

import subprocess
import sys
import os
import time
import webbrowser
from threading import Thread

def run_backend():
    """Run the backend server"""
    print("Starting backend server...")
    os.chdir('backend')
    subprocess.run([sys.executable, 'main.py'])

def run_frontend():
    """Run the frontend server"""
    print("Starting frontend server...")
    os.chdir('frontend')
    subprocess.run([sys.executable, 'server.py'])

def main():
    print("""
    ╔══════════════════════════════════════╗
    ║        TUG-O-CHAT GAME SERVER        ║
    ╚══════════════════════════════════════╝

    Starting servers...
    Backend: http://localhost:8000
    Frontend: http://localhost:3000

    Press Ctrl+C to stop both servers
    """)

    # Check if .env exists
    if not os.path.exists('backend/.env'):
        print("\n⚠️  WARNING: backend/.env file not found!")
        print("Please create it from .env.template and add your Twitch credentials")
        print("\nPress Enter to continue anyway or Ctrl+C to exit...")
        input()

    # Start backend in a thread
    backend_thread = Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Wait a bit for backend to start
    time.sleep(2)

    # Open browser
    print("\nOpening browser...")
    webbrowser.open('http://localhost:3000')

    # Run frontend in main thread (so Ctrl+C works properly)
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\n\nShutting down servers...")
        sys.exit(0)

if __name__ == '__main__':
    main()
