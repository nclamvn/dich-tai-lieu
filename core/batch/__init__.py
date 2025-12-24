"""
Batch processing sub-modules.
Extracted from batch_processor.py for maintainability.

Phase 1.5: Code cleanup - split ~1000 line function into manageable modules.
"""

from .job_handler import JobHandler, JobState, JobResult, JobTiming
from .chunk_processor import ChunkProcessor, ChunkResult, ProcessingStats
from .result_aggregator import ResultAggregator, AggregatedResult
from .progress_tracker import (
    ProgressTracker,
    ProgressState,
    ProgressCallback,
    create_logging_callback,
    create_websocket_callback,
)
from .orchestrator import BatchOrchestrator, OrchestratorConfig, OrchestratorResult

__all__ = [
    # Job management
    'JobHandler',
    'JobState',
    'JobResult',
    'JobTiming',
    # Chunk processing
    'ChunkProcessor',
    'ChunkResult',
    'ProcessingStats',
    # Result aggregation
    'ResultAggregator',
    'AggregatedResult',
    # Progress tracking
    'ProgressTracker',
    'ProgressState',
    'ProgressCallback',
    'create_logging_callback',
    'create_websocket_callback',
    # Orchestrator (V2)
    'BatchOrchestrator',
    'OrchestratorConfig',
    'OrchestratorResult',
]
