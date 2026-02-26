"""
Tests for VisionAnalyzer Agent (Sprint K)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
from core.book_writer_v2.agents.base import AgentContext
from core.book_writer_v2.config import BookWriterConfig
from core.book_writer_v2.ai_adapter import MockAIClient
from core.book_writer_v2.illustration_models import (
    ImageAnalysis,
    ImageCategory,
    ImageManifest,
    ImageSize,
    LayoutMode,
    BookGenre,
)


@pytest.fixture
def config():
    return BookWriterConfig()


@pytest.fixture
def mock_client():
    return MockAIClient()


@pytest.fixture
def agent(config, mock_client):
    return VisionAnalyzerAgent(config, mock_client)


@pytest.fixture
def context(config):
    return AgentContext(
        project_id="test-project",
        config=config,
        progress_callback=lambda msg, pct: None,
    )


class TestVisionAnalyzerAgent:
    def test_name(self, agent):
        assert agent.name == "VisionAnalyzer"

    def test_description(self, agent):
        assert "image" in agent.description.lower() or "analyze" in agent.description.lower()

    @pytest.mark.asyncio
    async def test_execute_empty_paths(self, agent, context):
        result = await agent.execute({"image_paths": []}, context)
        assert isinstance(result, ImageManifest)
        assert result.total_images == 0

    @pytest.mark.asyncio
    async def test_execute_no_paths_key(self, agent, context):
        result = await agent.execute({}, context)
        assert isinstance(result, ImageManifest)
        assert result.total_images == 0


class TestVisionAnalyzerParsing:
    def test_parse_category_valid(self):
        assert VisionAnalyzerAgent._parse_category("photo") == ImageCategory.PHOTO
        assert VisionAnalyzerAgent._parse_category("diagram") == ImageCategory.DIAGRAM
        assert VisionAnalyzerAgent._parse_category("CHART") == ImageCategory.CHART

    def test_parse_category_invalid(self):
        assert VisionAnalyzerAgent._parse_category("unknown_type") == ImageCategory.OTHER

    def test_parse_layout_valid(self):
        assert VisionAnalyzerAgent._parse_layout("full_page") == LayoutMode.FULL_PAGE
        assert VisionAnalyzerAgent._parse_layout("inline") == LayoutMode.INLINE

    def test_parse_layout_invalid(self):
        assert VisionAnalyzerAgent._parse_layout("blah") == LayoutMode.INLINE

    def test_parse_size_valid(self):
        assert VisionAnalyzerAgent._parse_size("small") == ImageSize.SMALL
        assert VisionAnalyzerAgent._parse_size("full") == ImageSize.FULL

    def test_parse_size_invalid(self):
        assert VisionAnalyzerAgent._parse_size("tiny") == ImageSize.MEDIUM

    def test_parse_genre_valid(self):
        assert VisionAnalyzerAgent._parse_genre("children") == BookGenre.CHILDREN
        assert VisionAnalyzerAgent._parse_genre("cookbook") == BookGenre.COOKBOOK

    def test_parse_genre_invalid(self):
        assert VisionAnalyzerAgent._parse_genre("romance") == BookGenre.NON_FICTION


class TestMockAIClientVision:
    @pytest.mark.asyncio
    async def test_generate_with_vision(self):
        client = MockAIClient()
        result = await client.generate_with_vision(
            prompt="Analyze this image",
            image_base64="fake_base64",
            media_type="image/jpeg",
        )
        assert "subject" in result.lower() or "sample" in result.lower()
        assert client.call_count == 1


class TestQualityScoring:
    def test_high_quality_threshold(self):
        img = ImageAnalysis(image_id="a", filename="a.jpg", filepath="/a.jpg", quality_score=0.7)
        assert img.is_high_quality is True

    def test_below_threshold(self):
        img = ImageAnalysis(image_id="b", filename="b.jpg", filepath="/b.jpg", quality_score=0.69)
        assert img.is_high_quality is False


class TestLayoutSuggestions:
    def test_landscape_suggestion(self):
        img = ImageAnalysis(
            image_id="l1",
            filename="l.jpg",
            filepath="/l.jpg",
            width=1920,
            height=1080,
            quality_score=0.9,
            suggested_layout=LayoutMode.FULL_PAGE,
        )
        assert img.is_landscape is True
        assert img.suggested_layout == LayoutMode.FULL_PAGE

    def test_portrait_suggestion(self):
        img = ImageAnalysis(
            image_id="p1",
            filename="p.jpg",
            filepath="/p.jpg",
            width=600,
            height=900,
            suggested_layout=LayoutMode.MARGIN,
        )
        assert img.is_portrait is True
        assert img.suggested_layout == LayoutMode.MARGIN


class TestScoreResolution:
    """Tests for _score_resolution static method."""

    def test_zero_dimensions(self):
        assert VisionAnalyzerAgent._score_resolution(0, 0) == 0.0

    def test_zero_width(self):
        assert VisionAnalyzerAgent._score_resolution(0, 500) == 0.0

    def test_high_res(self):
        assert VisionAnalyzerAgent._score_resolution(3000, 2000) == 1.0

    def test_medium_res(self):
        score = VisionAnalyzerAgent._score_resolution(1200, 800)
        assert score == 0.7

    def test_low_res(self):
        score = VisionAnalyzerAgent._score_resolution(400, 300)
        assert score == 0.3

    def test_1500px_tier(self):
        score = VisionAnalyzerAgent._score_resolution(1500, 1000)
        assert score == 0.85

    def test_600px_tier(self):
        score = VisionAnalyzerAgent._score_resolution(600, 400)
        assert score == 0.5


class TestSuggestLayout:
    """Tests for _suggest_layout static method."""

    def test_diagram_always_inline(self):
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.DIAGRAM, 1200, 800, 0.9, "full_page", "full"
        )
        assert layout == LayoutMode.INLINE
        assert size == ImageSize.LARGE

    def test_chart_inline_medium(self):
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.CHART, 600, 400, 0.8, "inline", "medium"
        )
        assert layout == LayoutMode.INLINE
        assert size == ImageSize.MEDIUM

    def test_high_quality_landscape_photo_full_page(self):
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.PHOTO, 2000, 1200, 0.9, "inline", "medium"
        )
        assert layout == LayoutMode.FULL_PAGE
        assert size == ImageSize.FULL

    def test_low_quality_never_full_page(self):
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.PHOTO, 2000, 1200, 0.3, "full_page", "full"
        )
        assert layout != LayoutMode.FULL_PAGE
        assert size not in (ImageSize.FULL, ImageSize.LARGE)

    def test_very_small_image_margin(self):
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.PHOTO, 200, 150, 0.8, "inline", "medium"
        )
        assert layout == LayoutMode.MARGIN
        assert size == ImageSize.SMALL

    def test_map_inline_large(self):
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.MAP, 1200, 900, 0.7, "float_top", "medium"
        )
        assert layout == LayoutMode.INLINE
        assert size == ImageSize.LARGE

    def test_screenshot_inline_medium(self):
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.SCREENSHOT, 1024, 768, 0.6, "float_top", "large"
        )
        assert layout == LayoutMode.INLINE
        assert size == ImageSize.MEDIUM

    def test_respects_ai_suggestion_when_no_override(self):
        """For 'other' category with decent quality, AI suggestion passes through."""
        layout, size = VisionAnalyzerAgent._suggest_layout(
            ImageCategory.OTHER, 800, 600, 0.6, "float_top", "large"
        )
        assert layout == LayoutMode.FLOAT_TOP
        assert size == ImageSize.LARGE


class TestMinDisplayWidth:
    """Tests for _min_display_width static method."""

    def test_zero_width(self):
        assert VisionAnalyzerAgent._min_display_width(0) == 200

    def test_large_image(self):
        assert VisionAnalyzerAgent._min_display_width(2000) == 600

    def test_medium_image(self):
        assert VisionAnalyzerAgent._min_display_width(1000) == 500

    def test_small_image(self):
        assert VisionAnalyzerAgent._min_display_width(600) == 400

    def test_tiny_image(self):
        assert VisionAnalyzerAgent._min_display_width(300) == 250

    def test_very_tiny_image(self):
        result = VisionAnalyzerAgent._min_display_width(80)
        assert result == 100  # clamped to min 100
