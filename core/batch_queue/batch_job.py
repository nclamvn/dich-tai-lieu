"""
Batch Job Definitions
AI Publisher Pro - Batch Queue System

Defines job structure, status, and tracking.
"""

import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json


class JobStatus(Enum):
    """Job status states"""
    PENDING = "pending"           # In queue, waiting
    PREPARING = "preparing"       # Extracting pages, analyzing
    PROCESSING = "processing"     # Translating
    PAUSED = "paused"            # Paused by user
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"            # Error occurred
    CANCELLED = "cancelled"       # Cancelled by user


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class JobProgress:
    """Tracks job progress"""
    total_pages: int = 0
    completed_pages: int = 0
    failed_pages: int = 0
    current_page: int = 0

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_remaining_seconds: float = 0

    # Cost tracking
    tokens_used: int = 0
    cost_incurred: float = 0.0

    @property
    def progress_percent(self) -> float:
        if self.total_pages == 0:
            return 0.0
        return (self.completed_pages / self.total_pages) * 100

    @property
    def elapsed_seconds(self) -> float:
        if not self.started_at:
            return 0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def pages_per_minute(self) -> float:
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0
        return (self.completed_pages / elapsed) * 60

    def to_dict(self) -> Dict:
        return {
            "total_pages": self.total_pages,
            "completed_pages": self.completed_pages,
            "failed_pages": self.failed_pages,
            "current_page": self.current_page,
            "progress_percent": round(self.progress_percent, 1),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "estimated_remaining_seconds": round(self.estimated_remaining_seconds, 1),
            "pages_per_minute": round(self.pages_per_minute, 1),
            "tokens_used": self.tokens_used,
            "cost_incurred": round(self.cost_incurred, 4),
        }


@dataclass
class BatchJob:
    """
    Represents a single translation job in the queue.
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""

    # Input
    input_path: str = ""                    # PDF or folder path
    input_type: str = "pdf"                 # pdf, images, folder

    # Translation settings
    source_lang: str = "Chinese"
    target_lang: str = "Vietnamese"
    translation_mode: str = "balanced"      # economy, balanced, quality

    # Output
    output_dir: str = ""
    output_format: str = "docx"             # docx, pdf, txt, md

    # Status
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    progress: JobProgress = field(default_factory=JobProgress)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Results
    output_path: Optional[str] = None
    translations: List[str] = field(default_factory=list)

    # Callbacks
    on_progress: Optional[Callable] = field(default=None, repr=False)
    on_complete: Optional[Callable] = field(default=None, repr=False)
    on_error: Optional[Callable] = field(default=None, repr=False)

    def __post_init__(self):
        if not self.name:
            self.name = Path(self.input_path).stem if self.input_path else f"Job-{self.id}"
        if not self.output_dir:
            self.output_dir = str(Path(self.input_path).parent / "output") if self.input_path else "./output"

    def update_status(self, status: JobStatus, error: Optional[str] = None):
        """Update job status"""
        self.status = status
        self.updated_at = datetime.now()

        if status == JobStatus.PROCESSING and not self.progress.started_at:
            self.progress.started_at = datetime.now()

        if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            self.progress.completed_at = datetime.now()

        if error:
            self.error_message = error

    def update_progress(
        self,
        completed_pages: Optional[int] = None,
        current_page: Optional[int] = None,
        tokens: Optional[int] = None,
        cost: Optional[float] = None
    ):
        """Update job progress"""
        if completed_pages is not None:
            self.progress.completed_pages = completed_pages
        if current_page is not None:
            self.progress.current_page = current_page
        if tokens is not None:
            self.progress.tokens_used += tokens
        if cost is not None:
            self.progress.cost_incurred += cost

        # Estimate remaining time
        if self.progress.completed_pages > 0:
            rate = self.progress.elapsed_seconds / self.progress.completed_pages
            remaining = self.progress.total_pages - self.progress.completed_pages
            self.progress.estimated_remaining_seconds = rate * remaining

        self.updated_at = datetime.now()

        # Trigger callback
        if self.on_progress:
            self.on_progress(self)

    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.retry_count < self.max_retries

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "input_path": self.input_path,
            "input_type": self.input_type,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "translation_mode": self.translation_mode,
            "output_dir": self.output_dir,
            "output_format": self.output_format,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": self.progress.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "output_path": self.output_path,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BatchJob":
        """Create from dictionary"""
        job = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            input_path=data.get("input_path", ""),
            input_type=data.get("input_type", "pdf"),
            source_lang=data.get("source_lang", "Chinese"),
            target_lang=data.get("target_lang", "Vietnamese"),
            translation_mode=data.get("translation_mode", "balanced"),
            output_dir=data.get("output_dir", ""),
            output_format=data.get("output_format", "docx"),
            status=JobStatus(data.get("status", "pending")),
            priority=JobPriority(data.get("priority", 2)),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            output_path=data.get("output_path"),
        )

        # Restore progress
        if "progress" in data:
            p = data["progress"]
            job.progress.total_pages = p.get("total_pages", 0)
            job.progress.completed_pages = p.get("completed_pages", 0)
            job.progress.failed_pages = p.get("failed_pages", 0)
            job.progress.tokens_used = p.get("tokens_used", 0)
            job.progress.cost_incurred = p.get("cost_incurred", 0.0)

        # Restore timestamps
        if "created_at" in data:
            job.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            job.updated_at = datetime.fromisoformat(data["updated_at"])

        return job


@dataclass
class BatchSummary:
    """Summary of batch queue status"""
    total_jobs: int = 0
    pending_jobs: int = 0
    processing_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0

    total_pages: int = 0
    completed_pages: int = 0

    total_cost: float = 0.0
    estimated_remaining_cost: float = 0.0

    estimated_remaining_time: float = 0.0  # seconds

    def to_dict(self) -> Dict:
        return {
            "total_jobs": self.total_jobs,
            "pending_jobs": self.pending_jobs,
            "processing_jobs": self.processing_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "total_pages": self.total_pages,
            "completed_pages": self.completed_pages,
            "progress_percent": round(
                (self.completed_pages / self.total_pages * 100) if self.total_pages > 0 else 0,
                1
            ),
            "total_cost": round(self.total_cost, 4),
            "estimated_remaining_cost": round(self.estimated_remaining_cost, 4),
            "estimated_remaining_time": round(self.estimated_remaining_time, 0),
            "estimated_remaining_minutes": round(self.estimated_remaining_time / 60, 1),
        }


# =========================================
# Job Persistence
# =========================================

class JobStore:
    """Persistent storage for jobs"""

    def __init__(self, storage_path: str = "./data/batch_jobs.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, BatchJob] = {}
        self._load()

    def _load(self):
        """Load jobs from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for job_data in data.get("jobs", []):
                        job = BatchJob.from_dict(job_data)
                        self._jobs[job.id] = job
            except Exception as e:
                print(f"Error loading jobs: {e}")

    def _save(self):
        """Save jobs to storage"""
        try:
            data = {
                "jobs": [job.to_dict() for job in self._jobs.values()],
                "updated_at": datetime.now().isoformat()
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving jobs: {e}")

    def add(self, job: BatchJob):
        """Add job to store"""
        self._jobs[job.id] = job
        self._save()

    def get(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID"""
        return self._jobs.get(job_id)

    def update(self, job: BatchJob):
        """Update job in store"""
        if job.id in self._jobs:
            self._jobs[job.id] = job
            self._save()

    def remove(self, job_id: str):
        """Remove job from store"""
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._save()

    def get_all(self) -> List[BatchJob]:
        """Get all jobs"""
        return list(self._jobs.values())

    def get_by_status(self, status: JobStatus) -> List[BatchJob]:
        """Get jobs by status"""
        return [j for j in self._jobs.values() if j.status == status]

    def clear_completed(self):
        """Clear completed and cancelled jobs"""
        to_remove = [
            job_id for job_id, job in self._jobs.items()
            if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]
        ]
        for job_id in to_remove:
            del self._jobs[job_id]
        self._save()
