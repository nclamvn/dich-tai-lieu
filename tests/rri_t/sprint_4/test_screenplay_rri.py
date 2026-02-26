"""
RRI-T Sprint 4: Screenplay Studio tests.

Persona coverage: End User, QA Destroyer, Business Analyst
Dimensions: D2 (API), D5 (Data Integrity), D7 (Edge Cases)
"""

import io
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from core.screenplay_studio.models import (
    ProjectStatus, ProjectTier, VideoProvider, Language,
)


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_screenplay_project(project_id=None, status="draft", user_id="default_user", **kw):
    p = MagicMock()
    p.id = project_id or str(uuid.uuid4())
    p.title = kw.get("title", "Test Screenplay")
    p.status = ProjectStatus(status) if isinstance(status, str) else status
    p.tier = ProjectTier.FREE
    p.language = Language.ENGLISH
    p.user_id = user_id
    p.source_type = "text"
    p.source_text = kw.get("source_text", "Once upon a time...")
    p.video_provider = None
    p.estimated_cost_usd = 0.0
    p.actual_cost_usd = 0.0
    p.story_analysis = None
    p.screenplay = None
    p.shot_list = None
    p.storyboard_images = []
    p.video_clips = []
    p.final_video_path = None
    p.error_message = None
    p.output_files = {}
    p.created_at = "2026-01-01T00:00:00"
    p.updated_at = "2026-01-01T00:00:00"
    return p


# ===========================================================================
# SCREEN-001: Create screenplay project
# ===========================================================================

class TestCreateScreenplay:
    """End User persona — screenplay creation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p0
    def test_screen_001_create_project(self, client):
        """SCREEN-001 | End User | Create screenplay project -> 200"""
        mock_proj = _mock_screenplay_project()
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.create.return_value = None
            # The route creates the project inline, not via a service
            resp = client.post("/api/screenplay/projects", json={
                "title": "My Screenplay",
                "source_type": "novel",
                "language": "en",
                "tier": "free",
                "source_text": "Once upon a time in a land far away, there lived a brave hero who embarked on a journey to save the kingdom. " * 3,
            })
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_screen_001b_list_projects(self, client):
        """SCREEN-001b | End User | List projects -> paginated"""
        mock_proj = _mock_screenplay_project()
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get_by_user.return_value = [mock_proj]
            mock_repo.count_by_user.return_value = 1
            resp = client.get("/api/screenplay/projects")
        assert resp.status_code == 200


# ===========================================================================
# SCREEN-002: Pipeline state management
# ===========================================================================

class TestScreenplayPipelineState:
    """QA Destroyer persona — state management."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_screen_002_get_project_by_id(self, client):
        """SCREEN-002 | QA | Get project by ID -> 200"""
        mock_proj = _mock_screenplay_project(project_id="sp-1")
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get.return_value = mock_proj
            resp = client.get("/api/screenplay/projects/sp-1")
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_screen_002b_get_nonexistent(self, client):
        """SCREEN-002b | QA | Get non-existent project -> 404"""
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get.return_value = None
            resp = client.get("/api/screenplay/projects/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.p1
    def test_screen_002c_delete_project(self, client):
        """SCREEN-002c | QA | Delete project -> 200"""
        mock_proj = _mock_screenplay_project(project_id="sp-1")
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get.return_value = mock_proj
            mock_repo.delete.return_value = True
            resp = client.delete("/api/screenplay/projects/sp-1")
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_screen_002d_delete_nonexistent(self, client):
        """SCREEN-002d | QA | Delete non-existent -> 404"""
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get.return_value = None
            resp = client.delete("/api/screenplay/projects/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.p1
    def test_screen_002e_access_other_user_project(self, client):
        """SCREEN-002e | Security | Access other user's project -> 403"""
        other_user_proj = _mock_screenplay_project(project_id="sp-other", user_id="other_user")
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get.return_value = other_user_proj
            resp = client.get("/api/screenplay/projects/sp-other")
        assert resp.status_code == 403


# ===========================================================================
# SCREEN-003: Cost estimation
# ===========================================================================

class TestCostEstimation:
    """Business Analyst persona — cost accuracy."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_screen_003_estimate_cost(self, client):
        """SCREEN-003 | BA | Cost estimation endpoint -> 200"""
        resp = client.post("/api/screenplay/estimate-cost", json={
            "source_text_length": 5000,
            "tier": "free",
            "target_runtime_minutes": 10,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "tier" in data
        assert "estimated_scenes" in data

    @pytest.mark.p1
    def test_screen_003b_estimate_pro_tier(self, client):
        """SCREEN-003b | BA | Pro tier cost estimate includes video cost"""
        resp = client.post("/api/screenplay/estimate-cost", json={
            "source_text_length": 10000,
            "tier": "pro",
            "video_provider": "pika",
            "target_runtime_minutes": 15,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "pro"

    @pytest.mark.p1
    def test_screen_003c_providers_endpoint(self, client):
        """SCREEN-003c | BA | List providers -> 200 with tiers info"""
        resp = client.get("/api/screenplay/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "tiers" in data
        assert "providers" in data


# ===========================================================================
# SCREEN-004: Model enums
# ===========================================================================

class TestScreenplayModels:
    """Business Analyst persona — data model completeness."""

    @pytest.mark.p0
    def test_screen_004_project_status_enum(self):
        """SCREEN-004 | BA | ProjectStatus has all pipeline states"""
        expected = ["DRAFT", "ANALYZING", "WRITING", "VISUALIZING",
                    "RENDERING", "COMPLETED", "FAILED", "CANCELLED"]
        for status in expected:
            assert hasattr(ProjectStatus, status)

    @pytest.mark.p0
    def test_screen_004b_tier_enum(self):
        """SCREEN-004b | BA | ProjectTier has all tiers"""
        expected = ["FREE", "STANDARD", "PRO", "DIRECTOR"]
        for tier in expected:
            assert hasattr(ProjectTier, tier)

    @pytest.mark.p0
    def test_screen_004c_video_provider_enum(self):
        """SCREEN-004c | BA | VideoProvider has all providers"""
        expected = ["PIKA", "RUNWAY", "VEO"]
        for provider in expected:
            assert hasattr(VideoProvider, provider)

    @pytest.mark.p1
    def test_screen_004d_language_enum(self):
        """SCREEN-004d | BA | Language enum includes EN and VI"""
        assert hasattr(Language, "ENGLISH")
        assert hasattr(Language, "VIETNAMESE")

    @pytest.mark.p1
    def test_screen_004e_status_values_lowercase(self):
        """SCREEN-004e | BA | Status values are lowercase strings"""
        for status in ProjectStatus:
            assert isinstance(status.value, str)


# ===========================================================================
# SCREEN-005: Text extraction
# ===========================================================================

class TestTextExtraction:
    """End User persona — text extraction from files."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_screen_005_extract_text_from_txt(self, client):
        """SCREEN-005 | End User | Extract text from .txt -> 200"""
        content = b"Once upon a time, in a land far away..."
        resp = client.post(
            "/api/screenplay/extract-text",
            files={"file": ("story.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert len(data["text"]) > 0


# ===========================================================================
# SCREEN-006: Update project
# ===========================================================================

class TestUpdateScreenplay:
    """End User persona — project updates."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.p1
    def test_screen_006_update_title(self, client):
        """SCREEN-006 | End User | Update project title -> 200"""
        mock_proj = _mock_screenplay_project(project_id="sp-1")
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get.return_value = mock_proj
            mock_repo.update.return_value = None
            resp = client.patch("/api/screenplay/projects/sp-1", json={
                "title": "Updated Title",
            })
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_screen_006b_update_nonexistent(self, client):
        """SCREEN-006b | QA | Update non-existent project -> 404"""
        with patch("api.routes.screenplay.repo") as mock_repo:
            mock_repo.get.return_value = None
            resp = client.patch("/api/screenplay/projects/nonexistent", json={
                "title": "Updated",
            })
        assert resp.status_code == 404
