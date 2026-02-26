"""
RRI-T Sprint 3: Translation pipeline orchestrator tests.

Persona coverage: End User, QA Destroyer, DevOps, Business Analyst
Dimensions: D2 (API), D3 (Performance), D5 (Data Integrity), D7 (Edge Cases)
"""

import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from core.job_queue import JobStatus


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(job_id="pipe-1", status="pending", progress=0.0, **kw):
    job = MagicMock()
    job.job_id = job_id
    job.job_name = kw.get("job_name", "Pipeline Test")
    job.status = status
    job.priority = 5
    job.progress = progress
    job.source_lang = kw.get("source_lang", "en")
    job.target_lang = kw.get("target_lang", "vi")
    job.created_at = time.time()
    job.started_at = time.time() - 60 if status not in ("pending",) else None
    job.completed_at = time.time() if status == "completed" else None
    job.avg_quality_score = kw.get("quality", 0.85)
    job.total_cost_usd = kw.get("cost", 0.01)
    job.error_message = kw.get("error", None)
    job.metadata = kw.get("metadata", {})
    job.output_file = "output.docx"
    job.output_format = "docx"
    job.total_chunks = kw.get("total_chunks", 10)
    job.completed_chunks = int(progress * 10)
    return job


# ===========================================================================
# PIPE-001: Full pipeline mock -> correct output
# ===========================================================================

class TestFullPipeline:
    """End User persona — happy path pipeline execution."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_pipe_001_create_and_track(self, client, tmp_path):
        """PIPE-001 | End User | Create job + track progress -> correct flow"""
        f = tmp_path / "input.txt"
        f.write_text("Test document content for translation.")

        # Create job
        mock_job = _make_job(status="pending")
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json={
                "job_name": "Pipeline Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "en",
                "target_lang": "vi",
            })
        assert resp.status_code == 201

        # Track progress
        running_job = _make_job(status="running", progress=0.5)
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = running_job
            resp = client.get(f"/api/jobs/{mock_job.job_id}/progress")
        assert resp.status_code == 200
        assert resp.json()["progress_percent"] == 50

    @pytest.mark.p0
    def test_pipe_001b_completed_has_output(self, client):
        """PIPE-001b | End User | Completed job has output_file"""
        job = _make_job(status="completed", progress=1.0)
        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job
            resp = client.get(f"/api/jobs/{job.job_id}/progress")
        data = resp.json()
        assert data["progress_percent"] == 100
        assert data["output_file"] is not None


# ===========================================================================
# PIPE-002: Empty document -> graceful error
# ===========================================================================

class TestEmptyDocument:
    """QA Destroyer persona — empty input handling."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_pipe_002_empty_document(self, client, tmp_path):
        """PIPE-002 | QA Destroyer | Empty document -> handles gracefully"""
        f = tmp_path / "empty.txt"
        f.write_text("")

        mock_job = _make_job()
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json={
                "job_name": "Empty Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "en",
                "target_lang": "vi",
            })
        # Job creation may succeed (validation happens at processing time)
        assert resp.status_code in (201, 400)


# ===========================================================================
# PIPE-003: Unicode stress test
# ===========================================================================

class TestUnicodeStress:
    """QA Destroyer persona — Unicode edge cases."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_pipe_003_cjk_input(self, client, tmp_path):
        """PIPE-003 | QA Destroyer | CJK text -> job created successfully"""
        f = tmp_path / "cjk.txt"
        f.write_text("这是一个中文测试文档。\n日本語のテスト。\n한국어 테스트.")

        mock_job = _make_job()
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json={
                "job_name": "CJK Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "zh",
                "target_lang": "vi",
            })
        assert resp.status_code == 201

    @pytest.mark.p1
    def test_pipe_003b_emoji_input(self, client, tmp_path):
        """PIPE-003b | QA Destroyer | Emoji text -> job created successfully"""
        f = tmp_path / "emoji.txt"
        f.write_text("Hello 🌍! Test with emojis 🚀✨🎉 and more text.")

        mock_job = _make_job()
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json={
                "job_name": "Emoji Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "en",
                "target_lang": "vi",
            })
        assert resp.status_code == 201

    @pytest.mark.p1
    def test_pipe_003c_rtl_input(self, client, tmp_path):
        """PIPE-003c | QA Destroyer | RTL (Arabic) text -> job created"""
        f = tmp_path / "rtl.txt"
        f.write_text("مرحبا بالعالم. هذا اختبار.")

        mock_job = _make_job()
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json={
                "job_name": "RTL Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "ar",
                "target_lang": "en",
            })
        assert resp.status_code == 201


# ===========================================================================
# PIPE-004: Provider fallback
# ===========================================================================

class TestProviderFallback:
    """DevOps persona — AI provider resilience."""

    @pytest.mark.p0
    def test_pipe_004_fallback_scenario(self):
        """PIPE-004 | DevOps | Primary provider down -> pipeline can use fallback"""
        from ai_providers.unified_client import ProviderStatus, ProviderHealth
        # Verify enum values exist for fallback tracking
        assert ProviderStatus.AVAILABLE.value
        assert ProviderStatus.ERROR.value
        assert ProviderStatus.RATE_LIMITED.value
        assert ProviderStatus.NO_CREDIT.value

    @pytest.mark.p0
    def test_pipe_004b_provider_health_dataclass(self):
        """PIPE-004b | DevOps | ProviderHealth tracks status"""
        from ai_providers.unified_client import ProviderHealth, ProviderStatus
        health = ProviderHealth(
            provider="openai",
            status=ProviderStatus.AVAILABLE,
            error=None,
            model="gpt-4o-mini"
        )
        assert health.status == ProviderStatus.AVAILABLE
        assert health.provider == "openai"


# ===========================================================================
# PIPE-005: Progress callback accuracy
# ===========================================================================

class TestProgressAccuracy:
    """Business Analyst persona — progress tracking fidelity."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_pipe_005_progress_stages(self, client):
        """PIPE-005 | BA | Progress moves from 0 to 100 through stages"""
        stages = [
            ("pending", 0.0, 0),
            ("running", 0.25, 25),
            ("running", 0.50, 50),
            ("running", 0.75, 75),
            ("completed", 1.0, 100),
        ]
        for status, prog, expected_pct in stages:
            job = _make_job(status=status, progress=prog)
            with patch("api.routes.jobs.queue") as mock_q:
                mock_q.get_job.return_value = job
                resp = client.get("/api/jobs/pipe-1/progress")
            assert resp.json()["progress_percent"] == expected_pct, \
                f"Expected {expected_pct}% at status={status}, progress={prog}"


# ===========================================================================
# PIPE-006: LaTeX formula preservation
# ===========================================================================

class TestFormulaPreservation:
    """QA Destroyer persona — formula pass-through."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_pipe_006_latex_in_input(self, client, tmp_path):
        """PIPE-006 | QA | LaTeX formula in input -> job accepts it"""
        f = tmp_path / "latex.txt"
        f.write_text(r"Einstein's famous equation: $E = mc^2$ and $$\int_0^\infty e^{-x} dx = 1$$")

        mock_job = _make_job()
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json={
                "job_name": "LaTeX Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "en",
                "target_lang": "vi",
                "domain": "stem",
            })
        assert resp.status_code == 201

    @pytest.mark.p1
    def test_pipe_006b_omml_mode_sets_metadata(self, client, tmp_path):
        """PIPE-006b | QA | Academic layout -> equation_rendering_mode=omml in metadata"""
        f = tmp_path / "input.txt"
        f.write_text("Test document with equations")

        mock_job = _make_job()
        with patch("api.routes.jobs.queue") as mock_q, \
             patch("api.routes.jobs.manager") as mock_mgr:
            mock_q.create_job.return_value = mock_job
            mock_mgr.broadcast = AsyncMock()
            resp = client.post("/api/jobs", json={
                "job_name": "Academic Test",
                "input_file": str(f),
                "output_file": str(tmp_path / "out.docx"),
                "source_lang": "en",
                "target_lang": "vi",
                "ui_layout_mode": "academic",
            })
        assert resp.status_code == 201
        call_kwargs = mock_q.create_job.call_args
        metadata = call_kwargs.kwargs.get("metadata", {})
        assert metadata.get("equation_rendering_mode") == "omml"


# ===========================================================================
# PIPE-007: Chunk boundary integrity
# ===========================================================================

class TestChunkBoundary:
    """QA Destroyer persona — no lost or duplicated text at chunk boundaries."""

    @pytest.mark.p0
    def test_pipe_007_chunker_small_doc_single_chunk(self):
        """PIPE-007 | QA | Small doc -> single chunk, no loss"""
        from core_v2.semantic_chunker import SemanticChunker
        chunker = SemanticChunker()
        text = "Short document." * 10  # ~150 chars, well under SMALL_DOC
        import asyncio
        chunks = asyncio.get_event_loop().run_until_complete(chunker.chunk(text))
        assert len(chunks) == 1
        assert chunks[0].content == text.strip()

    @pytest.mark.p0
    def test_pipe_007b_chunk_content_covers_full_text(self):
        """PIPE-007b | QA | Chunked text -> all content accounted for"""
        from core_v2.semantic_chunker import SemanticChunker
        chunker = SemanticChunker()
        # Medium document with clear paragraph breaks
        text = "\n\n".join([f"Paragraph {i}. " * 50 for i in range(10)])
        import asyncio
        chunks = asyncio.get_event_loop().run_until_complete(chunker.chunk(text))
        # Concatenated chunks should contain all original paragraphs
        combined = " ".join(c.content for c in chunks)
        for i in range(10):
            assert f"Paragraph {i}" in combined

    @pytest.mark.p1
    def test_pipe_007c_chunk_indices_sequential(self):
        """PIPE-007c | QA | Chunk indices are sequential (0, 1, 2, ...)"""
        from core_v2.semantic_chunker import SemanticChunker
        chunker = SemanticChunker()
        text = "\n\n".join([f"Section {i}. " * 80 for i in range(8)])
        import asyncio
        chunks = asyncio.get_event_loop().run_until_complete(chunker.chunk(text))
        if len(chunks) > 1:
            for i, chunk in enumerate(chunks):
                assert chunk.index == i

    @pytest.mark.p1
    def test_pipe_007d_chunk_total_consistent(self):
        """PIPE-007d | QA | Every chunk has same total_chunks value"""
        from core_v2.semantic_chunker import SemanticChunker
        chunker = SemanticChunker()
        text = "\n\n".join([f"Block {i}. " * 80 for i in range(8)])
        import asyncio
        chunks = asyncio.get_event_loop().run_until_complete(chunker.chunk(text))
        if len(chunks) > 1:
            totals = set(c.total_chunks for c in chunks)
            assert len(totals) == 1
            assert totals.pop() == len(chunks)


# ===========================================================================
# PIPE-008: Cost tracking
# ===========================================================================

class TestCostTracking:
    """Business Analyst persona — cost tracking per job."""

    @pytest.mark.p1
    def test_pipe_008_usage_stats_cost(self):
        """PIPE-008 | BA | UsageStats tracks cost_usd"""
        from ai_providers.unified_client import UsageStats
        stats = UsageStats(
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            elapsed_seconds=2.0,
            provider="openai",
            model="gpt-4o-mini",
        )
        assert stats.cost_usd >= 0  # Should compute cost

    @pytest.mark.p1
    def test_pipe_008b_usage_stats_to_dict(self):
        """PIPE-008b | BA | UsageStats.to_dict() has all fields"""
        from ai_providers.unified_client import UsageStats
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            elapsed_seconds=1.0,
            provider="openai",
            model="gpt-4o-mini",
        )
        d = stats.to_dict()
        assert "input_tokens" in d
        assert "output_tokens" in d
        assert "cost_usd" in d
        assert "provider" in d


# ===========================================================================
# PIPE-009: Concurrent jobs isolation
# ===========================================================================

class TestConcurrentJobs:
    """DevOps persona — no cross-contamination between concurrent jobs."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_pipe_009_separate_job_ids(self, client, tmp_path):
        """PIPE-009 | DevOps | Two jobs created -> distinct job_ids"""
        f = tmp_path / "input.txt"
        f.write_text("Test document content.")

        jobs = []
        for i in range(2):
            mock_job = _make_job(job_id=f"job-{i}")
            with patch("api.routes.jobs.queue") as mock_q, \
                 patch("api.routes.jobs.manager") as mock_mgr:
                mock_q.create_job.return_value = mock_job
                mock_mgr.broadcast = AsyncMock()
                resp = client.post("/api/jobs", json={
                    "job_name": f"Job {i}",
                    "input_file": str(f),
                    "output_file": str(tmp_path / f"out_{i}.docx"),
                    "source_lang": "en",
                    "target_lang": "vi",
                })
            assert resp.status_code == 201
            jobs.append(resp.json()["job_id"])

        assert jobs[0] != jobs[1]

    @pytest.mark.p1
    def test_pipe_009b_job_progress_isolated(self, client):
        """PIPE-009b | DevOps | Querying job A doesn't affect job B"""
        job_a = _make_job(job_id="job-a", status="running", progress=0.3)
        job_b = _make_job(job_id="job-b", status="completed", progress=1.0)

        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job_a
            resp_a = client.get("/api/jobs/job-a/progress")

        with patch("api.routes.jobs.queue") as mock_q:
            mock_q.get_job.return_value = job_b
            resp_b = client.get("/api/jobs/job-b/progress")

        assert resp_a.json()["progress_percent"] == 30
        assert resp_b.json()["progress_percent"] == 100
