# ═══════════════════════════════════════════════════════════════════
# FILE: api/book_writer_repository.py
# PURPOSE: SQLite CRUD for book projects with JSON serialization
# ═══════════════════════════════════════════════════════════════════

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

from .book_writer_models import BookProject, BookListItem, BookStatus

logger = logging.getLogger("book_writer.repository")


class BookWriterRepository:
    """SQLite-based persistence for book writer projects."""

    def __init__(self, db_path: str = "data/book_writer.db"):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if not exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS book_projects (
                    id TEXT PRIMARY KEY,
                    data JSON NOT NULL,
                    status TEXT NOT NULL DEFAULT 'created',
                    title TEXT,
                    input_mode TEXT,
                    total_words INTEGER DEFAULT 0,
                    chapter_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_book_status
                ON book_projects(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_book_updated
                ON book_projects(updated_at DESC)
            """)
            conn.commit()

    def save_project(self, project: BookProject):
        """Insert or update a book project."""
        # Get title from blueprint
        title = None
        if project.blueprint:
            bp = project.blueprint if isinstance(project.blueprint, dict) else project.blueprint.dict()
            title = bp.get("title")
        if not title and project.request:
            title = project.request.title

        # Count words and chapters
        total_words = 0
        ch_count = 0
        if project.chapters:
            ch_count = len(project.chapters)
            for ch in project.chapters:
                ch_data = ch if isinstance(ch, dict) else ch.dict()
                total_words += ch_data.get("word_count", 0)

        # Serialize to JSON
        data = project.model_dump_json()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO book_projects (id, data, status, title, input_mode,
                                          total_words, chapter_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data = excluded.data,
                    status = excluded.status,
                    title = excluded.title,
                    total_words = excluded.total_words,
                    chapter_count = excluded.chapter_count,
                    updated_at = excluded.updated_at
            """, (
                project.id,
                data,
                project.status.value,
                title,
                project.request.input_mode.value if project.request else None,
                total_words,
                ch_count,
                project.created_at.isoformat(),
                project.updated_at.isoformat(),
            ))
            conn.commit()

    def get_project(self, book_id: str) -> Optional[BookProject]:
        """Load a book project by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM book_projects WHERE id = ?", (book_id,)
            ).fetchone()

        if not row:
            return None

        try:
            return BookProject.model_validate_json(row[0])
        except Exception as e:
            logger.error(f"Failed to load project {book_id}: {e}")
            return None

    def list_projects(self, limit: int = 20, offset: int = 0) -> list[BookListItem]:
        """List projects ordered by updated_at desc."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT id, title, status, input_mode, chapter_count,
                       total_words, created_at, updated_at
                FROM book_projects
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()

        items = []
        for row in rows:
            try:
                items.append(BookListItem(
                    id=row[0],
                    title=row[1],
                    status=BookStatus(row[2]),
                    input_mode=row[3] or "seeds",
                    chapter_count=row[4] or 0,
                    total_words=row[5] or 0,
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                ))
            except Exception as e:
                logger.warning(f"Skipping invalid project row: {e}")

        return items

    def list_stalled_projects(self) -> list[BookListItem]:
        """Find projects stuck in non-terminal pipeline states (for resume on startup)."""
        stalled_statuses = (
            "analyzing", "analysis_ready", "architecting", "outlining",
            "writing", "enriching", "editing", "compiling",
        )
        placeholders = ",".join("?" for _ in stalled_statuses)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(f"""
                SELECT id, title, status, input_mode, chapter_count,
                       total_words, created_at, updated_at
                FROM book_projects
                WHERE status IN ({placeholders})
                ORDER BY updated_at DESC
            """, stalled_statuses).fetchall()

        items = []
        for row in rows:
            try:
                items.append(BookListItem(
                    id=row[0],
                    title=row[1],
                    status=BookStatus(row[2]),
                    input_mode=row[3] or "seeds",
                    chapter_count=row[4] or 0,
                    total_words=row[5] or 0,
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                ))
            except Exception as e:
                logger.warning(f"Skipping invalid stalled row: {e}")
        return items

    def delete_project(self, book_id: str) -> bool:
        """Delete a project."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM book_projects WHERE id = ?", (book_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
