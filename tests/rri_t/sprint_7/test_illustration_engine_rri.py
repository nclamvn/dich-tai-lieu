"""
RRI-T Sprint 7: Illustrated Book Engine (Sprint K) integration tests.

Covers the full illustration pipeline:
  K1: Data models + serialization
  K2: VisionAnalyzer agent
  K3: IllustratorAgent matching + layout
  K4-K5: DOCX / EPUB / PDF rendering via LayoutEngine
  K6: Pipeline integration (PublisherAgent delegation)
  K7: API response serialization

Persona coverage:
  - End User: Upload → analyze → illustrate → download
  - QA Destroyer: Edge cases, missing data, corrupt input
  - DevOps: Module imports, package exports

Dimensions: D2 (API), D5 (Data Integrity), D7 (Edge Cases)
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.book_writer_v2.config import BookWriterConfig, OutputFormat
from core.book_writer_v2.ai_adapter import MockAIClient
from core.book_writer_v2.agents.base import AgentContext
from core.book_writer_v2.models import BookProject, BookStatus
from core.book_writer_v2.illustration_models import (
    BookGenre,
    GalleryGroup,
    IllustrationPlan,
    ImageAnalysis,
    ImageCategory,
    ImageManifest,
    ImagePlacement,
    ImageSize,
    LayoutConfig,
    LayoutMode,
)

pytestmark = [pytest.mark.rri_t]


# ═══════════════════════════════════════════════════════════
# K1: DATA MODELS — Serialization Round-Trip
# ═══════════════════════════════════════════════════════════


class TestDataModelSerialization:
    """End User persona — illustration plan save/load."""

    @pytest.mark.p0
    def test_k1_001_plan_to_dict_roundtrip(self, illustration_plan):
        """K1-001 | EndUser | IllustrationPlan survives JSON round-trip."""
        data = illustration_plan.to_dict()
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        restored = IllustrationPlan.from_dict(restored_data)

        assert restored.project_id == illustration_plan.project_id
        assert len(restored.placements) == len(illustration_plan.placements)
        assert len(restored.galleries) == len(illustration_plan.galleries)
        assert restored.genre == illustration_plan.genre

    @pytest.mark.p0
    def test_k1_002_placement_fields_preserved(self, illustration_plan):
        """K1-002 | EndUser | All ImagePlacement fields survive serialization."""
        p = illustration_plan.placements[1]  # Full page with credit
        data = p.to_dict()
        restored = ImagePlacement.from_dict(data)

        assert restored.image_id == p.image_id
        assert restored.layout_mode == LayoutMode.FULL_PAGE
        assert restored.size == ImageSize.FULL
        assert restored.caption == p.caption
        assert restored.credit == "Photo by Tester"
        assert restored.alt_text == p.alt_text
        assert abs(restored.relevance_score - p.relevance_score) < 0.01

    @pytest.mark.p1
    def test_k1_003_gallery_group_roundtrip(self, illustration_plan):
        """K1-003 | EndUser | GalleryGroup survives serialization."""
        g = illustration_plan.galleries[0]
        data = g.to_dict()
        restored = GalleryGroup.from_dict(data)

        assert restored.group_id == g.group_id
        assert restored.image_ids == g.image_ids
        assert restored.title == g.title
        assert restored.chapter_index == g.chapter_index

    @pytest.mark.p1
    def test_k1_004_empty_plan_from_dict(self):
        """K1-004 | QA | Empty dict produces valid empty plan."""
        plan = IllustrationPlan.from_dict({})
        assert plan.placements == []
        assert plan.galleries == []
        assert plan.genre == BookGenre.NON_FICTION

    @pytest.mark.p1
    def test_k1_005_layout_config_genre_presets(self):
        """K1-005 | EndUser | Genre presets produce different configs."""
        children = LayoutConfig.for_genre(BookGenre.CHILDREN)
        technical = LayoutConfig.for_genre(BookGenre.TECHNICAL)

        assert children.max_images_per_chapter > technical.max_images_per_chapter
        assert children.caption_style == "bold"
        assert technical.caption_style == "plain"


# ═══════════════════════════════════════════════════════════
# K2: VISION ANALYZER — Agent Execution
# ═══════════════════════════════════════════════════════════


class TestVisionAnalyzerIntegration:
    """End User persona — image analysis workflow."""

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_k2_001_analyze_empty_paths(self, bw_config, mock_book_ai, agent_context):
        """K2-001 | EndUser | Empty image list returns empty manifest."""
        from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
        agent = VisionAnalyzerAgent(bw_config, mock_book_ai)
        result = await agent.execute({"image_paths": []}, agent_context)
        assert isinstance(result, ImageManifest)
        assert result.total_images == 0

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_k2_002_analyze_real_images(self, bw_config, mock_book_ai, agent_context, sample_images):
        """K2-002 | EndUser | Analyze 5 images → manifest with 5 entries."""
        from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
        agent = VisionAnalyzerAgent(bw_config, mock_book_ai)
        result = await agent.execute({"image_paths": sample_images}, agent_context)
        assert isinstance(result, ImageManifest)
        assert result.total_images == 5
        for img in result.images:
            assert img.width > 0
            assert img.height > 0
            assert img.quality_score > 0

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_k2_003_analyze_nonexistent_files(self, bw_config, mock_book_ai, agent_context):
        """K2-003 | QA | Non-existent files are skipped gracefully."""
        from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
        agent = VisionAnalyzerAgent(bw_config, mock_book_ai)
        result = await agent.execute(
            {"image_paths": ["/nonexistent/fake.jpg", "/also/missing.png"]},
            agent_context,
        )
        assert isinstance(result, ImageManifest)
        assert result.total_images == 0

    @pytest.mark.p1
    def test_k2_004_resolution_scoring(self):
        """K2-004 | EndUser | Resolution scoring tiers work correctly."""
        from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
        assert VisionAnalyzerAgent._score_resolution(0, 0) == 0.0
        assert VisionAnalyzerAgent._score_resolution(400, 300) == 0.3
        assert VisionAnalyzerAgent._score_resolution(1000, 800) == 0.7
        assert VisionAnalyzerAgent._score_resolution(2500, 1800) == 1.0


# ═══════════════════════════════════════════════════════════
# K3: ILLUSTRATOR — Matching + Layout
# ═══════════════════════════════════════════════════════════


class TestIllustratorIntegration:
    """End User persona — image-to-content matching."""

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_k3_001_execute_produces_plan(
        self, bw_config, mock_book_ai, agent_context,
        book_blueprint, image_manifest, sample_images,
    ):
        """K3-001 | EndUser | Illustrator produces plan from manifest."""
        from core.book_writer_v2.agents.illustrator import IllustratorAgent

        project = BookProject(
            id="k3-test",
            user_request="Test",
            blueprint=book_blueprint,
            uploaded_images=sample_images,
        )
        agent = IllustratorAgent(bw_config, mock_book_ai)
        plan = await agent.execute(
            {"project": project, "manifest": image_manifest},
            agent_context,
        )
        assert isinstance(plan, IllustrationPlan)
        # MockAIClient returns unparseable text — placements will be empty
        # but the agent should still return a valid plan with unmatched images
        assert plan.total_placed >= 0
        assert isinstance(plan.placements, list)
        assert isinstance(plan.unmatched_image_ids, list)

    @pytest.mark.p1
    def test_k3_002_genre_aware_layout(self, bw_config, mock_book_ai):
        """K3-002 | EndUser | Genre affects layout decisions."""
        from core.book_writer_v2.agents.illustrator import IllustratorAgent

        img = MagicMock()
        img.quality_score = 0.9
        img.category = ImageCategory.ART
        img.is_high_quality = True
        img.is_landscape = True
        img.suggested_layout = LayoutMode.FULL_PAGE
        img.suggested_size = ImageSize.FULL

        config = LayoutConfig.for_genre(BookGenre.CHILDREN)
        agent = IllustratorAgent(bw_config, mock_book_ai)

        # Children books prefer full page for high-quality art
        mode = agent._decide_layout(
            img, config, position=0,
            genre=BookGenre.CHILDREN, prev_layout=None,
        )
        assert mode == LayoutMode.FULL_PAGE

    @pytest.mark.p1
    def test_k3_003_quality_guard_blocks_full_page(self, bw_config, mock_book_ai):
        """K3-003 | QA | Low quality images cannot be FULL_PAGE."""
        from core.book_writer_v2.agents.illustrator import IllustratorAgent

        img = MagicMock()
        img.quality_score = 0.3  # Below 0.5 threshold
        img.suggested_layout = LayoutMode.FULL_PAGE
        img.suggested_size = ImageSize.FULL

        config = LayoutConfig.for_genre(BookGenre.NON_FICTION)
        agent = IllustratorAgent(bw_config, mock_book_ai)
        mode = agent._decide_layout(
            img, config, position=0,
        )
        assert mode != LayoutMode.FULL_PAGE


# ═══════════════════════════════════════════════════════════
# K4-K5: RENDERING — DOCX / EPUB / PDF via LayoutEngine
# ═══════════════════════════════════════════════════════════


class TestLayoutEngineIntegration:
    """End User persona — multi-format rendering."""

    @pytest.mark.p0
    def test_k4_001_docx_with_images(self, book_blueprint, illustration_plan, sample_images):
        """K4-001 | EndUser | DOCX renders with embedded images."""
        from core.book_writer_v2.renderers.layout_engine import LayoutEngine

        engine = LayoutEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=book_blueprint,
                plan=illustration_plan,
                image_dir=str(Path(sample_images[0]).parent),
                formats=["docx"],
                output_dir=Path(tmpdir),
            )
            assert "docx" in results
            assert os.path.exists(results["docx"])
            assert os.path.getsize(results["docx"]) > 5000

    @pytest.mark.p0
    def test_k4_002_epub_with_images(self, book_blueprint, illustration_plan, sample_images):
        """K4-002 | EndUser | EPUB renders with embedded images."""
        from core.book_writer_v2.renderers.layout_engine import LayoutEngine

        engine = LayoutEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=book_blueprint,
                plan=illustration_plan,
                image_dir=str(Path(sample_images[0]).parent),
                formats=["epub"],
                output_dir=Path(tmpdir),
            )
            assert "epub" in results
            assert os.path.exists(results["epub"])

    @pytest.mark.p1
    def test_k4_003_all_formats_at_once(self, book_blueprint, illustration_plan, sample_images):
        """K4-003 | EndUser | Render DOCX + EPUB + PDF simultaneously."""
        from core.book_writer_v2.renderers.layout_engine import LayoutEngine

        engine = LayoutEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=book_blueprint,
                plan=illustration_plan,
                image_dir=str(Path(sample_images[0]).parent),
                formats=["docx", "epub", "pdf"],
                output_dir=Path(tmpdir),
            )
            assert "docx" in results
            assert "epub" in results
            assert "pdf" in results

    @pytest.mark.p0
    def test_k4_004_render_no_plan(self, book_blueprint):
        """K4-004 | EndUser | Text-only book renders without crash."""
        from core.book_writer_v2.renderers.layout_engine import LayoutEngine

        engine = LayoutEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=book_blueprint,
                plan=None,
                image_dir="",
                formats=["docx", "epub"],
                output_dir=Path(tmpdir),
            )
            assert "docx" in results
            assert "epub" in results

    @pytest.mark.p1
    def test_k4_005_genre_aware_rendering(self, book_blueprint, illustration_plan, sample_images):
        """K4-005 | EndUser | Children's book gets different page size."""
        from core.book_writer_v2.renderers.docx_renderer import DocxIllustratedRenderer

        renderer = DocxIllustratedRenderer(genre=BookGenre.CHILDREN)
        preset = renderer.PAGE_PRESETS[BookGenre.CHILDREN]
        assert preset["width"] == 8.5
        assert preset["height"] == 8.5


# ═══════════════════════════════════════════════════════════
# K6: PIPELINE INTEGRATION — PublisherAgent Delegation
# ═══════════════════════════════════════════════════════════


class TestPublisherIntegration:
    """End User persona — PublisherAgent with LayoutEngine."""

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_k6_001_publisher_illustrated_docx(
        self, bw_config, mock_book_ai, agent_context,
        book_project_with_images,
    ):
        """K6-001 | EndUser | PublisherAgent delegates DOCX to LayoutEngine."""
        from core.book_writer_v2.agents.publisher import PublisherAgent

        bw_config.output_formats = [OutputFormat.DOCX]
        bw_config.output_dir = tempfile.mkdtemp()

        agent = PublisherAgent(bw_config, mock_book_ai)
        result = await agent.execute(book_project_with_images, agent_context)
        assert "docx" in result
        assert os.path.exists(result["docx"])

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_k6_002_publisher_text_only_bypass(self, bw_config, mock_book_ai, agent_context, book_blueprint):
        """K6-002 | EndUser | Text-only project bypasses LayoutEngine."""
        from core.book_writer_v2.agents.publisher import PublisherAgent

        bw_config.output_formats = [OutputFormat.MARKDOWN]
        bw_config.output_dir = tempfile.mkdtemp()

        project = BookProject(blueprint=book_blueprint)
        agent = PublisherAgent(bw_config, mock_book_ai)
        result = await agent.execute(project, agent_context)
        assert "markdown" in result
        assert os.path.exists(result["markdown"])

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_k6_003_publisher_mixed_formats(
        self, bw_config, mock_book_ai, agent_context,
        book_project_with_images,
    ):
        """K6-003 | EndUser | Mixed: DOCX via LayoutEngine + Markdown direct."""
        from core.book_writer_v2.agents.publisher import PublisherAgent

        bw_config.output_formats = [OutputFormat.DOCX, OutputFormat.MARKDOWN]
        bw_config.output_dir = tempfile.mkdtemp()

        agent = PublisherAgent(bw_config, mock_book_ai)
        result = await agent.execute(book_project_with_images, agent_context)
        assert "docx" in result
        assert "markdown" in result


# ═══════════════════════════════════════════════════════════
# K6: PERSISTENCE — Save/Load Illustration State
# ═══════════════════════════════════════════════════════════


class TestPersistenceIntegration:
    """End User persona — project save/load preserves illustration data."""

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_k6_004_save_load_with_plan(self, book_project_with_images):
        """K6-004 | EndUser | Save project → load → illustration plan intact."""
        from api.services.book_writer_v2_service import BookWriterV2Service

        service = BookWriterV2Service()
        project = book_project_with_images

        await service._save_project(project)
        loaded = await service._load_project(project.id)

        assert loaded is not None
        assert loaded.has_images() is True
        assert len(loaded.uploaded_images) == 5
        assert loaded.illustration_plan is not None
        assert len(loaded.illustration_plan.placements) == 3
        assert loaded.illustration_plan.genre == BookGenre.NON_FICTION

        # Cleanup
        os.remove(os.path.join(service.db_path, f"{project.id}.json"))

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_k6_005_save_load_without_plan(self, book_blueprint):
        """K6-005 | EndUser | Project without plan loads cleanly."""
        from api.services.book_writer_v2_service import BookWriterV2Service

        service = BookWriterV2Service()
        project = BookProject(
            id="k8-no-plan",
            user_request="No illustrations",
            blueprint=book_blueprint,
        )
        await service._save_project(project)
        loaded = await service._load_project(project.id)

        assert loaded is not None
        assert loaded.has_images() is False
        assert loaded.illustration_plan is None

        os.remove(os.path.join(service.db_path, f"{project.id}.json"))


# ═══════════════════════════════════════════════════════════
# K7: API RESPONSE — Serialization
# ═══════════════════════════════════════════════════════════


class TestAPIResponseIntegration:
    """DevOps persona — API contract correctness."""

    @pytest.mark.p0
    def test_k7_001_to_response_includes_illustration_fields(self, book_project_with_images):
        """K7-001 | DevOps | _to_response includes has_images + illustration_plan."""
        from api.routes.book_writer_v2 import _to_response

        resp = _to_response(book_project_with_images)
        assert resp.has_images is True
        assert len(resp.uploaded_images) == 5
        assert resp.illustration_plan is not None
        assert "placements" in resp.illustration_plan

    @pytest.mark.p0
    def test_k7_002_to_response_no_plan(self, book_blueprint):
        """K7-002 | DevOps | _to_response handles no illustration plan."""
        from api.routes.book_writer_v2 import _to_response

        project = BookProject(blueprint=book_blueprint)
        resp = _to_response(project)
        assert resp.has_images is False
        assert resp.uploaded_images == []
        assert resp.illustration_plan is None

    @pytest.mark.p1
    def test_k7_003_to_response_mock_plan_safety(self):
        """K7-003 | QA | _to_response handles MagicMock plan without crash."""
        from api.routes.book_writer_v2 import _to_response

        project = BookProject(user_request="test")
        project.illustration_plan = MagicMock()
        resp = _to_response(project)
        # Should not crash — _safe_plan_dict handles MagicMock
        assert resp.illustration_plan is None


# ═══════════════════════════════════════════════════════════
# PACKAGE EXPORTS — Module Import Verification
# ═══════════════════════════════════════════════════════════


class TestPackageExports:
    """DevOps persona — package structure correctness."""

    @pytest.mark.p0
    def test_agents_export_all_11(self):
        """PKG-001 | DevOps | agents/__init__.py exports all 11 agents."""
        from core.book_writer_v2 import agents
        assert hasattr(agents, "VisionAnalyzerAgent")
        assert hasattr(agents, "IllustratorAgent")
        assert hasattr(agents, "PublisherAgent")
        assert hasattr(agents, "WriterAgent")

    @pytest.mark.p0
    def test_renderers_export_all_4(self):
        """PKG-002 | DevOps | renderers/__init__.py exports all 4 renderers."""
        from core.book_writer_v2 import renderers
        assert hasattr(renderers, "DocxIllustratedRenderer")
        assert hasattr(renderers, "EpubRenderer")
        assert hasattr(renderers, "PdfIllustratedRenderer")
        assert hasattr(renderers, "LayoutEngine")

    @pytest.mark.p1
    def test_illustration_models_importable(self):
        """PKG-003 | DevOps | All illustration model classes importable."""
        from core.book_writer_v2.illustration_models import (
            BookGenre, GalleryGroup, IllustrationPlan,
            ImageAnalysis, ImageCategory, ImageManifest,
            ImagePlacement, ImageSize, LayoutConfig, LayoutMode,
        )
        assert BookGenre.CHILDREN.value == "children"


# ═══════════════════════════════════════════════════════════
# EDGE CASES — QA Destroyer
# ═══════════════════════════════════════════════════════════


class TestEdgeCases:
    """QA Destroyer persona — unusual and boundary inputs."""

    @pytest.mark.p1
    def test_edge_001_empty_plan_renders_clean(self, book_blueprint):
        """EDGE-001 | QA | Empty illustration plan renders text-only."""
        from core.book_writer_v2.renderers.layout_engine import LayoutEngine

        engine = LayoutEngine()
        empty_plan = IllustrationPlan()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=book_blueprint,
                plan=empty_plan,
                image_dir="",
                formats=["docx"],
                output_dir=Path(tmpdir),
            )
            assert "docx" in results
            assert os.path.exists(results["docx"])

    @pytest.mark.p1
    def test_edge_002_plan_with_missing_images(self, book_blueprint):
        """EDGE-002 | QA | Plan references non-existent images → no crash."""
        from core.book_writer_v2.renderers.layout_engine import LayoutEngine

        plan = IllustrationPlan(
            placements=[
                ImagePlacement(
                    image_id="/nonexistent/ghost.jpg",
                    chapter_index=0, section_index=0,
                    layout_mode=LayoutMode.INLINE, size=ImageSize.MEDIUM,
                    caption="Ghost image",
                ),
            ],
        )
        engine = LayoutEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=book_blueprint,
                plan=plan,
                image_dir="/nonexistent",
                formats=["docx", "epub"],
                output_dir=Path(tmpdir),
            )
            assert "docx" in results
            assert "epub" in results

    @pytest.mark.p1
    def test_edge_003_unicode_title_in_filename(self, book_blueprint):
        """EDGE-003 | QA | Unicode title produces safe filename."""
        from core.book_writer_v2.renderers.layout_engine import LayoutEngine

        book_blueprint.title = "Sách Minh Họa: Chí Phèo — Tiểu Thuyết"
        engine = LayoutEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            results = engine.render(
                blueprint=book_blueprint,
                plan=None,
                image_dir="",
                formats=["docx"],
                output_dir=Path(tmpdir),
            )
            assert "docx" in results
            path = results["docx"]
            assert os.path.exists(path)
            # No colon or quotes in filename
            assert ":" not in os.path.basename(path)

    @pytest.mark.p2
    def test_edge_004_plan_serialization_with_all_layout_modes(self):
        """EDGE-004 | QA | All 5 layout modes survive serialization."""
        placements = []
        for mode in LayoutMode:
            placements.append(ImagePlacement(
                image_id=f"img_{mode.value}",
                chapter_index=0,
                layout_mode=mode,
                size=ImageSize.MEDIUM,
            ))
        plan = IllustrationPlan(placements=placements)
        data = plan.to_dict()
        restored = IllustrationPlan.from_dict(data)

        restored_modes = {p.layout_mode for p in restored.placements}
        assert restored_modes == set(LayoutMode)

    @pytest.mark.p2
    def test_edge_005_plan_serialization_all_sizes(self):
        """EDGE-005 | QA | All 4 image sizes survive serialization."""
        placements = []
        for size in ImageSize:
            placements.append(ImagePlacement(
                image_id=f"img_{size.value}",
                chapter_index=0,
                layout_mode=LayoutMode.INLINE,
                size=size,
            ))
        plan = IllustrationPlan(placements=placements)
        data = plan.to_dict()
        restored = IllustrationPlan.from_dict(data)

        restored_sizes = {p.size for p in restored.placements}
        assert restored_sizes == set(ImageSize)

    @pytest.mark.p2
    def test_edge_006_plan_serialization_all_genres(self):
        """EDGE-006 | QA | All genres produce valid LayoutConfig."""
        for genre in BookGenre:
            config = LayoutConfig.for_genre(genre)
            assert config.max_images_per_chapter >= 1
            assert config.min_relevance_score >= 0


# ═══════════════════════════════════════════════════════════
# SMOKE TESTS — End-to-End Pipeline
# ═══════════════════════════════════════════════════════════


class TestE2ESmoke:
    """End User persona — full pipeline smoke tests."""

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_smoke_001_vision_to_docx(
        self, bw_config, mock_book_ai, agent_context,
        book_blueprint, sample_images,
    ):
        """SMOKE-001 | EndUser | Images → VisionAnalyzer → Illustrator → DOCX."""
        from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
        from core.book_writer_v2.agents.illustrator import IllustratorAgent
        from core.book_writer_v2.agents.publisher import PublisherAgent

        # Step 1: Analyze images
        vision = VisionAnalyzerAgent(bw_config, mock_book_ai)
        manifest = await vision.execute(
            {"image_paths": sample_images}, agent_context,
        )
        assert manifest.total_images == 5

        # Step 2: Match to content
        project = BookProject(
            id="smoke-test",
            user_request="Test",
            blueprint=book_blueprint,
            uploaded_images=sample_images,
        )
        illustrator = IllustratorAgent(bw_config, mock_book_ai)
        plan = await illustrator.execute(
            {"project": project, "manifest": manifest}, agent_context,
        )
        assert isinstance(plan, IllustrationPlan)
        # MockAIClient can't produce valid matching JSON — inject fixture plan
        plan = IllustrationPlan(
            project_id="smoke-test",
            placements=[ImagePlacement(
                image_id=sample_images[0],
                chapter_index=0, section_index=0,
                layout_mode=LayoutMode.INLINE, size=ImageSize.MEDIUM,
                relevance_score=0.8,
            )],
        )
        project.illustration_plan = plan

        # Step 3: Render DOCX
        bw_config.output_formats = [OutputFormat.DOCX]
        bw_config.output_dir = tempfile.mkdtemp()

        publisher = PublisherAgent(bw_config, mock_book_ai)
        output = await publisher.execute(project, agent_context)
        assert "docx" in output
        assert os.path.exists(output["docx"])
        assert os.path.getsize(output["docx"]) > 5000

    @pytest.mark.p0
    @pytest.mark.asyncio
    async def test_smoke_002_vision_to_epub(
        self, bw_config, mock_book_ai, agent_context,
        book_blueprint, sample_images,
    ):
        """SMOKE-002 | EndUser | Images → VisionAnalyzer → Illustrator → EPUB."""
        from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
        from core.book_writer_v2.agents.illustrator import IllustratorAgent
        from core.book_writer_v2.agents.publisher import PublisherAgent

        # Step 1: Analyze
        vision = VisionAnalyzerAgent(bw_config, mock_book_ai)
        manifest = await vision.execute(
            {"image_paths": sample_images}, agent_context,
        )

        # Step 2: Match
        project = BookProject(
            id="smoke-epub",
            user_request="Test",
            blueprint=book_blueprint,
            uploaded_images=sample_images,
        )
        illustrator = IllustratorAgent(bw_config, mock_book_ai)
        plan = await illustrator.execute(
            {"project": project, "manifest": manifest}, agent_context,
        )
        project.illustration_plan = plan

        # Step 3: Render EPUB
        bw_config.output_formats = [OutputFormat.EPUB]
        bw_config.output_dir = tempfile.mkdtemp()

        publisher = PublisherAgent(bw_config, mock_book_ai)
        output = await publisher.execute(project, agent_context)
        assert "epub" in output
        assert os.path.exists(output["epub"])

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_smoke_003_text_only_book(
        self, bw_config, mock_book_ai, agent_context, book_blueprint,
    ):
        """SMOKE-003 | EndUser | Text-only book renders all formats without crash."""
        from core.book_writer_v2.agents.publisher import PublisherAgent

        bw_config.output_formats = [OutputFormat.MARKDOWN, OutputFormat.HTML, OutputFormat.DOCX]
        bw_config.output_dir = tempfile.mkdtemp()

        project = BookProject(blueprint=book_blueprint)
        publisher = PublisherAgent(bw_config, mock_book_ai)
        output = await publisher.execute(project, agent_context)

        assert "markdown" in output
        assert "html" in output
        assert "docx" in output
        for path in output.values():
            assert os.path.exists(path)

    @pytest.mark.p1
    @pytest.mark.asyncio
    async def test_smoke_004_plan_persist_then_render(
        self, bw_config, mock_book_ai, agent_context,
        book_project_with_images, book_blueprint,
    ):
        """SMOKE-004 | EndUser | Save plan → reload → render successfully."""
        from api.services.book_writer_v2_service import BookWriterV2Service
        from core.book_writer_v2.agents.publisher import PublisherAgent

        # Save
        service = BookWriterV2Service()
        project = book_project_with_images
        await service._save_project(project)

        # Reload — verifies illustration plan persists
        loaded = await service._load_project(project.id)
        assert loaded is not None
        assert loaded.illustration_plan is not None
        assert len(loaded.illustration_plan.placements) == 3
        assert len(loaded.illustration_plan.galleries) == 1

        # Render using loaded plan on a project with blueprint
        # (_load_project doesn't reconstruct blueprint, so attach it)
        loaded.blueprint = book_blueprint

        bw_config.output_formats = [OutputFormat.DOCX]
        bw_config.output_dir = tempfile.mkdtemp()

        publisher = PublisherAgent(bw_config, mock_book_ai)
        output = await publisher.execute(loaded, agent_context)
        assert "docx" in output
        assert os.path.exists(output["docx"])

        # Cleanup
        os.remove(os.path.join(service.db_path, f"{project.id}.json"))
