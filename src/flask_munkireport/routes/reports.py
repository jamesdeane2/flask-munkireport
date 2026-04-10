"""Generic report endpoint — join any module table with machine + reportdata (last_seen)."""

import csv
import io
from flask import jsonify, request, current_app, g, Blueprint, Response
from ..auth import require_api_key
from ..database import MunkiReportDB
from ..utils import build_where_clause, build_order_clause, build_limit_clause, parse_timestamp

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

# Tables that should never be queried directly (system/internal)
BLOCKED_TABLES = {'sqlite_master', 'sqlite_sequence'}


def get_db():
    """Get database instance for request."""
    if 'db' not in g:
        g.db = MunkiReportDB(
            current_app.config['DATABASE_PATH'],
            timeout=current_app.config['SQLITE_TIMEOUT'],
            check_same_thread=current_app.config['SQLITE_CHECK_SAME_THREAD']
        )
    return g.db


@reports_bp.route('/tables', methods=['GET'])
@require_api_key
def list_tables():
    """List all available tables and their columns."""
    db = get_db()
    tables = db.list_tables()
    result = {}
    for table in tables:
        if table in BLOCKED_TABLES:
            continue
        columns = db.get_table_info(table)
        result[table] = [col['name'] for col in columns]
    return jsonify({"success": True, "tables": result})


@reports_bp.route('/export/<table_name>', methods=['GET', 'POST'])
@require_api_key
def export_table(table_name):
    """Export any module table joined with machine info and last_seen.

    GET params or POST body:
        - columns: comma-separated list of columns from the module table (default: all)
        - filter_<column>: filter by column value (GET) or "filters" dict (POST)
        - manifest: filter by manifest/business unit name
        - sort: column to sort by (prefix with - for DESC, default: -last_seen)
        - limit: max rows (default: 1000)
        - format: "json" (default) or "csv"

    Always includes: serial_number, hostname, last_seen, last_seen_iso

    Examples:
        GET  /reports/export/filevault?manifest=Pablo&sort=-last_seen&format=csv
        GET  /reports/export/filevault?filter_filevault_status=FileVault is On
        POST /reports/export/filevault {"filters": {"filevault_status": "FileVault is On"}, "manifest": "Pablo"}
    """
    try:
        db = get_db()

        # Validate table exists
        valid_tables = db.list_tables()
        if table_name not in valid_tables or table_name in BLOCKED_TABLES:
            return jsonify({
                "success": False,
                "error": f"Invalid table: {table_name}",
                "available_tables": [t for t in valid_tables if t not in BLOCKED_TABLES]
            }), 400

        # Get table columns for validation
        table_columns = [col['name'] for col in db.get_table_info(table_name)]

        # Parse parameters (support both GET query params and POST JSON body)
        if request.method == 'POST':
            data = request.get_json() or {}
            filters = data.get('filters', {})
            manifest = data.get('manifest')
            sort = data.get('sort', '-last_seen')
            limit = data.get('limit', 1000)
            output_format = data.get('format', 'json')
            requested_columns = data.get('columns', [])
            if isinstance(requested_columns, str):
                requested_columns = [c.strip() for c in requested_columns.split(',')]
        else:
            filters = {}
            # Extract filter_ prefixed params
            for key, value in request.args.items():
                if key.startswith('filter_'):
                    col = key[7:]  # strip 'filter_'
                    filters[col] = value
            manifest = request.args.get('manifest')
            sort = request.args.get('sort', '-last_seen')
            limit = request.args.get('limit', 1000, type=int)
            output_format = request.args.get('format', 'json')
            columns_param = request.args.get('columns', '')
            requested_columns = [c.strip() for c in columns_param.split(',') if c.strip()] if columns_param else []

        # Determine which module table columns to include
        if requested_columns:
            # Validate requested columns exist
            invalid = [c for c in requested_columns if c not in table_columns]
            if invalid:
                return jsonify({
                    "success": False,
                    "error": f"Invalid columns for {table_name}: {invalid}",
                    "available_columns": table_columns
                }), 400
            module_cols = requested_columns
        else:
            # All columns except serial_number (we get that from machine table)
            module_cols = [c for c in table_columns if c != 'serial_number']

        # Build SELECT
        select_fields = [
            'm.serial_number',
            'm.hostname',
            'm.machine_model',
        ]
        # Add module table columns
        for col in module_cols:
            select_fields.append(f't.{col}')
        # Always add last_seen
        select_fields.append('r.timestamp as last_seen')

        # Build FROM + JOINs
        # Module tables join to machine on serial_number
        from_clause = f'machine m'
        joins = [
            f'INNER JOIN {table_name} t ON m.serial_number = t.serial_number',
            'LEFT JOIN reportdata r ON m.serial_number = r.serial_number',
        ]

        # Handle manifest filter (needs munkireport table)
        if manifest:
            joins.append('LEFT JOIN munkireport mr ON m.serial_number = mr.serial_number')

        # Build WHERE
        where_parts = []
        params = []

        # Module table filters
        if filters:
            module_filters = {f't.{k}': v for k, v in filters.items()}
            where_clause, filter_params = build_where_clause(module_filters)
            if where_clause:
                where_parts.append(where_clause)
                params.extend(filter_params)

        # Manifest filter
        if manifest:
            where_parts.append('mr.manifestname = ?')
            params.append(manifest)

        # Build ORDER BY
        if sort:
            if sort.startswith('-'):
                order_col = sort[1:]
                order_dir = 'DESC'
            else:
                order_col = sort
                order_dir = 'ASC'

            # Map common aliases
            if order_col == 'last_seen':
                order_expr = f'r.timestamp {order_dir}'
            elif order_col == 'hostname':
                order_expr = f'm.hostname {order_dir}'
            elif order_col in table_columns:
                order_expr = f't.{order_col} {order_dir}'
            else:
                order_expr = f'r.timestamp {order_dir}'

            order_clause = f'ORDER BY {order_expr}'
        else:
            order_clause = 'ORDER BY r.timestamp DESC'

        # Build query
        query_parts = [
            f"SELECT {', '.join(select_fields)}",
            f"FROM {from_clause}",
        ]
        query_parts.extend(joins)
        if where_parts:
            query_parts.append(f"WHERE {' AND '.join(where_parts)}")
        query_parts.append(order_clause)
        if limit:
            query_parts.append(f"LIMIT {int(limit)}")

        query = ' '.join(query_parts)
        results = db.execute_query(query, tuple(params) if params else None)

        # Post-process: add ISO timestamp
        for row in results:
            if row.get('last_seen'):
                row['last_seen_iso'] = parse_timestamp(row['last_seen'])

        # Output
        if output_format == 'csv':
            if not results:
                return Response('No data\n', mimetype='text/csv')

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={table_name}_report.csv'
                }
            )

        return jsonify({
            "success": True,
            "table": table_name,
            "count": len(results),
            "data": results,
        })

    except Exception as e:
        current_app.logger.error(f"Report export error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
