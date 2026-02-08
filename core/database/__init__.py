"""
Database abstraction layer.

Usage:
    from core.database import get_db_backend

    backend = get_db_backend("jobs")
    with backend.connection() as conn:
        conn.execute("SELECT 1")
"""

from .config import get_db_backend
from .protocol import DatabaseBackend, DBConnection
from .sqlite_backend import SQLiteBackend
