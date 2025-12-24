"""
Job lifecycle management.
Handles job state transitions, timing, and result tracking.

Phase 1.5: Extracted from batch_processor.py for maintainability.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from config.logging_config import get_logger
from config.constants import (
    BATCH_TIMEOUT_SECONDS,
    BATCH_MAX_RETRIES,
)

logger = get_logger(__name__)


class JobState(Enum):
    """Job execution state (more granular than JobStatus)."""
    INITIALIZING = "initializing"
    LOADING_INPUT = "loading_input"
    OCR_PROCESSING = "ocr_processing"
    PREPROCESSING = "preprocessing"
    CHUNKING = "chunking"
    TRANSLATING = "translating"
    MERGING = "merging"
    POSTPROCESSING = "postprocessing"
    EXPORTING = "exporting"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobResult:
    """Result of a completed job."""
    job_id: str
    success: bool
    output_path: Optional[Path] = None
    translated_text: Optional[str] = None
    chunk_count: int = 0
    total_chars: int = 0
    duration_seconds: float = 0.0
    quality_score: float = 0.0
    estimated_cost: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobTiming:
    """Timing information for job phases."""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    phase_times: Dict[str, float] = field(default_factory=dict)

    def start(self):
        """Mark job start."""
        self.started_at = datetime.now()

    def complete(self):
        """Mark job completion."""
        self.completed_at = datetime.now()

    @property
    def total_duration(self) -> Optional[float]:
        """Get total duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def record_phase(self, phase: str, duration: float):
        """Record duration for a phase."""
        self.phase_times[phase] = duration


class JobHandler:
    """
    Manages job lifecycle within batch processing.

    Responsibilities:
    - Track job state transitions
    - Collect timing information
    - Handle retries
    - Build final results

    Usage:
        handler = JobHandler(job)
        handler.start()

        handler.transition_to(JobState.LOADING_INPUT)
        # ... do work ...
        handler.transition_to(JobState.CHUNKING)
        # ... do work ...

        result = handler.complete(translated_text, quality_score)
    """

    def __init__(
        self,
        job_id: str,
        job_name: str = "",
        timeout: int = BATCH_TIMEOUT_SECONDS,
        max_retries: int = BATCH_MAX_RETRIES,
    ):
        """
        Initialize job handler.

        Args:
            job_id: Unique job identifier
            job_name: Human-readable job name
            timeout: Job timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.job_id = job_id
        self.job_name = job_name
        self.timeout = timeout
        self.max_retries = max_retries

        self.state = JobState.INITIALIZING
        self.timing = JobTiming()
        self.retry_count = 0
        self.error: Optional[str] = None

        self._phase_start: Optional[datetime] = None
        self._metadata: Dict[str, Any] = {}

        logger.debug(f"JobHandler created: {job_id}")

    def start(self):
        """Mark job as started."""
        self.timing.start()
        self._phase_start = datetime.now()
        logger.info(f"Job started: {self.job_id}")

    def transition_to(self, new_state: JobState):
        """
        Transition to a new state.

        Args:
            new_state: Target state
        """
        # Record duration of previous phase
        if self._phase_start:
            duration = (datetime.now() - self._phase_start).total_seconds()
            self.timing.record_phase(self.state.value, duration)

        old_state = self.state
        self.state = new_state
        self._phase_start = datetime.now()

        logger.debug(f"Job {self.job_id}: {old_state.value} → {new_state.value}")

    def add_metadata(self, key: str, value: Any):
        """Add metadata to job result."""
        self._metadata[key] = value

    def complete(
        self,
        output_path: Optional[Path] = None,
        translated_text: Optional[str] = None,
        chunk_count: int = 0,
        quality_score: float = 0.0,
        estimated_cost: float = 0.0,
    ) -> JobResult:
        """
        Complete job successfully.

        Args:
            output_path: Path to output file
            translated_text: Translated text content
            chunk_count: Number of chunks processed
            quality_score: Average quality score
            estimated_cost: Estimated cost in USD

        Returns:
            JobResult with all information
        """
        self.transition_to(JobState.COMPLETED)
        self.timing.complete()

        result = JobResult(
            job_id=self.job_id,
            success=True,
            output_path=output_path,
            translated_text=translated_text,
            chunk_count=chunk_count,
            total_chars=len(translated_text) if translated_text else 0,
            duration_seconds=self.timing.total_duration or 0.0,
            quality_score=quality_score,
            estimated_cost=estimated_cost,
            metadata=self._metadata.copy(),
        )

        logger.info(
            f"Job completed: {self.job_id} "
            f"({chunk_count} chunks, {result.duration_seconds:.1f}s, "
            f"quality={quality_score:.2f})"
        )

        return result

    def fail(self, error: str) -> JobResult:
        """
        Mark job as failed.

        Args:
            error: Error message

        Returns:
            JobResult with failure information
        """
        self.transition_to(JobState.FAILED)
        self.timing.complete()
        self.error = error

        result = JobResult(
            job_id=self.job_id,
            success=False,
            duration_seconds=self.timing.total_duration or 0.0,
            error_message=error,
            metadata=self._metadata.copy(),
        )

        logger.error(f"Job failed: {self.job_id} - {error}")

        return result

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.retry_count < self.max_retries

    def prepare_retry(self) -> bool:
        """
        Prepare job for retry.

        Returns:
            True if retry is possible, False otherwise
        """
        if not self.can_retry():
            return False

        self.retry_count += 1
        self.state = JobState.INITIALIZING
        self.error = None

        logger.info(f"Job {self.job_id}: retry {self.retry_count}/{self.max_retries}")

        return True

    def get_state_summary(self) -> Dict[str, Any]:
        """Get current state summary."""
        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "state": self.state.value,
            "retry_count": self.retry_count,
            "timing": {
                "started_at": self.timing.started_at.isoformat() if self.timing.started_at else None,
                "duration_seconds": self.timing.total_duration,
                "phase_times": self.timing.phase_times,
            },
            "error": self.error,
        }
