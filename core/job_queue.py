#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Job Queue System - SQLite-based batch processing with priority scheduling

A lightweight, file-based job queue system for managing translation tasks.
No external dependencies like Redis or Celery required.
"""

import sqlite3
import json
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections.abc import Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import asyncio


class JobStatus(str, Enum):
    """Job status states"""
    PENDING = "pending"           # Job created, waiting to start
    QUEUED = "queued"            # Job in queue, ready to process
    RUNNING = "running"          # Currently processing
    PAUSED = "paused"            # Temporarily paused
    COMPLETED = "completed"      # Successfully completed
    FAILED = "failed"            # Failed with errors
    CANCELLED = "cancelled"      # Cancelled by user
    RETRYING = "retrying"        # Failed, will retry


class JobPriority(int, Enum):
    """Job priority levels (higher number = higher priority)"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20
    CRITICAL = 50


@dataclass
class TranslationJob:
    """A translation job with all metadata"""

    # Identification
    job_id: str
    job_name: str

    # Input/Output
    input_file: str
    output_file: str
    input_format: str = "txt"
    output_format: str = "txt"

    # Translation config
    source_lang: str = "en"
    target_lang: str = "vi"
    domain: Optional[str] = None
    glossary: Optional[str] = None

    # Processing config
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    concurrency: int = 5
    chunk_size: int = 3000

    # Priority & scheduling
    priority: int = JobPriority.NORMAL
    scheduled_at: Optional[float] = None  # Unix timestamp for scheduled jobs

    # Status & progress
    status: str = JobStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunks: int = 0

    # Quality & stats
    avg_quality_score: float = 0.0
    total_cost_usd: float = 0.0
    tm_hits: int = 0
    cache_hits: int = 0

    # Timestamps
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    updated_at: float = field(default_factory=time.time)

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Cancellation support
    cancellation_requested: bool = False

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert enums to values
        if isinstance(data.get('status'), Enum):
            data['status'] = data['status'].value
        if isinstance(data.get('priority'), Enum):
            data['priority'] = data['priority'].value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'TranslationJob':
        """Create from dictionary"""
        # Handle enum fields
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = data['status']
        if 'priority' in data and isinstance(data['priority'], int):
            data['priority'] = data['priority']
        return cls(**data)

    def update_progress(self, completed: int, total: int):
        """Update job progress"""
        self.completed_chunks = completed
        self.total_chunks = total
        if total > 0:
            self.progress = completed / total
        self.updated_at = time.time()

    def mark_started(self):
        """Mark job as started"""
        self.status = JobStatus.RUNNING
        self.started_at = time.time()
        self.updated_at = time.time()

    def mark_completed(self, avg_quality: float = 0.0, total_cost: float = 0.0):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED
        self.progress = 1.0
        self.completed_at = time.time()
        self.updated_at = time.time()
        self.avg_quality_score = avg_quality
        self.total_cost_usd = total_cost

    def mark_failed(self, error: str):
        """Mark job as failed"""
        self.status = JobStatus.FAILED
        self.error_message = error
        self.completed_at = time.time()
        self.updated_at = time.time()

    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.retry_count < self.max_retries

    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1
        self.status = JobStatus.RETRYING
        self.updated_at = time.time()

    def request_cancellation(self):
        """Request cancellation of this job"""
        self.cancellation_requested = True
        self.updated_at = time.time()

    def mark_cancelled(self):
        """Mark job as cancelled"""
        self.status = JobStatus.CANCELLED
        self.error_message = "Cancelled by user"
        self.completed_at = time.time()
        self.updated_at = time.time()


class JobQueue:
    """SQLite-based job queue with priority scheduling"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize job queue

        Args:
            db_path: Path to SQLite database (default: data/jobs.db)
        """
        if db_path is None:
            from config.settings import BASE_DIR
            db_path = BASE_DIR / "data" / "jobs.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)

        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                job_name TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 5,

                -- Input/Output
                input_file TEXT NOT NULL,
                output_file TEXT NOT NULL,
                input_format TEXT DEFAULT 'txt',
                output_format TEXT DEFAULT 'txt',

                -- Translation config
                source_lang TEXT DEFAULT 'en',
                target_lang TEXT DEFAULT 'vi',
                domain TEXT,
                glossary TEXT,

                -- Processing config
                provider TEXT DEFAULT 'openai',
                model TEXT DEFAULT 'gpt-4o-mini',
                concurrency INTEGER DEFAULT 5,
                chunk_size INTEGER DEFAULT 3000,

                -- Progress
                progress REAL DEFAULT 0.0,
                total_chunks INTEGER DEFAULT 0,
                completed_chunks INTEGER DEFAULT 0,
                failed_chunks INTEGER DEFAULT 0,

                -- Quality & stats
                avg_quality_score REAL DEFAULT 0.0,
                total_cost_usd REAL DEFAULT 0.0,
                tm_hits INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,

                -- Timestamps
                scheduled_at REAL,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                updated_at REAL NOT NULL,

                -- Error handling
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,

                -- Metadata (JSON)
                tags TEXT,
                metadata TEXT
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status_priority
            ON jobs(status, priority DESC, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON jobs(created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON jobs(status)
        """)

        conn.commit()
        conn.close()

    def create_job(
        self,
        job_name: str,
        input_file: str,
        output_file: str,
        source_lang: str = "en",
        target_lang: str = "vi",
        priority: int = JobPriority.NORMAL,
        **kwargs
    ) -> TranslationJob:
        """
        Create a new translation job

        Args:
            job_name: Human-readable job name
            input_file: Path to input file
            output_file: Path to output file
            source_lang: Source language code
            target_lang: Target language code
            priority: Job priority level
            **kwargs: Additional job parameters

        Returns:
            TranslationJob object
        """
        # Generate job ID
        job_id = self._generate_job_id(job_name, input_file)

        # Create job object
        job = TranslationJob(
            job_id=job_id,
            job_name=job_name,
            input_file=input_file,
            output_file=output_file,
            source_lang=source_lang,
            target_lang=target_lang,
            priority=priority,
            **kwargs
        )

        # Save to database
        self._save_job(job)

        return job

    def _generate_job_id(self, job_name: str, input_file: str) -> str:
        """Generate unique job ID"""
        timestamp = str(time.time())
        data = f"{job_name}:{input_file}:{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def _save_job(self, job: TranslationJob):
        """Save job to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO jobs (
                job_id, job_name, status, priority,
                input_file, output_file, input_format, output_format,
                source_lang, target_lang, domain, glossary,
                provider, model, concurrency, chunk_size,
                progress, total_chunks, completed_chunks, failed_chunks,
                avg_quality_score, total_cost_usd, tm_hits, cache_hits,
                scheduled_at, created_at, started_at, completed_at, updated_at,
                error_message, retry_count, max_retries,
                tags, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.job_id, job.job_name, job.status, job.priority,
            job.input_file, job.output_file, job.input_format, job.output_format,
            job.source_lang, job.target_lang, job.domain, job.glossary,
            job.provider, job.model, job.concurrency, job.chunk_size,
            job.progress, job.total_chunks, job.completed_chunks, job.failed_chunks,
            job.avg_quality_score, job.total_cost_usd, job.tm_hits, job.cache_hits,
            job.scheduled_at, job.created_at, job.started_at, job.completed_at, job.updated_at,
            job.error_message, job.retry_count, job.max_retries,
            json.dumps(job.tags), json.dumps(job.metadata)
        ))

        conn.commit()
        conn.close()

    def get_job(self, job_id: str) -> Optional[TranslationJob]:
        """Get job by ID (supports partial ID prefix matching)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try exact match first
        cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()

        # If not found and ID looks partial (< 12 chars), try prefix match
        if not row and len(job_id) < 12:
            cursor.execute(
                "SELECT * FROM jobs WHERE job_id LIKE ? LIMIT 1",
                (f"{job_id}%",)
            )
            row = cursor.fetchone()

        conn.close()

        if row:
            return self._row_to_job(row)
        return None

    def _row_to_job(self, row: sqlite3.Row) -> TranslationJob:
        """Convert database row to TranslationJob"""
        data = dict(row)

        # Parse JSON fields
        if data.get('tags'):
            data['tags'] = json.loads(data['tags'])
        else:
            data['tags'] = []

        if data.get('metadata'):
            data['metadata'] = json.loads(data['metadata'])
        else:
            data['metadata'] = {}

        return TranslationJob(**data)

    def update_job(self, job: TranslationJob):
        """Update job in database"""
        job.updated_at = time.time()
        self._save_job(job)

    def get_next_job(self) -> Optional[TranslationJob]:
        """
        Get next job to process based on priority and FIFO

        Returns:
            Next job or None if queue is empty
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get highest priority pending/retrying job (NOT queued - prevents race condition)
        cursor.execute("""
            SELECT * FROM jobs
            WHERE status IN ('pending', 'retrying')
            AND (scheduled_at IS NULL OR scheduled_at <= ?)
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        """, (time.time(),))

        row = cursor.fetchone()
        conn.close()

        if row:
            job = self._row_to_job(row)
            # Mark as queued immediately to prevent race condition
            job.status = JobStatus.QUEUED
            self.update_job(job)
            return job

        return None

    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TranslationJob]:
        """
        List jobs with optional filtering

        Args:
            status: Filter by status (None = all)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip

        Returns:
            List of jobs
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT * FROM jobs
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (status, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM jobs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_job(row) for row in rows]

    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM jobs
            GROUP BY status
        """)

        stats = {status: 0 for status in JobStatus}
        for status, count in cursor.fetchall():
            stats[status] = count

        # Total
        stats['total'] = sum(stats.values())

        conn.close()
        return stats

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.PAUSED]:
            job.status = JobStatus.CANCELLED
            job.updated_at = time.time()
            self.update_job(job)
            return True

        return False

    def delete_job(self, job_id: str) -> bool:
        """Delete a job (only if completed, failed, or cancelled)"""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            conn.commit()
            conn.close()
            return True

        return False

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Delete old completed/failed jobs

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of jobs deleted
        """
        cutoff_time = time.time() - (days * 86400)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM jobs
            WHERE status IN ('completed', 'failed', 'cancelled')
            AND completed_at < ?
        """, (cutoff_time,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted
