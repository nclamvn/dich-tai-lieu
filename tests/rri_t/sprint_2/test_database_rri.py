"""
RRI-T Sprint 2: Database abstraction layer tests.

Persona coverage: QA Destroyer, DevOps
Dimensions: D5 (Data Integrity), D6 (Infrastructure), D7 (Edge Cases)
"""

import threading
import pytest
from pathlib import Path

from core.database.sqlite_backend import SQLiteBackend, SQLiteCursor
from core.database.migrator import SchemaMigrator


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """Fresh non-persistent SQLiteBackend."""
    return SQLiteBackend(tmp_path / "test.db", persistent=False)


@pytest.fixture
def persistent_db(tmp_path):
    """Fresh persistent SQLiteBackend."""
    backend = SQLiteBackend(tmp_path / "persistent.db", persistent=True)
    yield backend
    backend.close()


# ===========================================================================
# DB-001: WAL mode enabled on connect
# ===========================================================================

class TestWALMode:
    """QA Destroyer persona — WAL mode verification."""

    @pytest.mark.p0
    def test_db_001_wal_mode_enabled(self, db):
        """DB-001 | QA | WAL mode enabled on connection"""
        with db.connection() as conn:
            result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"

    @pytest.mark.p0
    def test_db_001b_foreign_keys_enabled(self, db):
        """DB-001b | QA | Foreign keys enabled on connection"""
        with db.connection() as conn:
            result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1

    @pytest.mark.p0
    def test_db_001c_persistent_wal_mode(self, persistent_db):
        """DB-001c | QA | Persistent backend also has WAL mode"""
        with persistent_db.connection() as conn:
            result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"


# ===========================================================================
# DB-002: Transaction rollback on error
# ===========================================================================

class TestTransactionRollback:
    """QA Destroyer persona — data integrity under errors."""

    @pytest.mark.p0
    def test_db_002_rollback_on_error(self, db):
        """DB-002 | QA | Transaction rolls back on exception"""
        # Create table
        with db.connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO test (name) VALUES ('initial')")

        # Attempt insert that will fail after partial work
        with pytest.raises(Exception):
            with db.connection() as conn:
                conn.execute("INSERT INTO test (name) VALUES ('should_rollback')")
                raise RuntimeError("Simulated error")

        # Verify the failed insert was rolled back
        with db.connection() as conn:
            rows = conn.execute("SELECT * FROM test").fetchall()
        assert len(rows) == 1
        assert rows[0]["name"] == "initial"

    @pytest.mark.p0
    def test_db_002b_commit_on_success(self, db):
        """DB-002b | QA | Data persisted after successful transaction"""
        with db.connection() as conn:
            conn.execute("CREATE TABLE test2 (val TEXT)")
            conn.execute("INSERT INTO test2 (val) VALUES ('persisted')")

        with db.connection() as conn:
            rows = conn.execute("SELECT * FROM test2").fetchall()
        assert len(rows) == 1
        assert rows[0]["val"] == "persisted"

    @pytest.mark.p0
    def test_db_002c_persistent_rollback(self, persistent_db):
        """DB-002c | QA | Persistent backend also rolls back on error"""
        with persistent_db.connection() as conn:
            conn.execute("CREATE TABLE ptest (id INTEGER PRIMARY KEY, v TEXT)")
            conn.execute("INSERT INTO ptest (v) VALUES ('keep')")

        with pytest.raises(RuntimeError):
            with persistent_db.connection() as conn:
                conn.execute("INSERT INTO ptest (v) VALUES ('discard')")
                raise RuntimeError("fail")

        with persistent_db.connection() as conn:
            rows = conn.execute("SELECT * FROM ptest").fetchall()
        assert len(rows) == 1


# ===========================================================================
# DB-003: Migration idempotency
# ===========================================================================

class TestMigrationIdempotent:
    """QA Destroyer persona — migrations safe to run twice."""

    @pytest.mark.p0
    def test_db_003_migration_idempotent(self, db):
        """DB-003 | QA | Running migrations twice -> no error, same result"""
        migrator = SchemaMigrator(db)
        migrator.add("001_create_items", lambda c: c.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"
        ))

        # Run first time
        applied_1 = migrator.run()
        assert applied_1 == ["001_create_items"]

        # Run second time — should skip already applied
        applied_2 = migrator.run()
        assert applied_2 == []

    @pytest.mark.p0
    def test_db_003b_pending_shows_unapplied(self, db):
        """DB-003b | QA | pending() returns only unapplied migrations"""
        migrator = SchemaMigrator(db)
        migrator.add("001_first", lambda c: c.execute(
            "CREATE TABLE t1 (id INTEGER PRIMARY KEY)"
        ))
        migrator.add("002_second", lambda c: c.execute(
            "CREATE TABLE t2 (id INTEGER PRIMARY KEY)"
        ))

        assert len(migrator.pending()) == 2

        migrator.run()
        assert len(migrator.pending()) == 0

    @pytest.mark.p1
    def test_db_003c_incremental_migration(self, db):
        """DB-003c | QA | New migrations added after first run -> only new ones applied"""
        migrator = SchemaMigrator(db)
        migrator.add("001_first", lambda c: c.execute(
            "CREATE TABLE inc1 (id INTEGER PRIMARY KEY)"
        ))
        migrator.run()

        # Add second migration
        migrator.add("002_second", lambda c: c.execute(
            "CREATE TABLE inc2 (id INTEGER PRIMARY KEY)"
        ))
        applied = migrator.run()
        assert applied == ["002_second"]

    @pytest.mark.p1
    def test_db_003d_migration_chaining(self, db):
        """DB-003d | QA | add() returns self for chaining"""
        migrator = SchemaMigrator(db)
        result = migrator.add("001_a", lambda c: None).add("002_b", lambda c: None)
        assert result is migrator


# ===========================================================================
# DB-004: Concurrent writes
# ===========================================================================

class TestConcurrentWrites:
    """QA Destroyer persona — thread-safety."""

    @pytest.mark.p1
    def test_db_004_concurrent_writes_no_corruption(self, tmp_path):
        """DB-004 | QA | Concurrent writes -> no corruption"""
        db = SQLiteBackend(tmp_path / "concurrent.db", persistent=False)
        with db.connection() as conn:
            conn.execute("CREATE TABLE counter (id INTEGER PRIMARY KEY, val INTEGER)")
            conn.execute("INSERT INTO counter (id, val) VALUES (1, 0)")

        errors = []

        def increment():
            try:
                for _ in range(20):
                    with db.connection() as conn:
                        conn.execute("UPDATE counter SET val = val + 1 WHERE id = 1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent writes: {errors}"

        with db.connection() as conn:
            row = conn.execute("SELECT val FROM counter WHERE id = 1").fetchone()
        assert row["val"] == 100  # 5 threads * 20 increments


# ===========================================================================
# DB-005: SQLiteCursor interface
# ===========================================================================

class TestSQLiteCursor:
    """QA Destroyer persona — cursor wrapper correctness."""

    @pytest.mark.p1
    def test_db_005_cursor_chaining(self, db):
        """DB-005 | QA | execute() returns self for chaining"""
        with db.connection() as conn:
            conn.execute("CREATE TABLE chain (id INTEGER PRIMARY KEY, v TEXT)")
            result = conn.execute("INSERT INTO chain (v) VALUES ('test')")
            assert isinstance(result, SQLiteCursor)

    @pytest.mark.p1
    def test_db_005b_lastrowid(self, db):
        """DB-005b | QA | lastrowid returns inserted row ID"""
        with db.connection() as conn:
            conn.execute("CREATE TABLE lr (id INTEGER PRIMARY KEY AUTOINCREMENT, v TEXT)")
            conn.execute("INSERT INTO lr (v) VALUES ('a')")
            assert conn.lastrowid >= 1

    @pytest.mark.p1
    def test_db_005c_rowcount(self, db):
        """DB-005c | QA | rowcount reflects affected rows"""
        with db.connection() as conn:
            conn.execute("CREATE TABLE rc (id INTEGER PRIMARY KEY, v TEXT)")
            conn.execute("INSERT INTO rc (v) VALUES ('a')")
            conn.execute("INSERT INTO rc (v) VALUES ('b')")
            conn.execute("DELETE FROM rc")
            assert conn.rowcount == 2

    @pytest.mark.p1
    def test_db_005d_fetchone_empty(self, db):
        """DB-005d | QA | fetchone() on empty -> None"""
        with db.connection() as conn:
            conn.execute("CREATE TABLE empty_t (id INTEGER PRIMARY KEY)")
            row = conn.execute("SELECT * FROM empty_t").fetchone()
        assert row is None

    @pytest.mark.p1
    def test_db_005e_fetchall_empty(self, db):
        """DB-005e | QA | fetchall() on empty -> empty list"""
        with db.connection() as conn:
            conn.execute("CREATE TABLE empty_t2 (id INTEGER PRIMARY KEY)")
            rows = conn.execute("SELECT * FROM empty_t2").fetchall()
        assert rows == []

    @pytest.mark.p1
    def test_db_005f_no_cursor_fetchone(self, db):
        """DB-005f | QA | fetchone before execute -> None"""
        with db.connection() as conn:
            assert conn.fetchone() is None

    @pytest.mark.p1
    def test_db_005g_no_cursor_fetchall(self, db):
        """DB-005g | QA | fetchall before execute -> empty list"""
        with db.connection() as conn:
            assert conn.fetchall() == []


# ===========================================================================
# DB-006: Close behavior
# ===========================================================================

class TestClose:
    """DevOps persona — resource cleanup."""

    @pytest.mark.p1
    def test_db_006_close_persistent(self, tmp_path):
        """DB-006 | DevOps | close() on persistent backend clears connection"""
        db = SQLiteBackend(tmp_path / "close_test.db", persistent=True)
        with db.connection() as conn:
            conn.execute("CREATE TABLE x (id INTEGER PRIMARY KEY)")
        db.close()
        assert db._conn is None

    @pytest.mark.p1
    def test_db_006b_close_nonpersistent_noop(self, db):
        """DB-006b | DevOps | close() on non-persistent is safe no-op"""
        db.close()  # Should not raise
        # Can still use the db after close
        with db.connection() as conn:
            conn.execute("CREATE TABLE noop (id INTEGER PRIMARY KEY)")


# ===========================================================================
# DB-007: Directory auto-creation
# ===========================================================================

class TestDirectoryCreation:
    """DevOps persona — database directory auto-creation."""

    @pytest.mark.p1
    def test_db_007_parent_dir_created(self, tmp_path):
        """DB-007 | DevOps | Parent directories created if missing"""
        db_path = tmp_path / "deep" / "nested" / "db.sqlite"
        db = SQLiteBackend(db_path)
        with db.connection() as conn:
            conn.execute("CREATE TABLE auto (id INTEGER PRIMARY KEY)")
        assert db_path.parent.exists()
