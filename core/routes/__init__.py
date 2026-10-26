"""
Routes package for Fake News Detection Application.
Contains all route blueprints.
"""

from .api import api_bp
from .main import main_bp

__all__ = ['api_bp', 'main_bp']
