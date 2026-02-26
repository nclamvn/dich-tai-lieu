"""
Lightweight SQLite schema migration system.

Tracks applied migrations in a `_schema_migrations` table within each database.
Each migration is a version string + a Python callable that receives a connection.

Usage:
    from core.database.migrator import SchemaMigrator

    migrator = SchemaMigrator(backend)
    migrator.add("001_create_users", lambda conn: conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"
    ))
    migrator.run()
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from .sqlite_backend import SQLiteBackend, SQLiteCursor

logger = logging.getLogger(__name__)

MigrationFn = Callable[[SQLiteCursor], None]


class SchemaMigrator:
    """Runs versioned schema migrations on a SQLiteBackend database."""

    def __init__(self, backend: SQLiteBackend):
        self._backend = backend
        self._migrations: list[tuple[str, MigrationFn]] = []
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        with self._backend.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at REAL NOT NULL
                )
            """)

    def add(self, version: str, fn: MigrationFn) -> "SchemaMigrator":
        """Register a migration. Returns self for chaining."""
        self._migrations.append((version, fn))
        return self

    def pending(self) -> list[str]:
        """Return versions that have not been applied yet."""
        applied = self._applied_versions()
        return [v for v, _ in self._migrations if v not in applied]

    def run(self) -> list[str]:
        """Apply all pending migrations in order. Returns list of applied versions."""
        applied = self._applied_versions()
        newly_applied: list[str] = []

        for version, fn in self._migrations:
            if version in applied:
                continue
            logger.info(f"Applying migration: {version}")
            with self._backend.connection() as conn:
                fn(conn)
                conn.execute(
                    "INSERT INTO _schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, time.time()),
                )
            newly_applied.append(version)
            logger.info(f"Migration applied: {version}")

        return newly_applied

    def _applied_versions(self) -> set[str]:
        with self._backend.connection() as conn:
            rows = conn.execute(
                "SELECT version FROM _schema_migrations"
            ).fetchall()
        return {row[0] for row in rows}
