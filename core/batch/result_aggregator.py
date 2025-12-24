"""
Result aggregation and merging.
Combines chunk results into final document output.

Phase 1.5: Extracted from batch_processor.py for maintainability.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from config.logging_config import get_logger
from .chunk_processor import ChunkResult

logger = get_logger(__name__)


@dataclass
class AggregatedResult:
    """Final aggregated translation result."""
    text: str
    chunk_count: int
    total_chars: int
    successful_chunks: int
    failed_chunks: int
    avg_quality: float
    total_duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.chunk_count == 0:
            return 0.0
        return self.successful_chunks / self.chunk_count


class ResultAggregator:
    """
    Aggregates chunk results into final document.

    Features:
    - Merge chunks in order
    - Handle failures gracefully
    - Calculate statistics
    - STEM placeholder restoration

    Usage:
        aggregator = ResultAggregator()
        result = aggregator.aggregate(chunk_results)

        # With STEM restoration
        result = aggregator.aggregate_with_stem_restore(
            chunk_results,
            stem_preprocessed,
            formula_matches,
            code_matches
        )
    """

    def __init__(self, separator: str = "\n\n"):
        """
        Initialize aggregator.

        Args:
            separator: Separator between chunks (default: double newline)
        """
        self.separator = separator

    def aggregate(
        self,
        results: List[ChunkResult],
        include_failed: bool = True
    ) -> AggregatedResult:
        """
        Aggregate chunk results into single output.

        Args:
            results: List of ChunkResults in order
            include_failed: Whether to include failed chunks (with error markers)

        Returns:
            AggregatedResult with combined text and stats
        """
        if not results:
            return AggregatedResult(
                text="",
                chunk_count=0,
                total_chars=0,
                successful_chunks=0,
                failed_chunks=0,
                avg_quality=0.0,
                total_duration_ms=0.0,
            )

        # Separate successful and failed
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        # Combine texts
        texts = []
        for r in results:
            if r.success:
                texts.append(r.translated)
            elif include_failed:
                # Include error marker for failed chunks
                texts.append(f"[Translation failed: {r.error}]")

        combined_text = self.separator.join(texts)

        # Calculate stats
        total_duration = sum(r.duration_ms for r in results)
        avg_quality = (
            sum(r.quality_score for r in successful) / len(successful)
            if successful else 0.0
        )

        result = AggregatedResult(
            text=combined_text,
            chunk_count=len(results),
            total_chars=len(combined_text),
            successful_chunks=len(successful),
            failed_chunks=len(failed),
            avg_quality=avg_quality,
            total_duration_ms=total_duration,
            metadata={
                "failed_chunk_ids": [r.chunk_id for r in failed],
                "cache_hits": sum(1 for r in results if r.from_cache),
            }
        )

        if failed:
            logger.warning(f"Aggregation: {len(failed)} chunks failed")

        logger.info(
            f"Aggregated {len(results)} chunks → {len(combined_text)} chars "
            f"(quality={avg_quality:.2f})"
        )

        return result

    def aggregate_with_stem_restore(
        self,
        results: List[ChunkResult],
        stem_preprocessed: Any,
        formula_matches: List[Any],
        code_matches: List[Any],
    ) -> tuple[AggregatedResult, Dict[str, Any]]:
        """
        Aggregate results and restore STEM placeholders.

        Args:
            results: Chunk results
            stem_preprocessed: PreprocessedText from STEM preprocessing
            formula_matches: Detected formula matches
            code_matches: Detected code matches

        Returns:
            Tuple of (aggregated result, verification info)
        """
        # First aggregate normally
        aggregated = self.aggregate(results)

        # Import STEM module
        try:
            from core.stem import PlaceholderManager
        except ImportError:
            logger.warning("STEM module not available for restoration")
            return aggregated, {"error": "STEM module not available"}

        placeholder_manager = PlaceholderManager()

        # Restore formulas and code from placeholders
        restored_text = placeholder_manager.restore(
            translated_text=aggregated.text,
            mapping=stem_preprocessed.mapping
        )

        # Verify restoration
        verification = placeholder_manager.verify_restoration(
            original_text=stem_preprocessed.original_text,
            restored_text=restored_text,
            formula_matches=formula_matches,
            code_matches=code_matches
        )

        logger.info(f"STEM preservation: {verification['preservation_rate']:.1%}")

        if verification.get('formulas_lost', 0) > 0:
            logger.warning(f"Lost {verification['formulas_lost']} formulas")
        if verification.get('code_lost', 0) > 0:
            logger.warning(f"Lost {verification['code_lost']} code blocks")

        # Update aggregated result with restored text
        aggregated.text = restored_text
        aggregated.total_chars = len(restored_text)
        aggregated.metadata['stem_verification'] = verification

        return aggregated, verification

    def merge_with_existing(
        self,
        new_results: List[ChunkResult],
        existing_results: Dict[str, Any],
        all_chunk_ids: List[str],
    ) -> List[ChunkResult]:
        """
        Merge new results with existing (from checkpoint).

        Args:
            new_results: Newly processed results
            existing_results: Results from checkpoint (chunk_id -> result)
            all_chunk_ids: All chunk IDs in order

        Returns:
            Combined results in original order
        """
        # Create lookup for new results
        new_lookup = {r.chunk_id: r for r in new_results}

        # Build combined list in order
        combined = []
        for chunk_id in all_chunk_ids:
            if chunk_id in new_lookup:
                combined.append(new_lookup[chunk_id])
            elif chunk_id in existing_results:
                # Convert existing result to ChunkResult
                r = existing_results[chunk_id]
                combined.append(ChunkResult(
                    chunk_id=r.chunk_id,
                    original=r.source,
                    translated=r.translated,
                    quality_score=r.quality_score,
                    from_cache=True,
                ))
            else:
                logger.warning(f"Missing result for chunk {chunk_id}")
                combined.append(ChunkResult(
                    chunk_id=chunk_id,
                    original="",
                    translated="[MISSING]",
                    error="No result available"
                ))

        return combined
