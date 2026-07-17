"""Flask application factory."""

from flask import Flask, jsonify
import logging
from config import get_config


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Register blueprints
    from .routes import api
    app.register_blueprint(api, url_prefix='/api/v1')

    from .routes.compliance import compliance_bp
    app.register_blueprint(compliance_bp, url_prefix='/api/v1/compliance')

    from .routes.reports import reports_bp
    app.register_blueprint(reports_bp, url_prefix='/api/v1/reports')

    from .routes.business_units import business_units_bp
    app.register_blueprint(business_units_bp, url_prefix='/api/v1/business-units')

    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            "name": "Flask MunkiReport API",
            "version": "0.1.0",
            "endpoints": {
                "health": "/api/v1/health",
                "status": "/api/v1/status",
                "tools": "/api/v1/tools/*",
                "compliance": "/api/v1/compliance/ce-plus",
                "reports_tables": "/api/v1/reports/tables",
                "reports_export": "/api/v1/reports/export/<table_name>",
                "business_units": "/api/v1/business-units"
            },
            "documentation": "See README.md for API documentation"
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "error": "Not found",
            "message": "The requested endpoint does not exist"
        }), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500
    
    return app
