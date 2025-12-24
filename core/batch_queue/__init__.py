"""
Batch Queue System
AI Publisher Pro

Process multiple documents in a managed queue with:
- Priority queue management
- Parallel processing
- Progress tracking
- Cost estimation
- Pause/resume/cancel
- Persistent storage

Usage:
    from core.batch_queue import BatchQueue, BatchJob, JobPriority

    # Create queue
    queue = BatchQueue()

    # Add jobs
    queue.add_job("document1.pdf", translation_mode="balanced")
    queue.add_job("document2.pdf", priority=JobPriority.HIGH)

    # Start processing
    queue.start()

    # Monitor progress
    status = queue.get_status()
    print(f"Progress: {status['summary']['progress_percent']}%")
"""

from .batch_job import (
    BatchJob,
    JobStatus,
    JobPriority,
    JobProgress,
    BatchSummary,
    JobStore,
)

from .batch_queue import (
    BatchQueue,
    QueueConfig,
    create_batch_queue,
)

from .batch_worker import (
    process_document_job,
    estimate_job_time,
    estimate_job_cost,
)

__all__ = [
    # Job classes
    "BatchJob",
    "JobStatus",
    "JobPriority",
    "JobProgress",
    "BatchSummary",
    "JobStore",

    # Queue classes
    "BatchQueue",
    "QueueConfig",
    "create_batch_queue",

    # Worker functions
    "process_document_job",
    "estimate_job_time",
    "estimate_job_cost",
]

__version__ = "1.0.0"
