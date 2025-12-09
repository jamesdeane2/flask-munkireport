"""Machine-related query functions - vendored from mcp-munkireport."""

from typing import Any, Dict, List, Optional
from ..database import MunkiReportDB
from ..utils import (
    build_where_clause,
    build_order_clause,
    build_limit_clause,
    parse_timestamp,
)


def query_machines(
    db: MunkiReportDB,
    filters: Optional[Dict[str, Any]] = None,
    include: Optional[List[str]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query machines with flexible filters and optional related data."""
    # Apply default limit of 100 if no filters and no limit specified
    if limit is None and not filters:
        limit = 100
    filters = filters or {}
    include = include or []
    
    # Pre-process filters for manifest/business_unit
    manifest_filter = None
    if "manifest" in filters:
        manifest_filter = filters.pop("manifest")
    if "business_unit" in filters:
        manifest_filter = filters.pop("business_unit")
    
    # Build SELECT clause
    select_fields = ["m.*"]
    
    # Build FROM and JOIN clauses
    from_clause = "machine m"
    joins = []
    
    # Handle includes
    if "reportdata" in include or any(k.startswith("last_seen") for k in filters.keys()):
        joins.append("LEFT JOIN reportdata r ON m.serial_number = r.serial_number")
        if "reportdata" in include:
            select_fields.extend([
                "r.console_user",
                "r.long_username",
                "r.remote_ip",
                "r.uptime",
                "r.timestamp as last_seen",
            ])
    
    if "mdm_status" in include or "mdm_enrolled" in filters or "is_supervised" in filters:
        joins.append("LEFT JOIN mdm_status mdm ON m.serial_number = mdm.serial_number")
        if "mdm_status" in include:
            select_fields.extend([
                "mdm.mdm_enrolled",
                "mdm.mdm_enrolled_via_dep",
                "mdm.is_supervised",
                "mdm.enrolled_in_dep",
                "mdm.mdm_server_url",
            ])
    
    # Handle manifest filter
    if manifest_filter is not None:
        joins.append("LEFT JOIN munkireport mr ON m.serial_number = mr.serial_number")
        select_fields.append("mr.manifestname")
    
    # Build WHERE clause
    where_parts = []
    params = []
    
    if filters:
        machine_filters = {}
        reportdata_filters = {}
        mdm_filters = {}
        
        for key, value in filters.items():
            if key.startswith("last_seen"):
                new_key = key.replace("last_seen", "r.timestamp")
                reportdata_filters[new_key] = value
            elif key in ["mdm_enrolled", "is_supervised", "enrolled_in_dep", "mdm_enrolled_via_dep"]:
                mdm_filters[f"mdm.{key}"] = value
            else:
                machine_filters[f"m.{key}"] = value
        
        for filter_dict in [machine_filters, reportdata_filters, mdm_filters]:
            if filter_dict:
                where_clause, filter_params = build_where_clause(filter_dict)
                if where_clause:
                    where_parts.append(where_clause)
                    params.extend(filter_params)
    
    # Add manifest filter
    if manifest_filter is not None:
        manifest_where, manifest_params = build_where_clause({"mr.manifestname": manifest_filter})
        if manifest_where:
            where_parts.append(manifest_where)
            params.extend(manifest_params)
    
    # Construct query
    query_parts = [
        f"SELECT {', '.join(select_fields)}",
        f"FROM {from_clause}",
    ]
    
    if joins:
        query_parts.extend(joins)
    
    if where_parts:
        query_parts.append(f"WHERE {' AND '.join(where_parts)}")
    
    if order_by:
        if "last_seen" in order_by.lower():
            order_by = order_by.replace("last_seen", "r.timestamp")
        query_parts.append(build_order_clause(order_by))
    
    if limit:
        query_parts.append(build_limit_clause(limit))
    
    query = " ".join(query_parts)
    results = db.execute_query(query, tuple(params) if params else None)
    
    # Post-process
    for result in results:
        if "last_seen" in result and result["last_seen"]:
            result["last_seen_iso"] = parse_timestamp(result["last_seen"])
    
    return results


def get_machine_details(
    db: MunkiReportDB, serial_number: str
) -> Optional[Dict[str, Any]]:
    """Get complete details about a specific machine."""
    result = query_machines(
        db,
        filters={"serial_number": serial_number},
        include=["reportdata", "mdm_status"],
        limit=1,
    )
    
    if not result:
        return None
    
    machine = result[0]
    
    # Add recent events
    events_query = """
        SELECT type, module, msg, data, timestamp
        FROM event
        WHERE serial_number = ?
        ORDER BY timestamp DESC
        LIMIT 10
    """
    machine["recent_events"] = db.execute_query(events_query, (serial_number,))
    
    return machine


def get_mdm_enrollment_summary(db: MunkiReportDB) -> Dict[str, Any]:
    """Get summary statistics of MDM enrollment status."""
    query = """
        SELECT 
            mdm_enrolled,
            COUNT(*) as count,
            SUM(CASE WHEN is_supervised = 1 THEN 1 ELSE 0 END) as supervised_count
        FROM mdm_status
        GROUP BY mdm_enrolled
    """
    
    results = db.execute_query(query)
    
    summary = {
        "total_machines": sum(r["count"] for r in results),
        "by_status": {},
    }
    
    for row in results:
        status = row["mdm_enrolled"] or "Unknown"
        summary["by_status"][status] = {
            "count": row["count"],
            "supervised": row["supervised_count"],
        }
    
    return summary
