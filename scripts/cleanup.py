#!/usr/bin/env python3
"""
CLI entry point for manual file cleanup.

Usage:
    python -m scripts.cleanup              # run cleanup
    python -m scripts.cleanup --dry-run    # preview what would be cleaned
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    parser = argparse.ArgumentParser(description="AI Publisher Pro - File Cleanup")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be cleaned without deleting",
    )
    args = parser.parse_args()

    from core.services.file_cleanup import FileCleanupService

    svc = FileCleanupService()
    result = svc.run_cleanup(dry_run=args.dry_run)

    print(result)

    if result.errors:
        print(f"\nWarnings ({len(result.errors)}):")
        for err in result.errors:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
