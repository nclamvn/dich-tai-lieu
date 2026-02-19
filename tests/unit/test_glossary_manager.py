"""
Unit tests for api/services/glossary_manager.py — User Glossary System.

Target: 90%+ coverage.
"""

import json
import pytest
import time

from api.services.glossary_manager import (
    GlossaryManager,
    Glossary,
    GlossaryTerm,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def manager(tmp_path):
    """Fresh GlossaryManager with temp storage."""
    return GlossaryManager(storage_dir=str(tmp_path / "glossaries"))


@pytest.fixture
def populated_manager(manager):
    """Manager with one glossary containing terms."""
    gid = manager.create_glossary("Medical", source_language="en", target_language="vi")
    manager.add_term(gid, "heart", "tim")
    manager.add_term(gid, "lung", "phổi")
    manager.add_term(gid, "blood", "máu")
    return manager, gid


# ---------------------------------------------------------------------------
# GlossaryTerm
# ---------------------------------------------------------------------------

class TestGlossaryTerm:
    def test_defaults(self):
        term = GlossaryTerm(source="hello", target="xin chào")
        assert term.source == "hello"
        assert term.target == "xin chào"
        assert term.notes == ""
        assert term.domain == "general"
        assert term.added_at > 0

    def test_custom_fields(self):
        term = GlossaryTerm(
            source="heart", target="tim",
            notes="anatomy", domain="medical",
        )
        assert term.notes == "anatomy"
        assert term.domain == "medical"


# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------

class TestGlossary:
    def test_creation(self):
        g = Glossary(id="abc123", name="Test")
        assert g.id == "abc123"
        assert g.name == "Test"
        assert g.source_language == "en"
        assert g.target_language == "vi"
        assert g.term_count == 0
        assert g.created_at > 0
        assert g.updated_at > 0

    def test_term_count(self):
        g = Glossary(id="x", name="X", terms=[
            GlossaryTerm(source="a", target="b"),
            GlossaryTerm(source="c", target="d"),
        ])
        assert g.term_count == 2

    def test_to_dict(self):
        g = Glossary(id="x", name="X", description="desc")
        data = g.to_dict()
        assert data["id"] == "x"
        assert data["name"] == "X"
        assert data["description"] == "desc"
        assert isinstance(data["terms"], list)

    def test_from_dict(self):
        data = {
            "id": "abc",
            "name": "Test",
            "source_language": "ja",
            "target_language": "en",
            "terms": [{"source": "心臓", "target": "heart", "notes": "", "domain": "medical", "added_at": 1.0}],
        }
        g = Glossary.from_dict(data)
        assert g.id == "abc"
        assert g.source_language == "ja"
        assert g.term_count == 1
        assert g.terms[0].source == "心臓"

    def test_from_dict_defaults(self):
        data = {"id": "x", "name": "X"}
        g = Glossary.from_dict(data)
        assert g.source_language == "en"
        assert g.target_language == "vi"
        assert g.term_count == 0

    def test_roundtrip(self):
        g = Glossary(id="rt", name="Roundtrip", terms=[
            GlossaryTerm(source="a", target="b"),
        ])
        data = g.to_dict()
        g2 = Glossary.from_dict(data)
        assert g2.id == g.id
        assert g2.term_count == g.term_count
        assert g2.terms[0].source == "a"

    def test_get_term_dict(self):
        g = Glossary(id="x", name="X", terms=[
            GlossaryTerm(source="heart", target="tim"),
            GlossaryTerm(source="lung", target="phổi"),
        ])
        d = g.get_term_dict()
        assert d == {"heart": "tim", "lung": "phổi"}


# ---------------------------------------------------------------------------
# GlossaryManager — CRUD
# ---------------------------------------------------------------------------

class TestManagerCRUD:
    def test_create_glossary(self, manager):
        gid = manager.create_glossary("Test Glossary")
        assert len(gid) == 12
        assert manager.count == 1

    def test_get_glossary(self, manager):
        gid = manager.create_glossary("Test")
        g = manager.get_glossary(gid)
        assert g is not None
        assert g.name == "Test"

    def test_get_nonexistent(self, manager):
        assert manager.get_glossary("nonexistent") is None

    def test_list_glossaries(self, manager):
        manager.create_glossary("A")
        manager.create_glossary("B")
        lst = manager.list_glossaries()
        assert len(lst) == 2
        names = {g.name for g in lst}
        assert names == {"A", "B"}

    def test_list_empty(self, manager):
        assert manager.list_glossaries() == []

    def test_delete_glossary(self, manager):
        gid = manager.create_glossary("Deletable")
        assert manager.delete_glossary(gid) is True
        assert manager.get_glossary(gid) is None
        assert manager.count == 0

    def test_delete_nonexistent(self, manager):
        assert manager.delete_glossary("nope") is False

    def test_update_glossary(self, manager):
        gid = manager.create_glossary("Original")
        updated = manager.update_glossary(gid, name="Updated", description="New desc")
        assert updated.name == "Updated"
        assert updated.description == "New desc"

    def test_update_partial(self, manager):
        gid = manager.create_glossary("Original", description="old")
        manager.update_glossary(gid, name="New Name")
        g = manager.get_glossary(gid)
        assert g.name == "New Name"
        assert g.description == "old"  # unchanged

    def test_update_nonexistent(self, manager):
        assert manager.update_glossary("nope") is None


# ---------------------------------------------------------------------------
# GlossaryManager — Terms
# ---------------------------------------------------------------------------

class TestManagerTerms:
    def test_add_term(self, manager):
        gid = manager.create_glossary("Test")
        assert manager.add_term(gid, "hello", "xin chào") is True
        terms = manager.get_terms(gid)
        assert len(terms) == 1
        assert terms[0].source == "hello"

    def test_add_duplicate_updates(self, manager):
        gid = manager.create_glossary("Test")
        manager.add_term(gid, "hello", "xin chào")
        manager.add_term(gid, "Hello", "chào bạn")  # case-insensitive update
        terms = manager.get_terms(gid)
        assert len(terms) == 1
        assert terms[0].target == "chào bạn"

    def test_add_term_nonexistent_glossary(self, manager):
        assert manager.add_term("nope", "a", "b") is False

    def test_remove_term(self, populated_manager):
        manager, gid = populated_manager
        assert manager.remove_term(gid, "heart") is True
        terms = manager.get_terms(gid)
        assert len(terms) == 2
        sources = {t.source for t in terms}
        assert "heart" not in sources

    def test_remove_case_insensitive(self, populated_manager):
        manager, gid = populated_manager
        assert manager.remove_term(gid, "HEART") is True
        assert len(manager.get_terms(gid)) == 2

    def test_remove_nonexistent_term(self, populated_manager):
        manager, gid = populated_manager
        assert manager.remove_term(gid, "kidney") is False

    def test_remove_from_nonexistent_glossary(self, manager):
        assert manager.remove_term("nope", "a") is False

    def test_get_terms_empty(self, manager):
        gid = manager.create_glossary("Empty")
        assert manager.get_terms(gid) == []

    def test_get_terms_nonexistent(self, manager):
        assert manager.get_terms("nope") == []


# ---------------------------------------------------------------------------
# Integration features
# ---------------------------------------------------------------------------

class TestManagerIntegration:
    def test_get_term_dict(self, populated_manager):
        manager, gid = populated_manager
        d = manager.get_term_dict(gid)
        assert d == {"heart": "tim", "lung": "phổi", "blood": "máu"}

    def test_get_term_dict_nonexistent(self, manager):
        assert manager.get_term_dict("nope") == {}

    def test_merge_glossaries(self, manager):
        g1 = manager.create_glossary("G1")
        g2 = manager.create_glossary("G2")
        manager.add_term(g1, "heart", "tim")
        manager.add_term(g2, "heart", "trái tim")  # override
        manager.add_term(g2, "lung", "phổi")

        merged = manager.merge_glossaries([g1, g2])
        assert merged["heart"] == "trái tim"  # g2 overrides g1
        assert merged["lung"] == "phổi"

    def test_find_matches(self, populated_manager):
        manager, gid = populated_manager
        matches = manager.find_matches("The heart pumps blood", gid)
        sources = {m.source for m in matches}
        assert "heart" in sources
        assert "blood" in sources
        assert "lung" not in sources

    def test_find_matches_case_insensitive(self, populated_manager):
        manager, gid = populated_manager
        matches = manager.find_matches("HEART AND LUNG", gid)
        assert len(matches) == 2

    def test_find_matches_nonexistent(self, manager):
        assert manager.find_matches("text", "nope") == []


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestManagerPersistence:
    def test_persists_to_disk(self, tmp_path):
        storage = str(tmp_path / "glossaries")
        manager = GlossaryManager(storage_dir=storage)
        gid = manager.create_glossary("Persistent")
        manager.add_term(gid, "hello", "xin chào")

        # Verify file exists
        files = list((tmp_path / "glossaries").glob("*.json"))
        assert len(files) == 1

        # Read raw JSON
        data = json.loads(files[0].read_text())
        assert data["name"] == "Persistent"
        assert len(data["terms"]) == 1

    def test_reload_from_disk(self, tmp_path):
        storage = str(tmp_path / "glossaries")

        # Create and save
        m1 = GlossaryManager(storage_dir=storage)
        gid = m1.create_glossary("Reloadable")
        m1.add_term(gid, "heart", "tim")

        # New manager loads from same dir
        m2 = GlossaryManager(storage_dir=storage)
        assert m2.count == 1
        g = m2.get_glossary(gid)
        assert g is not None
        assert g.name == "Reloadable"
        assert g.term_count == 1

    def test_delete_removes_file(self, tmp_path):
        storage = str(tmp_path / "glossaries")
        manager = GlossaryManager(storage_dir=storage)
        gid = manager.create_glossary("Deletable")
        manager.delete_glossary(gid)

        files = list((tmp_path / "glossaries").glob("*.json"))
        assert len(files) == 0

    def test_storage_dir_property(self, manager):
        assert manager.storage_dir.exists()

    def test_corrupt_file_handled(self, tmp_path):
        storage = tmp_path / "glossaries"
        storage.mkdir()
        (storage / "bad.json").write_text("not json")

        # Should not raise
        manager = GlossaryManager(storage_dir=str(storage))
        assert manager.count == 0
