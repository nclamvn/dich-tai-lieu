"""Tests for schema migration system."""

import pytest

from core.database.sqlite_backend import SQLiteBackend
from core.database.migrator import SchemaMigrator


@pytest.fixture
def backend(tmp_path):
    return SQLiteBackend(tmp_path / "migrate_test.db")


class TestSchemaMigrator:

    def test_creates_migrations_table(self, backend):
        SchemaMigrator(backend)
        with backend.connection() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_migrations'"
            ).fetchone()
            assert row is not None

    def test_run_applies_migrations(self, backend):
        m = SchemaMigrator(backend)
        m.add("001_users", lambda conn: conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"
        ))
        m.add("002_posts", lambda conn: conn.execute(
            "CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT)"
        ))

        applied = m.run()
        assert applied == ["001_users", "002_posts"]

        # Tables should exist
        with backend.connection() as conn:
            conn.execute("SELECT * FROM users")
            conn.execute("SELECT * FROM posts")

    def test_skips_already_applied(self, backend):
        m = SchemaMigrator(backend)
        m.add("001_users", lambda conn: conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY)"
        ))
        m.run()

        # Second run should skip
        m2 = SchemaMigrator(backend)
        m2.add("001_users", lambda conn: conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY)"
        ))
        applied = m2.run()
        assert applied == []

    def test_pending_returns_unapplied(self, backend):
        m = SchemaMigrator(backend)
        m.add("001_a", lambda conn: None)
        m.add("002_b", lambda conn: None)

        assert m.pending() == ["001_a", "002_b"]
        m.run()
        assert m.pending() == []

    def test_chaining(self, backend):
        m = SchemaMigrator(backend)
        result = m.add("001", lambda conn: None).add("002", lambda conn: None)
        assert result is m
        assert len(m._migrations) == 2

    def test_migration_error_rolls_back(self, backend):
        m = SchemaMigrator(backend)
        m.add("001_good", lambda conn: conn.execute(
            "CREATE TABLE t1 (id INTEGER PRIMARY KEY)"
        ))
        m.add("002_bad", lambda conn: (_ for _ in ()).throw(RuntimeError("fail")))

        with pytest.raises(RuntimeError):
            m.run()

        # 001 should have been applied, 002 should not
        m2 = SchemaMigrator(backend)
        m2.add("001_good", lambda conn: None)
        m2.add("002_bad", lambda conn: None)
        assert m2.pending() == ["002_bad"]
