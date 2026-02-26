"""
Tests for Illustration Data Models (Sprint K)
"""

import pytest
from core.book_writer_v2.illustration_models import (
    ImageAnalysis,
    ImageCategory,
    ImageManifest,
    ImagePlacement,
    ImageSize,
    IllustrationPlan,
    LayoutConfig,
    LayoutMode,
    BookGenre,
    GalleryGroup,
    ChapterIndex,
    MatchCandidate,
)


class TestImageCategory:
    def test_all_values(self):
        values = {e.value for e in ImageCategory}
        assert "photo" in values
        assert "diagram" in values
        assert "other" in values

    def test_from_string(self):
        assert ImageCategory("photo") == ImageCategory.PHOTO
        assert ImageCategory("chart") == ImageCategory.CHART


class TestLayoutMode:
    def test_all_modes(self):
        assert len(LayoutMode) == 5
        assert LayoutMode.FULL_PAGE.value == "full_page"
        assert LayoutMode.GALLERY.value == "gallery"


class TestImageAnalysis:
    def test_defaults(self):
        img = ImageAnalysis(image_id="abc", filename="test.jpg", filepath="/tmp/test.jpg")
        assert img.quality_score == 0.0
        assert img.category == ImageCategory.OTHER
        assert img.suggested_layout == LayoutMode.INLINE

    def test_aspect_ratio_landscape(self):
        img = ImageAnalysis(image_id="a", filename="a.jpg", filepath="/a.jpg", width=1920, height=1080)
        assert img.aspect_ratio == pytest.approx(1.78, abs=0.01)
        assert img.is_landscape is True
        assert img.is_portrait is False

    def test_aspect_ratio_portrait(self):
        img = ImageAnalysis(image_id="b", filename="b.jpg", filepath="/b.jpg", width=600, height=1200)
        assert img.is_portrait is True
        assert img.is_landscape is False

    def test_aspect_ratio_square(self):
        img = ImageAnalysis(image_id="c", filename="c.jpg", filepath="/c.jpg", width=500, height=500)
        assert img.is_landscape is False
        assert img.is_portrait is False

    def test_aspect_ratio_zero_height(self):
        img = ImageAnalysis(image_id="d", filename="d.jpg", filepath="/d.jpg", width=500, height=0)
        assert img.aspect_ratio == 1.0

    def test_high_quality(self):
        img = ImageAnalysis(image_id="e", filename="e.jpg", filepath="/e.jpg", quality_score=0.8)
        assert img.is_high_quality is True
        img2 = ImageAnalysis(image_id="f", filename="f.jpg", filepath="/f.jpg", quality_score=0.3)
        assert img2.is_high_quality is False

    def test_to_dict(self):
        img = ImageAnalysis(
            image_id="test1",
            filename="photo.jpg",
            filepath="/path/photo.jpg",
            subject="Sunset",
            keywords=["nature", "sky"],
            width=800,
            height=600,
            quality_score=0.85,
        )
        d = img.to_dict()
        assert d["image_id"] == "test1"
        assert d["subject"] == "Sunset"
        assert d["quality_score"] == 0.85
        assert d["aspect_ratio"] == 1.33


class TestImageManifest:
    def test_empty_manifest(self):
        m = ImageManifest()
        assert m.total_images == 0
        assert m.images == []
        assert m.detected_genre == BookGenre.NON_FICTION

    def test_get_image(self):
        img = ImageAnalysis(image_id="x1", filename="a.jpg", filepath="/a.jpg")
        m = ImageManifest(images=[img])
        assert m.get_image("x1") is img
        assert m.get_image("nonexistent") is None

    def test_get_by_category(self):
        photos = [
            ImageAnalysis(image_id=f"p{i}", filename=f"{i}.jpg", filepath=f"/{i}.jpg", category=ImageCategory.PHOTO)
            for i in range(3)
        ]
        diagram = ImageAnalysis(image_id="d1", filename="d.png", filepath="/d.png", category=ImageCategory.DIAGRAM)
        m = ImageManifest(images=photos + [diagram])
        assert len(m.get_by_category(ImageCategory.PHOTO)) == 3
        assert len(m.get_by_category(ImageCategory.DIAGRAM)) == 1
        assert len(m.get_by_category(ImageCategory.ART)) == 0

    def test_to_dict(self):
        m = ImageManifest(
            images=[ImageAnalysis(image_id="i1", filename="a.jpg", filepath="/a.jpg")],
            detected_genre=BookGenre.CHILDREN,
        )
        d = m.to_dict()
        assert d["total_images"] == 1
        assert d["detected_genre"] == "children"


class TestImagePlacement:
    def test_defaults(self):
        p = ImagePlacement(image_id="img1", chapter_index=0)
        assert p.layout_mode == LayoutMode.INLINE
        assert p.size == ImageSize.MEDIUM
        assert p.relevance_score == 0.0

    def test_to_dict(self):
        p = ImagePlacement(
            image_id="img2",
            chapter_index=1,
            section_index=2,
            layout_mode=LayoutMode.FULL_PAGE,
            caption="Beautiful scene",
            relevance_score=0.95,
        )
        d = p.to_dict()
        assert d["image_id"] == "img2"
        assert d["layout_mode"] == "full_page"
        assert d["caption"] == "Beautiful scene"
        assert d["relevance_score"] == 0.95


class TestIllustrationPlan:
    def test_empty_plan(self):
        plan = IllustrationPlan()
        assert plan.total_placed == 0
        assert plan.total_unmatched == 0

    def test_get_placements_for_chapter(self):
        placements = [
            ImagePlacement(image_id="a", chapter_index=0, section_index=0),
            ImagePlacement(image_id="b", chapter_index=0, section_index=1),
            ImagePlacement(image_id="c", chapter_index=1, section_index=0),
        ]
        plan = IllustrationPlan(placements=placements)

        ch0 = plan.get_placements_for_chapter(0)
        assert len(ch0) == 2

        ch1 = plan.get_placements_for_chapter(1)
        assert len(ch1) == 1

        ch2 = plan.get_placements_for_chapter(2)
        assert len(ch2) == 0

    def test_get_placements_for_section(self):
        placements = [
            ImagePlacement(image_id="a", chapter_index=0, section_index=0),
            ImagePlacement(image_id="b", chapter_index=0, section_index=1),
        ]
        plan = IllustrationPlan(placements=placements)

        sec = plan.get_placements_for_section(0, 0)
        assert len(sec) == 1
        assert sec[0].image_id == "a"

    def test_to_dict(self):
        plan = IllustrationPlan(
            placements=[ImagePlacement(image_id="x", chapter_index=0)],
            unmatched_image_ids=["y", "z"],
        )
        d = plan.to_dict()
        assert d["total_placed"] == 1
        assert d["total_unmatched"] == 2


class TestLayoutConfig:
    def test_defaults(self):
        cfg = LayoutConfig()
        assert cfg.max_images_per_chapter == 5
        assert cfg.min_relevance_score == 0.3
        assert cfg.gallery_columns == 2

    def test_for_genre_children(self):
        cfg = LayoutConfig.for_genre(BookGenre.CHILDREN)
        assert cfg.max_images_per_chapter == 8
        assert cfg.caption_style == "bold"
        assert cfg.enable_galleries is False

    def test_for_genre_photography(self):
        cfg = LayoutConfig.for_genre(BookGenre.PHOTOGRAPHY)
        assert cfg.max_images_per_chapter == 10
        assert cfg.gallery_columns == 3

    def test_for_genre_technical(self):
        cfg = LayoutConfig.for_genre(BookGenre.TECHNICAL)
        assert cfg.prefer_full_page_for_high_quality is False
        assert cfg.caption_style == "plain"

    def test_for_genre_unknown(self):
        cfg = LayoutConfig.for_genre(BookGenre.FICTION)
        assert cfg.max_images_per_chapter == 5  # default


class TestMatchCandidate:
    def test_compute_combined(self):
        mc = MatchCandidate(
            image_id="i1",
            chapter_index=0,
            keyword_overlap=0.5,
            ai_relevance=0.8,
        )
        mc.compute_combined()
        expected = 0.5 * 0.4 + 0.8 * 0.6
        assert mc.combined_score == pytest.approx(expected, abs=0.01)

    def test_compute_combined_custom_weights(self):
        mc = MatchCandidate(image_id="i2", chapter_index=1, keyword_overlap=1.0, ai_relevance=0.0)
        mc.compute_combined(keyword_weight=1.0, ai_weight=0.0)
        assert mc.combined_score == pytest.approx(1.0)


class TestGalleryGroup:
    def test_to_dict(self):
        g = GalleryGroup(group_id="g1", image_ids=["a", "b"], title="My gallery", chapter_index=2)
        d = g.to_dict()
        assert d["group_id"] == "g1"
        assert d["image_ids"] == ["a", "b"]
        assert d["chapter_index"] == 2


class TestChapterIndex:
    def test_fields(self):
        ci = ChapterIndex(
            chapter_id="ch1",
            chapter_number=1,
            title="Introduction",
            topics=["AI", "ML"],
            keywords=["neural", "network"],
        )
        assert ci.chapter_id == "ch1"
        assert len(ci.topics) == 2
        assert len(ci.keywords) == 2


class TestBookStatus:
    def test_illustrating_status(self):
        from core.book_writer_v2.models import BookStatus
        assert BookStatus.ILLUSTRATING.value == "illustrating"


class TestBookProjectImages:
    def test_has_images_false(self):
        from core.book_writer_v2.models import BookProject
        p = BookProject()
        assert p.has_images() is False

    def test_has_images_true(self):
        from core.book_writer_v2.models import BookProject
        p = BookProject(uploaded_images=["/path/to/img.jpg"])
        assert p.has_images() is True

    def test_to_dict_includes_images(self):
        from core.book_writer_v2.models import BookProject
        p = BookProject(uploaded_images=["a.jpg", "b.jpg"])
        d = p.to_dict()
        assert "uploaded_images" in d
        assert d["has_images"] is True
        assert d["illustration_plan"] is None
