"""
Database configuration — reads DATABASE_BACKEND from settings
and returns the appropriate backend instance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .protocol import DatabaseBackend
from .sqlite_backend import SQLiteBackend


def get_db_backend(
    db_name: str,
    db_dir: Optional[Union[str, Path]] = None,
    persistent: bool = False,
) -> DatabaseBackend:
    """
    Factory: return a DatabaseBackend for the given database name.

    Args:
        db_name: logical name, e.g. "jobs", "usage", "errors".
                 For SQLite this becomes ``<db_dir>/<db_name>.db``.
        db_dir:  directory for database files.  Defaults to settings.database_dir.
        persistent: if True, reuse a single connection across calls
                    (suited for modules that keep a long-lived connection).

    Returns:
        A DatabaseBackend instance (currently always SQLiteBackend).
    """
    from config.settings import settings

    backend_type = getattr(settings, "database_backend", "sqlite")

    if db_dir is None:
        db_dir = getattr(settings, "database_dir", Path("data"))
    db_dir = Path(db_dir)

    if backend_type == "sqlite":
        return SQLiteBackend(db_dir / f"{db_name}.db", persistent=persistent)

    # Sprint 2: postgresql
    raise ValueError(f"Unsupported database backend: {backend_type}")
