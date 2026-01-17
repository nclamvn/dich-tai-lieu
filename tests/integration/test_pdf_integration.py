"""
Integration tests for PDF Template Engine.

Tests the full pipeline from templates to rendering.
"""

import pytest
import tempfile
from pathlib import Path

# Skip if reportlab not available
pytest.importorskip("reportlab")


class TestPdfTemplateImports:
    """Test PDF template module imports."""

    def test_pdf_renderer_import(self):
        """Test that PdfRenderer can be imported."""
        from core.pdf_engine import PdfRenderer, create_pdf_template

        assert PdfRenderer is not None
        assert create_pdf_template is not None

    def test_all_exports_available(self):
        """Test that all module exports are available."""
        from core.pdf_engine import (
            PdfRenderer,
            FontManager,
            StyleBuilder,
            PdfTemplate,
            TemplateType,
            PageSpec,
            FontSpec,
            ParagraphSpec,
            HeaderFooterSpec,
            TocSpec,
            create_pdf_template,
            EbookPdfTemplate,
            AcademicPdfTemplate,
            BusinessPdfTemplate,
        )

        assert PdfRenderer is not None
        assert FontManager is not None
        assert StyleBuilder is not None


class TestPdfTemplates:
    """Test PDF template creation and configuration."""

    def test_create_ebook_template(self):
        """Test creating ebook template."""
        from core.pdf_engine import create_pdf_template, TemplateType

        template = create_pdf_template('ebook')
        assert template is not None
        assert template.name == "Ebook PDF"
        assert template.template_type == TemplateType.EBOOK

    def test_create_academic_template(self):
        """Test creating academic template."""
        from core.pdf_engine import create_pdf_template, TemplateType

        template = create_pdf_template('academic')
        assert template is not None
        assert template.name == "Academic PDF"
        assert template.template_type == TemplateType.ACADEMIC

    def test_create_business_template(self):
        """Test creating business template."""
        from core.pdf_engine import create_pdf_template, TemplateType

        template = create_pdf_template('business')
        assert template is not None
        assert template.name == "Business PDF"
        assert template.template_type == TemplateType.BUSINESS

    def test_invalid_template_raises_error(self):
        """Test that invalid template name raises ValueError."""
        from core.pdf_engine import create_pdf_template

        with pytest.raises(ValueError):
            create_pdf_template('invalid_template')


class TestPdfTemplateSpecs:
    """Test template specifications."""

    def test_ebook_page_spec(self):
        """Test ebook template uses trade paperback size."""
        from core.pdf_engine import create_pdf_template
        from reportlab.lib.units import cm

        template = create_pdf_template('ebook')
        page_spec = template.get_page_spec()

        # Trade paperback is 14 x 21.5 cm
        assert abs(page_spec.width - 14*cm) < 1
        assert abs(page_spec.height - 21.5*cm) < 1

    def test_academic_page_spec(self):
        """Test academic template uses A4 size."""
        from core.pdf_engine import create_pdf_template
        from reportlab.lib.pagesizes import A4

        template = create_pdf_template('academic')
        page_spec = template.get_page_spec()

        # A4 dimensions
        assert abs(page_spec.width - A4[0]) < 1
        assert abs(page_spec.height - A4[1]) < 1

    def test_business_narrow_margins(self):
        """Test business template has narrower margins."""
        from core.pdf_engine import create_pdf_template
        from reportlab.lib.units import cm

        template = create_pdf_template('business')
        page_spec = template.get_page_spec()

        # Business should have 1.5cm side margins
        assert abs(page_spec.left_margin - 1.5*cm) < 0.1*cm
        assert abs(page_spec.right_margin - 1.5*cm) < 0.1*cm

    def test_templates_have_required_styles(self):
        """Test that templates have all required styles."""
        from core.pdf_engine import create_pdf_template

        required_styles = [
            'title', 'subtitle', 'author',
            'heading_1', 'heading_2', 'heading_3',
            'body', 'body_first',
            'quote', 'code', 'list_item', 'caption',
            'toc_title', 'toc_1', 'toc_2', 'toc_3',
            'glossary_term', 'glossary_def',
        ]

        for template_name in ['ebook', 'academic', 'business']:
            template = create_pdf_template(template_name)
            styles = template.get_styles()

            for style_name in required_styles:
                assert style_name in styles, f"Missing style '{style_name}' in {template_name}"


class TestFontManager:
    """Test font management."""

    def test_font_manager_creation(self):
        """Test FontManager can be created."""
        from core.pdf_engine import FontManager

        manager = FontManager()
        assert manager is not None
        assert len(manager.search_paths) > 0

    def test_font_manager_with_custom_paths(self):
        """Test FontManager with custom search paths."""
        from core.pdf_engine import FontManager

        custom_paths = ['/custom/path1', '/custom/path2']
        manager = FontManager(additional_paths=custom_paths)

        for path in custom_paths:
            assert path in manager.search_paths


class TestStyleBuilder:
    """Test style building."""

    def test_style_builder_creation(self):
        """Test StyleBuilder can be created."""
        from core.pdf_engine import StyleBuilder, create_pdf_template

        template = create_pdf_template('ebook')
        builder = StyleBuilder(template)

        assert builder is not None

    def test_build_all_styles(self):
        """Test building all styles from template."""
        from core.pdf_engine import StyleBuilder, create_pdf_template
        from reportlab.lib.styles import ParagraphStyle

        template = create_pdf_template('ebook')
        builder = StyleBuilder(template)
        styles = builder.build_all_styles()

        assert len(styles) > 0
        for name, style in styles.items():
            assert isinstance(style, ParagraphStyle)

    def test_get_specific_style(self):
        """Test getting a specific style."""
        from core.pdf_engine import StyleBuilder, create_pdf_template
        from reportlab.lib.styles import ParagraphStyle

        template = create_pdf_template('academic')
        builder = StyleBuilder(template)
        builder.build_all_styles()

        body_style = builder.get_style('body')
        assert isinstance(body_style, ParagraphStyle)


class TestPdfRenderer:
    """Test PDF rendering."""

    def test_renderer_creation(self):
        """Test PdfRenderer can be created."""
        from core.pdf_engine import PdfRenderer

        for template_name in ['ebook', 'academic', 'business']:
            renderer = PdfRenderer(template=template_name)
            assert renderer is not None
            assert renderer.template is not None

    def test_render_markdown(self):
        """Test rendering markdown to PDF."""
        from core.pdf_engine import PdfRenderer

        markdown_content = """# Test Document

## Introduction

This is a test paragraph with some **bold** and *italic* text.

### Section 1

- Item 1
- Item 2
- Item 3

## Conclusion

Final paragraph here.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            for template_name in ['ebook', 'academic', 'business']:
                output_path = Path(tmpdir) / f"test_{template_name}.pdf"

                renderer = PdfRenderer(template=template_name)
                result = renderer.render_markdown(
                    markdown_content=markdown_content,
                    output_path=str(output_path),
                    title="Test Document",
                    author="Test Author"
                )

                assert result.exists(), f"PDF not created for {template_name}"
                assert result.stat().st_size > 0, f"PDF is empty for {template_name}"


class TestOutputConverterPdfIntegration:
    """Test OutputConverter PDF integration."""

    def test_output_converter_has_pdf_methods(self):
        """Test that OutputConverter has PDF professional methods."""
        from core_v2.output_converter import OutputConverter

        converter = OutputConverter()
        assert hasattr(converter, 'convert_to_pdf_professional')
        assert hasattr(converter, 'convert_markdown_to_pdf_professional')

    @pytest.mark.asyncio
    async def test_convert_markdown_to_pdf_professional(self):
        """Test the professional PDF conversion method."""
        from core_v2.output_converter import OutputConverter

        converter = OutputConverter()

        markdown_content = """# Test

This is a test document.

## Section 1

Some content here.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_professional.pdf"

            result = await converter.convert_markdown_to_pdf_professional(
                markdown_content=markdown_content,
                output_path=output_path,
                template="ebook",
                title="Test Doc",
                author="Test Author"
            )

            assert result.exists()
            assert result.stat().st_size > 0


class TestPdfTemplateStyles:
    """Test that templates produce distinct styling."""

    def test_ebook_uses_serif_font(self):
        """Test ebook template uses DejaVu Serif."""
        from core.pdf_engine import create_pdf_template

        template = create_pdf_template('ebook')
        fonts = template.get_fonts()

        assert 'DejaVuSerif' in fonts.get('regular', '')

    def test_business_uses_sans_font(self):
        """Test business template uses DejaVu Sans."""
        from core.pdf_engine import create_pdf_template

        template = create_pdf_template('business')
        fonts = template.get_fonts()

        assert 'DejaVuSans' in fonts.get('regular', '')

    def test_templates_have_different_chapter_breaks(self):
        """Test that templates have different chapter break settings."""
        from core.pdf_engine import create_pdf_template

        ebook = create_pdf_template('ebook')
        business = create_pdf_template('business')

        # Ebook should have page breaks between chapters
        assert ebook.get_chapter_break() == 'page'

        # Business should have no page breaks (continuous)
        assert business.get_chapter_break() == 'none'


class TestVietnameseSupport:
    """Test Vietnamese language support."""

    def test_vietnamese_content_renders(self):
        """Test that Vietnamese content can be rendered."""
        from core.pdf_engine import PdfRenderer

        vietnamese_content = """# Tài liệu Tiếng Việt

## Giới thiệu

Đây là một đoạn văn bản tiếng Việt với các ký tự đặc biệt như:
ă, â, đ, ê, ô, ơ, ư, á, à, ả, ã, ạ.

### Danh sách

- Mục một
- Mục hai
- Mục ba

## Kết luận

Cảm ơn bạn đã đọc.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "vietnamese_test.pdf"

            renderer = PdfRenderer(template='ebook')
            result = renderer.render_markdown(
                markdown_content=vietnamese_content,
                output_path=str(output_path),
                title="Tài liệu Tiếng Việt",
                author="Tác giả"
            )

            assert result.exists()
            assert result.stat().st_size > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
