"""Vercel serverless entry point for the FastAPI backend.

vercel.json rewrites /api/* and /health to this function; FastAPI still sees
the original request path, so its routes are unchanged.
"""
import sys
from pathlib import Path

# Make the project root (main.py, database.py, …) importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: E402,F401
