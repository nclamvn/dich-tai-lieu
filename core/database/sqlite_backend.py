"""
SQLite implementation of DatabaseBackend.

Wraps the contextmanager pattern already used across the codebase
(api/job_repository.py, core/usage/database.py, etc.).
"""

from __future__ import annotations

import sqlite3
import threading
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

    When persistent=False (default): each call to connection() opens a new
    connection, commits on success, rolls back on error, and closes on exit.

    When persistent=True: a single connection is reused across calls,
    protected by a threading.Lock for thread safety.
    """

    def __init__(self, db_path: str | Path, persistent: bool = False):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._persistent = persistent
        self._conn: Optional[sqlite3.Connection] = None
        self._lock: Optional[threading.Lock] = threading.Lock() if persistent else None

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=not self._persistent,
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self) -> Iterator[SQLiteCursor]:
        if self._persistent:
            assert self._lock is not None
            with self._lock:
                if self._conn is None:
                    self._conn = self._create_connection()
                cursor = SQLiteCursor(self._conn)
                try:
                    yield cursor
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise
        else:
            conn = self._create_connection()
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
        if self._persistent and self._conn is not None:
            self._conn.close()
            self._conn = None
