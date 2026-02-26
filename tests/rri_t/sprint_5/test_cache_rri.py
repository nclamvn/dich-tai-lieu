"""
RRI-T Sprint 5: Chunk Cache + Checkpoint Manager tests.

Persona coverage: DevOps, QA Destroyer, Business Analyst
Dimensions: D3 (Performance), D5 (Data Integrity), D7 (Edge Cases)
"""

import time
from pathlib import Path

import pytest

from core.cache.chunk_cache import ChunkCache, compute_chunk_key
from core.cache.checkpoint_manager import CheckpointManager, CheckpointState


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cache(tmp_path):
    db_path = tmp_path / "test_chunks.db"
    c = ChunkCache(db_path=db_path)
    yield c
    c.close()


@pytest.fixture
def checkpoint_mgr(tmp_path):
    db_path = tmp_path / "test_checkpoints.db"
    mgr = CheckpointManager(db_path=db_path)
    yield mgr


# ===========================================================================
# CACHE-001: Key generation
# ===========================================================================

class TestCacheKeyGeneration:
    """QA Destroyer persona — cache key stability."""

    @pytest.mark.p0
    def test_cache_001_stable_key(self):
        """CACHE-001 | QA | Same input -> same key (deterministic)"""
        k1 = compute_chunk_key("Hello world", "en", "vi", "simple")
        k2 = compute_chunk_key("Hello world", "en", "vi", "simple")
        assert k1 == k2

    @pytest.mark.p0
    def test_cache_001b_different_text_different_key(self):
        """CACHE-001b | QA | Different text -> different key"""
        k1 = compute_chunk_key("Hello", "en", "vi")
        k2 = compute_chunk_key("Goodbye", "en", "vi")
        assert k1 != k2

    @pytest.mark.p0
    def test_cache_001c_different_lang_different_key(self):
        """CACHE-001c | QA | Different target lang -> different key"""
        k1 = compute_chunk_key("Hello", "en", "vi")
        k2 = compute_chunk_key("Hello", "en", "fr")
        assert k1 != k2

    @pytest.mark.p1
    def test_cache_001d_mode_affects_key(self):
        """CACHE-001d | QA | Different mode -> different key"""
        k1 = compute_chunk_key("Hello", "en", "vi", "simple")
        k2 = compute_chunk_key("Hello", "en", "vi", "academic")
        assert k1 != k2

    @pytest.mark.p1
    def test_cache_001e_key_is_hex_string(self):
        """CACHE-001e | QA | Key is a 64-char hex SHA256"""
        key = compute_chunk_key("test", "en", "vi")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    @pytest.mark.p1
    def test_cache_001f_whitespace_normalized(self):
        """CACHE-001f | QA | Leading/trailing whitespace stripped"""
        k1 = compute_chunk_key("  Hello  ", "en", "vi")
        k2 = compute_chunk_key("Hello", "en", "vi")
        assert k1 == k2


# ===========================================================================
# CACHE-002: Set/Get operations
# ===========================================================================

class TestCacheOperations:
    """DevOps persona — cache CRUD."""

    @pytest.mark.p0
    def test_cache_002_set_and_get(self, cache):
        """CACHE-002 | DevOps | set -> get returns same value"""
        key = compute_chunk_key("Hello world", "en", "vi")
        cache.set(key, "Xin chào thế giới", source_lang="en", target_lang="vi")

        result = cache.get(key)
        assert result == "Xin chào thế giới"

    @pytest.mark.p0
    def test_cache_002b_miss_returns_none(self, cache):
        """CACHE-002b | QA | Cache miss returns None"""
        result = cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.p1
    def test_cache_002c_overwrite_existing(self, cache):
        """CACHE-002c | QA | Set same key twice -> latest value wins"""
        key = compute_chunk_key("test", "en", "vi")
        cache.set(key, "old translation")
        cache.set(key, "new translation")

        result = cache.get(key)
        assert result == "new translation"

    @pytest.mark.p1
    def test_cache_002d_unicode_values(self, cache):
        """CACHE-002d | QA | Unicode values stored correctly"""
        key = compute_chunk_key("emoji test", "en", "vi")
        value = "Xin chào 🌍 世界 مرحبا"
        cache.set(key, value)
        assert cache.get(key) == value

    @pytest.mark.p1
    def test_cache_002e_clear_removes_all(self, cache):
        """CACHE-002e | DevOps | clear() removes all entries"""
        for i in range(5):
            key = compute_chunk_key(f"text {i}", "en", "vi")
            cache.set(key, f"translation {i}")

        cache.clear()
        stats = cache.stats()
        assert stats["total_entries"] == 0


# ===========================================================================
# CACHE-003: Hit/miss statistics
# ===========================================================================

class TestCacheStats:
    """Business Analyst persona — cache analytics."""

    @pytest.mark.p0
    def test_cache_003_stats_structure(self, cache):
        """CACHE-003 | BA | stats() has all expected keys"""
        stats = cache.stats()
        expected_keys = ["total_entries", "hits", "misses", "hit_rate", "db_size_mb"]
        for key in expected_keys:
            assert key in stats, f"Missing key: {key}"

    @pytest.mark.p1
    def test_cache_003b_hit_miss_tracking(self, cache):
        """CACHE-003b | BA | Hits and misses counted accurately"""
        key = compute_chunk_key("tracked", "en", "vi")
        cache.set(key, "value")

        cache.get(key)        # hit
        cache.get(key)        # hit
        cache.get("missing")  # miss

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    @pytest.mark.p1
    def test_cache_003c_hit_rate_calculation(self, cache):
        """CACHE-003c | BA | Hit rate calculated correctly"""
        key = compute_chunk_key("rate test", "en", "vi")
        cache.set(key, "val")

        cache.get(key)        # hit
        cache.get("missing")  # miss

        stats = cache.stats()
        assert stats["hit_rate"] == pytest.approx(0.5, abs=0.01)

    @pytest.mark.p1
    def test_cache_003d_empty_cache_zero_rate(self, cache):
        """CACHE-003d | QA | No requests -> hit_rate = 0.0"""
        stats = cache.stats()
        assert stats["hit_rate"] == 0.0
        assert stats["total_entries"] == 0


# ===========================================================================
# CHKPT-001: Checkpoint save/load
# ===========================================================================

class TestCheckpointSaveLoad:
    """DevOps persona — checkpoint persistence."""

    @pytest.mark.p0
    def test_chkpt_001_save_and_load(self, checkpoint_mgr):
        """CHKPT-001 | DevOps | Save checkpoint -> load returns same state"""
        checkpoint_mgr.save_checkpoint(
            job_id="job-1",
            input_file="/tmp/input.pdf",
            output_file="/tmp/output.docx",
            total_chunks=10,
            completed_chunk_ids=["c1", "c2", "c3"],
            results_data={"c1": {"text": "translated1"}, "c2": {"text": "translated2"}},
            job_metadata={"lang_pair": "en->vi"},
        )

        state = checkpoint_mgr.load_checkpoint("job-1")
        assert state is not None
        assert state.job_id == "job-1"
        assert state.total_chunks == 10
        assert len(state.completed_chunk_ids) == 3
        assert state.job_metadata["lang_pair"] == "en->vi"

    @pytest.mark.p0
    def test_chkpt_001b_load_nonexistent(self, checkpoint_mgr):
        """CHKPT-001b | QA | Load non-existent checkpoint -> None"""
        assert checkpoint_mgr.load_checkpoint("no-such-job") is None

    @pytest.mark.p0
    def test_chkpt_001c_has_checkpoint(self, checkpoint_mgr):
        """CHKPT-001c | DevOps | has_checkpoint reflects save state"""
        assert not checkpoint_mgr.has_checkpoint("job-2")

        checkpoint_mgr.save_checkpoint(
            job_id="job-2", input_file="in", output_file="out",
            total_chunks=5, completed_chunk_ids=[], results_data={},
        )
        assert checkpoint_mgr.has_checkpoint("job-2")

    @pytest.mark.p1
    def test_chkpt_001d_update_checkpoint(self, checkpoint_mgr):
        """CHKPT-001d | DevOps | Save twice updates completed chunks"""
        checkpoint_mgr.save_checkpoint(
            job_id="job-3", input_file="in", output_file="out",
            total_chunks=5, completed_chunk_ids=["c1"],
            results_data={"c1": {"text": "t1"}},
        )
        checkpoint_mgr.save_checkpoint(
            job_id="job-3", input_file="in", output_file="out",
            total_chunks=5, completed_chunk_ids=["c1", "c2"],
            results_data={"c1": {"text": "t1"}, "c2": {"text": "t2"}},
        )

        state = checkpoint_mgr.load_checkpoint("job-3")
        assert len(state.completed_chunk_ids) == 2


# ===========================================================================
# CHKPT-002: Completion tracking
# ===========================================================================

class TestCheckpointCompletion:
    """Business Analyst persona — progress tracking."""

    @pytest.mark.p0
    def test_chkpt_002_completion_percentage(self):
        """CHKPT-002 | BA | completion_percentage calculated correctly"""
        state = CheckpointState(
            job_id="j1", input_file="in", output_file="out",
            total_chunks=10, completed_chunk_ids=["c1", "c2", "c3"],
            results_data={}, job_metadata={},
            created_at=time.time(), updated_at=time.time(),
        )
        assert state.completion_percentage() == pytest.approx(0.3)

    @pytest.mark.p1
    def test_chkpt_002b_remaining_chunks(self):
        """CHKPT-002b | BA | remaining_chunks = total - completed"""
        state = CheckpointState(
            job_id="j2", input_file="in", output_file="out",
            total_chunks=10, completed_chunk_ids=["c1", "c2"],
            results_data={}, job_metadata={},
            created_at=time.time(), updated_at=time.time(),
        )
        assert state.remaining_chunks() == 8

    @pytest.mark.p1
    def test_chkpt_002c_zero_total_chunks(self):
        """CHKPT-002c | QA | Zero total chunks -> 0% completion"""
        state = CheckpointState(
            job_id="j3", input_file="in", output_file="out",
            total_chunks=0, completed_chunk_ids=[],
            results_data={}, job_metadata={},
            created_at=time.time(), updated_at=time.time(),
        )
        assert state.completion_percentage() == 0.0


# ===========================================================================
# CHKPT-003: Delete & cleanup
# ===========================================================================

class TestCheckpointCleanup:
    """DevOps persona — checkpoint lifecycle."""

    @pytest.mark.p1
    def test_chkpt_003_delete_checkpoint(self, checkpoint_mgr):
        """CHKPT-003 | DevOps | Delete removes checkpoint"""
        checkpoint_mgr.save_checkpoint(
            job_id="del-1", input_file="in", output_file="out",
            total_chunks=5, completed_chunk_ids=[], results_data={},
        )
        assert checkpoint_mgr.delete_checkpoint("del-1") is True
        assert checkpoint_mgr.load_checkpoint("del-1") is None

    @pytest.mark.p1
    def test_chkpt_003b_delete_nonexistent(self, checkpoint_mgr):
        """CHKPT-003b | QA | Delete non-existent -> False"""
        assert checkpoint_mgr.delete_checkpoint("no-such") is False

    @pytest.mark.p1
    def test_chkpt_003c_list_checkpoints(self, checkpoint_mgr):
        """CHKPT-003c | DevOps | list_checkpoints returns all saved"""
        for i in range(3):
            checkpoint_mgr.save_checkpoint(
                job_id=f"list-{i}", input_file="in", output_file="out",
                total_chunks=5, completed_chunk_ids=[], results_data={},
            )

        checkpoints = checkpoint_mgr.list_checkpoints()
        assert len(checkpoints) == 3

    @pytest.mark.p1
    def test_chkpt_003d_cleanup_old(self, checkpoint_mgr):
        """CHKPT-003d | DevOps | cleanup_old_checkpoints removes old entries"""
        checkpoint_mgr.save_checkpoint(
            job_id="old-1", input_file="in", output_file="out",
            total_chunks=5, completed_chunk_ids=[], results_data={},
        )

        # Backdate the checkpoint
        with checkpoint_mgr._backend.connection() as conn:
            old_time = time.time() - (30 * 86400)  # 30 days ago
            conn.execute(
                "UPDATE checkpoints SET updated_at = ? WHERE job_id = ?",
                (old_time, "old-1"),
            )

        deleted = checkpoint_mgr.cleanup_old_checkpoints(days=7)
        assert deleted == 1


# ===========================================================================
# CHKPT-004: Resume info
# ===========================================================================

class TestCheckpointResume:
    """DevOps persona — resume capability."""

    @pytest.mark.p1
    def test_chkpt_004_resume_info_structure(self, checkpoint_mgr):
        """CHKPT-004 | DevOps | get_resume_info returns expected keys"""
        checkpoint_mgr.save_checkpoint(
            job_id="resume-1", input_file="in", output_file="out",
            total_chunks=10, completed_chunk_ids=["c1", "c2"],
            results_data={"c1": {}, "c2": {}},
        )

        info = checkpoint_mgr.get_resume_info("resume-1")
        assert info is not None
        assert info["job_id"] == "resume-1"
        assert info["total_chunks"] == 10
        assert info["completed_chunks"] == 2
        assert info["remaining_chunks"] == 8
        assert info["can_resume"] is True

    @pytest.mark.p1
    def test_chkpt_004b_resume_info_nonexistent(self, checkpoint_mgr):
        """CHKPT-004b | QA | Resume info for non-existent -> None"""
        assert checkpoint_mgr.get_resume_info("ghost") is None

    @pytest.mark.p1
    def test_chkpt_004c_statistics(self, checkpoint_mgr):
        """CHKPT-004c | BA | get_statistics returns expected structure"""
        checkpoint_mgr.save_checkpoint(
            job_id="stat-1", input_file="in", output_file="out",
            total_chunks=10, completed_chunk_ids=["c1"], results_data={},
        )

        stats = checkpoint_mgr.get_statistics()
        assert "total_checkpoints" in stats
        assert "db_size_bytes" in stats
        assert stats["total_checkpoints"] == 1
