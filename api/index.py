"""
Vercel Serverless Function entry point.
Wraps the FastAPI app from backend/ for Vercel's Python runtime.
"""
import sys
import os

# Add backend directory to Python path so imports resolve correctly
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_dir))

from app.main import app

# Vercel expects a variable named `app` or `handler` — FastAPI's ASGI app works directly
handler = app
