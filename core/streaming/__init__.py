"""
Streaming Module - Phase 5.4: Multi-Format Streaming

Provides memory-efficient batch processing and real-time progress updates
for multiple output formats (DOCX, PDF, TXT).

Exports:
- StreamingBatchProcessor (main batch processor)
- ProgressStreamer (WebSocket broadcasting)
- BaseIncrementalBuilder (abstract base class for format builders)
- IncrementalDocxBuilder (memory-efficient DOCX building)
- IncrementalPdfBuilder (memory-efficient PDF building)
- IncrementalTxtBuilder (memory-efficient TXT building)
"""

from .streaming_processor import StreamingBatchProcessor
from .progress_streamer import ProgressStreamer
from .base_builder import BaseIncrementalBuilder
from .incremental_builder import IncrementalDocxBuilder
from .incremental_pdf_builder import IncrementalPdfBuilder
from .incremental_txt_builder import IncrementalTxtBuilder

__all__ = [
    'StreamingBatchProcessor',
    'ProgressStreamer',
    'BaseIncrementalBuilder',
    'IncrementalDocxBuilder',
    'IncrementalPdfBuilder',
    'IncrementalTxtBuilder'
]
