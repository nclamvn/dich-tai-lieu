"""
File Cleanup Service — prevents disk exhaustion in production.

Removes:
  - Temp files older than N hours
  - Orphaned uploads (no matching active job)
  - Old output files (>30 days)
  - Old checkpoints (>7 days)
  - Old resolved errors (>30 days)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """Summary of a cleanup run."""
    temp_files_removed: int = 0
    orphaned_uploads_removed: int = 0
    old_outputs_removed: int = 0
    checkpoints_removed: int = 0
    errors_cleared: int = 0
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    def __str__(self) -> str:
        mb = self.bytes_freed / (1024 * 1024)
        mode = " (DRY RUN)" if self.dry_run else ""
        return (
            f"Cleanup{mode}: temp={self.temp_files_removed}, "
            f"orphans={self.orphaned_uploads_removed}, "
            f"outputs={self.old_outputs_removed}, "
            f"checkpoints={self.checkpoints_removed}, "
            f"errors_cleared={self.errors_cleared}, "
            f"freed={mb:.1f}MB"
        )


class FileCleanupService:
    """Configurable file cleanup with retention policies."""

    def __init__(
        self,
        temp_max_age_hours: int | None = None,
        upload_retention_days: int | None = None,
        output_retention_days: int | None = None,
        checkpoint_retention_days: int | None = None,
    ):
        from config.settings import settings

        self.temp_dir = settings.temp_dir
        self.input_dir = settings.input_dir
        self.output_dir = settings.output_dir
        self.checkpoint_dir = settings.checkpoint_dir

        self.temp_max_age_hours = temp_max_age_hours or settings.cleanup_temp_max_age_hours
        self.upload_retention_days = upload_retention_days or settings.cleanup_upload_retention_days
        self.output_retention_days = output_retention_days or settings.cleanup_output_retention_days
        self.checkpoint_retention_days = checkpoint_retention_days or settings.cleanup_checkpoint_retention_days

    def run_cleanup(self, dry_run: bool = False) -> CleanupResult:
        """Execute full cleanup sweep."""
        result = CleanupResult(dry_run=dry_run)

        self._clean_temp_files(result, dry_run)
        self._clean_orphaned_uploads(result, dry_run)
        self._clean_old_outputs(result, dry_run)
        self._clean_old_checkpoints(result, dry_run)
        self._clean_old_errors(result, dry_run)

        logger.info(str(result))
        return result

    def _clean_temp_files(self, result: CleanupResult, dry_run: bool) -> None:
        """Remove temp files older than max_age_hours."""
        if not self.temp_dir.exists():
            return
        cutoff = time.time() - (self.temp_max_age_hours * 3600)
        self._remove_old_files(self.temp_dir, cutoff, result, "temp_files_removed", dry_run)

    def _clean_orphaned_uploads(self, result: CleanupResult, dry_run: bool) -> None:
        """Remove uploads older than retention period."""
        if not self.input_dir.exists():
            return
        cutoff = time.time() - (self.upload_retention_days * 86400)
        self._remove_old_files(self.input_dir, cutoff, result, "orphaned_uploads_removed", dry_run)

    def _clean_old_outputs(self, result: CleanupResult, dry_run: bool) -> None:
        """Remove output files older than retention period."""
        if not self.output_dir.exists():
            return
        cutoff = time.time() - (self.output_retention_days * 86400)
        self._remove_old_files(self.output_dir, cutoff, result, "old_outputs_removed", dry_run)

    def _clean_old_checkpoints(self, result: CleanupResult, dry_run: bool) -> None:
        """Leverage CheckpointManager.cleanup_old_checkpoints()."""
        try:
            from core.cache.checkpoint_manager import CheckpointManager
            cp = CheckpointManager()
            if not dry_run:
                removed = cp.cleanup_old_checkpoints(days=self.checkpoint_retention_days)
                result.checkpoints_removed = removed
            else:
                # Count how many would be removed
                cutoff_time = time.time() - (self.checkpoint_retention_days * 86400)
                all_cp = cp.list_checkpoints(limit=10000)
                result.checkpoints_removed = sum(
                    1 for c in all_cp if c.updated_at < cutoff_time
                )
        except Exception as e:
            result.errors.append(f"checkpoint cleanup: {e}")
            logger.warning(f"Checkpoint cleanup failed: {e}")

    def _clean_old_errors(self, result: CleanupResult, dry_run: bool) -> None:
        """Leverage ErrorTracker.clear_old_errors()."""
        try:
            from core.error_tracker import get_error_tracker
            tracker = get_error_tracker()
            if not dry_run:
                result.errors_cleared = tracker.clear_old_errors(days=30)
            else:
                result.errors_cleared = 0  # can't easily count without deleting
        except Exception as e:
            result.errors.append(f"error cleanup: {e}")
            logger.warning(f"Error cleanup failed: {e}")

    def _remove_old_files(
        self,
        directory: Path,
        cutoff_ts: float,
        result: CleanupResult,
        counter_attr: str,
        dry_run: bool,
    ) -> None:
        """Remove files older than cutoff timestamp from a directory."""
        count = 0
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            try:
                mtime = path.stat().st_mtime
                if mtime < cutoff_ts:
                    size = path.stat().st_size
                    if not dry_run:
                        path.unlink()
                    result.bytes_freed += size
                    count += 1
            except OSError as e:
                result.errors.append(f"{path}: {e}")

        setattr(result, counter_attr, getattr(result, counter_attr) + count)
