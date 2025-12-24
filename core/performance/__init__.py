"""
High Performance Translation Module

This module provides performance enhancements for large-scale translation:
- Adaptive concurrency tuning
- Smart batch scheduling
- Streaming translation
- Checkpoint/resume support
- Memory-efficient processing
"""

from .adaptive_concurrency import AdaptiveConcurrencyTuner, ConcurrencyMetrics, TuningConfig
from .smart_scheduler import SmartBatchScheduler, BatchStrategy, BatchConfig, ScheduledTask
from .streaming_translator import StreamingTranslator, StreamChunk, StreamState, StreamProgress
from .checkpoint_manager import CheckpointManager, Checkpoint, CheckpointType

__all__ = [
    # Adaptive concurrency
    'AdaptiveConcurrencyTuner',
    'ConcurrencyMetrics',
    'TuningConfig',
    # Smart batch scheduling
    'SmartBatchScheduler',
    'BatchStrategy',
    'BatchConfig',
    'ScheduledTask',
    # Streaming translation
    'StreamingTranslator',
    'StreamChunk',
    'StreamState',
    'StreamProgress',
    # Checkpoint management
    'CheckpointManager',
    'Checkpoint',
    'CheckpointType',
]

__version__ = '2.0.0'  # Phase 2: High Performance Translation Pipeline
