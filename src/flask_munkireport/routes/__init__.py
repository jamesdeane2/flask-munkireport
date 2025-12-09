"""API routes package initialization."""

from flask import Blueprint

# Create blueprint
api = Blueprint('api', __name__)

# Import routes to register them
from . import tools, health

__all__ = ['api']
