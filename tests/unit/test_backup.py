"""Tests for BackupManager."""

import sqlite3
import pytest
from pathlib import Path

from scripts.backup import BackupManager


@pytest.fixture
def backup_env(tmp_path):
    """Create a fake project layout with some SQLite databases."""
    base = tmp_path / "project"
    base.mkdir()

    # Create a couple of test databases
    for rel in ["data/jobs.db", "data/usage/usage.db"]:
        db_path = base / rel
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'hello')")
        conn.commit()
        conn.close()

    return base


@pytest.fixture
def manager(backup_env, tmp_path):
    return BackupManager(
        backup_dir=tmp_path / "backups",
        max_backups=3,
        base_dir=backup_env,
    )


class TestBackupManager:

    def test_create_backup(self, manager):
        path = manager.create_backup()
        assert path.exists()
        assert path.suffix == ".gz"
        assert "backup_" in path.name

    def test_list_backups(self, manager):
        manager.create_backup()
        backups = manager.list_backups()
        assert len(backups) == 1
        assert backups[0]["size_mb"] >= 0

    def test_restore_backup(self, manager, backup_env):
        # Create backup
        archive = manager.create_backup()

        # Delete original databases
        for db in backup_env.rglob("*.db"):
            db.unlink()

        # Restore
        restored = manager.restore(archive)
        assert len(restored) >= 1

        # Verify data is intact
        db_path = backup_env / "data" / "jobs.db"
        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT val FROM test_table WHERE id = 1").fetchone()
        conn.close()
        assert row[0] == "hello"

    def test_retention_policy(self, manager):
        # Create more backups than max_backups
        for _ in range(5):
            manager.create_backup()

        backups = manager.list_backups()
        assert len(backups) <= 3  # max_backups=3

    def test_restore_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.restore(Path("/nonexistent/backup.tar.gz"))

    def test_backup_no_databases_raises(self, tmp_path):
        empty_base = tmp_path / "empty_project"
        empty_base.mkdir()
        mgr = BackupManager(
            backup_dir=tmp_path / "backups2",
            base_dir=empty_base,
        )
        with pytest.raises(FileNotFoundError, match="No databases found"):
            mgr.create_backup()
