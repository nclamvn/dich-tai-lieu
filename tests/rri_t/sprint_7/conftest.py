"""
Sprint 7 — Illustrated Book Engine (Sprint K) fixtures.

Provides reusable fixtures for K1–K8 integration tests:
- sample_images: list of test image file paths
- book_blueprint: minimal BookBlueprint for rendering tests
- book_project_with_images: BookProject with uploaded_images populated
- illustration_plan: pre-built IllustrationPlan
- mock_book_ai_client: MockAIClient for book writer agents
"""

import os
import pytest
import tempfile
from pathlib import Path

from core.book_writer_v2.config import BookWriterConfig
from core.book_writer_v2.ai_adapter import MockAIClient
from core.book_writer_v2.agents.base import AgentContext
from core.book_writer_v2.models import (
    BookBlueprint,
    BookProject,
    Chapter,
    Part,
    Section,
    WordCountTarget,
    FrontMatter,
    BackMatter,
)
from core.book_writer_v2.illustration_models import (
    BookGenre,
    GalleryGroup,
    IllustrationPlan,
    ImageAnalysis,
    ImageCategory,
    ImageManifest,
    ImagePlacement,
    ImageSize,
    LayoutMode,
)


@pytest.fixture
def bw_config():
    """BookWriterConfig with defaults."""
    return BookWriterConfig()


@pytest.fixture
def mock_book_ai():
    """MockAIClient for book writer agents."""
    return MockAIClient()


@pytest.fixture
def agent_context(bw_config):
    """AgentContext for agent execution."""
    return AgentContext(
        project_id="k8-test",
        config=bw_config,
        progress_callback=lambda msg, pct: None,
    )


@pytest.fixture
def sample_images(tmp_path):
    """Create 5 test JPEG images with PIL, return list of paths."""
    paths = []
    try:
        from PIL import Image
        for i in range(5):
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (128, 0, 128)]
            img = Image.new("RGB", (800 + i * 100, 600 + i * 50), color=colors[i])
            p = tmp_path / f"test_image_{i}.jpg"
            img.save(str(p), format="JPEG")
            paths.append(str(p))
    except ImportError:
        # Fallback: write minimal JPEG headers
        for i in range(5):
            p = tmp_path / f"test_image_{i}.jpg"
            p.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 200 + b'\xff\xd9')
            paths.append(str(p))
    return paths


@pytest.fixture
def book_blueprint():
    """Minimal BookBlueprint with 2 chapters, 2 sections each."""
    sections_ch1 = [
        Section(
            id=f"s1-{i}", number=i + 1, title=f"Section {i+1}", chapter_id="ch1",
            word_count=WordCountTarget(target=500, actual=50),
            content=f"Content for section {i+1} of chapter 1. " * 10,
        )
        for i in range(2)
    ]
    sections_ch2 = [
        Section(
            id=f"s2-{i}", number=i + 1, title=f"Section {i+1}", chapter_id="ch2",
            word_count=WordCountTarget(target=500, actual=50),
            content=f"Content for section {i+1} of chapter 2. " * 10,
        )
        for i in range(2)
    ]
    ch1 = Chapter(
        id="ch1", number=1, title="Introduction", part_id="p1",
        sections=sections_ch1,
        introduction="Welcome to the book.",
        summary="Chapter 1 summary.",
        key_takeaways=["Point A", "Point B"],
    )
    ch2 = Chapter(
        id="ch2", number=2, title="Deep Dive", part_id="p1",
        sections=sections_ch2,
        introduction="Let us explore further.",
        summary="Chapter 2 summary.",
        key_takeaways=["Point C"],
    )
    part = Part(id="p1", number=1, title="Part One", chapters=[ch1, ch2])
    return BookBlueprint(
        title="Test Illustrated Book",
        subtitle="A Sprint K Test",
        author="K8 Test Suite",
        parts=[part],
        front_matter=FrontMatter(preface="Preface text."),
        back_matter=BackMatter(conclusion="Conclusion text."),
    )


@pytest.fixture
def image_manifest(sample_images):
    """ImageManifest from sample images."""
    analyses = []
    for i, path in enumerate(sample_images):
        analyses.append(ImageAnalysis(
            image_id=path,
            filename=os.path.basename(path),
            filepath=path,
            subject=f"Subject {i}",
            description=f"Description of image {i}",
            keywords=[f"keyword_{i}", "test", "illustration"],
            category=ImageCategory.PHOTO if i < 3 else ImageCategory.DIAGRAM,
            width=800 + i * 100,
            height=600 + i * 50,
            file_size_bytes=50000,
            media_type="image/jpeg",
            quality_score=0.7 + i * 0.05,
            suggested_layout=LayoutMode.INLINE,
            suggested_size=ImageSize.MEDIUM,
        ))
    return ImageManifest(
        images=analyses,
        detected_genre=BookGenre.NON_FICTION,
        total_images=len(analyses),
    )


@pytest.fixture
def illustration_plan(sample_images):
    """Pre-built IllustrationPlan with 3 placements + 1 gallery."""
    placements = [
        ImagePlacement(
            image_id=sample_images[0],
            chapter_index=0, section_index=0,
            layout_mode=LayoutMode.INLINE, size=ImageSize.MEDIUM,
            caption="Figure 1: Test inline image",
            alt_text="A test image",
            relevance_score=0.85,
        ),
        ImagePlacement(
            image_id=sample_images[1],
            chapter_index=0, section_index=1,
            layout_mode=LayoutMode.FULL_PAGE, size=ImageSize.FULL,
            caption="Figure 2: Full page diagram",
            alt_text="A full page diagram",
            credit="Photo by Tester",
            relevance_score=0.92,
        ),
        ImagePlacement(
            image_id=sample_images[2],
            chapter_index=1, section_index=0,
            layout_mode=LayoutMode.FLOAT_TOP, size=ImageSize.LARGE,
            caption="Figure 3: Float top image",
            relevance_score=0.78,
        ),
    ]
    galleries = [
        GalleryGroup(
            group_id="gal-1",
            image_ids=[sample_images[3], sample_images[4]],
            title="Test Gallery",
            caption="A collection of test images",
            chapter_index=1,
        ),
    ]
    return IllustrationPlan(
        project_id="k8-test",
        placements=placements,
        galleries=galleries,
        unmatched_image_ids=[],
        genre=BookGenre.NON_FICTION,
    )


@pytest.fixture
def book_project_with_images(book_blueprint, sample_images, illustration_plan):
    """BookProject with blueprint, uploaded images, and illustration plan."""
    return BookProject(
        id="k8-test-project",
        user_request="Test Illustrated Book",
        blueprint=book_blueprint,
        uploaded_images=sample_images,
        illustration_plan=illustration_plan,
    )
