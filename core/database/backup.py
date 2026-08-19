"""Consistent SQLite backups (production — data durability).

Uses SQLite's online backup API so each snapshot is transactionally consistent
even while the app is writing (WAL-safe) — a plain file copy of a live DB can be
torn. Backs up every ``*.db`` under a data directory, preserving relative
structure, and fails loud if any database can't be copied.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Union

logger = logging.getLogger(__name__)


def _backup_one(source: Path, dest: Path) -> None:
    """Write a consistent snapshot of ``source`` to ``dest`` via sqlite backup()."""
    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(dest))
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def backup_databases(data_dir: Union[str, Path], dest_dir: Union[str, Path]) -> List[Path]:
    """Back up every ``*.db`` under ``data_dir`` into ``dest_dir``.

    Preserves the relative directory structure. Skips anything already inside
    ``dest_dir`` (so a backup dir nested under the data dir isn't re-copied).
    Raises RuntimeError if any database fails to back up (after attempting all).
    """
    data_dir = Path(data_dir).resolve()
    dest_dir = Path(dest_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    backed: List[Path] = []
    failed: List[tuple] = []

    for db in sorted(data_dir.rglob("*.db")):
        if dest_dir == db.parent or dest_dir in db.parents:
            continue  # never back up the backups
        target = dest_dir / db.relative_to(data_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            _backup_one(db, target)
            backed.append(target)
            logger.info("Backed up %s -> %s", db, target)
        except Exception as e:  # noqa: BLE001 - collect, report all failures
            logger.error("Backup FAILED for %s: %s", db, e)
            failed.append((db, str(e)))

    if failed:
        details = ", ".join(str(p) for p, _ in failed)
        raise RuntimeError(f"{len(failed)} database(s) failed to back up: {details}")

    return backed
