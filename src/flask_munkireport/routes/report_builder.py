"""Report builder: no-code cross-module exports.

Serves the builder page (same-origin, no API key in browser JS) and three
read-only endpoints. Every table joins reportdata on serial_number; columns
and filters are validated against the whitelist in report_schema.py, filter
values are always bound parameters.
"""

import csv
import io
import re
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request, send_file

from ..database import MunkiReportDB
from ..report_schema import COLMAP, schema_json


def get_db(app):
    """Per-request read-only DB handle (same pattern as routes/tools.py)."""
    if "db" not in g:
        g.db = MunkiReportDB(
            app.config["DATABASE_PATH"],
            timeout=app.config["SQLITE_TIMEOUT"],
            check_same_thread=app.config["SQLITE_CHECK_SAME_THREAD"],
        )
    return g.db

report_builder_bp = Blueprint(
    "report_builder", __name__,
    static_folder="../static_report", static_url_path="/static",
)

PREVIEW_CAP = 25
OPS = {"eq": "=", "ne": "!=", "ct": "LIKE", "gt": ">", "lt": "<"}


# ── formatting ────────────────────────────────────────────────────────────

def _fmt(value, fmt):
    if value is None or value == "":
        return ""
    try:
        if fmt == "epoch":
            return datetime.fromtimestamp(int(value), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        if fmt == "secdays":
            return int(value) // 86400
        if fmt == "osver":
            v = int(value)
            return f"{v // 10000}.{(v // 100) % 100}.{v % 100}".removesuffix(".0")
        if fmt == "bool":
            return {0: "No", 1: "Yes", "0": "No", "1": "Yes"}.get(value, value)
        if fmt == "onoff":
            return {0: "Off", 1: "On", "0": "Off", "1": "On"}.get(value, value)
        if fmt == "firewall":
            return {0: "Off", 1: "On", 2: "On (Block All)",
                    "0": "Off", "1": "On", "2": "On (Block All)"}.get(value, value)
        if fmt == "actlock":
            return {"activation_lock_enabled": "Enabled",
                    "activation_lock_disabled": "Disabled",
                    "not_supported": "Not Supported"}.get(value, value)
    except (ValueError, TypeError, OSError):
        return value
    return value


def _filter_value(raw, fmt, op):
    """Make human filter values comparable to raw DB values."""
    if fmt == "epoch" and op in ("gt", "lt"):
        try:
            return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass
    if fmt in ("bool", "onoff", "firewall"):
        m = {"yes": 1, "no": 0, "true": 1, "false": 0, "on": 1, "off": 0, "1": 1, "0": 0}
        return m.get(str(raw).strip().lower(), raw)
    return raw


# ── query building ────────────────────────────────────────────────────────

def _parse_request():
    """Validate cols= and f= against the whitelist. Returns (cols, filters) or aborts."""
    cols = [c for c in request.args.get("cols", "").split(",") if c]
    bad = [c for c in cols if c not in COLMAP]
    if bad:
        return None, None, (jsonify({"success": False, "error": f"unknown columns: {bad}"}), 400)

    filters = []
    for f in request.args.getlist("f"):
        parts = f.split("~", 2)
        if len(parts) != 3:
            continue
        field, op, val = parts
        if field not in COLMAP or op not in OPS:
            return None, None, (jsonify({"success": False, "error": f"bad filter: {f}"}), 400)
        filters.append((field, op, val))
    return cols, filters, None


def _build_query(cols, filters, count_only=False):
    tables = {COLMAP[c][0] for c in cols} | {COLMAP[f][0] for f, _, _ in filters}
    tables.discard("reportdata")

    if count_only:
        select = "SELECT COUNT(*) AS n"
    else:
        parts = []
        for c in cols:
            table, col, _, _ = COLMAP[c]
            parts.append(f'"{table}"."{col}" AS "{c}"')
        select = "SELECT " + ", ".join(parts)

    sql = [select, "FROM reportdata"]
    for t in sorted(tables):
        sql.append(f'LEFT JOIN "{t}" ON "{t}".serial_number = reportdata.serial_number')

    where, params = ["COALESCE(reportdata.archive_status, 0) = 0"], []
    for field, op, val in filters:
        table, col, _, fmt = COLMAP[field]
        ref = f'"{table}"."{col}"'
        val = _filter_value(val, fmt, op)
        if op == "ct":
            where.append(f"{ref} LIKE ? ESCAPE '\\'")
            params.append("%" + re.sub(r"([%_\\])", r"\\\1", str(val)) + "%")
        elif op in ("gt", "lt"):
            where.append(f"CAST({ref} AS REAL) {OPS[op]} ?")
            params.append(val)
        else:
            where.append(f"{ref} {OPS[op]} ? COLLATE NOCASE")
            params.append(val)
    sql.append("WHERE " + " AND ".join(where))
    if not count_only:
        sql.append("ORDER BY reportdata.serial_number")
    return "\n".join(sql), tuple(params)


def _run(cols, filters, limit=None):
    db = get_db(current_app)
    sql, params = _build_query(cols, filters)
    if limit:
        sql += f"\nLIMIT {int(limit)}"
    rows = db.execute_query(sql, params or None)
    formatted = [{c: _fmt(r[c], COLMAP[c][3]) for c in cols} for r in rows]
    return formatted


# ── endpoints ─────────────────────────────────────────────────────────────

@report_builder_bp.route("/")
def page():
    return report_builder_bp.send_static_file("index.html")


@report_builder_bp.route("/api/schema")
def api_schema():
    return jsonify({"success": True, "modules": schema_json()})


@report_builder_bp.route("/api/query")
def api_query():
    cols, filters, err = _parse_request()
    if err:
        return err
    if not cols:
        return jsonify({"success": False, "error": "no columns requested"}), 400
    db = get_db(current_app)
    count_sql, count_params = _build_query(cols, filters, count_only=True)
    total_sql, _ = _build_query(cols, [], count_only=True)
    matched = db.execute_query(count_sql, count_params or None)[0]["n"]
    total = db.execute_query(total_sql)[0]["n"]
    rows = _run(cols, filters, limit=PREVIEW_CAP)
    return jsonify({"success": True, "rows": rows, "matched": matched,
                    "total": total, "preview_cap": PREVIEW_CAP})


@report_builder_bp.route("/api/export")
def api_export():
    cols, filters, err = _parse_request()
    if err:
        return err
    if not cols:
        return jsonify({"success": False, "error": "no columns requested"}), 400
    fmt = request.args.get("format", "csv")
    name = re.sub(r"[^\w-]+", "_", request.args.get("name", "") or "munkireport-export").strip("_")
    labels = [COLMAP[c][2] for c in cols]
    rows = _run(cols, filters)

    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Export"
        ws.append(labels)
        for cell in ws[1]:
            cell.font = cell.font.copy(bold=True)
        for r in rows:
            ws.append([r[c] for c in cols])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"{name}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(labels)
    for r in rows:
        w.writerow([r[c] for c in cols])
    return send_file(io.BytesIO(out.getvalue().encode("utf-8-sig")), as_attachment=True,
                     download_name=f"{name}.csv", mimetype="text/csv")
