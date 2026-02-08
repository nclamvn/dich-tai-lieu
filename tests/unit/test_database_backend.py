"""Tests for database abstraction layer."""

import pytest
import tempfile
from pathlib import Path

from core.database.protocol import DatabaseBackend, DBConnection
from core.database.sqlite_backend import SQLiteBackend


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary SQLiteBackend."""
    return SQLiteBackend(tmp_path / "test.db")


class TestSQLiteBackend:
    """SQLiteBackend protocol compliance and behavior."""

    def test_implements_protocol(self, tmp_db):
        assert isinstance(tmp_db, DatabaseBackend)

    def test_connection_context_manager(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
            conn.execute("INSERT INTO t (val) VALUES (?)", ("hello",))

        # Verify committed
        with tmp_db.connection() as conn:
            row = conn.execute("SELECT val FROM t WHERE id = 1").fetchone()
            assert row is not None
            assert row[0] == "hello"

    def test_rollback_on_error(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")

        with pytest.raises(Exception):
            with tmp_db.connection() as conn:
                conn.execute("INSERT INTO t (val) VALUES (?)", ("should_rollback",))
                raise RuntimeError("force rollback")

        with tmp_db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
            assert row[0] == 0

    def test_fetchone_returns_none_for_empty(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
            row = conn.execute("SELECT * FROM t").fetchone()
            assert row is None

    def test_fetchall_returns_empty_list(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
            rows = conn.execute("SELECT * FROM t").fetchall()
            assert rows == []

    def test_lastrowid(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)")
            conn.execute("INSERT INTO t (val) VALUES (?)", ("test",))
            assert conn.lastrowid == 1

    def test_rowcount(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER, val TEXT)")
            conn.execute("INSERT INTO t VALUES (1, 'a')")
            conn.execute("INSERT INTO t VALUES (2, 'b')")

        with tmp_db.connection() as conn:
            conn.execute("DELETE FROM t WHERE id = 1")
            assert conn.rowcount == 1

    def test_row_factory_sqlite_row(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (name TEXT, age INTEGER)")
            conn.execute("INSERT INTO t VALUES ('alice', 30)")

        with tmp_db.connection() as conn:
            row = conn.execute("SELECT * FROM t").fetchone()
            assert row["name"] == "alice"
            assert row["age"] == 30

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "test.db"
        backend = SQLiteBackend(deep_path)
        with backend.connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
        assert deep_path.exists()

    def test_close_is_noop(self, tmp_db):
        tmp_db.close()  # should not raise

    def test_multiple_sequential_connections(self, tmp_db):
        with tmp_db.connection() as conn:
            conn.execute("CREATE TABLE t (val TEXT)")

        for i in range(5):
            with tmp_db.connection() as conn:
                conn.execute("INSERT INTO t (val) VALUES (?)", (f"v{i}",))

        with tmp_db.connection() as conn:
            rows = conn.execute("SELECT COUNT(*) FROM t").fetchone()
            assert rows[0] == 5
