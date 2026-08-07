"""
Vercel Serverless Function entry point.
Exports the FastAPI app from backend/ for Vercel's native Python ASGI support.
"""
import sys
import os

# Add backend directory to Python path so all app.* imports resolve correctly
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_dir))

# Vercel's Python runtime natively supports ASGI — just export the FastAPI `app`
from app.main import app
