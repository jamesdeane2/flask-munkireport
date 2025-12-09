"""Event-related query functions - vendored from mcp-munkireport."""

from typing import Any, Dict, List, Optional
from ..database import MunkiReportDB
from ..utils import (
    build_where_clause,
    build_order_clause,
    build_limit_clause,
    parse_timestamp,
    parse_json_field,
)


def get_events(
    db: MunkiReportDB,
    filters: Optional[Dict[str, Any]] = None,
    include_machine: bool = False,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query events with optional machine information."""
    filters = filters or {}
    
    select_fields = ["e.*"]
    from_clause = "event e"
    joins = []
    
    if include_machine:
        joins.append("LEFT JOIN machine m ON e.serial_number = m.serial_number")
        select_fields.extend([
            "m.hostname",
            "m.computer_name",
            "m.machine_model",
        ])
    
    # Build WHERE clause with table prefixes
    prefixed_filters = {}
    for key, value in filters.items():
        if key.startswith("timestamp"):
            prefixed_filters[f"e.{key}"] = value
        elif key in ["type", "module", "serial_number"]:
            prefixed_filters[f"e.{key}"] = value
        else:
            prefixed_filters[key] = value
    
    where_clause, params = build_where_clause(prefixed_filters)
    
    query_parts = [
        f"SELECT {', '.join(select_fields)}",
        f"FROM {from_clause}",
    ]
    
    if joins:
        query_parts.extend(joins)
    
    if where_clause:
        query_parts.append(f"WHERE {where_clause}")
    
    if order_by:
        if "." not in order_by and not order_by.startswith("e."):
            order_by = f"e.{order_by}"
        query_parts.append(build_order_clause(order_by))
    else:
        query_parts.append("ORDER BY e.timestamp DESC")
    
    if limit:
        query_parts.append(build_limit_clause(limit))
    
    query = " ".join(query_parts)
    results = db.execute_query(query, tuple(params) if params else None)
    
    # Post-process
    for result in results:
        if "data" in result and result["data"]:
            result["data_parsed"] = parse_json_field(result["data"])
        if "timestamp" in result and result["timestamp"]:
            result["timestamp_iso"] = parse_timestamp(result["timestamp"])
    
    return results


def get_error_summary(db: MunkiReportDB) -> Dict[str, Any]:
    """Get summary of errors and warnings by machine."""
    query = """
        SELECT 
            m.hostname,
            m.serial_number,
            COUNT(CASE WHEN e.type = 'danger' THEN 1 END) as danger_count,
            COUNT(CASE WHEN e.type = 'error' THEN 1 END) as error_count,
            COUNT(CASE WHEN e.type = 'warning' THEN 1 END) as warning_count,
            MAX(e.timestamp) as last_event_timestamp
        FROM machine m
        LEFT JOIN event e ON m.serial_number = e.serial_number
        WHERE e.type IN ('danger', 'error', 'warning')
        GROUP BY m.serial_number
        HAVING (danger_count > 0 OR error_count > 0 OR warning_count > 0)
        ORDER BY danger_count DESC, error_count DESC, warning_count DESC
    """
    
    results = db.execute_query(query)
    
    for result in results:
        if result.get("last_event_timestamp"):
            result["last_event_iso"] = parse_timestamp(result["last_event_timestamp"])
    
    summary = {
        "machines_with_issues": len(results),
        "total_dangers": sum(r["danger_count"] for r in results),
        "total_errors": sum(r["error_count"] for r in results),
        "total_warnings": sum(r["warning_count"] for r in results),
        "machines": results,
    }
    
    return summary


def get_recent_critical_events(
    db: MunkiReportDB, hours: int = 24, limit: int = 50
) -> List[Dict[str, Any]]:
    """Get recent critical events (danger/error)."""
    import time
    
    threshold = int(time.time()) - (hours * 3600)
    
    return get_events(
        db,
        filters={
            "type": ["danger", "error"],
            "timestamp_after": threshold,
        },
        include_machine=True,
        order_by="timestamp DESC",
        limit=limit,
    )
