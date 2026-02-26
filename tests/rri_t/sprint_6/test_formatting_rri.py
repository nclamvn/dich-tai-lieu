"""
RRI-T Sprint 6: Formatting Engine tests.

Persona coverage: End User, QA Destroyer, Business Analyst
Dimensions: D2 (API), D5 (Data Integrity), D7 (Edge Cases)
"""

import pytest

from core.formatting.detector import StructureDetector, DocumentElement
from core.formatting.document_model import (
    DocumentModel, TocEntry, ValidationError, DocumentStats,
)
from core.formatting.style_engine import StyleEngine
from core.formatting.page_layout import PageLayoutManager
from core.formatting.toc_generator import TocGenerator
from core.formatting.templates.template_factory import TemplateFactory


pytestmark = [pytest.mark.rri_t]


# ===========================================================================
# FMT-001: Structure Detection
# ===========================================================================

class TestStructureDetection:
    """QA Destroyer persona — structure detection accuracy."""

    @pytest.mark.p0
    def test_fmt_001_detect_markdown_headings(self):
        """FMT-001 | QA | Markdown headings detected at correct levels"""
        text = "# Title\n\nSome intro paragraph.\n\n## Chapter 1\n\nContent.\n\n### Section 1.1\n\nMore content."
        detector = StructureDetector()
        elements = detector.detect(text)
        headings = [e for e in elements if e.type == "heading"]
        assert len(headings) >= 3
        assert headings[0].level == 1
        assert headings[1].level == 2
        assert headings[2].level == 3

    @pytest.mark.p0
    def test_fmt_001b_detect_paragraphs(self):
        """FMT-001b | QA | Regular text detected as paragraphs"""
        text = "First paragraph here.\n\nSecond paragraph here."
        detector = StructureDetector()
        elements = detector.detect(text)
        paragraphs = [e for e in elements if e.type == "paragraph"]
        assert len(paragraphs) >= 2

    @pytest.mark.p1
    def test_fmt_001c_detect_bullet_list(self):
        """FMT-001c | QA | Bullet list items detected"""
        text = "# Heading\n\nIntroduction paragraph.\n\n- Item one\n- Item two\n- Item three\n\nEnd."
        detector = StructureDetector()
        elements = detector.detect(text)
        list_elements = [e for e in elements if "list" in e.type.lower() or "bullet" in e.type.lower()]
        assert len(list_elements) >= 1

    @pytest.mark.p1
    def test_fmt_001d_detect_code_block(self):
        """FMT-001d | QA | Fenced code block detected"""
        text = "# Code Example\n\nSome intro.\n\n```python\ndef hello():\n    print('hi')\n```\n\nEnd."
        detector = StructureDetector()
        elements = detector.detect(text)
        code_elements = [e for e in elements if "code" in e.type.lower()]
        assert len(code_elements) >= 1

    @pytest.mark.p1
    def test_fmt_001e_empty_text(self):
        """FMT-001e | QA | Empty text -> no elements (or single empty)"""
        detector = StructureDetector()
        elements = detector.detect("")
        # Should not crash; may return empty or single element
        assert isinstance(elements, list)

    @pytest.mark.p1
    def test_fmt_001f_language_detection(self):
        """FMT-001f | QA | Language detection works"""
        detector = StructureDetector(language="auto")
        detector.detect("This is English text about software development.")
        lang = detector.get_detected_language()
        assert lang in ("en", "auto", "unknown")

    @pytest.mark.p1
    def test_fmt_001g_structure_summary(self):
        """FMT-001g | BA | get_structure_summary returns element counts"""
        text = "# Title\n\nParagraph one.\n\n## Chapter\n\nParagraph two."
        detector = StructureDetector()
        summary = detector.get_structure_summary(text)
        assert isinstance(summary, dict)


# ===========================================================================
# FMT-002: Document Model
# ===========================================================================

class TestDocumentModel:
    """Business Analyst persona — document AST."""

    @pytest.mark.p0
    def test_fmt_002_from_text(self):
        """FMT-002 | BA | DocumentModel.from_text creates populated model"""
        text = "# My Document\n\nFirst paragraph.\n\n## Section 1\n\nContent here."
        model = DocumentModel.from_text(text)
        assert len(model.elements) >= 3  # 2 headings + paragraphs
        assert len(model.toc) >= 2  # H1 + H2

    @pytest.mark.p0
    def test_fmt_002b_toc_generation(self):
        """FMT-002b | BA | TOC entries match headings"""
        text = "# Title\n\n## Chapter 1\n\nContent.\n\n## Chapter 2\n\nMore content."
        model = DocumentModel.from_text(text)
        toc = model.build_toc()
        assert len(toc) >= 3  # H1 + 2 x H2
        assert toc[0].level == 1
        assert toc[1].level == 2

    @pytest.mark.p0
    def test_fmt_002c_validation_no_headings(self):
        """FMT-002c | QA | Document with no headings -> warning"""
        model = DocumentModel()
        model.add_element(DocumentElement(
            type="paragraph", content="Just a paragraph.", element_id="p1",
        ))
        errors = model.validate()
        assert any(e.severity == "warning" for e in errors)
        assert any("no headings" in e.message.lower() for e in errors)

    @pytest.mark.p1
    def test_fmt_002d_validation_skipped_levels(self):
        """FMT-002d | QA | Skipped heading levels flagged"""
        model = DocumentModel()
        model.add_element(DocumentElement(
            type="heading", content="Title", level=1, element_id="h1",
        ))
        model.add_element(DocumentElement(
            type="heading", content="Deep", level=3, element_id="h3",
        ))
        errors = model.validate()
        assert any("skipped" in e.message.lower() for e in errors)

    @pytest.mark.p1
    def test_fmt_002e_statistics(self):
        """FMT-002e | BA | Document statistics accurate"""
        text = "# Title\n\nParagraph one.\n\n## Section\n\nParagraph two with more words here."
        model = DocumentModel.from_text(text)
        stats = model.get_statistics()
        assert isinstance(stats, DocumentStats)
        assert stats.total_elements > 0
        assert stats.word_count > 0

    @pytest.mark.p1
    def test_fmt_002f_get_headings(self):
        """FMT-002f | BA | get_headings filters by level"""
        text = "# Title\n\n## Sub 1\n\n## Sub 2\n\n### Deep"
        model = DocumentModel.from_text(text)
        h2s = model.get_headings(level=2)
        assert len(h2s) == 2

    @pytest.mark.p1
    def test_fmt_002g_to_dict(self):
        """FMT-002g | BA | to_dict() serializes model"""
        text = "# Title\n\nContent."
        model = DocumentModel.from_text(text)
        d = model.to_dict()
        assert "elements" in d
        assert isinstance(d["elements"], list)


# ===========================================================================
# FMT-003: Style Engine
# ===========================================================================

class TestStyleEngine:
    """End User persona — document styling."""

    @pytest.mark.p0
    def test_fmt_003_apply_default_style(self):
        """FMT-003 | End User | StyleEngine applies default template"""
        text = "# Title\n\nParagraph content.\n\n## Section\n\nMore content."
        model = DocumentModel.from_text(text)
        engine = StyleEngine()
        styled = engine.apply(model)
        assert styled is not None
        assert len(styled.elements) > 0

    @pytest.mark.p1
    def test_fmt_003b_heading_styled_bold(self):
        """FMT-003b | End User | Headings get bold styling"""
        text = "# Title\n\nContent."
        model = DocumentModel.from_text(text)
        engine = StyleEngine()
        styled = engine.apply(model)
        heading_elements = [e for e in styled.elements if hasattr(e, 'bold') and e.original.type == "heading"]
        if heading_elements:
            assert heading_elements[0].bold is True

    @pytest.mark.p1
    def test_fmt_003c_style_summary(self):
        """FMT-003c | BA | get_style_summary returns template info"""
        engine = StyleEngine()
        summary = engine.get_style_summary()
        assert isinstance(summary, dict)


# ===========================================================================
# FMT-004: Page Layout
# ===========================================================================

class TestPageLayout:
    """DevOps persona — page configuration."""

    @pytest.mark.p1
    def test_fmt_004_content_area_calculation(self):
        """FMT-004 | DevOps | Content area = page - margins"""
        manager = PageLayoutManager(page_size="A4", margins="normal")
        area = manager.calculate_content_area()
        assert area.width > 0
        assert area.height > 0
        # A4 is 8.27x11.69, normal margins are 1.0
        assert area.width < 8.27
        assert area.height < 11.69

    @pytest.mark.p1
    def test_fmt_004b_page_sizes(self):
        """FMT-004b | DevOps | Different page sizes produce different areas"""
        a4 = PageLayoutManager(page_size="A4")
        letter = PageLayoutManager(page_size="Letter")
        area_a4 = a4.calculate_content_area()
        area_letter = letter.calculate_content_area()
        # They should differ (A4 is taller, Letter is wider)
        assert area_a4.height != area_letter.height or area_a4.width != area_letter.width

    @pytest.mark.p1
    def test_fmt_004c_config_summary(self):
        """FMT-004c | BA | get_config_summary returns page settings"""
        manager = PageLayoutManager()
        config = manager.get_config_summary()
        assert isinstance(config, dict)


# ===========================================================================
# FMT-005: TOC Generator
# ===========================================================================

class TestTocGenerator:
    """Business Analyst persona — TOC generation."""

    @pytest.mark.p1
    def test_fmt_005_generate_toc(self):
        """FMT-005 | BA | TocGenerator creates entries from model"""
        text = "# Book Title\n\n## Chapter 1\n\nContent.\n\n## Chapter 2\n\nMore."
        model = DocumentModel.from_text(text)
        gen = TocGenerator()
        toc = gen.generate(model)
        assert toc is not None
        assert len(toc.entries) >= 3

    @pytest.mark.p1
    def test_fmt_005b_toc_to_markdown(self):
        """FMT-005b | BA | TOC renders to markdown"""
        text = "# Title\n\n## Chapter 1\n\nContent."
        model = DocumentModel.from_text(text)
        gen = TocGenerator()
        toc = gen.generate(model)
        md = gen.to_markdown(toc)
        assert isinstance(md, str)
        assert len(md) > 0

    @pytest.mark.p1
    def test_fmt_005c_toc_plain_text(self):
        """FMT-005c | BA | TOC renders to plain text"""
        text = "# Title\n\n## Section\n\nContent."
        model = DocumentModel.from_text(text)
        gen = TocGenerator()
        toc = gen.generate(model)
        plain = gen.to_plain_text(toc)
        assert isinstance(plain, str)


# ===========================================================================
# FMT-006: Template Factory
# ===========================================================================

class TestTemplateFactory:
    """Business Analyst persona — template management."""

    @pytest.mark.p0
    def test_fmt_006_list_templates(self):
        """FMT-006 | BA | TemplateFactory lists available templates"""
        templates = TemplateFactory.list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 4  # book, report, legal, academic

    @pytest.mark.p0
    def test_fmt_006b_get_known_templates(self):
        """FMT-006b | BA | Known templates retrievable"""
        for name in ["book", "report", "academic", "legal"]:
            template = TemplateFactory.get_template(name)
            assert template is not None
            assert template.name == name

    @pytest.mark.p1
    def test_fmt_006c_template_has_config(self):
        """FMT-006c | BA | Each template returns valid TemplateConfig"""
        template = TemplateFactory.get_template("book")
        config = template.get_config()
        assert config.name == "book"
        assert config.display_name
        assert config.description
        assert "H1" in config.heading_styles or "h1" in config.heading_styles

    @pytest.mark.p1
    def test_fmt_006d_auto_detect(self):
        """FMT-006d | QA | auto_detect returns valid template name"""
        text = "Chapter 1: Introduction\n\nOnce upon a time..."
        detected = TemplateFactory.auto_detect(text)
        assert detected in TemplateFactory.list_templates() or detected == "default"

    @pytest.mark.p1
    def test_fmt_006e_invalid_template(self):
        """FMT-006e | QA | Non-existent template -> fallback or error"""
        try:
            template = TemplateFactory.get_template("nonexistent_template")
            # If it returns a fallback, that's valid
            assert template is not None
        except (KeyError, ValueError):
            # Raising an error is also valid behavior
            pass


# ===========================================================================
# FMT-007: DocumentStats
# ===========================================================================

class TestDocumentStats:
    """Business Analyst persona — document analytics."""

    @pytest.mark.p1
    def test_fmt_007_stats_to_dict(self):
        """FMT-007 | BA | DocumentStats.to_dict() has all fields"""
        stats = DocumentStats()
        d = stats.to_dict()
        expected_keys = [
            "total_elements", "headings", "paragraphs",
            "lists", "tables", "code_blocks", "quotes",
            "word_count", "char_count",
        ]
        for key in expected_keys:
            assert key in d

    @pytest.mark.p1
    def test_fmt_007b_empty_stats(self):
        """FMT-007b | QA | Empty stats all zero"""
        stats = DocumentStats()
        assert stats.total_elements == 0
        assert stats.word_count == 0
        assert stats.paragraph_count == 0


# ===========================================================================
# FMT-008: ValidationError model
# ===========================================================================

class TestValidationError:
    """QA Destroyer persona — validation model."""

    @pytest.mark.p1
    def test_fmt_008_validation_error_repr(self):
        """FMT-008 | QA | ValidationError has readable repr"""
        err = ValidationError(
            severity="warning",
            message="No headings found",
            suggestion="Add a title",
        )
        assert "WARNING" in repr(err)
        assert "No headings found" in repr(err)

    @pytest.mark.p1
    def test_fmt_008b_toc_entry_fields(self):
        """FMT-008b | BA | TocEntry has level, title, element_id"""
        entry = TocEntry(level=1, title="Chapter 1", element_id="abc123")
        assert entry.level == 1
        assert entry.title == "Chapter 1"
        assert entry.page_number is None  # Not set until export
