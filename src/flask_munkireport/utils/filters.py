"""Utility functions for building SQL filters - vendored from mcp-munkireport."""

from typing import Any, Dict, List, Optional, Tuple


def build_where_clause(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Build a WHERE clause from a filters dictionary.
    
    Args:
        filters: Dictionary of field names to filter values
                Special keys:
                - Fields ending in '_before': Less than comparison (for dates)
                - Fields ending in '_after': Greater than comparison (for dates)
                - List values: IN clause
                
    Returns:
        Tuple of (WHERE clause string, list of parameters)
    """
    if not filters:
        return "", []

    conditions = []
    params = []

    for key, value in filters.items():
        if value is None:
            continue

        # Handle special suffixes for date comparisons
        if key.endswith("_before"):
            field = key.replace("_before", "")
            conditions.append(f"{field} < ?")
            params.append(value)
        elif key.endswith("_after"):
            field = key.replace("_after", "")
            conditions.append(f"{field} > ?")
            params.append(value)
        # Handle list values (IN clause)
        elif isinstance(value, list):
            if not value:
                continue
            placeholders = ", ".join(["?"] * len(value))
            conditions.append(f"{key} IN ({placeholders})")
            params.extend(value)
        # Handle boolean values
        elif isinstance(value, bool):
            conditions.append(f"{key} = ?")
            params.append(1 if value else 0)
        # Standard equality
        else:
            conditions.append(f"{key} = ?")
            params.append(value)

    where_clause = " AND ".join(conditions)
    return where_clause, params


def build_order_clause(order_by: Optional[str]) -> str:
    """Build an ORDER BY clause safely.
    
    Args:
        order_by: Order specification (e.g., 'timestamp DESC', 'hostname')
        
    Returns:
        ORDER BY clause string (empty if no order specified)
    """
    if not order_by:
        return ""
    
    # Basic SQL injection protection - only allow alphanumeric, underscores, spaces, dots, and DESC/ASC
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_. ")
    if not all(c in safe_chars for c in order_by):
        raise ValueError(f"Invalid characters in order_by: {order_by}")
    
    return f"ORDER BY {order_by}"


def build_limit_clause(limit: Optional[int]) -> str:
    """Build a LIMIT clause.
    
    Args:
        limit: Maximum number of rows to return
        
    Returns:
        LIMIT clause string (empty if no limit specified)
    """
    if limit is None or limit <= 0:
        return ""
    return f"LIMIT {int(limit)}"


def parse_timestamp(timestamp: Optional[int]) -> Optional[str]:
    """Convert Unix timestamp to ISO format string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        ISO format datetime string, or None if timestamp is None
    """
    if timestamp is None:
        return None
    
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).isoformat()


def parse_json_field(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse a JSON string field.
    
    Args:
        json_str: JSON string
        
    Returns:
        Parsed dictionary, or None if invalid/empty
    """
    if not json_str:
        return None
    
    import json
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
