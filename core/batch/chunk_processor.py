"""
Chunk-level translation processing.
Handles parallel translation of text chunks with progress tracking.

Phase 1.5: Extracted from batch_processor.py for maintainability.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any, Dict, Awaitable
import asyncio
import time

from config.logging_config import get_logger
from config.constants import (
    BATCH_CHUNK_SIZE,
    BATCH_PARALLEL_WORKERS,
)

logger = get_logger(__name__)


@dataclass
class ChunkResult:
    """Result of translating a single chunk."""
    chunk_id: str
    original: str
    translated: str
    quality_score: float = 0.0
    tokens_used: int = 0
    duration_ms: float = 0.0
    from_cache: bool = False
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class ProcessingStats:
    """Statistics from chunk processing."""
    total_chunks: int = 0
    successful: int = 0
    failed: int = 0
    from_cache: int = 0
    total_duration_ms: float = 0.0
    avg_quality: float = 0.0


# Type for translation function
TranslateFunc = Callable[[Any, Any], Awaitable[Any]]
ProgressFunc = Callable[[int, int, float], None]


class ChunkProcessor:
    """
    Processes text chunks for translation.

    Features:
    - Parallel processing with concurrency control
    - Progress callbacks
    - Checkpoint integration
    - Error handling per chunk

    Usage:
        processor = ChunkProcessor(
            translate_func=translator.translate_chunk,
            max_concurrency=10
        )

        results, stats = await processor.process_all(
            chunks=chunks,
            http_client=client,
            progress_callback=progress_fn
        )
    """

    def __init__(
        self,
        translate_func: TranslateFunc,
        max_concurrency: int = BATCH_PARALLEL_WORKERS,
        max_retries: int = 3,
        timeout: float = 120.0,
    ):
        """
        Initialize chunk processor.

        Args:
            translate_func: Async function(http_client, chunk) -> TranslationResult
            max_concurrency: Maximum parallel translations
            max_retries: Retries per chunk on failure
            timeout: Timeout per chunk in seconds
        """
        self.translate_func = translate_func
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.timeout = timeout

        self._semaphore: Optional[asyncio.Semaphore] = None
        self._cancelled = False

        logger.debug(
            f"ChunkProcessor initialized: "
            f"concurrency={max_concurrency}, retries={max_retries}"
        )

    def cancel(self):
        """Cancel ongoing processing."""
        self._cancelled = True
        logger.info("ChunkProcessor: cancellation requested")

    async def process_all(
        self,
        chunks: List[Any],
        http_client: Any,
        progress_callback: Optional[ProgressFunc] = None,
        checkpoint_callback: Optional[Callable[[str, Any], None]] = None,
        checkpoint_interval: int = 5,
    ) -> tuple[List[ChunkResult], ProcessingStats]:
        """
        Process all chunks in parallel.

        Args:
            chunks: List of chunk objects with .id and .text attributes
            http_client: HTTP client for API calls
            progress_callback: Optional callback(completed, total, quality)
            checkpoint_callback: Optional callback(chunk_id, result) for checkpoints
            checkpoint_interval: Save checkpoint every N chunks

        Returns:
            Tuple of (results list, processing stats)
        """
        if not chunks:
            return [], ProcessingStats()

        self._cancelled = False
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

        logger.info(
            f"Processing {len(chunks)} chunks with concurrency {self.max_concurrency}"
        )

        # Track completion for progress
        completed_count = 0
        total_quality = 0.0

        results: List[ChunkResult] = []
        results_lock = asyncio.Lock()

        async def process_single(chunk) -> ChunkResult:
            """Process a single chunk with semaphore control."""
            nonlocal completed_count, total_quality

            if self._cancelled:
                return ChunkResult(
                    chunk_id=chunk.id,
                    original=chunk.text,
                    translated="",
                    error="Cancelled"
                )

            async with self._semaphore:
                start_time = time.time()

                try:
                    # Call translation function
                    result = await asyncio.wait_for(
                        self.translate_func(http_client, chunk),
                        timeout=self.timeout
                    )

                    duration_ms = (time.time() - start_time) * 1000

                    chunk_result = ChunkResult(
                        chunk_id=result.chunk_id,
                        original=result.source,
                        translated=result.translated,
                        quality_score=result.quality_score,
                        duration_ms=duration_ms,
                        from_cache=getattr(result, 'from_cache', False),
                    )

                except asyncio.TimeoutError:
                    chunk_result = ChunkResult(
                        chunk_id=chunk.id,
                        original=chunk.text,
                        translated="[TIMEOUT]",
                        error=f"Timeout after {self.timeout}s"
                    )

                except Exception as e:
                    chunk_result = ChunkResult(
                        chunk_id=chunk.id,
                        original=chunk.text,
                        translated="[ERROR]",
                        error=str(e)
                    )

                # Update progress
                async with results_lock:
                    completed_count += 1
                    if chunk_result.success:
                        total_quality += chunk_result.quality_score

                    # Checkpoint callback
                    if checkpoint_callback and completed_count % checkpoint_interval == 0:
                        checkpoint_callback(chunk_result.chunk_id, chunk_result)

                # Progress callback
                if progress_callback:
                    avg_quality = total_quality / completed_count if completed_count > 0 else 0
                    progress_callback(completed_count, len(chunks), avg_quality)

                return chunk_result

        # Process all chunks concurrently
        tasks = [process_single(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions from gather
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Chunk {i} exception: {result}")
                final_results.append(ChunkResult(
                    chunk_id=chunks[i].id,
                    original=chunks[i].text,
                    translated="[EXCEPTION]",
                    error=str(result)
                ))
            else:
                final_results.append(result)

        # Calculate stats
        stats = self._calculate_stats(final_results)

        logger.info(
            f"Chunk processing complete: "
            f"{stats.successful}/{stats.total_chunks} successful, "
            f"{stats.failed} failed, {stats.from_cache} from cache"
        )

        return final_results, stats

    def _calculate_stats(self, results: List[ChunkResult]) -> ProcessingStats:
        """Calculate processing statistics."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        cached = [r for r in results if r.from_cache]

        total_duration = sum(r.duration_ms for r in results)
        avg_quality = (
            sum(r.quality_score for r in successful) / len(successful)
            if successful else 0.0
        )

        return ProcessingStats(
            total_chunks=len(results),
            successful=len(successful),
            failed=len(failed),
            from_cache=len(cached),
            total_duration_ms=total_duration,
            avg_quality=avg_quality,
        )

    async def process_with_checkpoint_resume(
        self,
        all_chunks: List[Any],
        completed_results: Dict[str, Any],
        http_client: Any,
        progress_callback: Optional[ProgressFunc] = None,
        checkpoint_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> tuple[List[ChunkResult], ProcessingStats]:
        """
        Process chunks with checkpoint resume support.

        Args:
            all_chunks: All chunks (including already completed)
            completed_results: Dict of chunk_id -> result for completed chunks
            http_client: HTTP client for API calls
            progress_callback: Progress callback
            checkpoint_callback: Checkpoint save callback

        Returns:
            Tuple of (all results in order, stats for new processing)
        """
        # Filter to only pending chunks
        pending_chunks = [
            chunk for chunk in all_chunks
            if chunk.id not in completed_results
        ]

        if not pending_chunks:
            logger.info("All chunks already completed from checkpoint")
            # Convert completed_results to ChunkResult format
            final_results = []
            for chunk in all_chunks:
                if chunk.id in completed_results:
                    r = completed_results[chunk.id]
                    final_results.append(ChunkResult(
                        chunk_id=r.chunk_id,
                        original=r.source,
                        translated=r.translated,
                        quality_score=r.quality_score,
                        from_cache=True,
                    ))
            return final_results, ProcessingStats(
                total_chunks=len(final_results),
                successful=len(final_results),
                from_cache=len(final_results),
            )

        logger.info(
            f"Resuming from checkpoint: "
            f"{len(completed_results)} done, {len(pending_chunks)} remaining"
        )

        # Process pending chunks
        new_results, stats = await self.process_all(
            chunks=pending_chunks,
            http_client=http_client,
            progress_callback=progress_callback,
            checkpoint_callback=checkpoint_callback,
        )

        # Merge results in original order
        new_results_dict = {r.chunk_id: r for r in new_results}

        final_results = []
        for chunk in all_chunks:
            if chunk.id in completed_results:
                r = completed_results[chunk.id]
                final_results.append(ChunkResult(
                    chunk_id=r.chunk_id,
                    original=r.source,
                    translated=r.translated,
                    quality_score=r.quality_score,
                    from_cache=True,
                ))
            elif chunk.id in new_results_dict:
                final_results.append(new_results_dict[chunk.id])
            else:
                logger.warning(f"Missing result for chunk {chunk.id}")
                final_results.append(ChunkResult(
                    chunk_id=chunk.id,
                    original=chunk.text,
                    translated="[MISSING]",
                    error="No result available"
                ))

        return final_results, stats
