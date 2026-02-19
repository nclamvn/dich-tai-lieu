"""
Unit tests for api/services/publishing_profile.py — Custom Publishing Profiles.

Target: 90%+ coverage.
"""

import json
import pytest

from api.services.publishing_profile import (
    PublishingProfile,
    ProfileStore,
    BUILTIN_PROFILES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    """Fresh ProfileStore with temp storage."""
    return ProfileStore(storage_dir=str(tmp_path / "profiles"))


# ---------------------------------------------------------------------------
# PublishingProfile
# ---------------------------------------------------------------------------

class TestPublishingProfile:
    def test_defaults(self):
        p = PublishingProfile(id="x", name="Test")
        assert p.output_format == "docx"
        assert p.template == "auto"
        assert p.is_builtin is False
        assert p.created_at > 0
        assert p.line_spacing == 0.0

    def test_to_prompt_with_style(self):
        p = PublishingProfile(
            id="x", name="X",
            style_guide="Formal tone",
            template="academic",
            font_family="Times New Roman",
            font_size="12pt",
            line_spacing=2.0,
            special_instructions="Keep footnotes",
        )
        prompt = p.to_prompt()
        assert "Formal tone" in prompt
        assert "academic" in prompt
        assert "Times New Roman" in prompt
        assert "12pt" in prompt
        assert "2.0" in prompt
        assert "Keep footnotes" in prompt

    def test_to_prompt_minimal(self):
        p = PublishingProfile(id="x", name="X")
        prompt = p.to_prompt()
        assert "docx" in prompt

    def test_to_dict(self):
        p = PublishingProfile(id="x", name="Test", output_format="pdf")
        d = p.to_dict()
        assert d["id"] == "x"
        assert d["name"] == "Test"
        assert d["output_format"] == "pdf"

    def test_from_dict(self):
        data = {
            "id": "abc",
            "name": "From Dict",
            "output_format": "epub",
            "style_guide": "Simple",
            "template": "ebook",
            "line_spacing": 1.5,
        }
        p = PublishingProfile.from_dict(data)
        assert p.id == "abc"
        assert p.output_format == "epub"
        assert p.style_guide == "Simple"
        assert p.line_spacing == 1.5

    def test_from_dict_defaults(self):
        data = {"id": "x", "name": "X"}
        p = PublishingProfile.from_dict(data)
        assert p.output_format == "docx"
        assert p.template == "auto"
        assert p.is_builtin is False

    def test_roundtrip(self):
        p = PublishingProfile(
            id="rt", name="Roundtrip",
            output_format="epub",
            style_guide="Test style",
        )
        data = p.to_dict()
        p2 = PublishingProfile.from_dict(data)
        assert p2.id == p.id
        assert p2.output_format == p.output_format
        assert p2.style_guide == p.style_guide


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

class TestBuiltinProfiles:
    def test_count(self):
        assert len(BUILTIN_PROFILES) >= 5

    def test_all_have_ids(self):
        for p in BUILTIN_PROFILES:
            assert p.id
            assert p.name
            assert p.is_builtin is True

    def test_known_profiles(self):
        ids = {p.id for p in BUILTIN_PROFILES}
        assert "novel" in ids
        assert "academic" in ids
        assert "business" in ids
        assert "technical" in ids
        assert "simple" in ids

    def test_novel_is_epub(self):
        novel = next(p for p in BUILTIN_PROFILES if p.id == "novel")
        assert novel.output_format == "epub"
        assert novel.template == "ebook"

    def test_academic_has_formatting(self):
        academic = next(p for p in BUILTIN_PROFILES if p.id == "academic")
        assert academic.font_family == "Times New Roman"
        assert academic.line_spacing == 2.0

    def test_all_have_style_guides(self):
        for p in BUILTIN_PROFILES:
            assert len(p.style_guide) > 10

    def test_to_prompt_non_empty(self):
        for p in BUILTIN_PROFILES:
            prompt = p.to_prompt()
            assert len(prompt) > 5


# ---------------------------------------------------------------------------
# ProfileStore — CRUD
# ---------------------------------------------------------------------------

class TestStoreCRUD:
    def test_list_includes_builtin(self, store):
        profiles = store.list_profiles()
        assert len(profiles) >= 5
        builtin_ids = {p.id for p in profiles if p.is_builtin}
        assert "novel" in builtin_ids

    def test_list_builtin_only(self, store):
        builtins = store.list_builtin()
        assert all(p.is_builtin for p in builtins)
        assert len(builtins) == store.builtin_count

    def test_list_custom_empty(self, store):
        assert store.list_custom() == []
        assert store.custom_count == 0

    def test_get_builtin(self, store):
        p = store.get_profile("novel")
        assert p is not None
        assert p.name == "Novel / Fiction"

    def test_get_nonexistent(self, store):
        assert store.get_profile("nope") is None

    def test_create_custom(self, store):
        pid = store.create_profile("My Style", output_format="epub")
        assert len(pid) == 12
        assert store.custom_count == 1

    def test_get_custom(self, store):
        pid = store.create_profile("Custom One")
        p = store.get_profile(pid)
        assert p is not None
        assert p.name == "Custom One"
        assert p.is_builtin is False

    def test_list_with_custom(self, store):
        store.create_profile("Custom A")
        store.create_profile("Custom B")
        all_profiles = store.list_profiles()
        assert len(all_profiles) >= 7  # 5 builtin + 2 custom

    def test_list_custom_only(self, store):
        store.create_profile("Only Custom")
        customs = store.list_custom()
        assert len(customs) == 1
        assert customs[0].name == "Only Custom"

    def test_update_custom(self, store):
        pid = store.create_profile("Updatable")
        updated = store.update_profile(pid, name="Updated Name", output_format="pdf")
        assert updated.name == "Updated Name"
        assert updated.output_format == "pdf"

    def test_update_nonexistent(self, store):
        assert store.update_profile("nope", name="X") is None

    def test_update_preserves_id(self, store):
        pid = store.create_profile("Original")
        store.update_profile(pid, name="Changed")
        p = store.get_profile(pid)
        assert p.id == pid
        assert p.name == "Changed"

    def test_delete_custom(self, store):
        pid = store.create_profile("Deletable")
        assert store.delete_profile(pid) is True
        assert store.get_profile(pid) is None
        assert store.custom_count == 0

    def test_delete_nonexistent(self, store):
        assert store.delete_profile("nope") is False

    def test_cannot_delete_builtin(self, store):
        assert store.delete_profile("novel") is False

    def test_total_count(self, store):
        store.create_profile("X")
        assert store.total_count == store.builtin_count + 1

    def test_get_profile_for_format(self, store):
        p = store.get_profile_for_format("epub")
        assert p is not None
        assert p.output_format == "epub"

    def test_get_profile_for_format_unknown(self, store):
        assert store.get_profile_for_format("latex") is None

    def test_custom_overrides_format_lookup(self, store):
        store.create_profile("My EPUB", output_format="epub")
        p = store.get_profile_for_format("epub")
        assert p.name == "My EPUB"  # custom found first


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestStorePersistence:
    def test_persists_to_disk(self, tmp_path):
        storage = str(tmp_path / "profiles")
        s = ProfileStore(storage_dir=storage)
        s.create_profile("Persistent")

        files = list((tmp_path / "profiles").glob("*.json"))
        assert len(files) == 1

    def test_reload_from_disk(self, tmp_path):
        storage = str(tmp_path / "profiles")
        s1 = ProfileStore(storage_dir=storage)
        pid = s1.create_profile("Reloadable", output_format="pdf")

        s2 = ProfileStore(storage_dir=storage)
        assert s2.custom_count == 1
        p = s2.get_profile(pid)
        assert p.name == "Reloadable"
        assert p.output_format == "pdf"

    def test_delete_removes_file(self, tmp_path):
        storage = str(tmp_path / "profiles")
        s = ProfileStore(storage_dir=storage)
        pid = s.create_profile("Temp")
        s.delete_profile(pid)

        files = list((tmp_path / "profiles").glob("*.json"))
        assert len(files) == 0

    def test_storage_dir_property(self, store):
        assert store.storage_dir.exists()

    def test_corrupt_file_handled(self, tmp_path):
        storage = tmp_path / "profiles"
        storage.mkdir()
        (storage / "bad.json").write_text("not json")

        s = ProfileStore(storage_dir=str(storage))
        assert s.custom_count == 0
