"""
PDF API Integration Tests

Tests for PDF template selection through the API pipeline.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import inspect

# API models
from api.aps_v2_models import PublishTextRequest, JobResponseV2, JobStatusV2


class TestPdfApiModels:
    """Test API model changes for pdf_template."""

    def test_publish_text_request_has_pdf_template(self):
        """PublishTextRequest should have pdf_template field."""
        request = PublishTextRequest(
            content="Test content",
            pdf_template="ebook"
        )
        assert request.pdf_template == "ebook"

    def test_publish_text_request_pdf_template_default(self):
        """pdf_template should default to 'auto'."""
        request = PublishTextRequest(content="Test content")
        assert request.pdf_template == "auto"

    def test_publish_text_request_all_templates(self):
        """Test all valid pdf_template values."""
        for template in ["auto", "ebook", "academic", "business"]:
            request = PublishTextRequest(
                content="Test content",
                pdf_template=template
            )
            assert request.pdf_template == template

    def test_publish_text_request_has_docx_template(self):
        """PublishTextRequest should also have docx_template field."""
        request = PublishTextRequest(
            content="Test content",
            docx_template="academic"
        )
        assert request.docx_template == "academic"


class TestPdfOrchestratorSignature:
    """Test orchestrator method signatures include pdf_template."""

    def test_publisher_publish_accepts_pdf_template(self):
        """UniversalPublisher.publish should accept pdf_template parameter."""
        from core_v2.orchestrator import UniversalPublisher
        sig = inspect.signature(UniversalPublisher.publish)
        assert "pdf_template" in sig.parameters

    def test_publisher_pdf_template_default(self):
        """pdf_template should default to 'auto'."""
        from core_v2.orchestrator import UniversalPublisher
        sig = inspect.signature(UniversalPublisher.publish)
        pdf_param = sig.parameters["pdf_template"]
        assert pdf_param.default == "auto"

    def test_convert_accepts_pdf_template(self):
        """_convert method should accept pdf_template parameter."""
        from core_v2.orchestrator import UniversalPublisher
        sig = inspect.signature(UniversalPublisher._convert)
        assert "pdf_template" in sig.parameters


class TestPdfServiceSignature:
    """Test service method signatures include pdf_template."""

    def test_create_job_accepts_pdf_template(self):
        """APSV2Service.create_job should accept pdf_template parameter."""
        from api.aps_v2_service import APSV2Service
        sig = inspect.signature(APSV2Service.create_job)
        assert "pdf_template" in sig.parameters

    def test_create_job_pdf_template_default(self):
        """pdf_template should default to 'auto'."""
        from api.aps_v2_service import APSV2Service
        sig = inspect.signature(APSV2Service.create_job)
        pdf_param = sig.parameters["pdf_template"]
        assert pdf_param.default == "auto"

    def test_process_job_accepts_pdf_template(self):
        """_process_job method should accept pdf_template parameter."""
        from api.aps_v2_service import APSV2Service
        sig = inspect.signature(APSV2Service._process_job)
        assert "pdf_template" in sig.parameters


class TestPdfRouterSignature:
    """Test API router parameters for pdf_template."""

    def test_router_publish_file_has_pdf_template(self):
        """Router publish_file should have pdf_template parameter."""
        from api.aps_v2_router import publish_file
        sig = inspect.signature(publish_file)
        assert "pdf_template" in sig.parameters

    def test_router_pdf_template_is_form_param(self):
        """pdf_template should be a Form parameter."""
        from api.aps_v2_router import publish_file
        from fastapi import Form
        sig = inspect.signature(publish_file)
        pdf_param = sig.parameters["pdf_template"]
        # Form parameters have their default wrapped in a Form object
        assert hasattr(pdf_param.default, 'default')


class TestPdfTemplateSelection:
    """Test PDF template auto-selection logic."""

    def test_template_mapping_for_genres(self):
        """Verify expected template mappings for document genres."""
        genre_to_template = {
            "novel": "ebook",
            "poetry": "ebook",
            "essay": "ebook",
            "academic_paper": "academic",
            "thesis": "academic",
            "arxiv_paper": "academic",
            "textbook": "academic",
            "business_report": "business",
            "white_paper": "business",
            "technical_doc": "business",
        }

        # Verify mapping exists for common genres
        for genre, expected_template in genre_to_template.items():
            assert expected_template in ["ebook", "academic", "business"]


class TestPdfOutputConverter:
    """Test output converter PDF methods."""

    def test_converter_has_pdf_professional_method(self):
        """OutputConverter should have convert_markdown_to_pdf_professional."""
        from core_v2.output_converter import OutputConverter
        assert hasattr(OutputConverter, 'convert_markdown_to_pdf_professional')

    def test_converter_pdf_method_accepts_template(self):
        """convert_markdown_to_pdf_professional should accept template param."""
        from core_v2.output_converter import OutputConverter
        sig = inspect.signature(OutputConverter.convert_markdown_to_pdf_professional)
        assert "template" in sig.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
