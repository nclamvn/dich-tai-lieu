"""
Job Repository - SQLite persistence for APS V2 jobs.

Ensures jobs survive server restarts.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
from contextlib import contextmanager

from core.database import get_db_backend

logger = logging.getLogger(__name__)


class JobRepository:
    """
    SQLite repository for APS V2 jobs.

    Persists job state to survive server restarts.
    """

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._backend = get_db_backend("aps_jobs", db_dir=self.db_path.parent)
        self._init_db()
        logger.info(f"JobRepository initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        with self._backend.connection() as conn:
            yield conn

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aps_jobs (
                    job_id TEXT PRIMARY KEY,
                    source_file TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    output_formats TEXT NOT NULL,
                    use_vision INTEGER DEFAULT 1,

                    status TEXT NOT NULL DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    current_stage TEXT DEFAULT '',
                    error TEXT,

                    -- Stored as JSON
                    dna_json TEXT,
                    output_paths_json TEXT DEFAULT '{}',

                    -- File content path (for resume)
                    content_path TEXT,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,

                    -- Multi-tenancy
                    user_id TEXT DEFAULT 'default_user'
                )
            """)

            # Index for finding pending/running jobs
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aps_jobs_status
                ON aps_jobs(status)
            """)

            # Migration: add user_id to existing databases
            try:
                conn.execute("ALTER TABLE aps_jobs ADD COLUMN user_id TEXT DEFAULT 'default_user'")
            except Exception:
                pass  # Column already exists

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aps_jobs_user_id
                ON aps_jobs(user_id)
            """)

            # STR-04: Migration — add deleted_at column for soft deletes
            try:
                conn.execute("ALTER TABLE aps_jobs ADD COLUMN deleted_at TEXT")
            except Exception:
                pass  # Column already exists

            # QA-23: Version history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    field TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT DEFAULT 'system',
                    changed_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_history_job_id
                ON job_history(job_id)
            """)

            logger.info("Database schema initialized")

    def save(self, job: Dict) -> None:
        """Save or update a job."""
        with self._get_connection() as conn:
            # Serialize complex fields
            output_formats = json.dumps(job.get("output_formats", []))
            output_paths = json.dumps(job.get("output_paths", {}))
            dna_json = json.dumps(job.get("dna")) if job.get("dna") else None

            # Convert datetime to string
            created_at = job.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            completed_at = job.get("completed_at")
            if isinstance(completed_at, datetime):
                completed_at = completed_at.isoformat()

            now = datetime.now().isoformat()

            conn.execute("""
                INSERT INTO aps_jobs (
                    job_id, source_file, source_language, target_language,
                    profile_id, output_formats, use_vision,
                    status, progress, current_stage, error,
                    dna_json, output_paths_json, content_path,
                    created_at, updated_at, completed_at, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    progress = excluded.progress,
                    current_stage = excluded.current_stage,
                    error = excluded.error,
                    dna_json = excluded.dna_json,
                    output_paths_json = excluded.output_paths_json,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at
            """, (
                job["job_id"],
                job.get("source_file", ""),
                job.get("source_language", "auto"),
                job.get("target_language", "vi"),
                job.get("profile_id", "novel"),
                output_formats,
                1 if job.get("use_vision", True) else 0,
                job.get("status", "pending"),
                job.get("progress", 0.0),
                job.get("current_stage", ""),
                job.get("error"),
                dna_json,
                output_paths,
                job.get("content_path"),
                created_at or now,
                now,
                completed_at,
                job.get("user_id", "default_user"),
            ))

    def get(self, job_id: str) -> Optional[Dict]:
        """Get a job by ID (excludes soft-deleted)."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM aps_jobs WHERE job_id = ? AND deleted_at IS NULL",
                (job_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

    def get_pending_jobs(self) -> List[Dict]:
        """Get all pending/running jobs for recovery (excludes soft-deleted)."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM aps_jobs
                WHERE status IN ('pending', 'running', 'vision_reading', 'translating')
                  AND deleted_at IS NULL
                ORDER BY created_at ASC
            """).fetchall()

            return [self._row_to_dict(row) for row in rows]

    # QA-18: Explicit column list for list queries (avoid SELECT *)
    _LIST_COLUMNS = (
        "job_id, source_file, source_language, target_language, profile_id, "
        "output_formats, use_vision, status, progress, current_stage, error, "
        "output_paths_json, created_at, updated_at, completed_at, user_id"
    )

    def get_all_jobs(self, limit: int = 50, user_id: Optional[str] = None) -> List[Dict]:
        """Get all jobs, most recent first (excludes soft-deleted). Optionally filter by user_id."""
        with self._get_connection() as conn:
            if user_id:
                rows = conn.execute(f"""
                    SELECT {self._LIST_COLUMNS} FROM aps_jobs
                    WHERE user_id = ? AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, limit)).fetchall()
            else:
                rows = conn.execute(f"""
                    SELECT {self._LIST_COLUMNS} FROM aps_jobs
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

            return [self._row_to_list_dict(row) for row in rows]

    def _row_to_list_dict(self, row: Any) -> Dict:
        """Convert list-query row to job dict (lighter, no dna_json/content_path)."""
        return {
            "job_id": row["job_id"],
            "source_file": row["source_file"],
            "source_language": row["source_language"],
            "target_language": row["target_language"],
            "profile_id": row["profile_id"],
            "output_formats": json.loads(row["output_formats"]),
            "use_vision": bool(row["use_vision"]),
            "status": row["status"],
            "progress": row["progress"],
            "current_stage": row["current_stage"],
            "error": row["error"],
            "dna": None,
            "output_paths": json.loads(row["output_paths_json"]),
            "content_path": None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
            "user_id": row["user_id"] if "user_id" in row.keys() else "default_user",
        }

    def delete(self, job_id: str) -> bool:
        """Soft-delete a job (STR-04)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE aps_jobs SET deleted_at = ?, updated_at = ? WHERE job_id = ? AND deleted_at IS NULL",
                (datetime.now().isoformat(), datetime.now().isoformat(), job_id)
            )
            return cursor.rowcount > 0

    def purge(self, job_id: str) -> bool:
        """Permanently delete a soft-deleted job (STR-04) and clean orphaned files (QA-22)."""
        with self._get_connection() as conn:
            # Get file paths before deleting
            row = conn.execute(
                "SELECT source_file, content_path, output_paths_json FROM aps_jobs WHERE job_id = ? AND deleted_at IS NOT NULL",
                (job_id,)
            ).fetchone()

            cursor = conn.execute(
                "DELETE FROM aps_jobs WHERE job_id = ? AND deleted_at IS NOT NULL",
                (job_id,)
            )
            if cursor.rowcount > 0 and row:
                self._cleanup_job_files(job_id, row)
            return cursor.rowcount > 0

    def _cleanup_job_files(self, job_id: str, row) -> None:
        """QA-22: Remove orphaned files for a deleted job."""
        paths_to_clean = []
        if row["content_path"]:
            paths_to_clean.append(row["content_path"])
        if row["source_file"]:
            paths_to_clean.append(row["source_file"])
        try:
            output_paths = json.loads(row["output_paths_json"] or "{}")
            paths_to_clean.extend(output_paths.values())
        except (json.JSONDecodeError, AttributeError):
            pass
        # Also check common directories
        for d in [f"uploads/v2/{job_id}", f"outputs/v2/{job_id}"]:
            if Path(d).exists():
                paths_to_clean.append(d)

        for path in paths_to_clean:
            if not path:
                continue
            p = Path(path)
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                elif p.exists():
                    p.unlink()
            except OSError:
                logger.warning(f"Failed to clean orphan file: {path}")

    def restore(self, job_id: str) -> bool:
        """Restore a soft-deleted job (STR-04)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE aps_jobs SET deleted_at = NULL, updated_at = ? WHERE job_id = ? AND deleted_at IS NOT NULL",
                (datetime.now().isoformat(), job_id)
            )
            return cursor.rowcount > 0

    def vacuum(self) -> None:
        """QA-20: Reclaim disk space after bulk deletes."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
            logger.info("VACUUM completed on aps_jobs database")

    def count_active_jobs(self, user_id: Optional[str] = None) -> int:
        """Count pending/running jobs for queue overflow check."""
        with self._get_connection() as conn:
            if user_id:
                row = conn.execute(
                    "SELECT COUNT(*) FROM aps_jobs WHERE user_id = ? AND status IN ('pending', 'running') AND deleted_at IS NULL",
                    (user_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM aps_jobs WHERE status IN ('pending', 'running') AND deleted_at IS NULL"
                ).fetchone()
            return row[0] if row else 0

    def update_progress(self, job_id: str, progress: float, stage: str) -> None:
        """Quick update for progress (optimized for frequent calls)."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE aps_jobs
                SET progress = ?, current_stage = ?, updated_at = ?
                WHERE job_id = ?
            """, (progress, stage, datetime.now().isoformat(), job_id))

    def mark_complete(self, job_id: str, output_paths: Dict) -> None:
        """Mark job as complete."""
        with self._get_connection() as conn:
            now = datetime.now().isoformat()
            conn.execute("""
                UPDATE aps_jobs
                SET status = 'complete', progress = 100.0,
                    current_stage = 'Complete',
                    output_paths_json = ?,
                    updated_at = ?, completed_at = ?
                WHERE job_id = ?
            """, (json.dumps(output_paths), now, now, job_id))
        self.record_history(job_id, "status", "running", "complete")

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE aps_jobs
                SET status = 'failed', error = ?, updated_at = ?
                WHERE job_id = ?
            """, (error, datetime.now().isoformat(), job_id))
        self.record_history(job_id, "status", "running", "failed")

    def _row_to_dict(self, row: Any) -> Dict:
        """Convert database row to job dict."""
        return {
            "job_id": row["job_id"],
            "source_file": row["source_file"],
            "source_language": row["source_language"],
            "target_language": row["target_language"],
            "profile_id": row["profile_id"],
            "output_formats": json.loads(row["output_formats"]),
            "use_vision": bool(row["use_vision"]),
            "status": row["status"],
            "progress": row["progress"],
            "current_stage": row["current_stage"],
            "error": row["error"],
            "dna": json.loads(row["dna_json"]) if row["dna_json"] else None,
            "output_paths": json.loads(row["output_paths_json"]),
            "content_path": row["content_path"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
            "user_id": row["user_id"] if "user_id" in row.keys() else "default_user",
        }

    # QA-23: Version history
    def record_history(self, job_id: str, field: str, old_value: str, new_value: str, changed_by: str = "system") -> None:
        """Record a change to a job field in the history table."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO job_history (job_id, field, old_value, new_value, changed_by, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, field, old_value, new_value, changed_by, datetime.now().isoformat()),
            )

    def get_history(self, job_id: str, limit: int = 50) -> List[Dict]:
        """Retrieve version history for a job."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT field, old_value, new_value, changed_by, changed_at FROM job_history WHERE job_id = ? ORDER BY changed_at DESC LIMIT ?",
                (job_id, limit),
            ).fetchall()
            return [
                {"field": r[0], "old_value": r[1], "new_value": r[2], "changed_by": r[3], "changed_at": r[4]}
                for r in rows
            ]


# Singleton instance
_repository: Optional[JobRepository] = None

def get_job_repository(db_path: str = "data/jobs.db") -> JobRepository:
    """Get or create the job repository singleton."""
    global _repository
    if _repository is None:
        _repository = JobRepository(db_path)
    return _repository
