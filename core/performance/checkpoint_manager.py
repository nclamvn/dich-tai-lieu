"""
Checkpoint Manager Module

Provides checkpoint/resume functionality for translation jobs,
enabling recovery from crashes, network failures, and manual cancellations.
"""

import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path
from enum import Enum

from config.logging_config import get_logger
logger = get_logger(__name__)


class CheckpointType(Enum):
    """Types of checkpoints"""
    AUTO = "auto"  # Automatic periodic checkpoint
    MANUAL = "manual"  # Manually triggered
    PRE_FAILURE = "pre_failure"  # Before expected failure point
    COMPLETION = "completion"  # Job completed successfully


@dataclass
class Checkpoint:
    """
    A checkpoint representing saved job state

    Attributes:
        checkpoint_id: Unique checkpoint identifier
        job_id: Associated job ID
        timestamp: When checkpoint was created
        checkpoint_type: Type of checkpoint
        progress_percentage: Job progress at checkpoint time
        completed_chunks: List of completed chunk IDs
        pending_chunks: List of pending chunk IDs
        partial_results: Partial translation results
        job_metadata: Job configuration and metadata
        error_info: Error information if checkpoint due to failure
    """
    checkpoint_id: str
    job_id: str
    timestamp: float
    checkpoint_type: CheckpointType
    progress_percentage: float
    completed_chunks: List[str]
    pending_chunks: List[str]
    partial_results: Dict[str, str]  # chunk_id -> translated_text
    job_metadata: Dict[str, Any]
    error_info: Optional[Dict[str, str]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['checkpoint_type'] = self.checkpoint_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Checkpoint':
        """Create from dictionary"""
        data['checkpoint_type'] = CheckpointType(data['checkpoint_type'])
        return cls(**data)


class CheckpointManager:
    """
    Manage checkpoints for translation jobs

    Provides:
    - Automatic periodic checkpointing
    - Manual checkpoint creation
    - Resume from last checkpoint
    - Checkpoint cleanup and archival
    - Crash recovery

    Example:
        manager = CheckpointManager(checkpoint_dir=Path("checkpoints"))

        # Create checkpoint during job
        checkpoint = manager.create_checkpoint(
            job_id="job_123",
            completed_chunks=["chunk_0", "chunk_1"],
            pending_chunks=["chunk_2", "chunk_3"],
            partial_results={"chunk_0": "...", "chunk_1": "..."},
            job_metadata={"input_file": "doc.pdf", ...}
        )

        # Resume from checkpoint
        checkpoint = manager.get_latest_checkpoint("job_123")
        if checkpoint:
            # Continue from checkpoint.pending_chunks
            pass

        # Cancel job (creates final checkpoint)
        manager.cancel_job("job_123")

        # Clean up completed job
        manager.cleanup_job("job_123")
    """

    def __init__(
        self,
        checkpoint_dir: Path,
        auto_checkpoint_interval: int = 10,  # Chunks
        max_checkpoints_per_job: int = 5,
        checkpoint_retention_days: int = 7
    ):
        """
        Initialize checkpoint manager

        Args:
            checkpoint_dir: Directory to store checkpoints
            auto_checkpoint_interval: Create checkpoint every N chunks
            max_checkpoints_per_job: Maximum checkpoints to keep per job
            checkpoint_retention_days: Days to retain old checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.auto_checkpoint_interval = auto_checkpoint_interval
        self.max_checkpoints_per_job = max_checkpoints_per_job
        self.checkpoint_retention_days = checkpoint_retention_days

        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Track active jobs
        self._active_jobs: Dict[str, Dict] = {}
        self._chunk_counters: Dict[str, int] = {}

    def create_checkpoint(
        self,
        job_id: str,
        completed_chunks: List[str],
        pending_chunks: List[str],
        partial_results: Dict[str, str],
        job_metadata: Dict[str, Any],
        checkpoint_type: CheckpointType = CheckpointType.AUTO,
        error_info: Optional[Dict[str, str]] = None
    ) -> Checkpoint:
        """
        Create a checkpoint for a job

        Args:
            job_id: Job identifier
            completed_chunks: List of completed chunk IDs
            pending_chunks: List of pending chunk IDs
            partial_results: Partial translation results
            job_metadata: Job configuration
            checkpoint_type: Type of checkpoint
            error_info: Error information if applicable

        Returns:
            Created checkpoint
        """
        # Calculate progress
        total_chunks = len(completed_chunks) + len(pending_chunks)
        progress = (len(completed_chunks) / total_chunks * 100.0) if total_chunks > 0 else 0.0

        # Generate checkpoint ID
        checkpoint_id = self._generate_checkpoint_id(job_id)

        # Create checkpoint
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            job_id=job_id,
            timestamp=time.time(),
            checkpoint_type=checkpoint_type,
            progress_percentage=progress,
            completed_chunks=completed_chunks,
            pending_chunks=pending_chunks,
            partial_results=partial_results,
            job_metadata=job_metadata,
            error_info=error_info
        )

        # Save to disk
        self._save_checkpoint(checkpoint)

        # Cleanup old checkpoints
        self._cleanup_old_checkpoints(job_id)

        return checkpoint

    def should_checkpoint(self, job_id: str) -> bool:
        """
        Check if it's time to create an automatic checkpoint

        Args:
            job_id: Job identifier

        Returns:
            True if checkpoint should be created
        """
        if job_id not in self._chunk_counters:
            self._chunk_counters[job_id] = 0

        self._chunk_counters[job_id] += 1

        if self._chunk_counters[job_id] >= self.auto_checkpoint_interval:
            self._chunk_counters[job_id] = 0
            return True

        return False

    def get_latest_checkpoint(self, job_id: str) -> Optional[Checkpoint]:
        """
        Get the most recent checkpoint for a job

        Args:
            job_id: Job identifier

        Returns:
            Latest checkpoint or None if no checkpoints exist
        """
        checkpoints = self.list_checkpoints(job_id)

        if not checkpoints:
            return None

        # Return most recent
        return max(checkpoints, key=lambda c: c.timestamp)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Get a specific checkpoint by ID

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint or None if not found
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Checkpoint.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading checkpoint {checkpoint_id}: {e}")
            return None

    def list_checkpoints(self, job_id: str) -> List[Checkpoint]:
        """
        List all checkpoints for a job

        Args:
            job_id: Job identifier

        Returns:
            List of checkpoints sorted by timestamp
        """
        checkpoints = []

        # Find all checkpoint files for this job
        for checkpoint_file in self.checkpoint_dir.glob(f"*_{job_id}_*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    checkpoint = Checkpoint.from_dict(data)
                    checkpoints.append(checkpoint)
            except Exception as e:
                logger.error(f"Error loading checkpoint {checkpoint_file}: {e}")
                continue

        # Sort by timestamp
        checkpoints.sort(key=lambda c: c.timestamp)

        return checkpoints

    def resume_from_checkpoint(self, job_id: str) -> Optional[Checkpoint]:
        """
        Resume a job from its latest checkpoint

        Args:
            job_id: Job identifier

        Returns:
            Checkpoint to resume from, or None if no checkpoint exists
        """
        checkpoint = self.get_latest_checkpoint(job_id)

        if checkpoint:
            logger.info(f"Resuming job {job_id} from checkpoint {checkpoint.checkpoint_id} ({checkpoint.progress_percentage:.1f}% complete, {len(checkpoint.completed_chunks)} done, {len(checkpoint.pending_chunks)} pending)")

        return checkpoint

    def cancel_job(
        self,
        job_id: str,
        completed_chunks: List[str],
        pending_chunks: List[str],
        partial_results: Dict[str, str],
        job_metadata: Dict[str, Any]
    ) -> Checkpoint:
        """
        Cancel a job and create final checkpoint

        Args:
            job_id: Job identifier
            completed_chunks: Completed chunk IDs
            pending_chunks: Pending chunk IDs
            partial_results: Partial results
            job_metadata: Job metadata

        Returns:
            Final checkpoint before cancellation
        """
        checkpoint = self.create_checkpoint(
            job_id=job_id,
            completed_chunks=completed_chunks,
            pending_chunks=pending_chunks,
            partial_results=partial_results,
            job_metadata=job_metadata,
            checkpoint_type=CheckpointType.MANUAL,
            error_info={'reason': 'User cancelled job'}
        )

        # Remove from active jobs
        if job_id in self._active_jobs:
            del self._active_jobs[job_id]
        if job_id in self._chunk_counters:
            del self._chunk_counters[job_id]

        logger.info(f"Job {job_id} cancelled. Checkpoint created: {checkpoint.checkpoint_id}")

        return checkpoint

    def mark_completed(
        self,
        job_id: str,
        completed_chunks: List[str],
        final_results: Dict[str, str],
        job_metadata: Dict[str, Any]
    ) -> Checkpoint:
        """
        Mark job as completed and create completion checkpoint

        Args:
            job_id: Job identifier
            completed_chunks: All chunk IDs
            final_results: Complete results
            job_metadata: Job metadata

        Returns:
            Completion checkpoint
        """
        checkpoint = self.create_checkpoint(
            job_id=job_id,
            completed_chunks=completed_chunks,
            pending_chunks=[],
            partial_results=final_results,
            job_metadata=job_metadata,
            checkpoint_type=CheckpointType.COMPLETION
        )

        # Remove from active jobs
        if job_id in self._active_jobs:
            del self._active_jobs[job_id]
        if job_id in self._chunk_counters:
            del self._chunk_counters[job_id]

        return checkpoint

    def cleanup_job(self, job_id: str, keep_latest: bool = True):
        """
        Clean up checkpoints for a job

        Args:
            job_id: Job identifier
            keep_latest: Keep the most recent checkpoint
        """
        checkpoints = self.list_checkpoints(job_id)

        if not checkpoints:
            return

        # Sort by timestamp
        checkpoints.sort(key=lambda c: c.timestamp)

        # Determine which to delete
        if keep_latest:
            to_delete = checkpoints[:-1]
        else:
            to_delete = checkpoints

        # Delete checkpoint files
        for checkpoint in to_delete:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()

        logger.info(f"Cleaned up {len(to_delete)} checkpoints for job {job_id}")

    def cleanup_old_checkpoints(self, max_age_days: Optional[int] = None):
        """
        Clean up checkpoints older than specified age

        Args:
            max_age_days: Maximum age in days (uses default if None)
        """
        max_age = max_age_days or self.checkpoint_retention_days
        cutoff_time = time.time() - (max_age * 24 * 60 * 60)

        deleted_count = 0

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    checkpoint = Checkpoint.from_dict(data)

                    # Delete if too old and not a completion checkpoint
                    if (checkpoint.timestamp < cutoff_time and
                        checkpoint.checkpoint_type != CheckpointType.COMPLETION):
                        checkpoint_file.unlink()
                        deleted_count += 1

            except Exception as e:
                logger.error(f"Error processing {checkpoint_file}: {e}")
                continue

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old checkpoints")

    def get_statistics(self) -> dict:
        """
        Get checkpoint statistics

        Returns:
            Dictionary with checkpoint metrics
        """
        all_checkpoints = list(self.checkpoint_dir.glob("*.json"))
        total_checkpoints = len(all_checkpoints)

        # Count by job
        jobs = set()
        checkpoint_types = {t: 0 for t in CheckpointType}

        for checkpoint_file in all_checkpoints:
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    checkpoint = Checkpoint.from_dict(data)
                    jobs.add(checkpoint.job_id)
                    checkpoint_types[checkpoint.checkpoint_type] += 1
            except:
                continue

        # Calculate total size
        total_size_mb = sum(f.stat().st_size for f in all_checkpoints) / (1024 * 1024)

        return {
            'total_checkpoints': total_checkpoints,
            'total_jobs': len(jobs),
            'checkpoint_types': {t.value: count for t, count in checkpoint_types.items()},
            'total_size_mb': total_size_mb,
            'checkpoint_dir': str(self.checkpoint_dir)
        }

    def _generate_checkpoint_id(self, job_id: str) -> str:
        """Generate unique checkpoint ID"""
        timestamp = str(time.time())
        unique_str = f"{job_id}_{timestamp}"
        hash_str = hashlib.md5(unique_str.encode()).hexdigest()[:8]
        return f"ckpt_{job_id}_{hash_str}"

    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Save checkpoint to disk"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    def _cleanup_old_checkpoints(self, job_id: str):
        """Remove old checkpoints exceeding max count"""
        checkpoints = self.list_checkpoints(job_id)

        if len(checkpoints) > self.max_checkpoints_per_job:
            # Sort by timestamp and keep only recent ones
            checkpoints.sort(key=lambda c: c.timestamp)
            to_delete = checkpoints[:-self.max_checkpoints_per_job]

            for checkpoint in to_delete:
                checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
                if checkpoint_file.exists():
                    checkpoint_file.unlink()


# Example usage and testing
if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    print("Checkpoint Manager - Demo")
    print("=" * 80)

    # Create temporary checkpoint directory
    with tempfile.TemporaryDirectory() as tmpdir:
        checkpoint_dir = Path(tmpdir) / "checkpoints"

        manager = CheckpointManager(
            checkpoint_dir=checkpoint_dir,
            auto_checkpoint_interval=5,
            max_checkpoints_per_job=3
        )

        print(f"Checkpoint directory: {checkpoint_dir}\n")

        # Simulate job with checkpoints
        job_id = "demo_job_001"

        print("Simulating job execution with checkpoints...\n")

        # Simulate processing chunks
        all_chunks = [f"chunk_{i}" for i in range(20)]
        completed = []
        results = {}

        for i, chunk_id in enumerate(all_chunks):
            # Simulate processing
            completed.append(chunk_id)
            results[chunk_id] = f"Translated text for {chunk_id}"

            # Check if checkpoint needed
            if manager.should_checkpoint(job_id):
                pending = all_chunks[i + 1:]
                checkpoint = manager.create_checkpoint(
                    job_id=job_id,
                    completed_chunks=completed.copy(),
                    pending_chunks=pending,
                    partial_results=results.copy(),
                    job_metadata={
                        'input_file': 'demo.pdf',
                        'source_lang': 'en',
                        'target_lang': 'vi'
                    }
                )
                print(f"✓ Checkpoint created: {checkpoint.checkpoint_id}")
                print(f"  Progress: {checkpoint.progress_percentage:.1f}%")
                print(f"  Completed: {len(checkpoint.completed_chunks)} chunks")
                print()

        # Mark as completed
        print("Job completed!\n")
        completion_checkpoint = manager.mark_completed(
            job_id=job_id,
            completed_chunks=completed,
            final_results=results,
            job_metadata={'status': 'completed'}
        )

        # List all checkpoints
        print("All checkpoints for job:")
        checkpoints = manager.list_checkpoints(job_id)
        for checkpoint in checkpoints:
            print(f"  - {checkpoint.checkpoint_id}: "
                  f"{checkpoint.checkpoint_type.value} "
                  f"({checkpoint.progress_percentage:.1f}%)")

        print()

        # Simulate resume
        print("Simulating job resume...")
        resume_checkpoint = manager.resume_from_checkpoint(job_id)

        if resume_checkpoint:
            print(f"  Would resume from: {resume_checkpoint.checkpoint_id}")
            print(f"  Pending chunks: {len(resume_checkpoint.pending_chunks)}")

        print()

        # Statistics
        stats = manager.get_statistics()
        print("Checkpoint Statistics:")
        for key, value in stats.items():
            if key != 'checkpoint_types':
                print(f"  {key}: {value}")
            else:
                print(f"  {key}:")
                for t, count in value.items():
                    print(f"    {t}: {count}")

        print("\n" + "=" * 80)
        print("✓ Demo complete!")
