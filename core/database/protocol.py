"""
DatabaseBackend protocol — the contract every backend must satisfy.

Usage:
    with backend.connection() as conn:
        conn.execute("SELECT 1")
        row = conn.fetchone()
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Protocol, runtime_checkable


@runtime_checkable
class DBConnection(Protocol):
    """Minimal connection interface returned by DatabaseBackend.connection()."""

    def execute(self, sql: str, parameters: Any = ...) -> Any: ...
    def fetchone(self) -> Optional[Any]: ...
    def fetchall(self) -> list: ...
    @property
    def lastrowid(self) -> Optional[int]: ...
    @property
    def rowcount(self) -> int: ...


@runtime_checkable
class DatabaseBackend(Protocol):
    """
    Protocol that all database backends must implement.

    The connection() context manager yields a DBConnection that
    auto-commits on success and rolls back on exception.
    """

    @contextmanager
    def connection(self) -> Iterator[DBConnection]: ...

    def close(self) -> None: ...
