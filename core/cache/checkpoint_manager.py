#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Checkpoint Manager - Fault-tolerant job state persistence

Phase 5.2: Allows translation jobs to resume from last saved state after interruption.
Stores completed chunk IDs and translation results in SQLite for crash recovery.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class CheckpointState:
    """Represents a saved checkpoint state for resume"""
    job_id: str
    input_file: str
    output_file: str
    total_chunks: int
    completed_chunk_ids: List[str]  # IDs of chunks already translated
    results_data: Dict[str, Any]  # Map of chunk_id -> serialized TranslationResult
    job_metadata: Dict[str, Any]
    created_at: float
    updated_at: float

    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_chunks == 0:
            return 0.0
        return len(self.completed_chunk_ids) / self.total_chunks

    def remaining_chunks(self) -> int:
        """Calculate remaining chunks"""
        return self.total_chunks - len(self.completed_chunk_ids)


class CheckpointManager:
    """
    Manages fault-tolerant checkpoints for translation jobs

    Features:
    - SQLite-based persistent storage
    - Thread-safe operations
    - Automatic state serialization/deserialization
    - Resume capability after crashes/interruptions
    """

    def __init__(self, db_path: Path):
        """
        Initialize checkpoint manager

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    job_id TEXT PRIMARY KEY,
                    input_file TEXT NOT NULL,
                    output_file TEXT NOT NULL,
                    total_chunks INTEGER NOT NULL,
                    completed_chunk_ids TEXT NOT NULL,  -- JSON array
                    results_data TEXT NOT NULL,  -- JSON object
                    job_metadata TEXT,  -- JSON object
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated_at
                ON checkpoints(updated_at)
            """)
            conn.commit()

    def save_checkpoint(
        self,
        job_id: str,
        input_file: str,
        output_file: str,
        total_chunks: int,
        completed_chunk_ids: List[str],
        results_data: Dict[str, Any],
        job_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save or update checkpoint state

        Args:
            job_id: Unique job identifier
            input_file: Path to input file
            output_file: Path to output file
            total_chunks: Total number of chunks in job
            completed_chunk_ids: List of chunk IDs that have been completed
            results_data: Map of chunk_id -> translation result dict
            job_metadata: Optional metadata dict
        """
        now = time.time()

        with sqlite3.connect(self.db_path) as conn:
            # Check if checkpoint exists
            cursor = conn.execute(
                "SELECT created_at FROM checkpoints WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            created_at = row[0] if row else now

            # Insert or replace
            conn.execute("""
                INSERT OR REPLACE INTO checkpoints (
                    job_id, input_file, output_file, total_chunks,
                    completed_chunk_ids, results_data, job_metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                input_file,
                output_file,
                total_chunks,
                json.dumps(completed_chunk_ids),
                json.dumps(results_data),
                json.dumps(job_metadata or {}),
                created_at,
                now
            ))
            conn.commit()

    def load_checkpoint(self, job_id: str) -> Optional[CheckpointState]:
        """
        Load checkpoint state for a job

        Args:
            job_id: Job identifier

        Returns:
            CheckpointState if checkpoint exists, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    job_id, input_file, output_file, total_chunks,
                    completed_chunk_ids, results_data, job_metadata,
                    created_at, updated_at
                FROM checkpoints
                WHERE job_id = ?
            """, (job_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # FIX-003: Handle both INT and STRING chunk IDs
            # JSON dict keys are always strings, convert to int if numeric
            raw_results_data = json.loads(row[5])
            results_data_fixed_keys = {
                int(k) if k.isdigit() else k: v
                for k, v in raw_results_data.items()
            }

            return CheckpointState(
                job_id=row[0],
                input_file=row[1],
                output_file=row[2],
                total_chunks=row[3],
                completed_chunk_ids=json.loads(row[4]),  # Array keeps original type
                results_data=results_data_fixed_keys,  # Dict keys fixed
                job_metadata=json.loads(row[6]) if row[6] else {},
                created_at=row[7],
                updated_at=row[8]
            )

    def has_checkpoint(self, job_id: str) -> bool:
        """
        Check if checkpoint exists for job

        Args:
            job_id: Job identifier

        Returns:
            True if checkpoint exists
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM checkpoints WHERE job_id = ? LIMIT 1",
                (job_id,)
            )
            return cursor.fetchone() is not None

    def delete_checkpoint(self, job_id: str) -> bool:
        """
        Delete checkpoint for completed job

        Args:
            job_id: Job identifier

        Returns:
            True if checkpoint was deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM checkpoints WHERE job_id = ?",
                (job_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_checkpoints(self, limit: int = 100) -> List[CheckpointState]:
        """
        List all saved checkpoints

        Args:
            limit: Maximum number of checkpoints to return

        Returns:
            List of CheckpointState objects, sorted by updated_at desc
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    job_id, input_file, output_file, total_chunks,
                    completed_chunk_ids, results_data, job_metadata,
                    created_at, updated_at
                FROM checkpoints
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))

            checkpoints = []
            for row in cursor.fetchall():
                # FIX-003: Handle both INT and STRING chunk IDs
                raw_results_data = json.loads(row[5])
                results_data_fixed_keys = {
                    int(k) if k.isdigit() else k: v
                    for k, v in raw_results_data.items()
                }

                checkpoints.append(CheckpointState(
                    job_id=row[0],
                    input_file=row[1],
                    output_file=row[2],
                    total_chunks=row[3],
                    completed_chunk_ids=json.loads(row[4]),  # Array keeps original type
                    results_data=results_data_fixed_keys,  # Dict keys fixed
                    job_metadata=json.loads(row[6]) if row[6] else {},
                    created_at=row[7],
                    updated_at=row[8]
                ))

            return checkpoints

    def get_resume_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get resume information for a job

        Args:
            job_id: Job identifier

        Returns:
            Dict with resume info or None if no checkpoint
        """
        checkpoint = self.load_checkpoint(job_id)
        if not checkpoint:
            return None

        return {
            'job_id': checkpoint.job_id,
            'total_chunks': checkpoint.total_chunks,
            'completed_chunks': len(checkpoint.completed_chunk_ids),
            'remaining_chunks': checkpoint.remaining_chunks(),
            'completion_percentage': checkpoint.completion_percentage(),
            'last_updated': datetime.fromtimestamp(checkpoint.updated_at).isoformat(),
            'can_resume': checkpoint.remaining_chunks() > 0
        }

    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """
        Delete checkpoints older than specified days

        Args:
            days: Delete checkpoints older than this many days

        Returns:
            Number of checkpoints deleted
        """
        cutoff_time = time.time() - (days * 86400)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM checkpoints WHERE updated_at < ?",
                (cutoff_time,)
            )
            conn.commit()
            return cursor.rowcount

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get checkpoint database statistics

        Returns:
            Dict with stats
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_checkpoints,
                    AVG(CAST(LENGTH(completed_chunk_ids) - LENGTH(REPLACE(completed_chunk_ids, ',', '')) + 1 AS FLOAT) / total_chunks) as avg_completion,
                    SUM(total_chunks) as total_chunks_all_jobs
                FROM checkpoints
            """)
            row = cursor.fetchone()

            return {
                'total_checkpoints': row[0] or 0,
                'avg_completion_rate': row[1] or 0.0,
                'total_chunks_tracked': row[2] or 0,
                'db_size_bytes': self.db_path.stat().st_size if self.db_path.exists() else 0
            }


def deserialize_translation_result(data: Dict[str, Any]) -> Any:
    """
    Deserialize translation result from checkpoint data

    Args:
        data: Serialized result dict

    Returns:
        TranslationResult object
    """
    # Import here to avoid circular dependency
    from core.validator import TranslationResult

    return TranslationResult(
        chunk_id=data.get('chunk_id', ''),
        source=data.get('source', ''),
        translated=data.get('translated', ''),
        quality_score=data.get('quality_score', 0.0),
        warnings=data.get('warnings', [])
    )


def serialize_translation_result(result: Any) -> Dict[str, Any]:
    """
    Serialize translation result for checkpoint storage

    Args:
        result: TranslationResult object

    Returns:
        Serializable dict
    """
    return {
        'chunk_id': result.chunk_id,
        'source': result.source,
        'translated': result.translated,
        'quality_score': result.quality_score,
        'warnings': result.warnings
    }
