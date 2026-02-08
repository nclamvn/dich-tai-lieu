"""
Unit tests for api/services/translation_memory.py — TM Service with fuzzy matching.

Uses test file name test_tm_service.py to avoid conflict with existing
test_translation_memory.py (which tests core/translation_memory.py).

Target: 90%+ coverage.
"""

import json
from pathlib import Path

import pytest

from api.services.translation_memory import (
    TranslationMemoryService,
    TMSegment,
    TMMatch,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tm():
    """In-memory TM (no persistence)."""
    return TranslationMemoryService()


@pytest.fixture
def tm_with_data(tm):
    """TM with pre-loaded segments."""
    tm.add_segment("en", "vi", "heart", "tim", domain="medical")
    tm.add_segment("en", "vi", "lung", "phổi", domain="medical")
    tm.add_segment("en", "vi", "hello", "xin chào", domain="general")
    tm.add_segment("en", "vi", "the heart is a muscle", "tim là một cơ", domain="medical")
    return tm


@pytest.fixture
def persistent_tm(tmp_path):
    """TM with JSON persistence."""
    path = str(tmp_path / "tm.json")
    return TranslationMemoryService(storage_path=path), path


# ---------------------------------------------------------------------------
# TMSegment
# ---------------------------------------------------------------------------

class TestTMSegment:
    def test_defaults(self):
        seg = TMSegment(source="a", target="b")
        assert seg.source_lang == "en"
        assert seg.target_lang == "vi"
        assert seg.domain == "general"
        assert seg.quality_score == 1.0
        assert seg.use_count == 0
        assert seg.created_at > 0

    def test_lang_pair(self):
        seg = TMSegment(source="a", target="b", source_lang="ja", target_lang="en")
        assert seg.lang_pair == "ja→en"

    def test_custom_fields(self):
        seg = TMSegment(
            source="heart", target="tim",
            domain="medical", quality_score=0.9,
            context="anatomy chapter",
        )
        assert seg.domain == "medical"
        assert seg.quality_score == 0.9
        assert seg.context == "anatomy chapter"


# ---------------------------------------------------------------------------
# TMMatch
# ---------------------------------------------------------------------------

class TestTMMatch:
    def test_exact_match(self):
        seg = TMSegment(source="a", target="b")
        match = TMMatch(segment=seg, similarity=1.0, match_type="exact")
        assert match.is_exact is True

    def test_fuzzy_match(self):
        seg = TMSegment(source="a", target="b")
        match = TMMatch(segment=seg, similarity=0.8, match_type="fuzzy")
        assert match.is_exact is False
        assert match.similarity == 0.8


# ---------------------------------------------------------------------------
# Add segments
# ---------------------------------------------------------------------------

class TestAddSegment:
    def test_add_basic(self, tm):
        seg = tm.add_segment("en", "vi", "hello", "xin chào")
        assert seg.source == "hello"
        assert seg.target == "xin chào"
        assert tm.segment_count == 1

    def test_add_with_domain(self, tm):
        seg = tm.add_segment("en", "vi", "heart", "tim", domain="medical")
        assert seg.domain == "medical"

    def test_add_duplicate_updates(self, tm):
        tm.add_segment("en", "vi", "hello", "xin chào")
        tm.add_segment("en", "vi", "hello", "chào bạn")
        assert tm.segment_count == 1
        match = tm.find_exact("en", "vi", "hello")
        assert match.segment.target == "chào bạn"

    def test_add_duplicate_increments_use_count(self, tm):
        tm.add_segment("en", "vi", "hello", "xin chào")
        tm.add_segment("en", "vi", "hello", "xin chào v2")
        match = tm.find_exact("en", "vi", "hello")
        assert match.segment.use_count >= 1

    def test_add_different_domains_not_duplicate(self, tm):
        tm.add_segment("en", "vi", "heart", "tim", domain="medical")
        tm.add_segment("en", "vi", "heart", "trái tim", domain="general")
        assert tm.segment_count == 2

    def test_add_strips_whitespace(self, tm):
        tm.add_segment("en", "vi", "  hello  ", "  xin chào  ")
        match = tm.find_exact("en", "vi", "hello")
        assert match is not None
        assert match.segment.source == "hello"

    def test_add_batch(self, tm):
        pairs = [("hello", "xin chào"), ("goodbye", "tạm biệt"), ("", "")]
        count = tm.add_batch("en", "vi", pairs)
        assert count == 2  # empty pair skipped
        assert tm.segment_count == 2

    def test_add_batch_empty(self, tm):
        assert tm.add_batch("en", "vi", []) == 0


# ---------------------------------------------------------------------------
# Exact matching
# ---------------------------------------------------------------------------

class TestExactMatch:
    def test_exact_found(self, tm_with_data):
        match = tm_with_data.find_exact("en", "vi", "heart")
        assert match is not None
        assert match.similarity == 1.0
        assert match.match_type == "exact"
        assert match.segment.target == "tim"

    def test_exact_not_found(self, tm_with_data):
        assert tm_with_data.find_exact("en", "vi", "kidney") is None

    def test_exact_case_insensitive(self, tm_with_data):
        match = tm_with_data.find_exact("en", "vi", "HEART")
        assert match is not None

    def test_exact_wrong_lang_pair(self, tm_with_data):
        assert tm_with_data.find_exact("vi", "en", "heart") is None

    def test_exact_with_domain_filter(self, tm_with_data):
        match = tm_with_data.find_exact("en", "vi", "heart", domain="medical")
        assert match is not None

    def test_exact_domain_mismatch(self, tm_with_data):
        assert tm_with_data.find_exact("en", "vi", "heart", domain="legal") is None

    def test_exact_increments_use_count(self, tm_with_data):
        tm_with_data.find_exact("en", "vi", "heart")
        tm_with_data.find_exact("en", "vi", "heart")
        match = tm_with_data.find_exact("en", "vi", "heart")
        assert match.segment.use_count >= 2


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

class TestFuzzyMatch:
    def test_fuzzy_finds_similar(self, tm_with_data):
        matches = tm_with_data.find_fuzzy("en", "vi", "hearts", threshold=0.7)
        assert len(matches) >= 1
        assert matches[0].segment.target == "tim"

    def test_fuzzy_no_results_below_threshold(self, tm_with_data):
        matches = tm_with_data.find_fuzzy("en", "vi", "xyz", threshold=0.9)
        assert len(matches) == 0

    def test_fuzzy_sorted_by_similarity(self, tm_with_data):
        matches = tm_with_data.find_fuzzy("en", "vi", "heart", threshold=0.5)
        for i in range(len(matches) - 1):
            assert matches[i].similarity >= matches[i + 1].similarity

    def test_fuzzy_max_results(self, tm):
        for i in range(10):
            tm.add_segment("en", "vi", f"test word {i}", f"từ {i}")
        matches = tm.find_fuzzy("en", "vi", "test word", max_results=3, threshold=0.5)
        assert len(matches) <= 3

    def test_fuzzy_with_domain_filter(self, tm_with_data):
        matches = tm_with_data.find_fuzzy(
            "en", "vi", "hearts", threshold=0.5, domain="medical",
        )
        assert all(m.segment.domain == "medical" for m in matches)

    def test_fuzzy_wrong_lang_pair(self, tm_with_data):
        matches = tm_with_data.find_fuzzy("ja", "en", "heart", threshold=0.5)
        assert len(matches) == 0

    def test_fuzzy_exact_returns_exact_type(self, tm_with_data):
        matches = tm_with_data.find_fuzzy("en", "vi", "heart", threshold=0.5)
        exact = [m for m in matches if m.match_type == "exact"]
        assert len(exact) >= 1

    def test_fuzzy_sentence_similarity(self, tm_with_data):
        matches = tm_with_data.find_fuzzy(
            "en", "vi", "the heart is a strong muscle", threshold=0.5,
        )
        assert len(matches) >= 1


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

class TestSimilarity:
    def test_identical(self):
        assert TranslationMemoryService._similarity("abc", "abc") == 1.0

    def test_empty_strings(self):
        assert TranslationMemoryService._similarity("", "") == 1.0

    def test_one_empty(self):
        assert TranslationMemoryService._similarity("abc", "") == 0.0
        assert TranslationMemoryService._similarity("", "abc") == 0.0

    def test_similar(self):
        s = TranslationMemoryService._similarity("heart", "hearts")
        assert 0.7 < s < 1.0

    def test_different(self):
        s = TranslationMemoryService._similarity("heart", "xyz")
        assert s < 0.5


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStatistics:
    def test_empty_stats(self, tm):
        stats = tm.get_statistics()
        assert stats["total_segments"] == 0
        assert stats["language_pairs"] == []
        assert stats["domains"] == []

    def test_stats_with_data(self, tm_with_data):
        stats = tm_with_data.get_statistics()
        assert stats["total_segments"] == 4
        assert "en→vi" in stats["language_pairs"]
        assert "medical" in stats["domains"]
        assert "general" in stats["domains"]
        assert stats["avg_quality"] == 1.0

    def test_clear(self, tm_with_data):
        tm_with_data.clear()
        assert tm_with_data.segment_count == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_persists_to_disk(self, persistent_tm):
        tm, path = persistent_tm
        tm.add_segment("en", "vi", "hello", "xin chào")

        data = json.loads(Path(path).read_text())
        assert len(data) == 1
        assert data[0]["source"] == "hello"

    def test_reload_from_disk(self, tmp_path):
        path = str(tmp_path / "tm.json")

        tm1 = TranslationMemoryService(storage_path=path)
        tm1.add_segment("en", "vi", "heart", "tim")

        tm2 = TranslationMemoryService(storage_path=path)
        assert tm2.segment_count == 1
        match = tm2.find_exact("en", "vi", "heart")
        assert match is not None
        assert match.segment.target == "tim"

    def test_no_persistence_without_path(self, tm):
        tm.add_segment("en", "vi", "hello", "xin chào")
        # No crash, just in-memory
        assert tm.segment_count == 1

    def test_corrupt_file_handled(self, tmp_path):
        path = tmp_path / "tm.json"
        path.write_text("not json")
        tm = TranslationMemoryService(storage_path=str(path))
        assert tm.segment_count == 0
