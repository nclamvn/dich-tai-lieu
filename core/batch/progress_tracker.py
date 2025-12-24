"""
Progress tracking and reporting.
Provides real-time progress updates for batch processing.

Phase 1.5: Extracted from batch_processor.py for maintainability.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime
import asyncio

from config.logging_config import get_logger

logger = get_logger(__name__)


# Type alias for progress callbacks
ProgressCallback = Callable[[float, str, Dict[str, Any]], None]


@dataclass
class ProgressState:
    """Current progress state."""
    total_steps: int = 0
    completed_steps: int = 0
    current_phase: str = ""
    current_step: str = ""
    percentage: float = 0.0
    eta_seconds: Optional[float] = None
    quality_score: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total": self.total_steps,
            "completed": self.completed_steps,
            "percentage": self.percentage,
            "phase": self.current_phase,
            "step": self.current_step,
            "elapsed_seconds": self.elapsed_seconds,
            "eta_seconds": self.eta_seconds,
            "quality_score": self.quality_score,
        }


class ProgressTracker:
    """
    Tracks and reports progress for batch operations.

    Features:
    - Phase-based progress (loading, translating, exporting)
    - Chunk-level progress within phases
    - ETA calculation
    - Multiple callbacks (WebSocket, logging, etc.)

    Usage:
        tracker = ProgressTracker(total_chunks=100)
        tracker.add_callback(websocket_callback)
        tracker.add_callback(log_callback)

        tracker.start_phase("translating", total_steps=100)

        for i in range(100):
            # ... do work ...
            tracker.update(i + 1, f"Chunk {i+1}/100", quality=0.95)

        tracker.complete_phase()
        tracker.finish()
    """

    # Phase weights for overall progress
    PHASE_WEIGHTS = {
        "loading": 0.05,
        "preprocessing": 0.05,
        "translating": 0.70,
        "postprocessing": 0.10,
        "exporting": 0.10,
    }

    def __init__(
        self,
        total_chunks: int = 0,
        job_id: str = "",
        job_name: str = "",
    ):
        """
        Initialize progress tracker.

        Args:
            total_chunks: Total number of chunks to process
            job_id: Job identifier for callbacks
            job_name: Human-readable job name
        """
        self.job_id = job_id
        self.job_name = job_name
        self.total_chunks = total_chunks

        self.state = ProgressState(total_steps=total_chunks)
        self._callbacks: List[ProgressCallback] = []
        self._phases_completed: List[str] = []
        self._current_phase: Optional[str] = None
        self._phase_progress: float = 0.0

        logger.debug(f"ProgressTracker created: {job_id} ({total_chunks} chunks)")

    def add_callback(self, callback: ProgressCallback):
        """Add progress callback."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback):
        """Remove progress callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def start(self):
        """Start progress tracking."""
        self.state.started_at = datetime.now()
        self._notify(0.0, "Starting...")
        logger.info(f"Progress tracking started: {self.job_id}")

    def start_phase(self, phase: str, total_steps: int = 0):
        """
        Start a new phase.

        Args:
            phase: Phase name (loading, translating, etc.)
            total_steps: Number of steps in this phase
        """
        self._current_phase = phase
        self.state.current_phase = phase
        self.state.total_steps = total_steps
        self.state.completed_steps = 0
        self._phase_progress = 0.0

        self._notify(
            self._calculate_overall_progress(),
            f"Starting {phase}..."
        )

        logger.debug(f"Phase started: {phase} ({total_steps} steps)")

    def update(
        self,
        completed: int,
        step_description: str = "",
        quality: float = 0.0,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Update progress within current phase.

        Args:
            completed: Number of completed steps
            step_description: Description of current step
            quality: Quality score for this update
            extra_data: Additional data to pass to callbacks
        """
        self.state.completed_steps = completed
        self.state.current_step = step_description
        self.state.quality_score = quality

        # Calculate phase progress
        if self.state.total_steps > 0:
            self._phase_progress = completed / self.state.total_steps
            self.state.percentage = self._phase_progress

        # Calculate ETA
        if completed > 0:
            elapsed = self.state.elapsed_seconds
            rate = completed / elapsed
            remaining = self.state.total_steps - completed
            self.state.eta_seconds = remaining / rate if rate > 0 else None

        # Notify callbacks
        overall = self._calculate_overall_progress()
        self._notify(overall, step_description, extra_data)

    def complete_phase(self):
        """Complete current phase."""
        if self._current_phase:
            self._phases_completed.append(self._current_phase)
            self._phase_progress = 1.0

            logger.debug(f"Phase completed: {self._current_phase}")

            self._notify(
                self._calculate_overall_progress(),
                f"Completed {self._current_phase}"
            )

            self._current_phase = None

    def finish(self, message: str = "Completed"):
        """Finish all progress tracking."""
        self.state.percentage = 1.0
        self.state.current_step = message
        self.state.eta_seconds = 0

        self._notify(1.0, message, {"completed": True})

        logger.info(
            f"Progress complete: {self.job_id} "
            f"({self.state.elapsed_seconds:.1f}s)"
        )

    def fail(self, error: str):
        """Mark progress as failed."""
        self.state.current_step = f"Failed: {error}"

        self._notify(
            self.state.percentage,
            f"Failed: {error}",
            {"failed": True, "error": error}
        )

        logger.error(f"Progress failed: {self.job_id} - {error}")

    def _calculate_overall_progress(self) -> float:
        """Calculate overall progress across all phases."""
        completed_weight = sum(
            self.PHASE_WEIGHTS.get(phase, 0.1)
            for phase in self._phases_completed
        )

        current_weight = self.PHASE_WEIGHTS.get(self._current_phase, 0.1)
        current_contribution = current_weight * self._phase_progress

        return min(1.0, completed_weight + current_contribution)

    def _notify(
        self,
        percentage: float,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Notify all callbacks."""
        data = {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "completed": self.state.completed_steps,
            "total": self.state.total_steps,
            "phase": self.state.current_phase,
            "elapsed_seconds": self.state.elapsed_seconds,
            "eta_seconds": self.state.eta_seconds,
            "quality_score": self.state.quality_score,
            **(extra or {})
        }

        for callback in self._callbacks:
            try:
                callback(percentage, message, data)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current state as dictionary."""
        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "progress": self._calculate_overall_progress(),
            **self.state.to_dict(),
            "phases_completed": self._phases_completed,
            "current_phase": self._current_phase,
        }


def create_websocket_callback(websocket_manager, event_name: str = "job_progress"):
    """
    Create a WebSocket broadcast callback.

    Args:
        websocket_manager: WebSocket manager instance
        event_name: Event name for broadcast

    Returns:
        Progress callback function
    """
    def callback(percentage: float, message: str, data: Dict[str, Any]):
        asyncio.create_task(websocket_manager.broadcast({
            "event": event_name,
            "progress": percentage,
            "message": message,
            **data
        }))

    return callback


def create_logging_callback(log_interval: int = 5):
    """
    Create a logging callback that logs every N updates.

    Args:
        log_interval: Log every N updates

    Returns:
        Progress callback function
    """
    counter = {"count": 0}

    def callback(percentage: float, message: str, data: Dict[str, Any]):
        counter["count"] += 1
        if counter["count"] % log_interval == 0 or percentage >= 1.0:
            quality = data.get("quality_score", 0)
            completed = data.get("completed", 0)
            total = data.get("total", 0)
            logger.info(
                f"Progress: {completed}/{total} ({percentage*100:.1f}%) "
                f"- Quality: {quality:.2f} - {message}"
            )

    return callback
