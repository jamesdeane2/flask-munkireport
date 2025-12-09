"""API authentication middleware."""

from functools import wraps
from flask import request, jsonify, current_app


def require_api_key(f):
    """Decorator to require valid API key in X-API-Key header."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                "success": False,
                "error": "Missing API key",
                "message": "Include X-API-Key header with your request"
            }), 401
        
        if api_key != current_app.config['API_KEY']:
            return jsonify({
                "success": False,
                "error": "Invalid API key",
                "message": "The provided API key is not valid"
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function
