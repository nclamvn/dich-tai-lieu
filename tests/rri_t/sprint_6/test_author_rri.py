"""
RRI-T Sprint 6: Author Mode API tests.

Persona coverage: End User, QA Destroyer, Business Analyst
Dimensions: D2 (API), D5 (Data Integrity), D7 (Edge Cases)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app


pytestmark = [pytest.mark.rri_t]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(app)


def _mock_engine():
    """Create a mock GhostwriterAgent engine."""
    engine = MagicMock()

    # Variation mocks
    var1 = MagicMock()
    var1.text = "Generated paragraph variation 1."
    var1.style = "neutral"
    var1.word_count = 5
    var1.confidence = 0.85

    var2 = MagicMock()
    var2.text = "Generated paragraph variation 2."
    var2.style = "neutral"
    var2.word_count = 5
    var2.confidence = 0.80

    engine.propose_next_paragraph = AsyncMock(return_value=[var1, var2])
    engine.rewrite_paragraph = AsyncMock(return_value="Rewritten text here.")
    engine.expand_idea = AsyncMock(return_value="Expanded content here with more detail.")
    engine.generate_chapter = AsyncMock(return_value="Chapter 1: The Beginning\n\nContent here.")
    engine.brainstorm_ideas = AsyncMock(return_value=["Idea 1", "Idea 2", "Idea 3"])
    engine.critique_text = AsyncMock(return_value="Good pacing but needs more detail.")
    engine.memory_store = MagicMock()
    engine.memory_store.get_characters.return_value = []
    engine.memory_store.get_timeline.return_value = []
    engine.memory_store.search.return_value = []
    return engine


# ===========================================================================
# AUTH-001: Styles endpoint (no LLM needed)
# ===========================================================================

class TestAuthorStyles:
    """End User persona — style discovery."""

    @pytest.mark.p0
    def test_author_001_list_styles(self, client):
        """AUTHOR-001 | End User | /api/author/styles -> available styles"""
        resp = client.get("/api/author/styles")
        assert resp.status_code == 200
        data = resp.json()
        assert "styles" in data
        assert "descriptions" in data
        assert len(data["styles"]) > 0

    @pytest.mark.p1
    def test_author_001b_known_styles_included(self, client):
        """AUTHOR-001b | End User | Known styles present in list"""
        resp = client.get("/api/author/styles")
        data = resp.json()
        styles = data["styles"]
        assert "neutral" in styles
        assert "formal" in styles


# ===========================================================================
# AUTH-002: Propose endpoint
# ===========================================================================

class TestAuthorPropose:
    """End User persona — co-writing."""

    @pytest.mark.p0
    def test_author_002_propose(self, client):
        """AUTHOR-002 | End User | /api/author/propose -> variations"""
        with patch("api.routes.author.get_engine", return_value=_mock_engine()):
            resp = client.post("/api/author/propose", json={
                "context": "The detective examined the crime scene.",
                "instruction": "Continue the investigation.",
                "style": "neutral",
                "target_length": 100,
                "n_variations": 2,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "variations" in data
        assert len(data["variations"]) == 2
        assert "text" in data["variations"][0]
        assert "style" in data

    @pytest.mark.p1
    def test_author_002b_propose_min_variations(self, client):
        """AUTHOR-002b | QA | n_variations=1 -> single variation"""
        engine = _mock_engine()
        engine.propose_next_paragraph = AsyncMock(return_value=[
            MagicMock(text="Single var.", style="neutral", word_count=2, confidence=0.9)
        ])
        with patch("api.routes.author.get_engine", return_value=engine):
            resp = client.post("/api/author/propose", json={
                "context": "Some context.",
                "n_variations": 1,
            })
        assert resp.status_code == 200
        assert len(resp.json()["variations"]) == 1

    @pytest.mark.p1
    def test_author_002c_propose_too_many_variations(self, client):
        """AUTHOR-002c | QA | n_variations > 5 -> 422"""
        resp = client.post("/api/author/propose", json={
            "context": "Some context.",
            "n_variations": 10,
        })
        assert resp.status_code == 422


# ===========================================================================
# AUTH-003: Rewrite endpoint
# ===========================================================================

class TestAuthorRewrite:
    """End User persona — text improvement."""

    @pytest.mark.p1
    def test_author_003_rewrite(self, client):
        """AUTHOR-003 | End User | /api/author/rewrite -> improved text"""
        with patch("api.routes.author.get_engine", return_value=_mock_engine()):
            resp = client.post("/api/author/rewrite", json={
                "text": "The thing was very good and nice.",
                "improvements": ["clarity", "conciseness"],
                "style": "formal",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "original_text" in data
        assert "rewritten_text" in data
        assert data["style"] == "formal"


# ===========================================================================
# AUTH-004: Expand endpoint
# ===========================================================================

class TestAuthorExpand:
    """End User persona — idea expansion."""

    @pytest.mark.p1
    def test_author_004_expand(self, client):
        """AUTHOR-004 | End User | /api/author/expand -> expanded text"""
        with patch("api.routes.author.get_engine", return_value=_mock_engine()):
            resp = client.post("/api/author/expand", json={
                "idea": "A detective solves a murder mystery.",
                "target_length": 500,
                "style": "descriptive",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "expanded_content" in data
        assert "word_count" in data


# ===========================================================================
# AUTH-005: Chapter generation
# ===========================================================================

class TestAuthorChapter:
    """End User persona — chapter creation."""

    @pytest.mark.p1
    def test_author_005_generate_chapter(self, client):
        """AUTHOR-005 | End User | /api/author/generate-chapter -> chapter text"""
        with patch("api.routes.author.get_engine", return_value=_mock_engine()):
            resp = client.post("/api/author/generate-chapter", json={
                "book_title": "The Mystery",
                "genre": "mystery",
                "chapter_outline": "Detective arrives at the scene.",
                "target_length": 1000,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "chapter_text" in data
        assert "word_count" in data


# ===========================================================================
# AUTH-006: Brainstorm & Critique
# ===========================================================================

class TestAuthorIdeation:
    """End User persona — creative ideation."""

    @pytest.mark.p1
    def test_author_006_brainstorm(self, client):
        """AUTHOR-006 | End User | /api/author/brainstorm -> ideas list"""
        with patch("api.routes.author.get_engine", return_value=_mock_engine()):
            resp = client.post("/api/author/brainstorm", json={
                "focus": "plot twists for a mystery novel",
                "n_ideas": 5,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "ideas" in data
        assert len(data["ideas"]) > 0

    @pytest.mark.p1
    def test_author_006b_critique(self, client):
        """AUTHOR-006b | End User | /api/author/critique -> feedback"""
        with patch("api.routes.author.get_engine", return_value=_mock_engine()):
            resp = client.post("/api/author/critique", json={
                "text": "The dark night was cold. She walked quickly.",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "critique" in data

    @pytest.mark.p1
    def test_author_006c_brainstorm_min_ideas(self, client):
        """AUTHOR-006c | QA | n_ideas < 3 -> 422"""
        resp = client.post("/api/author/brainstorm", json={
            "focus": "anything",
            "n_ideas": 1,
        })
        assert resp.status_code == 422


# ===========================================================================
# AUTH-007: Project management
# ===========================================================================

class TestAuthorProjects:
    """End User persona — project lifecycle."""

    @pytest.mark.p1
    def test_author_007_create_project(self, client):
        """AUTHOR-007 | End User | /api/author/projects -> new project"""
        engine = _mock_engine()
        project_mock = MagicMock()
        project_mock.project_id = "proj-123"
        project_mock.author_id = "author-1"
        project_mock.title = "My Novel"
        project_mock.status = "active"
        project_mock.current_word_count = 0
        project_mock.completion_percentage.return_value = 0.0
        engine.create_project = MagicMock(return_value=project_mock)
        with patch("api.routes.author.get_engine", return_value=engine):
            resp = client.post("/api/author/projects", json={
                "author_id": "author-1",
                "title": "My Novel",
                "description": "A mystery novel",
                "genre": "mystery",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "project_id" in data
        assert data["author_id"] == "author-1"

    @pytest.mark.p1
    def test_author_007b_list_projects(self, client):
        """AUTHOR-007b | End User | List projects for author"""
        with patch("api.routes.author.get_engine", return_value=_mock_engine()):
            resp = client.get("/api/author/projects/author-1")
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data


# ===========================================================================
# AUTH-008: Memory endpoints
# ===========================================================================

class TestAuthorMemory:
    """End User persona — memory management."""

    @pytest.mark.p1
    def test_author_008_add_character(self, client):
        """AUTHOR-008 | End User | Add character to memory"""
        engine = _mock_engine()
        engine.memory_store.add_character.return_value = MagicMock(
            name="Sherlock",
            character_id="char-1",
        )
        with patch("api.routes.author.get_engine", return_value=engine):
            resp = client.post("/api/author/memory/character", json={
                "project_id": "proj-1",
                "author_id": "author-1",
                "name": "Sherlock Holmes",
                "description": "A brilliant detective",
                "traits": ["observant", "eccentric"],
            })
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_author_008b_list_characters(self, client):
        """AUTHOR-008b | End User | List characters"""
        engine = _mock_engine()
        with patch("api.routes.author.get_engine", return_value=engine):
            resp = client.get("/api/author/memory/characters/author-1/proj-1")
        assert resp.status_code == 200

    @pytest.mark.p1
    def test_author_008c_add_event(self, client):
        """AUTHOR-008c | End User | Add timeline event"""
        engine = _mock_engine()
        engine.memory_store.add_event.return_value = MagicMock(
            event_id="evt-1",
            description="Murder discovered",
        )
        with patch("api.routes.author.get_engine", return_value=engine):
            resp = client.post("/api/author/memory/event", json={
                "project_id": "proj-1",
                "author_id": "author-1",
                "description": "Murder discovered at the manor",
                "chapter": 1,
            })
        assert resp.status_code == 200
