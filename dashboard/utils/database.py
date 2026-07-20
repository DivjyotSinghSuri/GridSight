"""
DuckDB connection management for the GridSight dashboard.

This module is intentionally minimal: it exposes a single factory
function so that all connection logic (location, mode, future
credentials, etc.) lives in exactly one place.
"""

from pathlib import Path

import duckdb


DATABASE_PATH = Path("gridsight.duckdb")


def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Returns a new DuckDB connection to the GridSight warehouse.

    This is the single entry point for all dashboard database
    interactions. Keeping connection logic centralized makes future
    changes (different database location, read-only mode, pooling,
    etc.) trivial and keeps `queries.py` free of connection details.
    """
    return duckdb.connect(str(DATABASE_PATH))