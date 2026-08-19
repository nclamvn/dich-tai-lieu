"""Production: consistent SQLite backups (data durability)."""

import sqlite3

import pytest

from core.database.backup import backup_databases


def _make_db(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.executemany("INSERT INTO t (v) VALUES (?)", [(v,) for v in values])
    con.commit()
    con.close()


def _rows(path):
    con = sqlite3.connect(str(path))
    try:
        return [r[0] for r in con.execute("SELECT v FROM t ORDER BY id")]
    finally:
        con.close()


def test_backs_up_all_dbs_preserving_structure(tmp_path):
    data, dest = tmp_path / "data", tmp_path / "backup"
    _make_db(data / "jobs.db", ["a", "b"])
    _make_db(data / "users" / "users.db", ["x"])

    backed = backup_databases(data, dest)

    assert (dest / "jobs.db").exists()
    assert (dest / "users" / "users.db").exists()
    assert len(backed) == 2


def test_backup_content_matches_source(tmp_path):
    data, dest = tmp_path / "data", tmp_path / "backup"
    _make_db(data / "jobs.db", ["a", "b", "c"])

    backup_databases(data, dest)

    assert _rows(dest / "jobs.db") == ["a", "b", "c"]


def test_backup_is_consistent_under_wal(tmp_path):
    data, dest = tmp_path / "data", tmp_path / "backup"
    db = data / "jobs.db"
    _make_db(db, ["a"])

    # A live WAL writer with a committed change the file copy might miss.
    con = sqlite3.connect(str(db))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("INSERT INTO t (v) VALUES ('b')")
    con.commit()
    try:
        backup_databases(data, dest)
    finally:
        con.close()

    assert _rows(dest / "jobs.db") == ["a", "b"]


def test_dest_inside_data_is_not_recursively_backed_up(tmp_path):
    data = tmp_path / "data"
    _make_db(data / "jobs.db", ["a"])
    dest = data / "backups"  # destination nested under the data dir

    backed = backup_databases(data, dest)

    assert len(backed) == 1  # only data/jobs.db, not the freshly-written copy


def test_failure_raises(tmp_path, monkeypatch):
    data, dest = tmp_path / "data", tmp_path / "backup"
    _make_db(data / "jobs.db", ["a"])

    import core.database.backup as backup_mod

    def _boom(src, dst):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(backup_mod, "_backup_one", _boom)
    with pytest.raises(RuntimeError):
        backup_databases(data, dest)
