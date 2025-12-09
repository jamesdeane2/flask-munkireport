"""Database connection and query execution - vendored from mcp-munkireport."""

import sqlite3
from typing import Any, Dict, List, Optional
from contextlib import contextmanager


class MunkiReportDB:
    """Manages connection to MunkiReport SQLite database."""

    def __init__(self, db_path: str, timeout: float = 30.0, check_same_thread: bool = False):
        """Initialize database connection.
        
        Args:
            db_path: Path to the SQLite database file
            timeout: Database timeout in seconds
            check_same_thread: SQLite same thread checking
        """
        self.db_path = db_path
        self.timeout = timeout
        self.check_same_thread = check_same_thread

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            timeout=self.timeout,
            check_same_thread=self.check_same_thread
        )
        conn.row_factory = sqlite3.Row
        # Ensure read-only mode
        conn.execute("PRAGMA query_only = ON")
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Convert rows to dictionaries
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results

    def execute_single(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single result.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Dictionary representing the row, or None if no results
        """
        results = self.execute_query(query, params)
        return results[0] if results else None

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = f"PRAGMA table_info({table_name})"
        return self.execute_query(query)

    def list_tables(self) -> List[str]:
        """Get list of all tables in the database.
        
        Returns:
            List of table names
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        results = self.execute_query(query)
        return [row["name"] for row in results]
