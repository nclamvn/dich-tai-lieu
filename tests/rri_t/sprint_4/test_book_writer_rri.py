"""
RRI-T Sprint 4: Book Writer v2 tests.

Persona coverage: End User, QA Destroyer, Business Analyst
Dimensions: D2 (API), D5 (Data Integrity), D7 (Edge Cases)
"""

import io
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from api.routes.book_writer_v2 import get_service
from core.book_writer_v2.models import BookStatus, SectionStatus, WordCountTarget


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_project(project_id="bk-1", status="created", **kw):
    p = MagicMock()
    p.id = project_id
    p.title = kw.get("title", "Test Book")
    # status must have .value attribute like an enum
    status_mock = MagicMock()
    status_mock.value = status
    p.status = status_mock
    p.current_agent = kw.get("current_agent", None)
    p.current_task = kw.get("current_task", None)
    p.sections_completed = kw.get("sections_completed", 0)
    p.sections_total = kw.get("sections_total", 10)
    p.progress_percentage = kw.get("progress", 0.0)
    p.word_progress = kw.get("word_progress", 0.0)
    p.expansion_rounds = kw.get("expansion_rounds", 0)
    p.output_files = kw.get("output_files", {})
    p.created_at = "2026-01-01T00:00:00"
    p.updated_at = "2026-01-01T00:00:00"
    p.completed_at = None
    p.errors = []
    p.blueprint = None
    return p


def _mock_service():
    svc = MagicMock()
    svc.create_book = AsyncMock(return_value=_mock_project())
    svc.get_project = AsyncMock(return_value=_mock_project())
    svc.list_projects = AsyncMock(return_value=([_mock_project()], 1))
    svc.delete_project = AsyncMock(return_value=True)
    svc.pause_project = AsyncMock(return_value=True)
    svc.upload_draft = AsyncMock(return_value={"file_id": "d1", "filename": "d.txt", "size": 100})
    svc.preview_structure = AsyncMock(return_value={
        "title": "Preview",
        "estimated_chapters": 5,
        "estimated_pages": 100,
        "estimated_words": 25000,
    })
    return svc


# ===========================================================================
# BOOK-001: Create book project -> valid response
# ===========================================================================

class TestCreateBook:
    """End User persona — book creation flow."""

    @pytest.fixture
    def svc_and_client(self):
        svc = _mock_service()
        app.dependency_overrides[get_service] = lambda: svc
        yield svc, TestClient(app)
        app.dependency_overrides.pop(get_service, None)

    @pytest.mark.p0
    def test_book_001_create_project(self, svc_and_client):
        """BOOK-001 | End User | Create book project -> 201"""
        svc, client = svc_and_client
        resp = client.post("/api/v2/books-v2/", json={
            "title": "My Test Book",
            "description": "A book about testing software quality",
            "target_pages": 100,
            "genre": "non-fiction",
        })
        assert resp.status_code == 201

    @pytest.mark.p1
    def test_book_001b_create_with_all_options(self, svc_and_client):
        """BOOK-001b | End User | Create with all optional params"""
        _, client = svc_and_client
        resp = client.post("/api/v2/books-v2/", json={
            "title": "Full Options Book",
            "description": "Testing all options in the creation flow",
            "target_pages": 200,
            "genre": "fiction",
            "audience": "adults",
            "subtitle": "A Subtitle",
            "author_name": "Test Author",
            "language": "en",
            "output_formats": ["docx"],
        })
        assert resp.status_code == 201

    @pytest.mark.p0
    def test_book_001c_list_projects(self, svc_and_client):
        """BOOK-001c | End User | List projects -> paginated response"""
        _, client = svc_and_client
        resp = client.get("/api/v2/books-v2/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.p1
    def test_book_001d_create_invalid_genre_rejected(self, svc_and_client):
        """BOOK-001d | QA | Invalid genre -> 422"""
        _, client = svc_and_client
        resp = client.post("/api/v2/books-v2/", json={
            "title": "Bad Genre Book",
            "description": "Testing invalid genre value",
            "target_pages": 100,
            "genre": "invalid_genre",
        })
        assert resp.status_code == 422

    @pytest.mark.p1
    def test_book_001e_pages_out_of_range(self, svc_and_client):
        """BOOK-001e | QA | target_pages < 50 or > 1000 -> 422"""
        _, client = svc_and_client
        resp = client.post("/api/v2/books-v2/", json={
            "title": "Too Short",
            "description": "Testing page limit validation",
            "target_pages": 10,
            "genre": "non-fiction",
        })
        assert resp.status_code == 422


# ===========================================================================
# BOOK-002: Agent failure mid-pipeline -> recoverable
# ===========================================================================

class TestAgentFailure:
    """QA Destroyer persona — pipeline resilience."""

    @pytest.fixture
    def svc_and_client(self):
        svc = _mock_service()
        app.dependency_overrides[get_service] = lambda: svc
        yield svc, TestClient(app)
        app.dependency_overrides.pop(get_service, None)

    @pytest.mark.p0
    def test_book_002_get_failed_project(self, svc_and_client):
        """BOOK-002 | QA | Failed project -> returns with error details"""
        svc, client = svc_and_client
        failed_project = _mock_project(status="failed")
        failed_project.errors = [{"agent": "WriterAgent", "error": "timeout", "message": "Agent WriterAgent failed: timeout"}]
        svc.get_project = AsyncMock(return_value=failed_project)

        resp = client.get("/api/v2/books-v2/bk-1")
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_book_002b_nonexistent_project_404(self, svc_and_client):
        """BOOK-002b | QA | Non-existent project -> 404"""
        svc, client = svc_and_client
        svc.get_project = AsyncMock(return_value=None)
        resp = client.get("/api/v2/books-v2/nonexistent")
        assert resp.status_code == 404


# ===========================================================================
# BOOK-003: WordCountTarget model
# ===========================================================================

class TestBookCheckpoint:
    """Business Analyst persona — data persistence."""

    @pytest.mark.p0
    def test_book_003_word_count_target_completion(self):
        """BOOK-003 | BA | WordCountTarget tracks completion percentage"""
        wc = WordCountTarget(target=50000, actual=25000)
        assert wc.completion == 50.0

    @pytest.mark.p0
    def test_book_003b_word_count_target_remaining(self):
        """BOOK-003b | BA | WordCountTarget shows remaining words"""
        wc = WordCountTarget(target=50000, actual=30000)
        assert wc.remaining == 20000

    @pytest.mark.p0
    def test_book_003c_word_count_is_complete(self):
        """BOOK-003c | BA | is_complete at 95%+"""
        wc = WordCountTarget(target=50000, actual=48000)
        assert wc.is_complete  # 96% >= 95%

        wc2 = WordCountTarget(target=50000, actual=40000)
        assert not wc2.is_complete  # 80% < 95%

    @pytest.mark.p1
    def test_book_003d_word_count_needs_expansion(self):
        """BOOK-003d | BA | needs_expansion when < 90%"""
        wc = WordCountTarget(target=50000, actual=40000)
        assert wc.needs_expansion  # 80% < 90%

        wc2 = WordCountTarget(target=50000, actual=47000)
        assert not wc2.needs_expansion  # 94% >= 90%

    @pytest.mark.p1
    def test_book_003e_word_count_is_over(self):
        """BOOK-003e | BA | is_over when > 105%"""
        wc = WordCountTarget(target=50000, actual=55000)
        assert wc.is_over  # 110% > 105%

    @pytest.mark.p1
    def test_book_003f_zero_target(self):
        """BOOK-003f | QA | Zero target -> 100% completion (no division by zero)"""
        wc = WordCountTarget(target=0, actual=0)
        assert wc.completion == 100.0


# ===========================================================================
# BOOK-004: Delete / Pause
# ===========================================================================

class TestBookEdgeCases:
    """QA Destroyer persona — edge cases."""

    @pytest.fixture
    def svc_and_client(self):
        svc = _mock_service()
        app.dependency_overrides[get_service] = lambda: svc
        yield svc, TestClient(app)
        app.dependency_overrides.pop(get_service, None)

    @pytest.mark.p1
    def test_book_004_delete_project(self, svc_and_client):
        """BOOK-004 | QA | Delete project -> 200"""
        _, client = svc_and_client
        resp = client.delete("/api/v2/books-v2/bk-1")
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_book_004b_delete_nonexistent(self, svc_and_client):
        """BOOK-004b | QA | Delete non-existent -> 404"""
        svc, client = svc_and_client
        svc.delete_project = AsyncMock(return_value=False)
        resp = client.delete("/api/v2/books-v2/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.p1
    def test_book_004c_pause_project(self, svc_and_client):
        """BOOK-004c | QA | Pause running project"""
        _, client = svc_and_client
        resp = client.post("/api/v2/books-v2/bk-1/pause")
        assert resp.status_code in (200, 400)


# ===========================================================================
# BOOK-005: Status enum completeness
# ===========================================================================

class TestBookModels:
    """Business Analyst persona — data model validation."""

    @pytest.mark.p0
    def test_book_005_status_enum_all_values(self):
        """BOOK-005 | BA | BookStatus has all pipeline statuses"""
        expected = ["CREATED", "ANALYZING", "ARCHITECTING", "OUTLINING",
                    "WRITING", "EXPANDING", "ENRICHING", "EDITING",
                    "QUALITY_CHECK", "PUBLISHING", "COMPLETED", "FAILED", "PAUSED"]
        for status in expected:
            assert hasattr(BookStatus, status)

    @pytest.mark.p0
    def test_book_005b_section_status_enum(self):
        """BOOK-005b | BA | SectionStatus has all statuses"""
        expected = ["PENDING", "OUTLINED", "WRITING", "WRITTEN",
                    "NEEDS_EXPANSION", "EXPANDING", "ENRICHING",
                    "EDITING", "COMPLETE", "FAILED"]
        for status in expected:
            assert hasattr(SectionStatus, status)

    @pytest.mark.p1
    def test_book_005c_status_values_are_strings(self):
        """BOOK-005c | BA | All status values are lowercase strings"""
        for status in BookStatus:
            assert isinstance(status.value, str)
            assert status.value == status.value.lower()


# ===========================================================================
# BOOK-006: Draft upload + preview
# ===========================================================================

class TestDraftUpload:
    """End User persona — draft upload flow."""

    @pytest.fixture
    def svc_and_client(self):
        svc = _mock_service()
        app.dependency_overrides[get_service] = lambda: svc
        yield svc, TestClient(app)
        app.dependency_overrides.pop(get_service, None)

    @pytest.mark.p1
    def test_book_006_upload_draft(self, svc_and_client):
        """BOOK-006 | End User | Upload draft file -> 200"""
        _, client = svc_and_client
        resp = client.post(
            "/api/v2/books-v2/upload-draft",
            files={"file": ("draft.txt", io.BytesIO(b"Chapter 1\nContent..."), "text/plain")},
        )
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_book_006b_preview_structure(self, svc_and_client):
        """BOOK-006b | End User | Preview book structure -> 200"""
        svc, client = svc_and_client
        svc.get_structure_preview = AsyncMock(return_value={
            "target_pages": 100, "content_pages": 90, "content_words": 22500,
            "num_parts": 3, "total_chapters": 9, "chapters_per_part": 3,
            "total_sections": 27, "words_per_chapter": 2500,
            "words_per_section": 833, "estimated_time_minutes": 30,
        })
        resp = client.post("/api/v2/books-v2/preview-structure?target_pages=100")
        assert resp.status_code == 200
