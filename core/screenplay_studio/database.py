"""
Screenplay Studio Database Repository

SQLite-based storage for screenplay projects.
"""

import sqlite3
import json
import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from .models import ScreenplayProject, ProjectStatus, ProjectTier

logger = logging.getLogger(__name__)


class ScreenplayRepository:
    """Repository for screenplay project persistence"""

    def __init__(self, db_path: str = "data/screenplay_studio.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get database connection with WAL mode"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS screenplay_projects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_type TEXT DEFAULT 'novel',
                    language TEXT DEFAULT 'en',
                    tier TEXT DEFAULT 'free',
                    video_provider TEXT,
                    status TEXT DEFAULT 'draft',
                    current_phase INTEGER DEFAULT 0,
                    progress_percent REAL DEFAULT 0,
                    error_message TEXT,
                    source_text TEXT,
                    source_file_path TEXT,
                    story_analysis_json TEXT,
                    screenplay_json TEXT,
                    estimated_cost_usd REAL DEFAULT 0,
                    actual_cost_usd REAL DEFAULT 0,
                    output_files_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_user_id
                ON screenplay_projects(user_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_status
                ON screenplay_projects(status)
            """)

            logger.info(f"Screenplay database initialized at {self.db_path}")

    def create(self, project: ScreenplayProject) -> ScreenplayProject:
        """Create a new project"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO screenplay_projects (
                    id, user_id, title, source_type, language, tier, video_provider,
                    status, current_phase, progress_percent, error_message,
                    source_text, source_file_path, story_analysis_json, screenplay_json,
                    estimated_cost_usd, actual_cost_usd, output_files_json,
                    created_at, updated_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.id,
                project.user_id,
                project.title,
                project.source_type,
                project.language.value,
                project.tier.value,
                project.video_provider.value if project.video_provider else None,
                project.status.value,
                project.current_phase,
                project.progress_percent,
                project.error_message,
                project.source_text,
                project.source_file_path,
                json.dumps(project.story_analysis.to_dict()) if project.story_analysis else None,
                json.dumps(project.screenplay.to_dict()) if project.screenplay else None,
                project.estimated_cost_usd,
                project.actual_cost_usd,
                json.dumps(project.output_files),
                project.created_at.isoformat(),
                project.updated_at.isoformat(),
                project.completed_at.isoformat() if project.completed_at else None,
            ))

        logger.info(f"Created screenplay project: {project.id}")
        return project

    def get(self, project_id: str) -> Optional[ScreenplayProject]:
        """Get project by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM screenplay_projects WHERE id = ?",
                (project_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_project(row)

    def get_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[ScreenplayProject]:
        """Get all projects for a user"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM screenplay_projects
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset)).fetchall()

            return [self._row_to_project(row) for row in rows]

    def update(self, project: ScreenplayProject) -> ScreenplayProject:
        """Update an existing project"""
        project.updated_at = datetime.now()

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE screenplay_projects SET
                    title = ?,
                    source_type = ?,
                    language = ?,
                    tier = ?,
                    video_provider = ?,
                    status = ?,
                    current_phase = ?,
                    progress_percent = ?,
                    error_message = ?,
                    source_text = ?,
                    source_file_path = ?,
                    story_analysis_json = ?,
                    screenplay_json = ?,
                    estimated_cost_usd = ?,
                    actual_cost_usd = ?,
                    output_files_json = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE id = ?
            """, (
                project.title,
                project.source_type,
                project.language.value,
                project.tier.value,
                project.video_provider.value if project.video_provider else None,
                project.status.value,
                project.current_phase,
                project.progress_percent,
                project.error_message,
                project.source_text,
                project.source_file_path,
                json.dumps(project.story_analysis.to_dict()) if project.story_analysis else None,
                json.dumps(project.screenplay.to_dict()) if project.screenplay else None,
                project.estimated_cost_usd,
                project.actual_cost_usd,
                json.dumps(project.output_files),
                project.updated_at.isoformat(),
                project.completed_at.isoformat() if project.completed_at else None,
                project.id,
            ))

        logger.info(f"Updated screenplay project: {project.id}")
        return project

    def delete(self, project_id: str) -> bool:
        """Delete a project"""
        with self._get_connection() as conn:
            result = conn.execute(
                "DELETE FROM screenplay_projects WHERE id = ?",
                (project_id,)
            )
            deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Deleted screenplay project: {project_id}")

        return deleted

    def count_by_user(self, user_id: str) -> int:
        """Count projects for a user"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM screenplay_projects WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return row[0]

    def _row_to_project(self, row: sqlite3.Row) -> ScreenplayProject:
        """Convert database row to ScreenplayProject"""
        data = {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "source_type": row["source_type"],
            "language": row["language"],
            "tier": row["tier"],
            "video_provider": row["video_provider"],
            "status": row["status"],
            "current_phase": row["current_phase"],
            "progress_percent": row["progress_percent"],
            "error_message": row["error_message"],
            "source_text": row["source_text"] or "",
            "source_file_path": row["source_file_path"],
            "story_analysis": json.loads(row["story_analysis_json"]) if row["story_analysis_json"] else None,
            "screenplay": json.loads(row["screenplay_json"]) if row["screenplay_json"] else None,
            "estimated_cost_usd": row["estimated_cost_usd"],
            "actual_cost_usd": row["actual_cost_usd"],
            "output_files": json.loads(row["output_files_json"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
        }

        return ScreenplayProject.from_dict(data)
