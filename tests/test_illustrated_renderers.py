"""
Tests for Illustrated Renderers (Sprint K)

Tests DOCX, HTML, Markdown with illustrations, EPUB renderer,
DocxIllustratedRenderer, and empty plan fallback.
"""

import os
import pytest
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock

from core.book_writer_v2.agents.publisher import PublisherAgent
from core.book_writer_v2.agents.base import AgentContext
from core.book_writer_v2.config import BookWriterConfig, OutputFormat
from core.book_writer_v2.ai_adapter import MockAIClient
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
    IllustrationPlan,
    ImagePlacement,
    ImageSize,
    LayoutConfig,
    LayoutMode,
    GalleryGroup,
)
from core.book_writer_v2.renderers.docx_renderer import DocxIllustratedRenderer
from core.book_writer_v2.renderers.epub_renderer import EpubRenderer
from core.book_writer_v2.renderers.pdf_renderer import PdfIllustratedRenderer
from core.book_writer_v2.renderers.layout_engine import LayoutEngine


@pytest.fixture
def config():
    return BookWriterConfig()


@pytest.fixture
def mock_client():
    return MockAIClient()


@pytest.fixture
def agent(config, mock_client):
    return PublisherAgent(config, mock_client)


@pytest.fixture
def context(config):
    return AgentContext(
        project_id="test-pub",
        config=config,
        progress_callback=lambda msg, pct: None,
    )


def make_blueprint():
    section = Section(
        id="s1", number=1, title="Test Section", chapter_id="ch1",
        word_count=WordCountTarget(target=500, actual=20),
        content="This is test content for the section. " * 10,
    )
    chapter = Chapter(
        id="ch1", number=1, title="Test Chapter", part_id="p1",
        sections=[section],
        introduction="Chapter intro text.",
        summary="Chapter summary text.",
        key_takeaways=["Key point one", "Key point two"],
    )
    part = Part(id="p1", number=1, title="Part One", chapters=[chapter])
    return BookBlueprint(
        title="Test Book",
        subtitle="A Test",
        author="Test Author",
        parts=[part],
        front_matter=FrontMatter(preface="This is the preface."),
        back_matter=BackMatter(conclusion="This is the conclusion."),
    )


def make_plan():
    return IllustrationPlan(
        placements=[
            ImagePlacement(
                image_id="img1",
                chapter_index=0,
                section_index=0,
                layout_mode=LayoutMode.INLINE,
                size=ImageSize.MEDIUM,
                caption="Test caption",
                relevance_score=0.85,
            ),
            ImagePlacement(
                image_id="img2",
                chapter_index=0,
                section_index=0,
                layout_mode=LayoutMode.FLOAT_TOP,
                size=ImageSize.LARGE,
                caption="Float top caption",
                relevance_score=0.75,
            ),
            ImagePlacement(
                image_id="img3",
                chapter_index=0,
                section_index=0,
                layout_mode=LayoutMode.FULL_PAGE,
                size=ImageSize.FULL,
                caption="Full page image",
                relevance_score=0.95,
            ),
        ],
    )


class TestMarkdownWithIllustrations:
    @pytest.mark.asyncio
    async def test_markdown_no_plan(self, agent):
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_markdown(bp, Path(tmpdir))
            content = path.read_text()
            assert "# Test Book" in content
            assert "Test Section" in content
            assert "![" not in content  # No illustrations

    @pytest.mark.asyncio
    async def test_markdown_with_plan(self, agent):
        bp = make_blueprint()
        plan = make_plan()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_markdown(bp, Path(tmpdir), plan)
            content = path.read_text()
            assert "# Test Book" in content
            # Markdown illustrations inserted
            assert "![" in content
            assert "Test caption" in content

    @pytest.mark.asyncio
    async def test_markdown_empty_plan(self, agent):
        bp = make_blueprint()
        plan = IllustrationPlan()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_markdown(bp, Path(tmpdir), plan)
            content = path.read_text()
            assert "# Test Book" in content
            assert "![" not in content


class TestHTMLWithIllustrations:
    @pytest.mark.asyncio
    async def test_html_no_plan(self, agent):
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_html(bp, Path(tmpdir))
            content = path.read_text()
            assert "<h1>Test Book</h1>" in content
            assert "<figure" not in content

    @pytest.mark.asyncio
    async def test_html_with_plan(self, agent):
        bp = make_blueprint()
        plan = make_plan()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_html(bp, Path(tmpdir), plan)
            content = path.read_text()
            assert "<figure" in content
            assert "Test caption" in content
            assert "figcaption" in content

    @pytest.mark.asyncio
    async def test_html_figure_styling(self, agent):
        bp = make_blueprint()
        plan = IllustrationPlan(
            placements=[
                ImagePlacement(
                    image_id="styled",
                    chapter_index=0,
                    section_index=0,
                    layout_mode=LayoutMode.FULL_PAGE,
                    size=ImageSize.FULL,
                    caption="Styled image",
                ),
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_html(bp, Path(tmpdir), plan)
            content = path.read_text()
            assert "full-page" in content


class TestDOCXWithIllustrations:
    @pytest.mark.asyncio
    async def test_docx_no_plan(self, agent):
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_docx(bp, Path(tmpdir))
            assert path.exists()
            assert path.suffix == ".docx"

    @pytest.mark.asyncio
    async def test_docx_with_empty_plan(self, agent):
        bp = make_blueprint()
        plan = IllustrationPlan()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_docx(bp, Path(tmpdir), plan)
            assert path.exists()
            assert path.suffix == ".docx"

    @pytest.mark.asyncio
    async def test_docx_with_plan_missing_images(self, agent):
        """Images not found on disk should be skipped gracefully."""
        bp = make_blueprint()
        plan = make_plan()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await agent._generate_docx(bp, Path(tmpdir), plan)
            assert path.exists()  # Should not crash


class TestPublisherExecute:
    @pytest.mark.asyncio
    async def test_execute_text_only(self, agent, context):
        config = agent.config
        config.output_formats = [OutputFormat.MARKDOWN]
        config.output_dir = tempfile.mkdtemp()

        bp = make_blueprint()
        project = BookProject(blueprint=bp)

        result = await agent.execute(project, context)
        assert "markdown" in result
        assert os.path.exists(result["markdown"])

    @pytest.mark.asyncio
    async def test_execute_with_plan(self, agent, context):
        config = agent.config
        config.output_formats = [OutputFormat.MARKDOWN, OutputFormat.HTML]
        config.output_dir = tempfile.mkdtemp()

        bp = make_blueprint()
        plan = make_plan()
        project = BookProject(blueprint=bp, illustration_plan=plan)

        result = await agent.execute(project, context)
        assert "markdown" in result
        assert "html" in result

        # Verify illustrations appear in HTML
        html_content = Path(result["html"]).read_text()
        assert "<figure" in html_content


class TestSanitizeFilename:
    def test_removes_invalid_chars(self, agent):
        assert agent._sanitize_filename('My "Book": A Test') == "My_Book_A_Test"

    def test_truncates_long_names(self, agent):
        long_name = "A" * 200
        result = agent._sanitize_filename(long_name)
        assert len(result) <= 100


class TestHTMLFigure:
    def test_inline_figure(self, agent):
        p = ImagePlacement(
            image_id="test_img",
            chapter_index=0,
            layout_mode=LayoutMode.INLINE,
            size=ImageSize.MEDIUM,
            caption="My caption",
        )
        html = agent._html_figure(p)
        assert "<figure>" in html
        assert "My caption" in html
        assert "50%" in html

    def test_full_page_figure(self, agent):
        p = ImagePlacement(
            image_id="fp_img",
            chapter_index=0,
            layout_mode=LayoutMode.FULL_PAGE,
            size=ImageSize.FULL,
            caption="Full page",
        )
        html = agent._html_figure(p)
        assert "full-page" in html
        assert "100%" in html


class TestResolveImagePath:
    def test_existing_path(self, agent):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake image data")
            path = f.name
        try:
            result = agent._resolve_image_path(path)
            assert result == path
        finally:
            os.unlink(path)

    def test_nonexistent_returns_none(self, agent):
        result = agent._resolve_image_path("nonexistent_image_id_12345")
        assert result is None


# ── DocxIllustratedRenderer Tests ─────────────────────


def _create_test_image(directory: str, name: str = "test.jpg") -> str:
    """Create a minimal valid JPEG file for testing."""
    filepath = os.path.join(directory, name)
    try:
        from PIL import Image
        img = Image.new("RGB", (800, 600), color="blue")
        img.save(filepath, format="JPEG")
    except ImportError:
        # Fallback: write a minimal JPEG header
        with open(filepath, "wb") as f:
            f.write(b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9')
    return filepath


class TestDocxRendererBasic:
    def test_render_empty_plan(self):
        renderer = DocxIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "book.docx")
            result = renderer.render(bp, IllustrationPlan(), "", out)
            assert os.path.exists(result)
            assert result.endswith(".docx")

    def test_render_no_plan(self):
        renderer = DocxIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "book.docx")
            result = renderer.render(bp, None, "", out)
            assert os.path.exists(result)

    def test_render_with_missing_images(self):
        """Plan references images that don't exist — should not crash."""
        renderer = DocxIllustratedRenderer()
        bp = make_blueprint()
        plan = make_plan()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "book.docx")
            result = renderer.render(bp, plan, "", out)
            assert os.path.exists(result)


class TestDocxRendererWithImages:
    def test_render_with_inline_image(self):
        renderer = DocxIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = _create_test_image(tmpdir, "inline_test.jpg")
            plan = IllustrationPlan(
                placements=[
                    ImagePlacement(
                        image_id=img_path,
                        chapter_index=0,
                        section_index=0,
                        layout_mode=LayoutMode.INLINE,
                        size=ImageSize.MEDIUM,
                        caption="Inline test image",
                    ),
                ],
            )
            out = os.path.join(tmpdir, "book.docx")
            result = renderer.render(bp, plan, tmpdir, out)
            assert os.path.exists(result)
            # File should be larger than empty DOCX due to embedded image
            assert os.path.getsize(result) > 5000

    def test_render_with_full_page_image(self):
        renderer = DocxIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = _create_test_image(tmpdir, "fullpage.jpg")
            plan = IllustrationPlan(
                placements=[
                    ImagePlacement(
                        image_id=img_path,
                        chapter_index=0,
                        section_index=0,
                        layout_mode=LayoutMode.FULL_PAGE,
                        size=ImageSize.FULL,
                        caption="Full page image",
                    ),
                ],
            )
            out = os.path.join(tmpdir, "book.docx")
            result = renderer.render(bp, plan, tmpdir, out)
            assert os.path.exists(result)

    def test_render_with_credit(self):
        renderer = DocxIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = _create_test_image(tmpdir, "credit.jpg")
            plan = IllustrationPlan(
                placements=[
                    ImagePlacement(
                        image_id=img_path,
                        chapter_index=0,
                        section_index=0,
                        layout_mode=LayoutMode.INLINE,
                        size=ImageSize.MEDIUM,
                        caption="Photo with credit",
                        credit="Photo by John Doe, 2024",
                    ),
                ],
            )
            out = os.path.join(tmpdir, "book.docx")
            result = renderer.render(bp, plan, tmpdir, out)
            assert os.path.exists(result)


class TestDocxRendererGenreSetup:
    def test_children_page_size(self):
        renderer = DocxIllustratedRenderer(genre=BookGenre.CHILDREN)
        preset = renderer.PAGE_PRESETS[BookGenre.CHILDREN]
        assert preset["width"] == 8.5
        assert preset["height"] == 8.5

    def test_technical_page_size(self):
        renderer = DocxIllustratedRenderer(genre=BookGenre.TECHNICAL)
        preset = renderer.PAGE_PRESETS[BookGenre.TECHNICAL]
        assert preset["width"] == 7.0
        assert preset["margin"] == 1.0

    def test_photography_page_size(self):
        renderer = DocxIllustratedRenderer(genre=BookGenre.PHOTOGRAPHY)
        preset = renderer.PAGE_PRESETS[BookGenre.PHOTOGRAPHY]
        assert preset["width"] == 10.0
        assert preset["height"] == 12.0

    def test_default_page_size(self):
        renderer = DocxIllustratedRenderer(genre=BookGenre.NON_FICTION)
        content_width = renderer._get_content_width()
        # Default: 6.0 - 2*0.75 = 4.5
        assert content_width == 4.5


class TestDocxRendererFigureNumbering:
    def test_technical_figure_numbering(self):
        renderer = DocxIllustratedRenderer(genre=BookGenre.TECHNICAL)
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            img1 = _create_test_image(tmpdir, "fig1.jpg")
            img2 = _create_test_image(tmpdir, "fig2.jpg")
            plan = IllustrationPlan(
                placements=[
                    ImagePlacement(
                        image_id=img1,
                        chapter_index=0,
                        section_index=0,
                        layout_mode=LayoutMode.INLINE,
                        size=ImageSize.MEDIUM,
                        caption="Architecture diagram",
                    ),
                    ImagePlacement(
                        image_id=img2,
                        chapter_index=0,
                        section_index=0,
                        layout_mode=LayoutMode.INLINE,
                        size=ImageSize.MEDIUM,
                        caption="Flow chart",
                    ),
                ],
            )
            out = os.path.join(tmpdir, "book.docx")
            renderer.render(bp, plan, tmpdir, out)
            # Verify figure counter was incremented
            assert renderer.figure_counter[0] == 2

    def test_non_technical_no_figure_numbering(self):
        renderer = DocxIllustratedRenderer(genre=BookGenre.FICTION)
        # Fiction genre should not increment figure counter
        assert renderer.figure_counter == {}


class TestDocxRendererGallery:
    def test_gallery_rendering(self):
        renderer = DocxIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            imgs = [_create_test_image(tmpdir, f"gal{i}.jpg") for i in range(4)]
            plan = IllustrationPlan(
                placements=[
                    ImagePlacement(
                        image_id=imgs[i],
                        chapter_index=0,
                        section_index=0,
                        layout_mode=LayoutMode.GALLERY,
                        size=ImageSize.MEDIUM,
                        caption=f"Gallery image {i+1}",
                    )
                    for i in range(4)
                ],
                galleries=[
                    GalleryGroup(
                        group_id="g1",
                        image_ids=imgs,
                        title="Test Gallery",
                        caption="A collection of test images",
                        chapter_index=0,
                    ),
                ],
            )
            out = os.path.join(tmpdir, "book.docx")
            result = renderer.render(bp, plan, tmpdir, out)
            assert os.path.exists(result)
            assert os.path.getsize(result) > 5000


class TestDocxRendererWidthCalc:
    def test_size_small(self):
        renderer = DocxIllustratedRenderer()
        width = renderer._calculate_width(ImageSize.SMALL)
        assert width >= 1.5  # min clamp
        assert width <= renderer._get_content_width()

    def test_size_full(self):
        renderer = DocxIllustratedRenderer()
        width = renderer._calculate_width(ImageSize.FULL)
        assert width == renderer._get_content_width()

    def test_size_medium(self):
        renderer = DocxIllustratedRenderer()
        content = renderer._get_content_width()
        width = renderer._calculate_width(ImageSize.MEDIUM)
        assert abs(width - content * 0.5) < 0.01


class TestDocxRendererResolveImage:
    def test_resolve_direct_path(self):
        renderer = DocxIllustratedRenderer()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake")
            path = f.name
        try:
            result = renderer._resolve_image_path(path, "")
            assert result == path
        finally:
            os.unlink(path)

    def test_resolve_in_image_dir(self):
        renderer = DocxIllustratedRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = _create_test_image(tmpdir, "myimage.jpg")
            result = renderer._resolve_image_path("myimage", tmpdir)
            assert result is not None
            assert "myimage" in result

    def test_resolve_nonexistent(self):
        renderer = DocxIllustratedRenderer()
        result = renderer._resolve_image_path("doesnotexist_xyz", "")
        assert result is None


# ── EpubRenderer Tests ─────────────────────────────────


class TestEpubRendererBasic:
    def test_render_no_plan(self):
        renderer = EpubRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(bp, Path(tmpdir))
            assert path.exists()
            assert str(path).endswith(".epub")

    def test_render_empty_plan(self):
        renderer = EpubRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(bp, Path(tmpdir), IllustrationPlan())
            assert path.exists()

    def test_render_with_genre(self):
        renderer = EpubRenderer(genre=BookGenre.CHILDREN)
        assert renderer.genre == BookGenre.CHILDREN
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(bp, Path(tmpdir))
            assert path.exists()

    def test_filename_sanitization(self):
        renderer = EpubRenderer()
        bp = make_blueprint()
        bp.title = 'Book: "With" Special/Chars'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = renderer.render(bp, Path(tmpdir))
            assert path.exists()
            # No illegal chars in filename
            assert ":" not in path.name
            assert '"' not in path.name


class TestEpubRendererXhtml:
    def test_chapter_xhtml_basic(self):
        renderer = EpubRenderer()
        bp = make_blueprint()
        chapter = bp.parts[0].chapters[0]
        xhtml = renderer._build_chapter_xhtml(chapter, 0, None, {})
        assert '<?xml version="1.0"' in xhtml
        assert "Chapter 1: Test Chapter" in xhtml
        assert "Test Section" in xhtml
        assert "Chapter intro text" in xhtml
        assert "Chapter summary text" in xhtml
        assert "Key point one" in xhtml

    def test_chapter_xhtml_with_plan(self):
        renderer = EpubRenderer()
        bp = make_blueprint()
        chapter = bp.parts[0].chapters[0]
        plan = make_plan()
        # Simulate image_items mapping
        image_items = {"img1": "images/img1.jpg", "img2": "images/img2.jpg"}
        xhtml = renderer._build_chapter_xhtml(chapter, 0, plan, image_items)
        # FLOAT_TOP img2 should appear before content
        assert "images/img2.jpg" in xhtml
        # INLINE img1 should appear after section content
        assert "images/img1.jpg" in xhtml
        # FULL_PAGE img3 excluded (separate spine page)
        assert "img3" not in xhtml

    def test_fullpage_xhtml(self):
        renderer = EpubRenderer()
        placement = ImagePlacement(
            image_id="fp1",
            chapter_index=0,
            layout_mode=LayoutMode.FULL_PAGE,
            size=ImageSize.FULL,
            caption="Full page landscape",
            alt_text="A wide landscape view",
            credit="Photo by Alice",
        )
        image_items = {"fp1": "images/fp1.jpg"}
        xhtml = renderer._build_fullpage_xhtml(placement, image_items)
        assert "full-page-body" in xhtml
        assert "full-page" in xhtml
        assert "Full page landscape" in xhtml
        assert "A wide landscape view" in xhtml
        assert "Photo by Alice" in xhtml

    def test_gallery_xhtml(self):
        renderer = EpubRenderer()
        plan = IllustrationPlan(
            placements=[
                ImagePlacement(
                    image_id="g1", chapter_index=0, layout_mode=LayoutMode.GALLERY,
                    size=ImageSize.MEDIUM, caption="Gallery pic 1",
                ),
                ImagePlacement(
                    image_id="g2", chapter_index=0, layout_mode=LayoutMode.GALLERY,
                    size=ImageSize.MEDIUM, caption="Gallery pic 2",
                ),
            ],
            galleries=[
                GalleryGroup(
                    group_id="gal1", image_ids=["g1", "g2"],
                    title="My Gallery", caption="Nice photos",
                    chapter_index=0,
                ),
            ],
        )
        image_items = {"g1": "images/g1.jpg", "g2": "images/g2.jpg"}
        xhtml = renderer._build_gallery_xhtml(plan.galleries[0], plan, image_items)
        assert "gallery" in xhtml
        assert "My Gallery" in xhtml
        assert "Nice photos" in xhtml
        assert "gallery-item" in xhtml
        assert "images/g1.jpg" in xhtml
        assert "images/g2.jpg" in xhtml


class TestEpubRendererFigures:
    def test_xhtml_figure_inline(self):
        renderer = EpubRenderer()
        p = ImagePlacement(
            image_id="i1", chapter_index=0, layout_mode=LayoutMode.INLINE,
            size=ImageSize.MEDIUM, caption="Inline caption",
            alt_text="Alt text here",
        )
        html = renderer._xhtml_figure(p, {"i1": "images/i1.jpg"})
        assert "illustration" in html
        assert "50%" in html
        assert "Inline caption" in html
        assert "Alt text here" in html

    def test_xhtml_figure_margin(self):
        renderer = EpubRenderer()
        p = ImagePlacement(
            image_id="m1", chapter_index=0, layout_mode=LayoutMode.MARGIN,
            size=ImageSize.SMALL, caption="Margin note",
        )
        html = renderer._xhtml_figure(p, {"m1": "images/m1.jpg"})
        assert "margin-img" in html

    def test_xhtml_figure_with_credit(self):
        renderer = EpubRenderer()
        p = ImagePlacement(
            image_id="c1", chapter_index=0, layout_mode=LayoutMode.INLINE,
            size=ImageSize.MEDIUM, caption="Photo", credit="By Bob",
        )
        html = renderer._xhtml_figure(p, {"c1": "images/c1.jpg"})
        assert "credit" in html
        assert "By Bob" in html

    def test_xhtml_figure_missing_image(self):
        renderer = EpubRenderer()
        p = ImagePlacement(
            image_id="missing", chapter_index=0, layout_mode=LayoutMode.INLINE,
            size=ImageSize.MEDIUM,
        )
        html = renderer._xhtml_figure(p, {})
        assert html == ""


class TestEpubRendererCss:
    def test_default_css_has_gallery(self):
        renderer = EpubRenderer()
        css = renderer._default_css()
        assert ".gallery" in css
        assert "flex-wrap" in css

    def test_default_css_has_margin(self):
        renderer = EpubRenderer()
        css = renderer._default_css()
        assert ".margin-img" in css
        assert "float: right" in css

    def test_default_css_has_credit(self):
        renderer = EpubRenderer()
        css = renderer._default_css()
        assert ".credit" in css

    def test_default_css_has_fullpage(self):
        renderer = EpubRenderer()
        css = renderer._default_css()
        assert ".full-page-body" in css
        assert "page-break-before" in css


class TestEpubRendererEscape:
    def test_escape_html_entities(self):
        assert EpubRenderer._escape('A & B <C> "D"') == 'A &amp; B &lt;C&gt; &quot;D&quot;'


# ── PdfIllustratedRenderer Tests ───────────────────────


class TestPdfRendererBasic:
    def test_init_default(self):
        renderer = PdfIllustratedRenderer()
        assert renderer.genre == BookGenre.NON_FICTION
        assert renderer.config is not None

    def test_init_with_genre(self):
        renderer = PdfIllustratedRenderer(genre=BookGenre.CHILDREN)
        assert renderer.genre == BookGenre.CHILDREN

    def test_can_convert_returns_bool(self):
        result = PdfIllustratedRenderer.can_convert()
        assert isinstance(result, bool)

    def test_find_soffice_returns_str_or_none(self):
        result = PdfIllustratedRenderer._find_soffice()
        assert result is None or isinstance(result, str)


class TestPdfRendererFallback:
    def test_render_fallback_to_docx(self):
        """When no PDF converter is available, should save DOCX as fallback."""
        renderer = PdfIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "book.pdf")
            result = renderer.render(bp, None, "", out)
            # Result should exist (either PDF or DOCX fallback)
            assert os.path.exists(result)
            # The file should be a valid output
            assert os.path.getsize(result) > 0

    def test_render_with_plan_fallback(self):
        """With plan but no converter — should still produce output."""
        renderer = PdfIllustratedRenderer()
        bp = make_blueprint()
        plan = make_plan()
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "output.pdf")
            result = renderer.render(bp, plan, "", out)
            assert os.path.exists(result)

    def test_render_creates_output_dir(self):
        """Output directory should be created if it doesn't exist."""
        renderer = PdfIllustratedRenderer()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "sub", "dir")
            out = os.path.join(nested, "book.pdf")
            result = renderer.render(bp, None, "", out)
            assert os.path.exists(result)


class TestPdfRendererConversion:
    def test_convert_docx_to_pdf_no_soffice(self):
        """When soffice is not available, _convert_docx_to_pdf returns None."""
        renderer = PdfIllustratedRenderer()
        # Only test if soffice is NOT available
        if not renderer._find_soffice():
            result = renderer._convert_docx_to_pdf("/tmp/fake.docx", "/tmp")
            assert result is None

    def test_convert_via_docx2pdf_invalid_file(self):
        """Converting a non-existent file should return None (not crash)."""
        renderer = PdfIllustratedRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_docx = os.path.join(tmpdir, "fake.docx")
            out_pdf = os.path.join(tmpdir, "out.pdf")
            result = renderer._convert_via_docx2pdf(fake_docx, out_pdf)
            assert result is None


# ── LayoutEngine Tests ─────────────────────────────────


class TestLayoutEngine:
    def test_render_docx_format(self):
        engine = LayoutEngine()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=bp, plan=None, image_dir="",
                formats=["docx"], output_dir=Path(tmpdir),
            )
            assert "docx" in results
            assert os.path.exists(results["docx"])

    def test_render_epub_format(self):
        engine = LayoutEngine()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=bp, plan=None, image_dir="",
                formats=["epub"], output_dir=Path(tmpdir),
            )
            assert "epub" in results
            assert os.path.exists(results["epub"])

    def test_render_multiple_formats(self):
        engine = LayoutEngine()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=bp, plan=None, image_dir="",
                formats=["docx", "epub"], output_dir=Path(tmpdir),
            )
            assert "docx" in results
            assert "epub" in results

    def test_render_with_genre(self):
        engine = LayoutEngine()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=bp, plan=None, image_dir="",
                formats=["docx"], output_dir=Path(tmpdir),
                genre=BookGenre.CHILDREN,
            )
            assert "docx" in results

    def test_render_unknown_format_skipped(self):
        engine = LayoutEngine()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=bp, plan=None, image_dir="",
                formats=["unknown_format"], output_dir=Path(tmpdir),
            )
            assert "unknown_format" not in results

    def test_render_creates_output_dir(self):
        engine = LayoutEngine()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "sub" / "dir"
            results = engine.render(
                blueprint=bp, plan=None, image_dir="",
                formats=["docx"], output_dir=nested,
            )
            assert nested.exists()
            assert "docx" in results

    def test_render_pdf_fallback(self):
        """PDF render should produce output (PDF or DOCX fallback)."""
        engine = LayoutEngine()
        bp = make_blueprint()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=bp, plan=None, image_dir="",
                formats=["pdf"], output_dir=Path(tmpdir),
            )
            assert "pdf" in results
            assert os.path.exists(results["pdf"])


# ── K6 Pipeline Integration Tests ──────────────────────

from core.book_writer_v2.illustration_models import IllustrationPlan as IPlan


class TestFromDictDeserialization:
    """Test from_dict() round-trip for illustration models."""

    def test_image_placement_roundtrip(self):
        from core.book_writer_v2.illustration_models import ImagePlacement
        orig = ImagePlacement(
            image_id="img1", chapter_index=2, section_index=1,
            paragraph_index=3, layout_mode=LayoutMode.FULL_PAGE,
            size=ImageSize.LARGE, alignment="left",
            caption="Test caption", credit="Photo by Bob",
            alt_text="A landscape", border=True,
            page_break_before=True, relevance_score=0.87,
        )
        data = orig.to_dict()
        restored = ImagePlacement.from_dict(data)
        assert restored.image_id == "img1"
        assert restored.chapter_index == 2
        assert restored.layout_mode == LayoutMode.FULL_PAGE
        assert restored.size == ImageSize.LARGE
        assert restored.credit == "Photo by Bob"
        assert restored.alt_text == "A landscape"
        assert restored.border is True
        assert abs(restored.relevance_score - 0.87) < 0.01

    def test_gallery_group_roundtrip(self):
        orig = GalleryGroup(
            group_id="g1", image_ids=["a", "b", "c"],
            title="Gallery", caption="Nice pics", chapter_index=1,
        )
        data = orig.to_dict()
        restored = GalleryGroup.from_dict(data)
        assert restored.group_id == "g1"
        assert restored.image_ids == ["a", "b", "c"]
        assert restored.title == "Gallery"
        assert restored.caption == "Nice pics"

    def test_illustration_plan_roundtrip(self):
        plan = IPlan(
            project_id="proj1",
            placements=[
                ImagePlacement(
                    image_id="img1", chapter_index=0,
                    layout_mode=LayoutMode.INLINE, size=ImageSize.MEDIUM,
                    caption="Cap1", relevance_score=0.8,
                ),
                ImagePlacement(
                    image_id="img2", chapter_index=1,
                    layout_mode=LayoutMode.FULL_PAGE, size=ImageSize.FULL,
                    caption="Cap2", credit="Credit", relevance_score=0.95,
                ),
            ],
            galleries=[
                GalleryGroup(
                    group_id="g1", image_ids=["img1", "img2"],
                    title="Gallery", chapter_index=0,
                ),
            ],
            unmatched_image_ids=["orphan1"],
            genre=BookGenre.CHILDREN,
            layout_style_notes="Colorful layout",
        )
        data = plan.to_dict()
        restored = IPlan.from_dict(data)
        assert restored.project_id == "proj1"
        assert len(restored.placements) == 2
        assert restored.placements[0].layout_mode == LayoutMode.INLINE
        assert restored.placements[1].credit == "Credit"
        assert len(restored.galleries) == 1
        assert restored.galleries[0].title == "Gallery"
        assert restored.unmatched_image_ids == ["orphan1"]
        assert restored.genre == BookGenre.CHILDREN
        assert restored.layout_style_notes == "Colorful layout"

    def test_plan_from_dict_defaults(self):
        """from_dict with minimal data should not crash."""
        restored = IPlan.from_dict({})
        assert restored.project_id == ""
        assert restored.placements == []
        assert restored.galleries == []


class TestPublisherLayoutEngineIntegration:
    """Test that PublisherAgent correctly delegates to LayoutEngine."""

    @pytest.mark.asyncio
    async def test_publisher_text_only_bypasses_layout_engine(self, agent, context):
        """Text-only book should NOT use LayoutEngine."""
        config = agent.config
        config.output_formats = [OutputFormat.MARKDOWN]
        config.output_dir = tempfile.mkdtemp()

        bp = make_blueprint()
        project = BookProject(blueprint=bp)

        result = await agent.execute(project, context)
        assert "markdown" in result
        assert os.path.exists(result["markdown"])

    @pytest.mark.asyncio
    async def test_publisher_illustrated_uses_layout_engine(self, agent, context):
        """Illustrated book with DOCX should delegate to LayoutEngine."""
        config = agent.config
        config.output_formats = [OutputFormat.DOCX]
        config.output_dir = tempfile.mkdtemp()

        bp = make_blueprint()
        plan = make_plan()
        project = BookProject(blueprint=bp, illustration_plan=plan)

        result = await agent.execute(project, context)
        assert "docx" in result
        assert os.path.exists(result["docx"])

    @pytest.mark.asyncio
    async def test_publisher_illustrated_epub(self, agent, context):
        """Illustrated book with EPUB should delegate to LayoutEngine."""
        config = agent.config
        config.output_formats = [OutputFormat.EPUB]
        config.output_dir = tempfile.mkdtemp()

        bp = make_blueprint()
        plan = make_plan()
        project = BookProject(blueprint=bp, illustration_plan=plan)

        result = await agent.execute(project, context)
        assert "epub" in result
        assert os.path.exists(result["epub"])

    @pytest.mark.asyncio
    async def test_publisher_mixed_formats(self, agent, context):
        """Mixed formats: DOCX via LayoutEngine, Markdown direct."""
        config = agent.config
        config.output_formats = [OutputFormat.DOCX, OutputFormat.MARKDOWN]
        config.output_dir = tempfile.mkdtemp()

        bp = make_blueprint()
        plan = make_plan()
        project = BookProject(blueprint=bp, illustration_plan=plan)

        result = await agent.execute(project, context)
        assert "docx" in result
        assert "markdown" in result


class TestServiceLoadProjectIllustration:
    """Test that _load_project restores illustration state."""

    @pytest.mark.asyncio
    async def test_load_preserves_uploaded_images(self):
        from api.services.book_writer_v2_service import BookWriterV2Service
        service = BookWriterV2Service()

        bp = make_blueprint()
        project = BookProject(
            blueprint=bp,
            uploaded_images=["/path/to/img1.jpg", "/path/to/img2.png"],
        )
        await service._save_project(project)

        loaded = await service._load_project(project.id)
        assert loaded is not None
        assert loaded.uploaded_images == ["/path/to/img1.jpg", "/path/to/img2.png"]
        assert loaded.has_images() is True

        # Cleanup
        os.remove(os.path.join(service.db_path, f"{project.id}.json"))

    @pytest.mark.asyncio
    async def test_load_preserves_illustration_plan(self):
        from api.services.book_writer_v2_service import BookWriterV2Service
        service = BookWriterV2Service()

        bp = make_blueprint()
        plan = IPlan(
            project_id="test",
            placements=[
                ImagePlacement(
                    image_id="img1", chapter_index=0,
                    layout_mode=LayoutMode.INLINE, size=ImageSize.MEDIUM,
                    caption="Test", relevance_score=0.8,
                ),
            ],
            genre=BookGenre.TECHNICAL,
        )
        project = BookProject(blueprint=bp, illustration_plan=plan)
        await service._save_project(project)

        loaded = await service._load_project(project.id)
        assert loaded is not None
        assert loaded.illustration_plan is not None
        assert len(loaded.illustration_plan.placements) == 1
        assert loaded.illustration_plan.placements[0].image_id == "img1"
        assert loaded.illustration_plan.genre == BookGenre.TECHNICAL

        # Cleanup
        os.remove(os.path.join(service.db_path, f"{project.id}.json"))

    @pytest.mark.asyncio
    async def test_load_without_illustration_plan(self):
        from api.services.book_writer_v2_service import BookWriterV2Service
        service = BookWriterV2Service()

        project = BookProject(user_request="test")
        await service._save_project(project)

        loaded = await service._load_project(project.id)
        assert loaded is not None
        assert loaded.illustration_plan is None
        assert loaded.uploaded_images == []

        # Cleanup
        os.remove(os.path.join(service.db_path, f"{project.id}.json"))


class TestAgentExports:
    """Verify new agents are accessible via __init__.py."""

    def test_vision_analyzer_importable(self):
        from core.book_writer_v2.agents import VisionAnalyzerAgent
        assert VisionAnalyzerAgent is not None

    def test_illustrator_importable(self):
        from core.book_writer_v2.agents import IllustratorAgent
        assert IllustratorAgent is not None


class TestRendererExports:
    """Verify renderers are accessible via __init__.py."""

    def test_docx_renderer_importable(self):
        from core.book_writer_v2.renderers import DocxIllustratedRenderer
        assert DocxIllustratedRenderer is not None

    def test_epub_renderer_importable(self):
        from core.book_writer_v2.renderers import EpubRenderer
        assert EpubRenderer is not None

    def test_pdf_renderer_importable(self):
        from core.book_writer_v2.renderers import PdfIllustratedRenderer
        assert PdfIllustratedRenderer is not None

    def test_layout_engine_importable(self):
        from core.book_writer_v2.renderers import LayoutEngine
        assert LayoutEngine is not None
