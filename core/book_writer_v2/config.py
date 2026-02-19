"""
Book Writer v2.0 Configuration

Central configuration for all pipeline settings.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class AIProvider(Enum):
    """Supported AI providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


class OutputFormat(Enum):
    """Supported output formats"""
    DOCX = "docx"
    PDF = "pdf"
    MARKDOWN = "markdown"
    EPUB = "epub"
    HTML = "html"


@dataclass
class BookWriterConfig:
    """
    Configuration for Book Writer v2.0 Pipeline.

    All settings that control book generation behavior.
    """

    # === WORD COUNT SETTINGS ===

    words_per_page: int = 300
    """Standard words per page for book formatting"""

    target_words_per_section: int = 1500
    """Target words per section - optimized for single API call"""

    min_words_per_section: int = 1200
    """Minimum acceptable words per section"""

    max_words_per_section: int = 2000
    """Maximum words per section before splitting"""

    # === STRUCTURE SETTINGS ===

    default_sections_per_chapter: int = 4
    """Default number of sections in each chapter"""

    min_sections_per_chapter: int = 3
    """Minimum sections per chapter"""

    max_sections_per_chapter: int = 6
    """Maximum sections per chapter"""

    default_chapters_per_part: int = 4
    """Default chapters per part/division"""

    min_parts: int = 2
    """Minimum parts for books > 100 pages"""

    max_parts: int = 5
    """Maximum parts"""

    # === QUALITY THRESHOLDS ===

    min_total_completion: float = 95.0
    """Minimum % of target word count required"""

    max_total_completion: float = 105.0
    """Maximum % of target (prevent over-generation)"""

    section_expansion_threshold: float = 90.0
    """Section needs expansion if below this % of target"""

    section_complete_threshold: float = 95.0
    """Section is complete at this % of target"""

    chapter_balance_threshold: float = 80.0
    """Each chapter must be at least this % of its target"""

    max_expansion_attempts: int = 3
    """Maximum expansion attempts per section"""

    max_total_expansion_rounds: int = 5
    """Maximum full expansion rounds for entire book"""

    # === AI MODEL SETTINGS ===

    primary_provider: AIProvider = AIProvider.ANTHROPIC
    """Primary AI provider"""

    primary_model: str = "claude-sonnet-4-20250514"
    """Primary model for content generation"""

    fallback_provider: AIProvider = AIProvider.OPENAI
    """Fallback AI provider"""

    fallback_model: str = "gpt-4o"
    """Fallback model if primary fails"""

    max_tokens_per_call: int = 4096
    """Maximum tokens per API call"""

    temperature: float = 0.7
    """Temperature for creative content"""

    temperature_expansion: float = 0.8
    """Slightly higher temperature for expansion (more variety)"""

    temperature_editing: float = 0.3
    """Lower temperature for editing (more precise)"""

    # === FRONT/BACK MATTER ===

    include_dedication: bool = True
    include_preface: bool = True
    include_acknowledgments: bool = True
    include_table_of_contents: bool = True
    include_conclusion: bool = True
    include_glossary: bool = True
    include_index: bool = False
    include_appendices: bool = True

    front_matter_pages: int = 10
    """Estimated pages for front matter"""

    back_matter_pages: int = 15
    """Estimated pages for back matter"""

    # === OUTPUT SETTINGS ===

    output_formats: List[OutputFormat] = field(
        default_factory=lambda: [OutputFormat.DOCX, OutputFormat.MARKDOWN]
    )
    """Output formats to generate"""

    output_dir: str = "output/books"
    """Directory for generated books"""

    # === PROGRESS & CHECKPOINTS ===

    enable_websocket_progress: bool = True
    """Send real-time progress via WebSocket"""

    checkpoint_interval: int = 5
    """Save checkpoint every N sections"""

    enable_auto_save: bool = True
    """Auto-save progress to database"""

    # === COMPUTED PROPERTIES ===

    def calculate_structure(self, target_pages: int) -> dict:
        """
        Calculate optimal book structure based on target pages.

        Returns dict with recommended parts, chapters, sections.
        """
        content_pages = target_pages - self.front_matter_pages - self.back_matter_pages
        content_words = content_pages * self.words_per_page

        total_sections = content_words // self.target_words_per_section

        total_chapters = max(
            total_sections // self.default_sections_per_chapter,
            3,
        )

        if target_pages < 100:
            num_parts = 1
        elif target_pages < 200:
            num_parts = 2
        elif target_pages < 400:
            num_parts = 3
        else:
            num_parts = min(4, target_pages // 100)

        chapters_per_part = total_chapters // num_parts

        return {
            "target_pages": target_pages,
            "content_pages": content_pages,
            "content_words": content_words,
            "total_sections": total_sections,
            "total_chapters": total_chapters,
            "num_parts": num_parts,
            "chapters_per_part": chapters_per_part,
            "words_per_chapter": content_words // total_chapters,
            "words_per_section": self.target_words_per_section,
        }
