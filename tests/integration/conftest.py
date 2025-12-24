#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest fixtures for integration tests.

Provides:
- stress_test_dir: Path to stress test files
- mock_translator: Mock translator that doesn't call real API
- temp_output_dir: Temporary directory for test outputs
- checkpoint_db: Temporary checkpoint database
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def stress_test_dir():
    """Path to stress test files directory."""
    path = PROJECT_ROOT / "tests" / "fixtures" / "stress_test"
    if not path.exists():
        pytest.skip(f"Stress test files not found at {path}")
    return path


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test outputs."""
    temp_dir = Path(tempfile.mkdtemp(prefix="translator_test_"))
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_checkpoint_db(temp_output_dir):
    """Temporary checkpoint database."""
    from core.cache.checkpoint_manager import CheckpointManager
    db_path = temp_output_dir / "test_checkpoint.db"
    manager = CheckpointManager(db_path)
    yield manager
    # Cleanup handled by temp_output_dir


@pytest.fixture
def mock_translator():
    """
    Mock translator that returns predictable translations without API calls.

    Translation format: "TRANSLATED: {original_text}"
    This allows us to verify content is preserved through the pipeline.
    """
    class MockTranslator:
        def __init__(self):
            self.call_count = 0
            self.translated_chunks = []

        async def translate_chunk(self, client, chunk):
            """Mock translation - prefix with TRANSLATED:"""
            from core.validator import TranslationResult

            self.call_count += 1
            self.translated_chunks.append(chunk.id)

            # Simple mock: prefix with TRANSLATED and keep original
            translated_text = f"TRANSLATED: {chunk.text}"

            # Copy overlap_char_count from chunk
            overlap_count = getattr(chunk, 'overlap_char_count', 0)

            return TranslationResult(
                chunk_id=chunk.id,
                source=chunk.text,
                translated=translated_text,
                quality_score=0.95,
                overlap_char_count=overlap_count
            )

        def reset(self):
            """Reset counters for new test."""
            self.call_count = 0
            self.translated_chunks = []

    return MockTranslator()


@pytest.fixture
def chunker():
    """Standard SmartChunker instance for testing."""
    from core.chunker import SmartChunker
    return SmartChunker(max_chars=2000, context_window=200)


@pytest.fixture
def merger():
    """SmartMerger class for testing."""
    from core.merger import SmartMerger
    return SmartMerger


# ============================================================================
# HELPER FUNCTIONS (available to all tests)
# ============================================================================

def count_duplicate_paragraphs(text: str) -> dict:
    """
    Count paragraphs that appear more than once.

    Returns:
        Dict with 'total_paragraphs', 'unique_paragraphs', 'duplicates' (list)
    """
    # Split by double newlines
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    # Filter out very short paragraphs (headers, markers)
    meaningful_paragraphs = [p for p in paragraphs if len(p) > 50]

    # Count occurrences
    from collections import Counter
    counts = Counter(meaningful_paragraphs)

    duplicates = [(p[:100] + "...", count) for p, count in counts.items() if count > 1]

    return {
        'total_paragraphs': len(meaningful_paragraphs),
        'unique_paragraphs': len(counts),
        'duplicate_count': len(duplicates),
        'duplicates': duplicates
    }


def verify_chapter_order(text: str, chapter_pattern: str = r"CHAPTER (\d+)") -> bool:
    """
    Verify chapters appear in correct ascending order.

    Args:
        text: Document text
        chapter_pattern: Regex pattern to match chapter numbers

    Returns:
        True if chapters are in order
    """
    import re
    matches = re.findall(chapter_pattern, text)
    if not matches:
        return True  # No chapters to check

    chapter_numbers = [int(m) for m in matches]
    return chapter_numbers == sorted(chapter_numbers)


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity ratio using SequenceMatcher.

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    from difflib import SequenceMatcher
    return SequenceMatcher(None, text1, text2).ratio()


def extract_chunk_markers(text: str) -> list:
    """
    Extract [CHUNK_BOUNDARY_XXX] markers from text.

    Returns:
        List of chunk numbers found
    """
    import re
    matches = re.findall(r'\[CHUNK_BOUNDARY_(\d+)\]', text)
    return [int(m) for m in matches]


def check_code_blocks_intact(text: str) -> dict:
    """
    Check if code blocks are intact (not split mid-block).

    Returns:
        Dict with 'total_blocks', 'intact_blocks', 'broken_blocks'
    """
    import re

    # Find all code block starts and ends
    starts = list(re.finditer(r'```\w*\n', text))
    ends = list(re.finditer(r'\n```', text))

    # Simple check: equal number of starts and ends
    intact = len(starts) == len(ends)

    return {
        'total_starts': len(starts),
        'total_ends': len(ends),
        'intact': intact
    }


def check_tables_intact(text: str) -> bool:
    """
    Check if markdown tables are intact (header, separator, rows together).

    Returns:
        True if tables appear intact
    """
    import re

    # Find table patterns (| col | col |)
    table_lines = re.findall(r'^\|[^|]+\|.*$', text, re.MULTILINE)

    if not table_lines:
        return True  # No tables

    # Check that separator lines (|---|---|) exist
    separator_lines = [l for l in table_lines if re.match(r'^\|[-:|]+\|', l)]

    return len(separator_lines) > 0


# Make helper functions available as fixtures too
@pytest.fixture
def helpers():
    """Bundle of helper functions."""
    class Helpers:
        count_duplicate_paragraphs = staticmethod(count_duplicate_paragraphs)
        verify_chapter_order = staticmethod(verify_chapter_order)
        calculate_similarity = staticmethod(calculate_similarity)
        extract_chunk_markers = staticmethod(extract_chunk_markers)
        check_code_blocks_intact = staticmethod(check_code_blocks_intact)
        check_tables_intact = staticmethod(check_tables_intact)

    return Helpers()
