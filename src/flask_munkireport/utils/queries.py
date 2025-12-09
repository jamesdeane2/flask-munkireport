"""General query functions - vendored from mcp-munkireport."""

from typing import Any, Dict, List, Optional
from ..database import MunkiReportDB
from ..utils import build_where_clause


def get_database_stats(db: MunkiReportDB) -> Dict[str, Any]:
    """Get overall database statistics."""
    tables = db.list_tables()
    
    table_counts = {}
    important_tables = [
        "machine",
        "reportdata",
        "event",
        "mdm_status",
        "applications",
        "munkiinfo",
    ]
    
    for table in important_tables:
        if table in tables:
            result = db.execute_single(f"SELECT COUNT(*) as count FROM {table}")
            table_counts[table] = result["count"] if result else 0
    
    import os
    db_size = os.path.getsize(db.db_path)
    
    return {
        "database_path": db.db_path,
        "database_size_mb": round(db_size / (1024 * 1024), 2),
        "total_tables": len(tables),
        "all_tables": tables,
        "table_row_counts": table_counts,
    }


def get_table_summary(
    db: MunkiReportDB,
    table_name: str,
    group_by: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Get aggregated statistics for a table."""
    # Validate table name
    valid_tables = db.list_tables()
    if table_name not in valid_tables:
        raise ValueError(f"Invalid table name: {table_name}")
    
    if group_by:
        table_info = db.get_table_info(table_name)
        valid_columns = [col["name"] for col in table_info]
        if group_by not in valid_columns:
            raise ValueError(f"Invalid column: {group_by}")
        
        query = f"SELECT {group_by}, COUNT(*) as count FROM {table_name}"
    else:
        query = f"SELECT COUNT(*) as total_count FROM {table_name}"
    
    params = []
    if filters:
        where_clause, params = build_where_clause(filters)
        if where_clause:
            query += f" WHERE {where_clause}"
    
    if group_by:
        query += f" GROUP BY {group_by} ORDER BY count DESC"
    
    results = db.execute_query(query, tuple(params) if params else None)
    
    if group_by:
        return {
            "table": table_name,
            "grouped_by": group_by,
            "total_groups": len(results),
            "groups": results,
        }
    else:
        return {
            "table": table_name,
            "total_count": results[0]["total_count"] if results else 0,
        }
