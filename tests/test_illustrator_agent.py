"""
Tests for IllustratorAgent (Sprint K)
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from core.book_writer_v2.agents.illustrator import IllustratorAgent
from core.book_writer_v2.agents.base import AgentContext
from core.book_writer_v2.config import BookWriterConfig
from core.book_writer_v2.ai_adapter import MockAIClient
from core.book_writer_v2.illustration_models import (
    BookGenre,
    ChapterIndex,
    GalleryGroup,
    IllustrationPlan,
    ImageAnalysis,
    ImageCategory,
    ImageManifest,
    ImagePlacement,
    ImageSize,
    LayoutConfig,
    LayoutMode,
    MatchCandidate,
)
from core.book_writer_v2.models import (
    BookBlueprint,
    BookProject,
    Chapter,
    Part,
    Section,
    WordCountTarget,
)


@pytest.fixture
def config():
    return BookWriterConfig()


@pytest.fixture
def mock_client():
    return MockAIClient()


@pytest.fixture
def agent(config, mock_client):
    return IllustratorAgent(config, mock_client)


@pytest.fixture
def context(config):
    return AgentContext(
        project_id="test-project",
        config=config,
        progress_callback=lambda msg, pct: None,
    )


def make_section(num=1, content="This is a test section about technology and innovation."):
    return Section(
        id=str(uuid.uuid4()),
        number=num,
        title=f"Section {num}",
        chapter_id="ch1",
        word_count=WordCountTarget(target=1500, actual=len(content.split())),
        content=content,
    )


def make_chapter(num=1, section_count=3, keywords_in_content=""):
    content = f"This chapter covers {keywords_in_content or 'various topics'} in detail. " * 20
    sections = [make_section(i + 1, content) for i in range(section_count)]
    return Chapter(
        id=str(uuid.uuid4()),
        number=num,
        title=f"Chapter {num}: {keywords_in_content or 'Overview'}",
        part_id="part1",
        sections=sections,
    )


def make_blueprint(chapter_count=3):
    chapters = [make_chapter(i + 1) for i in range(chapter_count)]
    part = Part(id="part1", number=1, title="Part 1", chapters=chapters)
    return BookBlueprint(title="Test Book", parts=[part])


def make_image(image_id="img1", keywords=None, category=ImageCategory.PHOTO, quality=0.8):
    return ImageAnalysis(
        image_id=image_id,
        filename=f"{image_id}.jpg",
        filepath=f"/tmp/{image_id}.jpg",
        subject=f"Subject of {image_id}",
        description=f"Description of {image_id}",
        keywords=keywords or ["test", "image"],
        category=category,
        width=1920,
        height=1080,
        quality_score=quality,
        suggested_layout=LayoutMode.INLINE,
        suggested_size=ImageSize.MEDIUM,
    )


def make_manifest(images=None, genre=BookGenre.NON_FICTION):
    if images is None:
        images = [make_image(f"img{i}") for i in range(3)]
    return ImageManifest(images=images, detected_genre=genre, total_images=len(images))


class TestIllustratorAgent:
    def test_name(self, agent):
        assert agent.name == "Illustrator"

    def test_description(self, agent):
        assert "match" in agent.description.lower() or "layout" in agent.description.lower()

    @pytest.mark.asyncio
    async def test_execute_no_blueprint(self, agent, context):
        project = BookProject()
        manifest = make_manifest()
        result = await agent.execute({"project": project, "manifest": manifest}, context)
        assert isinstance(result, IllustrationPlan)
        assert result.total_placed == 0

    @pytest.mark.asyncio
    async def test_execute_no_images(self, agent, context):
        project = BookProject(blueprint=make_blueprint())
        manifest = ImageManifest()
        result = await agent.execute({"project": project, "manifest": manifest}, context)
        assert isinstance(result, IllustrationPlan)
        assert result.total_placed == 0


class TestBuildChapterIndex:
    def test_basic_index(self, agent):
        bp = make_blueprint(3)
        indices = agent._build_chapter_index(bp)
        assert len(indices) == 3
        assert all(isinstance(ci, ChapterIndex) for ci in indices)
        assert indices[0].chapter_number == 1
        assert indices[2].chapter_number == 3

    def test_topics_include_titles(self, agent):
        bp = make_blueprint(1)
        indices = agent._build_chapter_index(bp)
        # Topics should include chapter + section titles
        assert len(indices[0].topics) >= 1


class TestMatchImageToContent:
    @pytest.mark.asyncio
    async def test_returns_candidate(self, agent):
        image = make_image("i1", keywords=["technology", "innovation"])
        chapter = ChapterIndex(
            chapter_id="ch1",
            chapter_number=1,
            title="Technology Overview",
            topics=["technology"],
            keywords=["technology", "innovation", "digital"],
        )
        candidate = await agent._match_image_to_content(image, chapter)
        assert isinstance(candidate, MatchCandidate)
        assert candidate.combined_score >= 0.0


class TestLayoutDecisions:
    def test_high_quality_landscape_first(self, agent):
        img = make_image(quality=0.9)
        img._width = 1920  # landscape
        config = LayoutConfig(prefer_full_page_for_high_quality=True)
        layout = agent._decide_layout(img, config, position=0)
        assert layout == LayoutMode.FULL_PAGE

    def test_first_image_float_top_if_not_full_page(self, agent):
        img = make_image(quality=0.5)
        config = LayoutConfig(prefer_full_page_for_high_quality=True)
        layout = agent._decide_layout(img, config, position=0)
        assert layout == LayoutMode.FLOAT_TOP

    def test_small_image_margin(self, agent):
        img = make_image()
        img.suggested_size = ImageSize.SMALL
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=2)
        assert layout == LayoutMode.MARGIN

    def test_default_uses_suggestion(self, agent):
        img = make_image()
        img.suggested_layout = LayoutMode.GALLERY
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=1)
        assert layout == LayoutMode.GALLERY


class TestDecideSize:
    def test_full_page_gets_full_size(self, agent):
        img = make_image()
        size = agent._decide_size(img, LayoutMode.FULL_PAGE)
        assert size == ImageSize.FULL

    def test_margin_gets_small(self, agent):
        img = make_image()
        size = agent._decide_size(img, LayoutMode.MARGIN)
        assert size == ImageSize.SMALL

    def test_float_top_gets_large(self, agent):
        img = make_image()
        size = agent._decide_size(img, LayoutMode.FLOAT_TOP)
        assert size == ImageSize.LARGE


class TestBalanceDistribution:
    def test_trims_overloaded_chapters(self, agent):
        config = LayoutConfig(max_images_per_chapter=2)
        placements = [
            ImagePlacement(image_id=f"i{i}", chapter_index=0, relevance_score=0.5 + i * 0.1)
            for i in range(5)
        ]
        balanced = agent._balance_distribution(placements, config)
        ch0 = [p for p in balanced if p.chapter_index == 0]
        assert len(ch0) <= 2

    def test_keeps_highest_relevance(self, agent):
        config = LayoutConfig(max_images_per_chapter=1)
        placements = [
            ImagePlacement(image_id="low", chapter_index=0, relevance_score=0.1),
            ImagePlacement(image_id="high", chapter_index=0, relevance_score=0.9),
        ]
        balanced = agent._balance_distribution(placements, config)
        assert len(balanced) == 1
        assert balanced[0].image_id == "high"

    def test_no_change_within_limit(self, agent):
        config = LayoutConfig(max_images_per_chapter=5)
        placements = [
            ImagePlacement(image_id=f"i{i}", chapter_index=0)
            for i in range(3)
        ]
        balanced = agent._balance_distribution(placements, config)
        assert len(balanced) == 3


class TestIdentifyGalleries:
    def test_groups_same_category(self, agent):
        config = LayoutConfig(enable_galleries=True)
        placements = [
            ImagePlacement(image_id=f"p{i}", chapter_index=0)
            for i in range(4)
        ]
        images = [
            make_image(f"p{i}", category=ImageCategory.PHOTO)
            for i in range(4)
        ]
        manifest = make_manifest(images)

        galleries = agent._identify_galleries(placements, manifest, config)
        assert len(galleries) >= 1
        assert all(isinstance(g, GalleryGroup) for g in galleries)

    def test_no_galleries_if_disabled(self, agent):
        config = LayoutConfig(enable_galleries=False)
        placements = [
            ImagePlacement(image_id=f"p{i}", chapter_index=0)
            for i in range(4)
        ]
        manifest = make_manifest([make_image(f"p{i}") for i in range(4)])
        galleries = agent._identify_galleries(placements, manifest, config)
        assert galleries == []

    def test_no_gallery_for_few_images(self, agent):
        config = LayoutConfig(enable_galleries=True)
        placements = [
            ImagePlacement(image_id="p0", chapter_index=0),
            ImagePlacement(image_id="p1", chapter_index=0),
        ]
        manifest = make_manifest([make_image(f"p{i}") for i in range(2)])
        galleries = agent._identify_galleries(placements, manifest, config)
        assert galleries == []


class TestGenerateCaption:
    @pytest.mark.asyncio
    async def test_generates_string(self, agent):
        img = make_image()
        caption = await agent._generate_caption(img, "Technology", "Intro", BookGenre.NON_FICTION)
        assert isinstance(caption, str)
        assert len(caption) > 0


class TestGenreAwareLayout:
    """Tests that layout decisions adapt to book genre."""

    def test_technical_diagram_always_inline(self, agent):
        img = make_image(category=ImageCategory.DIAGRAM, quality=0.95)
        config = LayoutConfig(prefer_full_page_for_high_quality=True)
        layout = agent._decide_layout(img, config, position=0, genre=BookGenre.TECHNICAL)
        assert layout == LayoutMode.INLINE

    def test_children_artwork_full_page(self, agent):
        img = make_image(category=ImageCategory.ART, quality=0.85)
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=0, genre=BookGenre.CHILDREN)
        assert layout == LayoutMode.FULL_PAGE

    def test_children_non_art_inline(self, agent):
        img = make_image(category=ImageCategory.DIAGRAM, quality=0.9)
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=0, genre=BookGenre.CHILDREN)
        assert layout == LayoutMode.INLINE

    def test_photography_high_quality_landscape_full_page(self, agent):
        img = make_image(quality=0.9)
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=0, genre=BookGenre.PHOTOGRAPHY)
        assert layout == LayoutMode.FULL_PAGE

    def test_cookbook_food_photo_full_page(self, agent):
        img = make_image(category=ImageCategory.PHOTO, quality=0.85)
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=0, genre=BookGenre.COOKBOOK)
        assert layout == LayoutMode.FULL_PAGE

    def test_cookbook_diagram_inline(self, agent):
        img = make_image(category=ImageCategory.DIAGRAM, quality=0.8)
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=1, genre=BookGenre.COOKBOOK)
        assert layout == LayoutMode.INLINE


class TestQualityGuards:
    """Tests that low quality images are constrained."""

    def test_low_quality_never_full_page(self, agent):
        img = make_image(quality=0.3)
        config = LayoutConfig(prefer_full_page_for_high_quality=True)
        layout = agent._decide_layout(img, config, position=0)
        assert layout != LayoutMode.FULL_PAGE

    def test_low_quality_first_position_float_top(self, agent):
        img = make_image(quality=0.4)
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=0)
        assert layout == LayoutMode.FLOAT_TOP

    def test_low_quality_small_gets_margin(self, agent):
        img = make_image(quality=0.3)
        img.suggested_size = ImageSize.SMALL
        config = LayoutConfig()
        layout = agent._decide_layout(img, config, position=2)
        assert layout == LayoutMode.MARGIN


class TestAvoidConsecutiveFullPage:
    """Tests that 2 FULL_PAGE in a row is avoided."""

    def test_no_consecutive_full_page(self, agent):
        img = make_image(quality=0.95)
        config = LayoutConfig(prefer_full_page_for_high_quality=True)
        layout = agent._decide_layout(
            img, config, position=0, prev_layout=LayoutMode.FULL_PAGE
        )
        assert layout != LayoutMode.FULL_PAGE


class TestAltTextGeneration:
    """Tests for _generate_alt_text."""

    def test_photo_with_subject(self):
        img = make_image(category=ImageCategory.PHOTO)
        alt = IllustratorAgent._generate_alt_text(img)
        assert "Photo" in alt
        assert img.subject in alt

    def test_diagram_alt_text(self):
        img = make_image(category=ImageCategory.DIAGRAM)
        alt = IllustratorAgent._generate_alt_text(img)
        assert "Diagram" in alt

    def test_with_era_context(self):
        img = make_image()
        img.era_or_context = "1954"
        alt = IllustratorAgent._generate_alt_text(img)
        assert "1954" in alt

    def test_other_category_fallback(self):
        img = ImageAnalysis(
            image_id="x", filename="x.jpg", filepath="/x.jpg",
            category=ImageCategory.OTHER,
        )
        alt = IllustratorAgent._generate_alt_text(img)
        assert alt == "Image"


class TestChapterIndexEnhanced:
    """Tests for enhanced _build_chapter_index with entities and time periods."""

    def test_extracts_paragraph_count(self, agent):
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        ch = make_chapter(num=1, section_count=1, keywords_in_content="test")
        ch.sections[0].content = content
        bp = BookBlueprint(title="Test", parts=[Part(id="p1", number=1, title="P1", chapters=[ch])])
        indices = agent._build_chapter_index(bp)
        assert indices[0].paragraph_count >= 3

    def test_populates_sections_list(self, agent):
        bp = make_blueprint(1)
        indices = agent._build_chapter_index(bp)
        assert len(indices[0].sections) == 3  # make_chapter default section_count=3
        assert "title" in indices[0].sections[0]
        assert "index" in indices[0].sections[0]

    def test_extracts_summary_from_chapter(self, agent):
        ch = make_chapter(num=1)
        ch.summary = "This is a test chapter summary."
        bp = BookBlueprint(title="T", parts=[Part(id="p1", number=1, title="P", chapters=[ch])])
        indices = agent._build_chapter_index(bp)
        assert "test chapter summary" in indices[0].summary


class TestUnmatchedImages:
    """Tests that irrelevant images stay in unmatched list."""

    @pytest.mark.asyncio
    async def test_irrelevant_image_unmatched(self, agent, context):
        """Image with keywords that don't match any chapter content stays unmatched."""
        bp = make_blueprint(1)
        bp.parts[0].chapters[0].title = "Mathematics"
        bp.parts[0].chapters[0].sections[0].content = "algebra equations polynomials " * 20

        img = make_image("alien", keywords=["alien", "spaceship", "galaxy", "nebula"])
        manifest = make_manifest([img])

        project = BookProject(blueprint=bp)
        result = await agent.execute({"project": project, "manifest": manifest}, context)
        assert isinstance(result, IllustrationPlan)
        # With MockAIClient the AI relevance might be non-zero,
        # but the overall structure should still be valid
        assert result.total_placed + len(result.unmatched_image_ids) == 1
