"""
Unit tests for api/services/converter.py — target 85%+ coverage.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from api.services.converter import (
    get_media_type,
    convert_to_markdown,
    convert_to_txt,
    convert_to_pdf,
    convert_document_format,
)


# ---------------------------------------------------------------------------
# get_media_type
# ---------------------------------------------------------------------------

class TestGetMediaType:
    def test_known_formats(self):
        assert get_media_type("docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert get_media_type("pdf") == "application/pdf"
        assert get_media_type("txt") == "text/plain"
        assert get_media_type("html") == "text/html"
        assert get_media_type("md") == "text/markdown"
        assert get_media_type("srt") == "text/plain"

    def test_unknown_format(self):
        assert get_media_type("xyz") == "application/octet-stream"


# ---------------------------------------------------------------------------
# convert_to_markdown
# ---------------------------------------------------------------------------

class TestConvertToMarkdown:
    def _mock_doc(self, paragraphs):
        """paragraphs: list of (text, style_name) tuples."""
        doc = MagicMock()
        paras = []
        for text, style in paragraphs:
            p = MagicMock()
            p.text = text
            if style:
                p.style = MagicMock()
                p.style.name = style
            else:
                p.style = None
            paras.append(p)
        doc.paragraphs = paras
        return doc

    def test_normal_text(self, tmp_path):
        target = tmp_path / "out.md"
        with patch("docx.Document", return_value=self._mock_doc([
            ("Hello world", "Normal"),
        ])):
            result = convert_to_markdown(tmp_path / "in.docx", target)
        assert result == target
        content = target.read_text()
        assert "Hello world" in content

    def test_heading_styles(self, tmp_path):
        target = tmp_path / "out.md"
        with patch("docx.Document", return_value=self._mock_doc([
            ("Title", "Title"),
            ("Chapter", "Heading 1"),
            ("Section", "Heading 2"),
            ("Subsection", "Heading 3"),
            ("Body", "Normal"),
        ])):
            result = convert_to_markdown(tmp_path / "in.docx", target)
        content = result.read_text()
        assert "# Title" in content
        assert "# Chapter" in content
        assert "## Section" in content
        assert "### Subsection" in content
        assert "\nBody\n" in content

    def test_empty_paragraphs(self, tmp_path):
        target = tmp_path / "out.md"
        with patch("docx.Document", return_value=self._mock_doc([
            ("", "Normal"),
            ("After blank", "Normal"),
        ])):
            convert_to_markdown(tmp_path / "in.docx", target)
        content = target.read_text()
        assert "After blank" in content

    def test_no_style_object(self, tmp_path):
        target = tmp_path / "out.md"
        with patch("docx.Document", return_value=self._mock_doc([
            ("No style para", None),
        ])):
            convert_to_markdown(tmp_path / "in.docx", target)
        content = target.read_text()
        assert "No style para" in content


# ---------------------------------------------------------------------------
# convert_to_txt
# ---------------------------------------------------------------------------

class TestConvertToTxt:
    def test_basic_conversion(self, tmp_path):
        target = tmp_path / "out.txt"
        mock_doc = MagicMock()
        p1, p2 = MagicMock(), MagicMock()
        p1.text = "First paragraph"
        p2.text = "Second paragraph"
        mock_doc.paragraphs = [p1, p2]

        with patch("docx.Document", return_value=mock_doc):
            result = convert_to_txt(tmp_path / "in.docx", target)

        assert result == target
        content = target.read_text()
        assert "First paragraph" in content
        assert "Second paragraph" in content
        assert "\n\n" in content  # double-newline separator

    def test_empty_document(self, tmp_path):
        target = tmp_path / "out.txt"
        mock_doc = MagicMock()
        mock_doc.paragraphs = []

        with patch("docx.Document", return_value=mock_doc):
            convert_to_txt(tmp_path / "in.docx", target)

        assert target.read_text() == ""


# ---------------------------------------------------------------------------
# convert_to_pdf
# ---------------------------------------------------------------------------

class TestConvertToPdf:
    def test_libreoffice_success(self, tmp_path):
        target = tmp_path / "out.pdf"
        target.write_text("fake pdf")  # simulate soffice creating it

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = convert_to_pdf(tmp_path / "in.docx", target, tmp_path)

        assert result == target

    def test_libreoffice_fails_reportlab_fallback(self, tmp_path):
        target = tmp_path / "out.pdf"
        mock_doc = MagicMock()
        p = MagicMock()
        p.text = "Hello & <world>"
        mock_doc.paragraphs = [p]

        mock_pdf = MagicMock()

        with patch("subprocess.run", side_effect=FileNotFoundError("soffice not found")), \
             patch("docx.Document", return_value=mock_doc), \
             patch("reportlab.platypus.SimpleDocTemplate", return_value=mock_pdf), \
             patch("reportlab.lib.styles.getSampleStyleSheet") as mock_styles, \
             patch("reportlab.pdfbase.pdfmetrics.registerFont") as mock_register, \
             patch("reportlab.platypus.Paragraph") as MockParagraph, \
             patch("reportlab.platypus.Spacer") as MockSpacer:
            # Font registration fails → Helvetica fallback
            mock_register.side_effect = Exception("no font")
            styles_obj = MagicMock()
            mock_styles.return_value = styles_obj

            result = convert_to_pdf(tmp_path / "in.docx", target, tmp_path)

        assert result == target
        mock_pdf.build.assert_called_once()

    def test_both_methods_fail(self, tmp_path):
        target = tmp_path / "out.pdf"

        with patch("subprocess.run", side_effect=FileNotFoundError), \
             patch("docx.Document", side_effect=Exception("no docx")):
            with pytest.raises(Exception, match="no docx"):
                convert_to_pdf(tmp_path / "in.docx", target, tmp_path)


# ---------------------------------------------------------------------------
# convert_document_format (entry point)
# ---------------------------------------------------------------------------

class TestConvertDocumentFormat:
    @pytest.mark.asyncio
    async def test_dispatch_markdown(self, tmp_path):
        with patch("api.services.converter.convert_to_markdown", return_value=tmp_path / "out.md") as mock:
            result = await convert_document_format(
                tmp_path / "in.docx", "md", tmp_path, "out"
            )
        mock.assert_called_once()
        assert result == tmp_path / "out.md"

    @pytest.mark.asyncio
    async def test_dispatch_txt(self, tmp_path):
        with patch("api.services.converter.convert_to_txt", return_value=tmp_path / "out.txt") as mock:
            result = await convert_document_format(
                tmp_path / "in.docx", "txt", tmp_path, "out"
            )
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_pdf(self, tmp_path):
        with patch("api.services.converter.convert_to_pdf", return_value=tmp_path / "out.pdf") as mock:
            result = await convert_document_format(
                tmp_path / "in.docx", "pdf", tmp_path, "out"
            )
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsupported_format(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported target format"):
            await convert_document_format(
                tmp_path / "in.docx", "xyz", tmp_path, "out"
            )
