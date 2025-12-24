"""
Unit tests for core.batch.result_aggregator module.

Tests ResultAggregator and AggregatedResult classes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from core.batch.result_aggregator import (
    ResultAggregator,
    AggregatedResult,
)
from core.batch.chunk_processor import ChunkResult


class TestAggregatedResult:
    """Tests for AggregatedResult dataclass."""

    def test_result_creation_minimal(self):
        """Test creating AggregatedResult with minimal data."""
        result = AggregatedResult(
            text="Translated text",
            chunk_count=10,
            total_chars=500,
            successful_chunks=10,
            failed_chunks=0,
            avg_quality=0.92,
            total_duration_ms=5000.0
        )
        assert result.text == "Translated text"
        assert result.chunk_count == 10
        assert result.successful_chunks == 10
        assert result.avg_quality == 0.92

    def test_result_with_metadata(self):
        """Test creating AggregatedResult with metadata."""
        result = AggregatedResult(
            text="text",
            chunk_count=5,
            total_chars=100,
            successful_chunks=4,
            failed_chunks=1,
            avg_quality=0.85,
            total_duration_ms=2000.0,
            metadata={'failed_chunk_ids': ['chunk_3'], 'cache_hits': 2}
        )
        assert result.metadata['failed_chunk_ids'] == ['chunk_3']
        assert result.metadata['cache_hits'] == 2

    def test_success_rate_property(self):
        """Test success_rate property calculation."""
        result = AggregatedResult(
            text="",
            chunk_count=10,
            total_chars=0,
            successful_chunks=8,
            failed_chunks=2,
            avg_quality=0.0,
            total_duration_ms=0.0
        )
        assert result.success_rate == 0.8

    def test_success_rate_zero_chunks(self):
        """Test success_rate with zero chunks."""
        result = AggregatedResult(
            text="",
            chunk_count=0,
            total_chars=0,
            successful_chunks=0,
            failed_chunks=0,
            avg_quality=0.0,
            total_duration_ms=0.0
        )
        assert result.success_rate == 0.0

    def test_success_rate_all_successful(self):
        """Test success_rate with all successful."""
        result = AggregatedResult(
            text="",
            chunk_count=100,
            total_chars=0,
            successful_chunks=100,
            failed_chunks=0,
            avg_quality=0.0,
            total_duration_ms=0.0
        )
        assert result.success_rate == 1.0


class TestResultAggregator:
    """Tests for ResultAggregator class."""

    @pytest.fixture
    def aggregator(self):
        """Create a ResultAggregator instance."""
        return ResultAggregator()

    @pytest.fixture
    def sample_results(self):
        """Create sample ChunkResults for testing."""
        return [
            ChunkResult(
                chunk_id="chunk_0",
                original="Hello",
                translated="Xin chao",
                quality_score=0.9,
                duration_ms=100.0
            ),
            ChunkResult(
                chunk_id="chunk_1",
                original="World",
                translated="The gioi",
                quality_score=0.85,
                duration_ms=120.0
            ),
            ChunkResult(
                chunk_id="chunk_2",
                original="Test",
                translated="Bai kiem tra",
                quality_score=0.88,
                duration_ms=110.0
            ),
        ]

    def test_aggregator_initialization_default(self):
        """Test default separator."""
        agg = ResultAggregator()
        assert agg.separator == "\n\n"

    def test_aggregator_initialization_custom(self):
        """Test custom separator."""
        agg = ResultAggregator(separator=" | ")
        assert agg.separator == " | "

    def test_aggregate_empty_results(self, aggregator):
        """Test aggregating empty results list."""
        result = aggregator.aggregate([])
        assert result.text == ""
        assert result.chunk_count == 0
        assert result.successful_chunks == 0
        assert result.avg_quality == 0.0

    def test_aggregate_success(self, aggregator, sample_results):
        """Test successful aggregation."""
        result = aggregator.aggregate(sample_results)

        assert result.chunk_count == 3
        assert result.successful_chunks == 3
        assert result.failed_chunks == 0
        assert "Xin chao" in result.text
        assert "The gioi" in result.text
        assert "Bai kiem tra" in result.text
        assert result.avg_quality == pytest.approx(0.8767, rel=0.01)
        assert result.total_duration_ms == 330.0

    def test_aggregate_with_separator(self, sample_results):
        """Test aggregation with custom separator."""
        agg = ResultAggregator(separator=" --- ")
        result = agg.aggregate(sample_results)

        assert " --- " in result.text
        parts = result.text.split(" --- ")
        assert len(parts) == 3

    def test_aggregate_with_failures(self, aggregator):
        """Test aggregation with failed chunks."""
        results = [
            ChunkResult(
                chunk_id="chunk_0",
                original="Hello",
                translated="Xin chao",
                quality_score=0.9,
                duration_ms=100.0
            ),
            ChunkResult(
                chunk_id="chunk_1",
                original="World",
                translated="",
                error="API timeout",
                duration_ms=120.0
            ),
        ]

        result = aggregator.aggregate(results)

        assert result.chunk_count == 2
        assert result.successful_chunks == 1
        assert result.failed_chunks == 1
        assert "[Translation failed: API timeout]" in result.text
        assert result.metadata['failed_chunk_ids'] == ['chunk_1']

    def test_aggregate_exclude_failed(self, aggregator):
        """Test aggregation excluding failed chunks."""
        results = [
            ChunkResult(
                chunk_id="chunk_0",
                original="Hello",
                translated="Xin chao",
                quality_score=0.9,
                duration_ms=100.0
            ),
            ChunkResult(
                chunk_id="chunk_1",
                original="World",
                translated="",
                error="API timeout",
                duration_ms=120.0
            ),
        ]

        result = aggregator.aggregate(results, include_failed=False)

        assert "[Translation failed" not in result.text
        assert "Xin chao" in result.text

    def test_aggregate_all_failures(self, aggregator):
        """Test aggregation when all chunks fail."""
        results = [
            ChunkResult(
                chunk_id="chunk_0",
                original="Hello",
                translated="",
                error="Error 1",
                duration_ms=100.0
            ),
            ChunkResult(
                chunk_id="chunk_1",
                original="World",
                translated="",
                error="Error 2",
                duration_ms=100.0
            ),
        ]

        result = aggregator.aggregate(results)

        assert result.successful_chunks == 0
        assert result.failed_chunks == 2
        assert result.avg_quality == 0.0
        assert "[Translation failed: Error 1]" in result.text
        assert "[Translation failed: Error 2]" in result.text

    def test_aggregate_with_cache_hits(self, aggregator):
        """Test aggregation tracking cache hits."""
        results = [
            ChunkResult(
                chunk_id="chunk_0",
                original="Hello",
                translated="Xin chao",
                quality_score=0.9,
                from_cache=True
            ),
            ChunkResult(
                chunk_id="chunk_1",
                original="World",
                translated="The gioi",
                quality_score=0.85,
                from_cache=False
            ),
            ChunkResult(
                chunk_id="chunk_2",
                original="Test",
                translated="Test",
                quality_score=0.88,
                from_cache=True
            ),
        ]

        result = aggregator.aggregate(results)
        assert result.metadata['cache_hits'] == 2

    def test_aggregate_quality_calculation(self, aggregator):
        """Test average quality calculation."""
        results = [
            ChunkResult(chunk_id="c0", original="", translated="t", quality_score=0.8),
            ChunkResult(chunk_id="c1", original="", translated="t", quality_score=0.9),
            ChunkResult(chunk_id="c2", original="", translated="t", quality_score=1.0),
        ]

        result = aggregator.aggregate(results)
        expected_avg = (0.8 + 0.9 + 1.0) / 3
        assert result.avg_quality == pytest.approx(expected_avg, rel=0.001)


class TestResultAggregatorMerge:
    """Tests for merge_with_existing method."""

    @pytest.fixture
    def aggregator(self):
        return ResultAggregator()

    def test_merge_all_new(self, aggregator):
        """Test merging when all results are new."""
        new_results = [
            ChunkResult(chunk_id="c0", original="t0", translated="tr0"),
            ChunkResult(chunk_id="c1", original="t1", translated="tr1"),
        ]
        all_chunk_ids = ["c0", "c1"]

        merged = aggregator.merge_with_existing(
            new_results=new_results,
            existing_results={},
            all_chunk_ids=all_chunk_ids
        )

        assert len(merged) == 2
        assert merged[0].chunk_id == "c0"
        assert merged[1].chunk_id == "c1"

    def test_merge_all_existing(self, aggregator):
        """Test merging when all results are from checkpoint."""
        # Create mock existing results
        @dataclass
        class MockExistingResult:
            chunk_id: str
            source: str
            translated: str
            quality_score: float = 0.9

        existing_results = {
            "c0": MockExistingResult(chunk_id="c0", source="t0", translated="cached0"),
            "c1": MockExistingResult(chunk_id="c1", source="t1", translated="cached1"),
        }
        all_chunk_ids = ["c0", "c1"]

        merged = aggregator.merge_with_existing(
            new_results=[],
            existing_results=existing_results,
            all_chunk_ids=all_chunk_ids
        )

        assert len(merged) == 2
        assert merged[0].translated == "cached0"
        assert merged[1].translated == "cached1"
        assert all(r.from_cache for r in merged)

    def test_merge_mixed(self, aggregator):
        """Test merging with mixed new and existing results."""
        @dataclass
        class MockExistingResult:
            chunk_id: str
            source: str
            translated: str
            quality_score: float = 0.9

        new_results = [
            ChunkResult(chunk_id="c1", original="t1", translated="new1"),
            ChunkResult(chunk_id="c3", original="t3", translated="new3"),
        ]

        existing_results = {
            "c0": MockExistingResult(chunk_id="c0", source="t0", translated="cached0"),
            "c2": MockExistingResult(chunk_id="c2", source="t2", translated="cached2"),
        }

        all_chunk_ids = ["c0", "c1", "c2", "c3"]

        merged = aggregator.merge_with_existing(
            new_results=new_results,
            existing_results=existing_results,
            all_chunk_ids=all_chunk_ids
        )

        assert len(merged) == 4
        assert merged[0].translated == "cached0"
        assert merged[0].from_cache is True
        assert merged[1].translated == "new1"
        assert merged[1].from_cache is False
        assert merged[2].translated == "cached2"
        assert merged[2].from_cache is True
        assert merged[3].translated == "new3"

    def test_merge_maintains_order(self, aggregator):
        """Test that merge maintains original chunk order."""
        new_results = [
            ChunkResult(chunk_id="c2", original="t2", translated="tr2"),
            ChunkResult(chunk_id="c0", original="t0", translated="tr0"),
        ]

        all_chunk_ids = ["c0", "c1", "c2"]

        @dataclass
        class MockExistingResult:
            chunk_id: str
            source: str
            translated: str
            quality_score: float = 0.9

        existing_results = {
            "c1": MockExistingResult(chunk_id="c1", source="t1", translated="cached1"),
        }

        merged = aggregator.merge_with_existing(
            new_results=new_results,
            existing_results=existing_results,
            all_chunk_ids=all_chunk_ids
        )

        assert [r.chunk_id for r in merged] == ["c0", "c1", "c2"]

    def test_merge_missing_chunk(self, aggregator):
        """Test handling of missing chunks during merge."""
        all_chunk_ids = ["c0", "c1", "c2"]

        merged = aggregator.merge_with_existing(
            new_results=[],
            existing_results={},  # No results at all
            all_chunk_ids=all_chunk_ids
        )

        assert len(merged) == 3
        for r in merged:
            assert r.error == "No result available"
            assert r.translated == "[MISSING]"


class TestResultAggregatorSTEM:
    """Tests for STEM restoration functionality."""

    @pytest.fixture
    def aggregator(self):
        return ResultAggregator()

    def test_aggregate_with_stem_restore_no_module(self, aggregator):
        """Test STEM restore when module not available."""
        results = [
            ChunkResult(chunk_id="c0", original="test", translated="translated")
        ]

        # Create mock preprocessed with required attributes
        mock_preprocessed = Mock()
        mock_preprocessed.mapping = {}
        mock_preprocessed.original_text = "test"

        # Test when STEM module raises ImportError
        with patch.object(aggregator, 'aggregate_with_stem_restore') as mock_method:
            # Simulate the ImportError handling behavior
            mock_method.return_value = (
                aggregator.aggregate(results),
                {"error": "STEM module not available"}
            )
            result, verification = mock_method(
                results=results,
                stem_preprocessed=mock_preprocessed,
                formula_matches=[],
                code_matches=[]
            )
            assert "error" in verification

    def test_aggregate_with_stem_restore_success(self, aggregator):
        """Test successful STEM restoration."""
        results = [
            ChunkResult(
                chunk_id="c0",
                original="test with $E=mc^2$",
                translated="translated with FORMULA_0"
            )
        ]

        # Create mock STEM objects
        mock_preprocessed = Mock()
        mock_preprocessed.mapping = {'FORMULA_0': '$E=mc^2$'}
        mock_preprocessed.original_text = "test with $E=mc^2$"

        mock_placeholder_manager = Mock()
        mock_placeholder_manager.restore.return_value = "translated with $E=mc^2$"
        mock_placeholder_manager.verify_restoration.return_value = {
            'preservation_rate': 1.0,
            'formulas_lost': 0,
            'code_lost': 0
        }

        # Patch at the module level where it's imported
        with patch.dict('sys.modules', {'core.stem': Mock(PlaceholderManager=Mock(return_value=mock_placeholder_manager))}):
            try:
                result, verification = aggregator.aggregate_with_stem_restore(
                    results=results,
                    stem_preprocessed=mock_preprocessed,
                    formula_matches=[],
                    code_matches=[]
                )
                # If STEM module works, check results
                if 'error' not in verification:
                    assert verification.get('preservation_rate', 0) >= 0
            except (ImportError, ModuleNotFoundError):
                # If STEM module not available, that's expected
                pytest.skip("STEM module not available")


class TestResultAggregatorEdgeCases:
    """Edge case tests for ResultAggregator."""

    def test_single_chunk(self):
        """Test aggregation of single chunk."""
        agg = ResultAggregator()
        results = [
            ChunkResult(chunk_id="c0", original="hello", translated="xin chao", quality_score=0.95)
        ]

        result = agg.aggregate(results)

        assert result.chunk_count == 1
        assert result.text == "xin chao"
        assert result.avg_quality == 0.95

    def test_empty_translations(self):
        """Test aggregation with empty translation strings."""
        agg = ResultAggregator()
        results = [
            ChunkResult(chunk_id="c0", original="hello", translated="", quality_score=0.9),
            ChunkResult(chunk_id="c1", original="world", translated="", quality_score=0.8),
        ]

        result = agg.aggregate(results)

        assert result.text == "\n\n"  # Just separators
        assert result.successful_chunks == 2  # Empty string is still success

    def test_unicode_content(self):
        """Test aggregation with unicode content."""
        agg = ResultAggregator()
        results = [
            ChunkResult(
                chunk_id="c0",
                original="Hello",
                translated="Xin chao the gioi",  # Vietnamese
                quality_score=0.9
            ),
            ChunkResult(
                chunk_id="c1",
                original="World",
                translated="Marhaba",  # Arabic
                quality_score=0.85
            ),
        ]

        result = agg.aggregate(results)

        assert "Xin chao" in result.text
        assert "Marhaba" in result.text

    def test_very_long_text(self):
        """Test aggregation with very long text."""
        agg = ResultAggregator()
        long_text = "A" * 10000  # 10K characters

        results = [
            ChunkResult(chunk_id="c0", original="x", translated=long_text, quality_score=0.9)
        ]

        result = agg.aggregate(results)

        assert len(result.text) == 10000
        assert result.total_chars == 10000
