"""
Job Repository - SQLite persistence for APS V2 jobs.

Ensures jobs survive server restarts.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class JobRepository:
    """
    SQLite repository for APS V2 jobs.

    Persists job state to survive server restarts.
    """

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"JobRepository initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

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
                    completed_at TEXT
                )
            """)

            # Index for finding pending/running jobs
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_aps_jobs_status
                ON aps_jobs(status)
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
                    created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ))

    def get(self, job_id: str) -> Optional[Dict]:
        """Get a job by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM aps_jobs WHERE job_id = ?",
                (job_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_dict(row)

    def get_pending_jobs(self) -> List[Dict]:
        """Get all pending/running jobs for recovery."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM aps_jobs
                WHERE status IN ('pending', 'running', 'vision_reading', 'translating')
                ORDER BY created_at ASC
            """).fetchall()

            return [self._row_to_dict(row) for row in rows]

    def get_all_jobs(self, limit: int = 50) -> List[Dict]:
        """Get all jobs, most recent first."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM aps_jobs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [self._row_to_dict(row) for row in rows]

    def delete(self, job_id: str) -> bool:
        """Delete a job."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM aps_jobs WHERE job_id = ?",
                (job_id,)
            )
            return cursor.rowcount > 0

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

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE aps_jobs
                SET status = 'failed', error = ?, updated_at = ?
                WHERE job_id = ?
            """, (error, datetime.now().isoformat(), job_id))

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
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
        }


# Singleton instance
_repository: Optional[JobRepository] = None

def get_job_repository(db_path: str = "data/jobs.db") -> JobRepository:
    """Get or create the job repository singleton."""
    global _repository
    if _repository is None:
        _repository = JobRepository(db_path)
    return _repository
