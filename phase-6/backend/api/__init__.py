"""
Phase 6 Backend API Blueprint

API endpoints for the minimal UI and user experience system.
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them
from . import routes
