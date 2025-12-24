"""
Batch Queue Manager
AI Publisher Pro - Batch Queue System

Manages document queue, scheduling, and processing.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
import threading
from queue import PriorityQueue
import json

from .batch_job import (
    BatchJob,
    JobStatus,
    JobPriority,
    JobProgress,
    BatchSummary,
    JobStore
)


@dataclass
class QueueConfig:
    """Queue configuration"""

    # Processing
    max_concurrent_jobs: int = 2          # Jobs processed simultaneously
    max_concurrent_pages: int = 10        # Pages per job

    # Retry
    max_retries: int = 3
    retry_delay_seconds: float = 5.0

    # Persistence
    auto_save: bool = True
    save_interval_seconds: float = 30.0
    storage_path: str = "./data/batch_queue.json"

    # Limits
    max_queue_size: int = 100
    max_pages_per_job: int = 1000

    # Cost limits
    max_cost_per_batch: float = 50.0      # Alert if batch > $50
    pause_on_cost_limit: bool = False


class BatchQueue:
    """
    Batch Queue Manager for processing multiple documents.

    Features:
    - Add/remove jobs
    - Priority queue
    - Parallel processing
    - Pause/resume/cancel
    - Progress tracking
    - Cost estimation
    - Persistence
    """

    def __init__(
        self,
        config: Optional[QueueConfig] = None,
        translation_service=None
    ):
        self.config = config or QueueConfig()
        self.translation_service = translation_service

        # Job storage
        self._store = JobStore(self.config.storage_path)

        # Queue (priority-based)
        self._queue: List[BatchJob] = []
        self._processing: Dict[str, BatchJob] = {}

        # State
        self._is_running = False
        self._is_paused = False
        self._lock = threading.Lock()

        # Event loop for async processing
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._worker_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_job_start: Optional[Callable[[BatchJob], None]] = None
        self.on_job_progress: Optional[Callable[[BatchJob], None]] = None
        self.on_job_complete: Optional[Callable[[BatchJob], None]] = None
        self.on_job_error: Optional[Callable[[BatchJob, str], None]] = None
        self.on_queue_empty: Optional[Callable[[], None]] = None

        # Load pending jobs from storage
        self._load_pending_jobs()

    def _load_pending_jobs(self):
        """Load pending jobs from storage"""
        for job in self._store.get_all():
            if job.status in [JobStatus.PENDING, JobStatus.PAUSED]:
                self._queue.append(job)
        self._sort_queue()

    def _sort_queue(self):
        """Sort queue by priority and creation time"""
        self._queue.sort(
            key=lambda j: (-j.priority.value, j.created_at)
        )

    # =========================================
    # Job Management
    # =========================================

    def add_job(
        self,
        input_path: str,
        source_lang: str = "Chinese",
        target_lang: str = "Vietnamese",
        translation_mode: str = "balanced",
        output_format: str = "docx",
        priority: JobPriority = JobPriority.NORMAL,
        name: Optional[str] = None
    ) -> BatchJob:
        """
        Add a new job to the queue.

        Args:
            input_path: Path to PDF or image folder
            source_lang: Source language
            target_lang: Target language
            translation_mode: economy, balanced, quality
            output_format: docx, pdf, txt, md
            priority: Job priority
            name: Optional job name

        Returns:
            Created BatchJob
        """
        if len(self._queue) >= self.config.max_queue_size:
            raise ValueError(f"Queue full (max {self.config.max_queue_size} jobs)")

        # Determine input type
        path = Path(input_path)
        if path.is_file() and path.suffix.lower() == ".pdf":
            input_type = "pdf"
        elif path.is_dir():
            input_type = "folder"
        else:
            input_type = "images"

        # Create job
        job = BatchJob(
            name=name or path.stem,
            input_path=str(path.absolute()),
            input_type=input_type,
            source_lang=source_lang,
            target_lang=target_lang,
            translation_mode=translation_mode,
            output_format=output_format,
            priority=priority,
            max_retries=self.config.max_retries
        )

        # Set callbacks
        job.on_progress = self._handle_job_progress
        job.on_complete = self._handle_job_complete
        job.on_error = self._handle_job_error

        # Add to queue and storage
        with self._lock:
            self._queue.append(job)
            self._sort_queue()
            self._store.add(job)

        return job

    def add_jobs(self, paths: List[str], **kwargs) -> List[BatchJob]:
        """Add multiple jobs at once"""
        jobs = []
        for path in paths:
            try:
                job = self.add_job(path, **kwargs)
                jobs.append(job)
            except Exception as e:
                print(f"Error adding job for {path}: {e}")
        return jobs

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from queue"""
        with self._lock:
            # Check if processing
            if job_id in self._processing:
                return False  # Can't remove processing job

            # Remove from queue
            self._queue = [j for j in self._queue if j.id != job_id]
            self._store.remove(job_id)
            return True

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID"""
        # Check processing
        if job_id in self._processing:
            return self._processing[job_id]

        # Check queue
        for job in self._queue:
            if job.id == job_id:
                return job

        # Check storage
        return self._store.get(job_id)

    def get_all_jobs(self) -> List[BatchJob]:
        """Get all jobs (queue + processing)"""
        return self._queue + list(self._processing.values())

    def get_queue(self) -> List[BatchJob]:
        """Get queued jobs"""
        return self._queue.copy()

    def get_processing(self) -> List[BatchJob]:
        """Get currently processing jobs"""
        return list(self._processing.values())

    # =========================================
    # Job Control
    # =========================================

    def pause_job(self, job_id: str) -> bool:
        """Pause a specific job"""
        job = self.get_job(job_id)
        if job and job.status == JobStatus.PROCESSING:
            job.update_status(JobStatus.PAUSED)
            self._store.update(job)
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        job = self.get_job(job_id)
        if job and job.status == JobStatus.PAUSED:
            job.update_status(JobStatus.PENDING)
            self._store.update(job)
            return True
        return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.get_job(job_id)
        if job:
            job.update_status(JobStatus.CANCELLED)

            # Remove from processing if needed
            if job_id in self._processing:
                del self._processing[job_id]

            # Remove from queue
            self._queue = [j for j in self._queue if j.id != job_id]
            self._store.update(job)
            return True
        return False

    def retry_job(self, job_id: str) -> bool:
        """Retry a failed job"""
        job = self.get_job(job_id)
        if job and job.status == JobStatus.FAILED and job.can_retry():
            job.retry_count += 1
            job.update_status(JobStatus.PENDING)
            job.error_message = None

            with self._lock:
                self._queue.append(job)
                self._sort_queue()

            self._store.update(job)
            return True
        return False

    def set_priority(self, job_id: str, priority: JobPriority) -> bool:
        """Change job priority"""
        job = self.get_job(job_id)
        if job and job.status == JobStatus.PENDING:
            job.priority = priority
            self._sort_queue()
            self._store.update(job)
            return True
        return False

    # =========================================
    # Queue Control
    # =========================================

    def start(self):
        """Start processing the queue"""
        if self._is_running:
            return

        self._is_running = True
        self._is_paused = False

        # Start worker in background
        self._loop = asyncio.new_event_loop()
        self._worker_thread = threading.Thread(
            target=self._run_worker,
            daemon=True
        )
        self._worker_thread.start()

    def stop(self):
        """Stop processing (gracefully)"""
        self._is_running = False

        # Wait for current jobs to complete
        if hasattr(self, '_worker_thread') and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)

    def pause(self):
        """Pause queue processing"""
        self._is_paused = True

    def resume(self):
        """Resume queue processing"""
        self._is_paused = False

    def clear(self, include_processing: bool = False):
        """Clear the queue"""
        with self._lock:
            # Cancel queued jobs
            for job in self._queue:
                job.update_status(JobStatus.CANCELLED)
                self._store.update(job)
            self._queue.clear()

            # Optionally cancel processing jobs
            if include_processing:
                for job in self._processing.values():
                    job.update_status(JobStatus.CANCELLED)
                    self._store.update(job)
                self._processing.clear()

    # =========================================
    # Worker
    # =========================================

    def _run_worker(self):
        """Run the worker loop"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._worker_loop())

    async def _worker_loop(self):
        """Main worker loop"""
        while self._is_running:
            # Check if paused
            if self._is_paused:
                await asyncio.sleep(1)
                continue

            # Check if can process more jobs
            if len(self._processing) >= self.config.max_concurrent_jobs:
                await asyncio.sleep(0.5)
                continue

            # Get next job from queue
            job = self._get_next_job()
            if not job:
                # Queue empty
                if self.on_queue_empty and len(self._processing) == 0:
                    self.on_queue_empty()
                await asyncio.sleep(1)
                continue

            # Start processing job
            asyncio.create_task(self._process_job(job))

        # Cleanup
        if self._loop:
            self._loop.stop()

    def _get_next_job(self) -> Optional[BatchJob]:
        """Get next job from queue"""
        with self._lock:
            for i, job in enumerate(self._queue):
                if job.status == JobStatus.PENDING:
                    self._queue.pop(i)
                    self._processing[job.id] = job
                    return job
        return None

    async def _process_job(self, job: BatchJob):
        """Process a single job"""
        try:
            # Update status
            job.update_status(JobStatus.PREPARING)
            self._store.update(job)

            if self.on_job_start:
                self.on_job_start(job)

            # Import processing functions
            from .batch_worker import process_document_job

            # Process the document
            await process_document_job(
                job=job,
                translation_service=self.translation_service,
                max_concurrent=self.config.max_concurrent_pages,
                on_progress=lambda j: self._handle_job_progress(j)
            )

            # Mark complete
            job.update_status(JobStatus.COMPLETED)
            self._store.update(job)

            if self.on_job_complete:
                self.on_job_complete(job)

        except Exception as e:
            error_msg = str(e)
            job.update_status(JobStatus.FAILED, error=error_msg)
            self._store.update(job)

            if self.on_job_error:
                self.on_job_error(job, error_msg)

            # Auto-retry if possible
            if job.can_retry():
                await asyncio.sleep(self.config.retry_delay_seconds)
                self.retry_job(job.id)

        finally:
            # Remove from processing
            with self._lock:
                if job.id in self._processing:
                    del self._processing[job.id]

    def _handle_job_progress(self, job: BatchJob):
        """Handle job progress update"""
        self._store.update(job)
        if self.on_job_progress:
            self.on_job_progress(job)

    def _handle_job_complete(self, job: BatchJob):
        """Handle job completion"""
        self._store.update(job)

    def _handle_job_error(self, job: BatchJob, error: str):
        """Handle job error"""
        self._store.update(job)

    # =========================================
    # Status & Summary
    # =========================================

    def get_summary(self) -> BatchSummary:
        """Get queue summary"""
        all_jobs = self.get_all_jobs() + self._store.get_by_status(JobStatus.COMPLETED)

        summary = BatchSummary()
        summary.total_jobs = len(all_jobs)

        for job in all_jobs:
            # Count by status
            if job.status == JobStatus.PENDING:
                summary.pending_jobs += 1
            elif job.status == JobStatus.PROCESSING:
                summary.processing_jobs += 1
            elif job.status == JobStatus.COMPLETED:
                summary.completed_jobs += 1
            elif job.status == JobStatus.FAILED:
                summary.failed_jobs += 1

            # Pages
            summary.total_pages += job.progress.total_pages
            summary.completed_pages += job.progress.completed_pages

            # Cost
            summary.total_cost += job.progress.cost_incurred

            # Remaining time
            summary.estimated_remaining_time += job.progress.estimated_remaining_seconds

        return summary

    def get_status(self) -> Dict[str, Any]:
        """Get queue status"""
        summary = self.get_summary()
        return {
            "is_running": self._is_running,
            "is_paused": self._is_paused,
            "queue_size": len(self._queue),
            "processing_count": len(self._processing),
            "summary": summary.to_dict()
        }

    # =========================================
    # Cost Estimation
    # =========================================

    def estimate_batch_cost(self) -> Dict[str, float]:
        """Estimate total batch cost"""
        total_pages = 0

        for job in self._queue:
            # Estimate pages if not known
            if job.progress.total_pages == 0:
                # Rough estimate based on file size
                path = Path(job.input_path)
                if path.exists():
                    size_mb = path.stat().st_size / (1024 * 1024)
                    estimated_pages = int(size_mb * 10)  # ~10 pages per MB
                    total_pages += estimated_pages
            else:
                remaining = job.progress.total_pages - job.progress.completed_pages
                total_pages += remaining

        # Cost per page by mode
        cost_per_page = {
            "economy": 0.001,
            "balanced": 0.004,
            "quality": 0.05
        }

        # Calculate by mode
        estimates = {"total": 0}
        for job in self._queue:
            mode = job.translation_mode
            pages = job.progress.total_pages or 50  # Default estimate
            cost = pages * cost_per_page.get(mode, 0.004)
            estimates[mode] = estimates.get(mode, 0) + cost
            estimates["total"] += cost

        return estimates


# =========================================
# Convenience Functions
# =========================================

def create_batch_queue(
    translation_service=None,
    max_concurrent_jobs: int = 2,
    storage_path: str = "./data/batch_queue.json"
) -> BatchQueue:
    """Create a batch queue with default settings"""
    config = QueueConfig(
        max_concurrent_jobs=max_concurrent_jobs,
        storage_path=storage_path
    )
    return BatchQueue(config=config, translation_service=translation_service)
