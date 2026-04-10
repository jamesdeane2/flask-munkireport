"""Compliance endpoints — CE+ and future frameworks."""

from flask import jsonify, request, current_app, g, Blueprint
from ..auth import require_api_key
from ..database import MunkiReportDB
from ..utils.ce_plus import generate_report


compliance_bp = Blueprint('compliance', __name__, url_prefix='/compliance')


def get_db():
    """Get database instance for request."""
    if 'db' not in g:
        g.db = MunkiReportDB(
            current_app.config['DATABASE_PATH'],
            timeout=current_app.config['SQLITE_TIMEOUT'],
            check_same_thread=current_app.config['SQLITE_CHECK_SAME_THREAD']
        )
    return g.db


@compliance_bp.route('/ce-plus', methods=['POST'])
@require_api_key
def route_ce_plus():
    """Generate a Cyber Essentials Plus compliance report.

    Request body:
        {
            "manifest": "Pablo" (required),
            "include_passing": false (optional)
        }

    Returns full compliance assessment scoped to the given manifest.
    """
    try:
        data = request.get_json()

        if not data or 'manifest' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: manifest",
            }), 400

        manifest = data['manifest']
        include_passing = data.get('include_passing', False)

        db = get_db()
        report = generate_report(
            db,
            manifest=manifest,
            include_passing=include_passing,
        )

        return jsonify(report)

    except Exception as e:
        current_app.logger.error(f"CE+ compliance report error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500
