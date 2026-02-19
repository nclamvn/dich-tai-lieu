#!/usr/bin/env python3
"""
Backup Manager — SQLite online backup for all databases.

Creates compressed tar.gz archives with configurable retention.

Usage:
    python -m scripts.backup                    # create backup
    python -m scripts.backup --list             # list existing backups
    python -m scripts.backup --restore <path>   # restore from backup
"""

import argparse
import logging
import shutil
import sqlite3
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

# All known SQLite databases in the project
DATABASE_LOCATIONS = [
    "data/jobs.db",
    "data/aps_jobs.db",
    "data/cache/chunks.db",
    "data/checkpoints/checkpoints.db",
    "data/errors/error_tracker.db",
    "data/usage/usage.db",
    "data/api_keys/keys.db",
    "data/users/users.db",
]


class BackupManager:
    """SQLite online backup with compression and retention."""

    def __init__(
        self,
        backup_dir: Optional[Path] = None,
        max_backups: int = 10,
        base_dir: Optional[Path] = None,
    ):
        if base_dir is None:
            from config.settings import BASE_DIR
            base_dir = BASE_DIR

        self.base_dir = base_dir
        self.backup_dir = backup_dir or (base_dir / "data" / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = max_backups

    def create_backup(self) -> Path:
        """
        Create a compressed backup of all SQLite databases.

        Uses sqlite3 online backup API for consistency.

        Returns:
            Path to the created backup archive.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        staging_dir = self.backup_dir / f"staging_{timestamp}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        backed_up = []

        try:
            for rel_path in DATABASE_LOCATIONS:
                db_path = self.base_dir / rel_path
                if not db_path.exists():
                    continue

                # Create matching directory structure in staging
                dest = staging_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)

                # Use SQLite online backup API
                self._backup_sqlite(db_path, dest)
                backed_up.append(rel_path)

            if not backed_up:
                shutil.rmtree(staging_dir, ignore_errors=True)
                raise FileNotFoundError("No databases found to back up")

            # Create compressed archive
            archive_path = self.backup_dir / f"backup_{timestamp}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(staging_dir, arcname=f"backup_{timestamp}")

            logger.info(
                "Backup created: %s (%d databases, %.1f MB)",
                archive_path.name,
                len(backed_up),
                archive_path.stat().st_size / (1024 * 1024),
            )

            # Enforce retention
            self._enforce_retention()

            return archive_path

        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def _backup_sqlite(self, source: Path, dest: Path) -> None:
        """Use SQLite online backup API for a consistent copy."""
        src_conn = sqlite3.connect(str(source))
        dst_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

    def restore(self, archive_path: Path) -> List[str]:
        """
        Restore databases from a backup archive.

        Args:
            archive_path: Path to .tar.gz backup archive.

        Returns:
            List of restored database paths.
        """
        if not archive_path.exists():
            raise FileNotFoundError(f"Backup not found: {archive_path}")

        staging_dir = self.backup_dir / "restore_staging"
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

        restored = []

        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(staging_dir)

            # Find the extracted backup directory
            subdirs = list(staging_dir.iterdir())
            if not subdirs:
                raise ValueError("Empty backup archive")
            backup_root = subdirs[0]

            for rel_path in DATABASE_LOCATIONS:
                src = backup_root / rel_path
                if not src.exists():
                    continue

                dest = self.base_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)

                # Use SQLite backup API for safe restore
                self._backup_sqlite(src, dest)
                restored.append(rel_path)

            logger.info("Restored %d databases from %s", len(restored), archive_path.name)
            return restored

        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def list_backups(self) -> List[dict]:
        """List all available backups."""
        backups = []
        for f in sorted(self.backup_dir.glob("backup_*.tar.gz"), reverse=True):
            stat = f.stat()
            backups.append({
                "path": str(f),
                "name": f.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return backups

    def _enforce_retention(self) -> None:
        """Delete oldest backups beyond max_backups."""
        archives = sorted(
            self.backup_dir.glob("backup_*.tar.gz"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for old in archives[self.max_backups:]:
            old.unlink()
            logger.info("Retention: removed old backup %s", old.name)


def main():
    parser = argparse.ArgumentParser(description="AI Publisher Pro - Backup Manager")
    parser.add_argument("--list", action="store_true", help="List existing backups")
    parser.add_argument("--restore", type=str, help="Restore from backup archive path")
    parser.add_argument("--max-backups", type=int, default=10, help="Max backups to retain")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    mgr = BackupManager(max_backups=args.max_backups)

    if args.list:
        backups = mgr.list_backups()
        if not backups:
            print("No backups found.")
        else:
            print(f"Found {len(backups)} backup(s):")
            for b in backups:
                print(f"  {b['name']}  ({b['size_mb']} MB)  {b['created']}")

    elif args.restore:
        restored = mgr.restore(Path(args.restore))
        print(f"Restored {len(restored)} database(s):")
        for r in restored:
            print(f"  - {r}")

    else:
        path = mgr.create_backup()
        print(f"Backup created: {path}")


if __name__ == "__main__":
    main()
