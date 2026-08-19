#!/usr/bin/env python3
"""Back up all SQLite databases under data/ into a timestamped folder.

Consistent (WAL-safe) snapshots via SQLite's online backup API. Exit code is
non-zero if any database fails to back up.

Examples
--------
  python3 scripts/backup_db.py --dest backups
  # -> backups/20260819-051530/<mirrors data/ layout>

  # cron (daily at 02:30):
  # 30 2 * * *  cd /app && python3 scripts/backup_db.py --dest /var/backups/dtl
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database.backup import backup_databases  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Back up SQLite databases under data/")
    parser.add_argument("--data", default=str(ROOT / "data"), help="data directory to back up")
    parser.add_argument("--dest", required=True, help="backup root (a timestamped subdir is created)")
    parser.add_argument("--stamp", default=None, help="override the timestamp subfolder name")
    args = parser.parse_args(argv)

    stamp = args.stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = Path(args.dest) / stamp

    try:
        backed = backup_databases(args.data, dest)
    except RuntimeError as e:
        print(f"Backup completed with errors: {e}", file=sys.stderr)
        return 1

    print(f"Backed up {len(backed)} database(s) -> {dest}")
    for path in backed:
        print(f"  - {path.relative_to(dest)}")
    print(
        "\nReminder: data/.encryption_key is NOT a .db and is not included here — "
        "back it up separately and securely (losing it makes encrypted data unreadable)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
