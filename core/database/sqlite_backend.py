"""
SQLite implementation of DatabaseBackend.

Wraps the contextmanager pattern already used across the codebase
(api/job_repository.py, core/usage/database.py, etc.).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional


class SQLiteCursor:
    """Thin wrapper so that a single object exposes execute + fetch."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._cursor: Optional[sqlite3.Cursor] = None

    def execute(self, sql: str, parameters: Any = ()) -> "SQLiteCursor":
        self._cursor = self._conn.execute(sql, parameters)
        return self

    def fetchone(self) -> Optional[sqlite3.Row]:
        if self._cursor is None:
            return None
        return self._cursor.fetchone()

    def fetchall(self) -> list:
        if self._cursor is None:
            return []
        return self._cursor.fetchall()

    @property
    def lastrowid(self) -> Optional[int]:
        if self._cursor is None:
            return None
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        if self._cursor is None:
            return 0
        return self._cursor.rowcount


class SQLiteBackend:
    """
    SQLite DatabaseBackend implementation.

    Each call to connection() opens a new connection, sets row_factory,
    commits on success, rolls back on error, and closes on exit.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[SQLiteCursor]:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        cursor = SQLiteCursor(conn)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        pass  # connections are per-call, nothing to close
