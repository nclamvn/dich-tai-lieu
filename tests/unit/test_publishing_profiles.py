"""Tests for core_v2/publishing_profiles.py — profile data, lookup, and prompt generation."""

import pytest

from core_v2.publishing_profiles import (
    PublishingProfile,
    PROFILES,
    BASE_RENDERING_SKILL,
    get_profile,
    list_profiles,
)


# ==================== Profile Registry ====================


class TestProfileRegistry:
    """All profiles exist and have required fields."""

    EXPECTED_PROFILES = [
        "novel", "poetry", "essay",
        "business_report", "white_paper",
        "academic_paper", "arxiv_paper", "thesis", "textbook",
        "technical_doc", "api_doc", "user_manual",
    ]

    def test_all_expected_profiles_exist(self):
        for pid in self.EXPECTED_PROFILES:
            assert pid in PROFILES, f"Profile '{pid}' missing"

    def test_profile_count(self):
        assert len(PROFILES) >= 11

    @pytest.mark.parametrize("pid", EXPECTED_PROFILES)
    def test_required_fields(self, pid):
        p = PROFILES[pid]
        assert p.id == pid
        assert p.name, f"Profile '{pid}' has no name"
        assert p.description, f"Profile '{pid}' has no description"
        assert p.output_format in ("docx", "pdf", "epub", "html")
        assert p.style_guide.strip(), f"Profile '{pid}' has no style_guide"

    @pytest.mark.parametrize("pid", EXPECTED_PROFILES)
    def test_id_matches_key(self, pid):
        assert PROFILES[pid].id == pid


# ==================== Template Assignments ====================


class TestTemplateAssignments:
    """template_name matches expected category."""

    def test_fiction_profiles_use_ebook(self):
        for pid in ("novel", "poetry", "essay"):
            assert PROFILES[pid].template_name == "ebook"

    def test_business_profiles_use_business(self):
        for pid in ("business_report", "white_paper", "technical_doc", "api_doc", "user_manual"):
            assert PROFILES[pid].template_name == "business"

    def test_academic_profiles_use_academic(self):
        for pid in ("academic_paper", "arxiv_paper", "thesis", "textbook"):
            assert PROFILES[pid].template_name == "academic"


# ==================== get_profile / list_profiles ====================


class TestProfileLookup:
    """get_profile() and list_profiles() helpers."""

    def test_get_existing_profile(self):
        p = get_profile("novel")
        assert p is not None
        assert p.id == "novel"

    def test_get_nonexistent_profile(self):
        assert get_profile("nonexistent_genre") is None

    def test_list_profiles_returns_all_ids(self):
        ids = list_profiles()
        assert isinstance(ids, list)
        assert "novel" in ids
        assert "academic_paper" in ids
        assert len(ids) == len(PROFILES)


# ==================== to_prompt ====================


class TestToPrompt:
    """PublishingProfile.to_prompt() output."""

    def test_includes_name(self):
        p = PROFILES["novel"]
        prompt = p.to_prompt()
        assert "Novel / Fiction" in prompt

    def test_includes_style_guide(self):
        p = PROFILES["novel"]
        prompt = p.to_prompt()
        assert "Style Guide:" in prompt
        assert "narrative" in prompt.lower()

    def test_includes_special_instructions_when_present(self):
        p = PROFILES["novel"]
        assert p.special_instructions  # novel has special instructions
        prompt = p.to_prompt()
        assert "Special Instructions:" in prompt

    def test_includes_rendering_instructions_when_present(self):
        p = PROFILES["novel"]
        assert p.rendering_instructions
        prompt = p.to_prompt()
        assert "Formatting:" in prompt

    def test_omits_special_instructions_when_empty(self):
        p = PublishingProfile(
            id="test", name="Test", description="Test",
            output_format="docx", style_guide="Some guide",
        )
        prompt = p.to_prompt()
        assert "Special Instructions:" not in prompt

    def test_omits_rendering_when_empty(self):
        p = PublishingProfile(
            id="test", name="Test", description="Test",
            output_format="docx", style_guide="Some guide",
        )
        prompt = p.to_prompt()
        assert "Formatting:" not in prompt


# ==================== BASE_RENDERING_SKILL ====================


class TestBaseRenderingSkill:
    """BASE_RENDERING_SKILL constant contains key rules."""

    def test_contains_heading_rules(self):
        assert "##" in BASE_RENDERING_SKILL

    def test_contains_bold_italic(self):
        assert "**bold**" in BASE_RENDERING_SKILL
        assert "*italic*" in BASE_RENDERING_SKILL

    def test_contains_code_block_rule(self):
        assert "```" in BASE_RENDERING_SKILL

    def test_contains_table_rule(self):
        assert "|" in BASE_RENDERING_SKILL
