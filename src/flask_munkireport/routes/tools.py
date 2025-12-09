"""Tool endpoints - main query API."""

from flask import jsonify, request, current_app, g
from . import api
from ..auth import require_api_key
from ..database import MunkiReportDB
from ..utils.machines import query_machines, get_machine_details, get_mdm_enrollment_summary
from ..utils.events import get_events, get_error_summary, get_recent_critical_events
from ..utils.queries import get_database_stats, get_table_summary


def get_db():
    """Get database instance for request."""
    if 'db' not in g:
        g.db = MunkiReportDB(
            current_app.config['DATABASE_PATH'],
            timeout=current_app.config['SQLITE_TIMEOUT'],
            check_same_thread=current_app.config['SQLITE_CHECK_SAME_THREAD']
        )
    return g.db


@api.route('/tools/query_machines', methods=['POST'])
@require_api_key
def route_query_machines():
    """Query machines with filters."""
    try:
        data = request.get_json() or {}
        db = get_db()
        
        result = query_machines(
            db,
            filters=data.get('filters'),
            include=data.get('include'),
            order_by=data.get('order_by'),
            limit=data.get('limit')
        )
        
        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_machine_details/<serial_number>', methods=['GET'])
@require_api_key
def route_get_machine_details(serial_number):
    """Get details for a specific machine."""
    try:
        db = get_db()
        result = get_machine_details(db, serial_number)
        
        if result is None:
            return jsonify({
                "success": False,
                "error": f"Machine not found: {serial_number}"
            }), 404
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_mdm_enrollment_summary', methods=['GET'])
@require_api_key
def route_get_mdm_enrollment_summary():
    """Get MDM enrollment summary."""
    try:
        db = get_db()
        result = get_mdm_enrollment_summary(db)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_events', methods=['POST'])
@require_api_key
def route_get_events():
    """Query events."""
    try:
        data = request.get_json() or {}
        db = get_db()
        
        result = get_events(
            db,
            filters=data.get('filters'),
            include_machine=data.get('include_machine', False),
            order_by=data.get('order_by'),
            limit=data.get('limit')
        )
        
        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_error_summary', methods=['GET'])
@require_api_key
def route_get_error_summary():
    """Get error summary."""
    try:
        db = get_db()
        result = get_error_summary(db)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_recent_critical_events', methods=['GET'])
@require_api_key
def route_get_recent_critical_events():
    """Get recent critical events."""
    try:
        hours = request.args.get('hours', default=24, type=int)
        limit = request.args.get('limit', default=50, type=int)
        
        db = get_db()
        result = get_recent_critical_events(db, hours=hours, limit=limit)
        
        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_database_stats', methods=['GET'])
@require_api_key
def route_get_database_stats():
    """Get database statistics."""
    try:
        db = get_db()
        result = get_database_stats(db)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api.route('/tools/get_table_summary', methods=['POST'])
@require_api_key
def route_get_table_summary():
    """Get table summary with optional grouping."""
    try:
        data = request.get_json() or {}
        db = get_db()
        
        if 'table_name' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: table_name"
            }), 400
        
        result = get_table_summary(
            db,
            table_name=data['table_name'],
            group_by=data.get('group_by'),
            filters=data.get('filters')
        )
        
        return jsonify({
            "success": True,
            "data": result
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
