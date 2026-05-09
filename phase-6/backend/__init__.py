"""
Phase 6 - Minimal UI and User Experience (Backend)

Purpose: Deliver a clean, low-friction interface for facts-only Q&A.
"""

from .app import create_app
from .api import api_bp

__all__ = ['create_app', 'api_bp']
__version__ = '6.0.0'
