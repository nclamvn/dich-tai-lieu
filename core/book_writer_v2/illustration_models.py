"""
Illustrated Book Engine — Data Models (Sprint K)

Defines all types for image analysis, content matching,
layout planning, and rendering configuration.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
from datetime import datetime


class ImageCategory(Enum):
    """Category detected by Vision AI."""
    PHOTO = "photo"
    ILLUSTRATION = "illustration"
    DIAGRAM = "diagram"
    CHART = "chart"
    MAP = "map"
    SCREENSHOT = "screenshot"
    ART = "art"
    INFOGRAPHIC = "infographic"
    OTHER = "other"


class LayoutMode(Enum):
    """How an image is placed in the output."""
    FULL_PAGE = "full_page"
    INLINE = "inline"
    FLOAT_TOP = "float_top"
    GALLERY = "gallery"
    MARGIN = "margin"


class ImageSize(Enum):
    """Relative size of image in layout."""
    SMALL = "small"      # ~25% width
    MEDIUM = "medium"    # ~50% width
    LARGE = "large"      # ~75% width
    FULL = "full"        # 100% width


class BookGenre(Enum):
    """Genre hint for layout/caption style."""
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    CHILDREN = "children"
    TECHNICAL = "technical"
    COOKBOOK = "cookbook"
    TRAVEL = "travel"
    PHOTOGRAPHY = "photography"
    MEMOIR = "memoir"
    ACADEMIC = "academic"


@dataclass
class ImageAnalysis:
    """Vision AI output for a single uploaded image."""
    image_id: str
    filename: str
    filepath: str

    # Vision AI results
    subject: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    category: ImageCategory = ImageCategory.OTHER
    dominant_colors: List[str] = field(default_factory=list)
    era_or_context: Optional[str] = None    # Time period or context if identifiable
    mood: Optional[str] = None              # Visual mood: dramatic, serene, clinical, etc.
    text_in_image: Optional[str] = None     # Any text visible in the image

    # Technical properties (from PIL)
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0
    media_type: str = "image/jpeg"
    format: str = ""                        # jpg, png, webp, etc.

    # AI-suggested placement
    quality_score: float = 0.0        # 0.0–1.0
    suggested_layout: LayoutMode = LayoutMode.INLINE
    suggested_size: ImageSize = ImageSize.MEDIUM
    min_display_width_px: int = 400   # Minimum width to look good

    @property
    def aspect_ratio(self) -> float:
        if self.height == 0:
            return 1.0
        return self.width / self.height

    @property
    def is_landscape(self) -> bool:
        return self.aspect_ratio > 1.2

    @property
    def is_portrait(self) -> bool:
        return self.aspect_ratio < 0.8

    @property
    def is_high_quality(self) -> bool:
        return self.quality_score >= 0.7

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "filename": self.filename,
            "subject": self.subject,
            "description": self.description,
            "keywords": self.keywords,
            "category": self.category.value,
            "dominant_colors": self.dominant_colors,
            "era_or_context": self.era_or_context,
            "mood": self.mood,
            "text_in_image": self.text_in_image,
            "width": self.width,
            "height": self.height,
            "file_size_bytes": self.file_size_bytes,
            "media_type": self.media_type,
            "format": self.format,
            "quality_score": round(self.quality_score, 2),
            "suggested_layout": self.suggested_layout.value,
            "suggested_size": self.suggested_size.value,
            "min_display_width_px": self.min_display_width_px,
            "aspect_ratio": round(self.aspect_ratio, 2),
        }


@dataclass
class ImageManifest:
    """Collection of analyzed images + detected genre."""
    images: List[ImageAnalysis] = field(default_factory=list)
    detected_genre: BookGenre = BookGenre.NON_FICTION
    total_images: int = 0
    project_id: str = ""
    analysis_provider: str = "anthropic"
    analyzed_at: Optional[datetime] = None

    def __post_init__(self):
        self.total_images = len(self.images)

    def get_image(self, image_id: str) -> Optional[ImageAnalysis]:
        for img in self.images:
            if img.image_id == image_id:
                return img
        return None

    def get_by_category(self, category: ImageCategory) -> List[ImageAnalysis]:
        return [img for img in self.images if img.category == category]

    def to_dict(self) -> dict:
        return {
            "images": [img.to_dict() for img in self.images],
            "detected_genre": self.detected_genre.value,
            "total_images": len(self.images),
            "project_id": self.project_id,
            "analysis_provider": self.analysis_provider,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }


@dataclass
class ImagePlacement:
    """Where and how a single image appears in the book."""
    image_id: str
    chapter_index: int
    section_index: int = 0
    paragraph_index: int = 0

    # Layout decisions
    layout_mode: LayoutMode = LayoutMode.INLINE
    size: ImageSize = ImageSize.MEDIUM
    alignment: str = "center"           # left, center, right

    # Generated content
    caption: str = ""
    credit: Optional[str] = None        # Photo credit / source attribution
    alt_text: str = ""                  # Accessibility alt text

    # Rendering hints
    border: bool = False                # Add thin border around image
    page_break_before: bool = False     # Start new page before this image
    page_break_after: bool = False      # Page break after (for full_page)

    # Matching confidence
    relevance_score: float = 0.0     # 0.0–1.0

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "chapter_index": self.chapter_index,
            "section_index": self.section_index,
            "paragraph_index": self.paragraph_index,
            "layout_mode": self.layout_mode.value,
            "size": self.size.value,
            "alignment": self.alignment,
            "caption": self.caption,
            "credit": self.credit,
            "alt_text": self.alt_text,
            "border": self.border,
            "page_break_before": self.page_break_before,
            "page_break_after": self.page_break_after,
            "relevance_score": round(self.relevance_score, 2),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImagePlacement":
        return cls(
            image_id=data["image_id"],
            chapter_index=data.get("chapter_index", 0),
            section_index=data.get("section_index", 0),
            paragraph_index=data.get("paragraph_index", 0),
            layout_mode=LayoutMode(data.get("layout_mode", "inline")),
            size=ImageSize(data.get("size", "medium")),
            alignment=data.get("alignment", "center"),
            caption=data.get("caption", ""),
            credit=data.get("credit"),
            alt_text=data.get("alt_text", ""),
            border=data.get("border", False),
            page_break_before=data.get("page_break_before", False),
            page_break_after=data.get("page_break_after", False),
            relevance_score=data.get("relevance_score", 0.0),
        )


@dataclass
class GalleryGroup:
    """A group of related images displayed together."""
    group_id: str
    image_ids: List[str] = field(default_factory=list)
    title: str = ""
    caption: Optional[str] = None
    chapter_index: int = 0
    after_paragraph: int = 0

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "image_ids": self.image_ids,
            "title": self.title,
            "caption": self.caption,
            "chapter_index": self.chapter_index,
            "after_paragraph": self.after_paragraph,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GalleryGroup":
        return cls(
            group_id=data.get("group_id", ""),
            image_ids=data.get("image_ids", []),
            title=data.get("title", ""),
            caption=data.get("caption"),
            chapter_index=data.get("chapter_index", 0),
            after_paragraph=data.get("after_paragraph", 0),
        )


@dataclass
class ChapterIndex:
    """Extracted topics/entities for a single chapter."""
    chapter_id: str
    chapter_number: int
    title: str
    summary: str = ""
    topics: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    time_periods: List[str] = field(default_factory=list)
    paragraph_count: int = 0
    sections: List[Dict] = field(default_factory=list)  # [{index, title, keywords, summary}]


@dataclass
class MatchCandidate:
    """A potential image-to-chapter match with scoring."""
    image_id: str
    chapter_index: int
    keyword_overlap: float = 0.0     # 0.0–1.0
    ai_relevance: float = 0.0       # 0.0–1.0
    combined_score: float = 0.0

    def compute_combined(self, keyword_weight: float = 0.4, ai_weight: float = 0.6):
        self.combined_score = (
            self.keyword_overlap * keyword_weight
            + self.ai_relevance * ai_weight
        )


@dataclass
class IllustrationPlan:
    """Complete plan: which images go where, with what layout."""
    project_id: str = ""
    placements: List[ImagePlacement] = field(default_factory=list)
    galleries: List[GalleryGroup] = field(default_factory=list)
    unmatched_image_ids: List[str] = field(default_factory=list)
    genre: BookGenre = BookGenre.NON_FICTION
    layout_style_notes: str = ""        # Overall layout style guidance

    def get_placements_for_chapter(self, chapter_index: int) -> List[ImagePlacement]:
        return [
            p for p in self.placements
            if p.chapter_index == chapter_index
        ]

    def get_placements_for_section(
        self, chapter_index: int, section_index: int
    ) -> List[ImagePlacement]:
        return [
            p for p in self.placements
            if p.chapter_index == chapter_index
            and p.section_index == section_index
        ]

    @property
    def total_placed(self) -> int:
        return len(self.placements)

    @property
    def total_unmatched(self) -> int:
        return len(self.unmatched_image_ids)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "placements": [p.to_dict() for p in self.placements],
            "galleries": [g.to_dict() for g in self.galleries],
            "unmatched_image_ids": self.unmatched_image_ids,
            "total_placed": self.total_placed,
            "total_unmatched": self.total_unmatched,
            "genre": self.genre.value,
            "layout_style_notes": self.layout_style_notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IllustrationPlan":
        placements = [
            ImagePlacement.from_dict(p) for p in data.get("placements", [])
        ]
        galleries = [
            GalleryGroup.from_dict(g) for g in data.get("galleries", [])
        ]
        return cls(
            project_id=data.get("project_id", ""),
            placements=placements,
            galleries=galleries,
            unmatched_image_ids=data.get("unmatched_image_ids", []),
            genre=BookGenre(data.get("genre", "non_fiction")),
            layout_style_notes=data.get("layout_style_notes", ""),
        )


@dataclass
class LayoutConfig:
    """Rendering configuration for illustrated output."""
    max_images_per_chapter: int = 5
    max_images_per_section: int = 2
    min_relevance_score: float = 0.3
    prefer_full_page_for_high_quality: bool = True
    enable_galleries: bool = True
    gallery_columns: int = 2
    caption_style: str = "italic"      # italic | bold | plain
    image_max_width_px: int = 1440
    image_max_height_px: int = 1920

    # Size percentages for DOCX rendering
    size_pct: Dict[str, float] = field(default_factory=lambda: {
        "small": 0.25,
        "medium": 0.50,
        "large": 0.75,
        "full": 1.0,
    })

    @classmethod
    def for_genre(cls, genre: BookGenre) -> "LayoutConfig":
        """Return genre-appropriate layout defaults."""
        presets: Dict[BookGenre, dict] = {
            BookGenre.CHILDREN: dict(
                max_images_per_chapter=8,
                max_images_per_section=3,
                prefer_full_page_for_high_quality=True,
                enable_galleries=False,
                caption_style="bold",
            ),
            BookGenre.PHOTOGRAPHY: dict(
                max_images_per_chapter=10,
                max_images_per_section=4,
                prefer_full_page_for_high_quality=True,
                enable_galleries=True,
                gallery_columns=3,
                caption_style="italic",
            ),
            BookGenre.TECHNICAL: dict(
                max_images_per_chapter=6,
                max_images_per_section=2,
                prefer_full_page_for_high_quality=False,
                caption_style="plain",
            ),
            BookGenre.COOKBOOK: dict(
                max_images_per_chapter=8,
                max_images_per_section=3,
                prefer_full_page_for_high_quality=True,
                enable_galleries=True,
                gallery_columns=2,
                caption_style="italic",
            ),
            BookGenre.TRAVEL: dict(
                max_images_per_chapter=8,
                max_images_per_section=3,
                prefer_full_page_for_high_quality=True,
                enable_galleries=True,
                gallery_columns=2,
            ),
        }
        overrides = presets.get(genre, {})
        return cls(**overrides)

    def to_dict(self) -> dict:
        return {
            "max_images_per_chapter": self.max_images_per_chapter,
            "max_images_per_section": self.max_images_per_section,
            "min_relevance_score": self.min_relevance_score,
            "prefer_full_page_for_high_quality": self.prefer_full_page_for_high_quality,
            "enable_galleries": self.enable_galleries,
            "gallery_columns": self.gallery_columns,
            "caption_style": self.caption_style,
        }
