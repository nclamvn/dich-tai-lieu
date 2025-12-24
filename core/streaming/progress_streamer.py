#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Progress Streamer - Phase 5.3

Real-time progress broadcasting via WebSocket for live translation preview.
"""

import time
from typing import Any, Optional

from config.logging_config import get_logger
logger = get_logger(__name__)


class ProgressStreamer:
    """
    Stream translation progress via WebSocket

    Events emitted:
    - job_started: Job begins processing
    - chunk_translated: Individual chunk completed
    - batch_completed: Batch finished
    - batch_exported: Partial DOCX available
    - job_completed: Job fully complete

    Usage:
        streamer = ProgressStreamer(websocket_manager)

        await streamer.broadcast_chunk_translated(
            job_id="job_123",
            chunk_id="chunk_1",
            preview="Translated text...",
            quality_score=0.92
        )
    """

    def __init__(self, websocket_manager: Any):
        """
        Initialize progress streamer

        Args:
            websocket_manager: WebSocket manager for broadcasting events
        """
        self.ws_manager = websocket_manager

    async def broadcast_job_started(
        self,
        job_id: str,
        total_chunks: int,
        total_batches: int
    ):
        """
        Broadcast job start event

        Args:
            job_id: Job identifier
            total_chunks: Total number of chunks
            total_batches: Total number of batches
        """
        await self._broadcast({
            "event": "job_started",
            "job_id": job_id,
            "total_chunks": total_chunks,
            "total_batches": total_batches,
            "timestamp": time.time()
        })

    async def broadcast_chunk_translated(
        self,
        job_id: str,
        chunk_id: str,
        preview: str,
        quality_score: float
    ):
        """
        Broadcast individual chunk completion

        Args:
            job_id: Job identifier
            chunk_id: Chunk identifier
            preview: Preview of translated text (first 200 chars)
            quality_score: Translation quality score
        """
        await self._broadcast({
            "event": "chunk_translated",
            "job_id": job_id,
            "chunk_id": chunk_id,
            "preview": preview,
            "quality_score": quality_score,
            "timestamp": time.time()
        })

    async def broadcast_batch_completed(
        self,
        job_id: str,
        batch_idx: int,
        total_batches: int,
        progress: float,
        chunks_completed: int
    ):
        """
        Broadcast batch completion

        Args:
            job_id: Job identifier
            batch_idx: Completed batch index (1-based)
            total_batches: Total number of batches
            progress: Overall progress (0.0 to 1.0)
            chunks_completed: Total chunks completed so far
        """
        await self._broadcast({
            "event": "batch_completed",
            "job_id": job_id,
            "batch": batch_idx,
            "total_batches": total_batches,
            "progress": progress,
            "chunks_completed": chunks_completed,
            "timestamp": time.time()
        })

    async def broadcast_batch_exported(
        self,
        job_id: str,
        batch_idx: int,
        partial_file: str
    ):
        """
        Broadcast partial export availability

        Args:
            job_id: Job identifier
            batch_idx: Batch index
            partial_file: Path to partial DOCX file
        """
        await self._broadcast({
            "event": "batch_exported",
            "job_id": job_id,
            "batch": batch_idx,
            "partial_file": partial_file,
            "download_available": True,
            "timestamp": time.time()
        })

    async def broadcast_job_completed(
        self,
        job_id: str,
        total_chunks: int,
        memory_saved_mb: float
    ):
        """
        Broadcast job completion

        Args:
            job_id: Job identifier
            total_chunks: Total chunks processed
            memory_saved_mb: Memory saved through streaming (MB)
        """
        await self._broadcast({
            "event": "job_completed",
            "job_id": job_id,
            "total_chunks": total_chunks,
            "memory_saved_mb": memory_saved_mb,
            "timestamp": time.time()
        })

    async def _broadcast(self, message: dict):
        """
        Internal broadcast method

        Args:
            message: Message dict to broadcast
        """
        if self.ws_manager:
            try:
                await self.ws_manager.broadcast(message)
            except Exception as e:
                # Don't fail job if WebSocket broadcast fails
                logger.warning(f"WebSocket broadcast failed: {e}")
