"""Health check and status endpoints."""

from flask import jsonify, current_app
from . import api
from ..database import MunkiReportDB


@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - no auth required."""
    return jsonify({
        "success": True,
        "status": "healthy",
        "version": "0.1.0"
    })


@api.route('/status', methods=['GET'])
def status():
    """Detailed status endpoint - no auth required."""
    try:
        # Try to connect to database
        db = MunkiReportDB(
            current_app.config['DATABASE_PATH'],
            timeout=current_app.config['SQLITE_TIMEOUT'],
            check_same_thread=current_app.config['SQLITE_CHECK_SAME_THREAD']
        )
        tables = db.list_tables()
        db_accessible = True
    except Exception as e:
        db_accessible = False
        tables = []
    
    return jsonify({
        "success": True,
        "version": "0.1.0",
        "database": {
            "accessible": db_accessible,
            "path": current_app.config['DATABASE_PATH'],
            "tables": len(tables)
        }
    })
