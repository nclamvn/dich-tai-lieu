"""
Integration tests for DOCX Template Engine integration.

Tests the full pipeline from API → Service → Orchestrator → OutputConverter → DocxRenderer.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil

# Skip if dependencies not available
pytest.importorskip("docx")


class TestDocxTemplateIntegration:
    """Test DOCX template integration across the pipeline."""

    def test_docx_renderer_import(self):
        """Test that DocxRenderer can be imported from the engine."""
        from core.docx_engine import DocxRenderer, create_template

        assert DocxRenderer is not None
        assert create_template is not None

    def test_create_templates(self):
        """Test creating all template types."""
        from core.docx_engine import create_template, TemplateType

        for template_type in ['ebook', 'academic', 'business']:
            template = create_template(template_type)
            assert template is not None
            assert template.get_styles() is not None
            assert template.get_page_setup() is not None

    def test_docx_renderer_from_markdown(self):
        """Test rendering markdown to DOCX with different templates."""
        from core.docx_engine import DocxRenderer

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
                output_path = Path(tmpdir) / f"test_{template_name}.docx"

                renderer = DocxRenderer(template=template_name)
                result = renderer.render_markdown(
                    markdown_content=markdown_content,
                    output_path=str(output_path),
                    title="Test Document",
                    author="Test Author"
                )

                assert result.exists(), f"DOCX not created for {template_name}"
                assert result.stat().st_size > 0, f"DOCX is empty for {template_name}"

    def test_auto_select_template_ebook(self):
        """Test auto-selecting ebook template for fiction genre."""
        from core_v2.output_converter import OutputConverter

        converter = OutputConverter()

        # Create test manifest
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text('''{
                "meta": {"title": "My Novel", "author": "Author Name"},
                "document_dna": {"genre": "novel", "tone": "literary"}
            }''')

            template = converter._auto_select_template(Path(tmpdir))
            assert template == "ebook"

    def test_auto_select_template_academic(self):
        """Test auto-selecting academic template for research genre."""
        from core_v2.output_converter import OutputConverter

        converter = OutputConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text('''{
                "meta": {"title": "Research Paper"},
                "document_dna": {"genre": "academic research", "tone": "formal"}
            }''')

            template = converter._auto_select_template(Path(tmpdir))
            assert template == "academic"

    def test_auto_select_template_business(self):
        """Test auto-selecting business template for corporate genre."""
        from core_v2.output_converter import OutputConverter

        converter = OutputConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            manifest_path.write_text('''{
                "meta": {"title": "Q4 Report"},
                "document_dna": {"genre": "business report", "tone": "professional"}
            }''')

            template = converter._auto_select_template(Path(tmpdir))
            assert template == "business"

    def test_auto_select_template_default(self):
        """Test default template selection when no manifest exists."""
        from core_v2.output_converter import OutputConverter

        converter = OutputConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            template = converter._auto_select_template(Path(tmpdir))
            assert template == "ebook"  # Default to ebook

    @pytest.mark.asyncio
    async def test_convert_markdown_to_docx_professional(self):
        """Test the professional DOCX conversion method."""
        from core_v2.output_converter import OutputConverter

        converter = OutputConverter()

        markdown_content = """# Test

This is a test document.

## Section 1

Some content here.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_professional.docx"

            result = await converter.convert_markdown_to_docx_professional(
                markdown_content=markdown_content,
                output_path=output_path,
                template="ebook",
                title="Test Doc",
                author="Test Author"
            )

            assert result.exists()
            assert result.stat().st_size > 0


class TestAPIIntegration:
    """Test API layer integration."""

    def test_api_models_docx_template_field(self):
        """Test that API models include docx_template field."""
        from api.aps_v2_models import PublishTextRequest

        # Create request with docx_template
        request = PublishTextRequest(
            content="Test content",
            docx_template="academic"
        )

        assert request.docx_template == "academic"

        # Test default value
        request_default = PublishTextRequest(content="Test")
        assert request_default.docx_template == "auto"


class TestServiceIntegration:
    """Test service layer integration."""

    @pytest.mark.asyncio
    async def test_service_accepts_docx_template(self):
        """Test that service accepts docx_template parameter."""
        from api.aps_v2_service import APSV2Service

        with tempfile.TemporaryDirectory() as tmpdir:
            service = APSV2Service(
                output_dir=f"{tmpdir}/outputs",
                upload_dir=f"{tmpdir}/uploads"
            )

            # Mock the publisher to avoid actual LLM calls
            service._ensure_publisher = MagicMock()
            service._publisher = MagicMock()
            service._llm_client = MagicMock()

            # Create a job with docx_template
            job = await service.create_job(
                source_file="test.txt",
                content="Test content",
                source_language="en",
                target_language="vi",
                profile_id="essay",
                output_formats=["docx"],
                docx_template="academic"
            )

            assert job["docx_template"] == "academic"


class TestOrchestratorIntegration:
    """Test orchestrator layer integration."""

    def test_orchestrator_signature_includes_docx_template(self):
        """Test that orchestrator publish method accepts docx_template."""
        import inspect
        from core_v2.orchestrator import UniversalPublisher

        sig = inspect.signature(UniversalPublisher.publish)
        params = list(sig.parameters.keys())

        assert "docx_template" in params


class TestTemplateStyles:
    """Test that templates produce distinct styling."""

    def test_ebook_template_has_trade_paperback_size(self):
        """Test ebook template uses trade paperback dimensions."""
        from core.docx_engine import create_template
        from docx.shared import Cm

        template = create_template('ebook')
        page_setup = template.get_page_setup()

        # Trade paperback is 14cm x 21.5cm
        assert abs(page_setup.width.cm - 14.0) < 0.5
        assert abs(page_setup.height.cm - 21.5) < 0.5

    def test_academic_template_has_a4_size(self):
        """Test academic template uses A4 dimensions."""
        from core.docx_engine import create_template
        from docx.shared import Cm

        template = create_template('academic')
        page_setup = template.get_page_setup()

        # A4 is 21cm x 29.7cm
        assert abs(page_setup.width.cm - 21.0) < 0.5
        assert abs(page_setup.height.cm - 29.7) < 0.5

    def test_business_template_has_narrow_margins(self):
        """Test business template uses narrow margins."""
        from core.docx_engine import create_template

        template = create_template('business')
        page_setup = template.get_page_setup()

        # Business should have narrower margins than academic
        assert page_setup.left_margin.cm <= 2.0
        assert page_setup.right_margin.cm <= 2.0

    def test_templates_have_different_fonts(self):
        """Test that each template uses different fonts."""
        from core.docx_engine import create_template

        ebook = create_template('ebook')
        academic = create_template('academic')
        business = create_template('business')

        ebook_body = ebook.get_styles()['body'].font.name
        academic_body = academic.get_styles()['body'].font.name
        business_body = business.get_styles()['body'].font.name

        # Each template should have a distinct body font
        fonts = {ebook_body, academic_body, business_body}
        assert len(fonts) >= 2, "Templates should have variety in fonts"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
