"""Business units endpoint.

Lists MunkiReport business units — the authoritative client list that drives
the enrolment page's dropdown. Self-maintaining: as clients are onboarded in
MunkiReport, they appear here automatically.

Business units are stored EAV-style in the `business_unit` table
(unitid, property, value); the display name is the row with property='name'.
"""

from flask import jsonify, current_app, g, Blueprint

from ..auth import require_api_key
from ..database import MunkiReportDB

business_units_bp = Blueprint('business_units', __name__, url_prefix='/business-units')


def get_db():
    """Get a read-only DB instance for this request."""
    if 'db' not in g:
        g.db = MunkiReportDB(
            current_app.config['DATABASE_PATH'],
            timeout=current_app.config['SQLITE_TIMEOUT'],
            check_same_thread=current_app.config['SQLITE_CHECK_SAME_THREAD'],
        )
    return g.db


@business_units_bp.route('', methods=['GET'])
@business_units_bp.route('/', methods=['GET'])
@require_api_key
def list_business_units():
    """Return business units (unitid + name), ordered case-insensitively by name."""
    db = get_db()
    rows = db.execute_query(
        "SELECT unitid, value AS name FROM business_unit "
        "WHERE property = 'name' ORDER BY value COLLATE NOCASE"
    )
    return jsonify({
        "success": True,
        "count": len(rows),
        "business_units": rows,
    })
