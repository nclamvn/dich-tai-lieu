"""Tests for core_v2/output_converter.py — OutputConverter and OutputFormat."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core_v2.output_converter import OutputConverter, OutputFormat


# ==================== OutputFormat Enum ====================


class TestOutputFormat:
    """OutputFormat enum values."""

    def test_all_formats_exist(self):
        expected = {"docx", "pdf", "epub", "html", "latex", "md"}
        actual = {f.value for f in OutputFormat}
        assert expected == actual

    def test_format_from_string(self):
        assert OutputFormat("docx") == OutputFormat.DOCX
        assert OutputFormat("pdf") == OutputFormat.PDF
        assert OutputFormat("md") == OutputFormat.MARKDOWN


# ==================== OutputConverter Initialization ====================


class TestOutputConverterInit:
    """OutputConverter creation and dependency detection."""

    def test_default_temp_dir(self):
        converter = OutputConverter()
        assert converter.temp_dir.exists()

    def test_custom_temp_dir(self, tmp_path):
        custom = tmp_path / "my_temp"
        converter = OutputConverter(temp_dir=custom)
        assert converter.temp_dir == custom
        assert custom.exists()

    def test_dependency_detection(self):
        converter = OutputConverter()
        assert isinstance(converter.has_pandoc, bool)
        assert isinstance(converter.has_pdflatex, bool)
        assert isinstance(converter.has_xelatex, bool)


# ==================== get_supported_formats ====================


class TestSupportedFormats:
    """get_supported_formats based on available tools."""

    def test_always_includes_md_and_html(self):
        converter = OutputConverter()
        formats = converter.get_supported_formats()
        assert "md" in formats
        assert "html" in formats

    def test_includes_docx_when_pandoc_available(self):
        converter = OutputConverter()
        if converter.has_pandoc:
            assert "docx" in converter.get_supported_formats()


# ==================== Markdown Output ====================


class TestMarkdownOutput:
    """Direct markdown output (no external deps needed)."""

    @pytest.mark.asyncio
    async def test_convert_to_markdown(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "temp")
        output = tmp_path / "output.md"
        content = "# Title\n\nSome content here."

        result = await converter.convert(
            content=content,
            output_format=OutputFormat.MARKDOWN,
            output_path=output,
            title="Test",
        )
        assert result is True
        assert output.exists()
        assert output.read_text() == content

    @pytest.mark.asyncio
    async def test_convert_markdown_with_formulas(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "temp")
        output = tmp_path / "output.md"
        content = "Formula: $E=mc^2$"

        result = await converter.convert(
            content=content,
            output_format=OutputFormat.MARKDOWN,
            output_path=output,
            has_formulas=True,
        )
        assert result is True
        assert "$E=mc^2$" in output.read_text()


# ==================== LaTeX Output ====================


class TestLatexOutput:
    """LaTeX file output."""

    @pytest.mark.asyncio
    async def test_convert_to_latex(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "temp")
        output = tmp_path / "output.tex"
        content = "Some math: $x^2$"

        result = await converter.convert(
            content=content,
            output_format=OutputFormat.LATEX,
            output_path=output,
            title="Math Paper",
            has_formulas=True,
        )
        assert result is True
        assert output.exists()
        tex_content = output.read_text()
        assert "\\begin{document}" in tex_content
        assert "Math Paper" in tex_content

    @pytest.mark.asyncio
    async def test_full_latex_passthrough(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "temp")
        output = tmp_path / "output.tex"
        content = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"

        result = await converter.convert(
            content=content,
            output_format=OutputFormat.LATEX,
            output_path=output,
            has_formulas=True,
        )
        assert result is True
        assert "\\documentclass{article}" in output.read_text()


# ==================== HTML Fallback ====================


class TestHTMLFallback:
    """HTML conversion fallback when pandoc is absent."""

    @pytest.mark.asyncio
    async def test_html_fallback_without_pandoc(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "temp")
        converter.has_pandoc = False
        output = tmp_path / "output.html"

        result = await converter.convert(
            content="<h1>Hello</h1><p>World</p>",
            output_format=OutputFormat.HTML,
            output_path=output,
        )
        assert result is True
        assert output.exists()
        html = output.read_text()
        assert "<!DOCTYPE html>" in html
        assert "Hello" in html


# ==================== _wrap_latex_document ====================


class TestWrapLatexDocument:
    """LaTeX document wrapper."""

    def test_includes_title_and_author(self):
        converter = OutputConverter()
        doc = converter._wrap_latex_document("Body text", "My Title", "Author Name")
        assert "\\title{My Title}" in doc
        assert "\\author{Author Name}" in doc
        assert "\\begin{document}" in doc
        assert "Body text" in doc
        assert "\\end{document}" in doc

    def test_includes_ams_packages(self):
        converter = OutputConverter()
        doc = converter._wrap_latex_document("x", "T", "A")
        assert "amsmath" in doc
        assert "amssymb" in doc

    def test_no_title_author(self):
        converter = OutputConverter()
        doc = converter._wrap_latex_document("Body", None, None)
        assert "\\begin{document}" in doc
        assert "\\maketitle" not in doc


# ==================== Source Format Detection ====================


class TestSourceFormatDetection:
    """Detection of LaTeX vs Markdown source."""

    @pytest.mark.asyncio
    async def test_detects_full_latex(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "temp")
        output = tmp_path / "output.md"
        content = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}"

        # Convert to markdown should passthrough for formula content
        result = await converter.convert(
            content=content,
            output_format=OutputFormat.MARKDOWN,
            output_path=output,
            has_formulas=True,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_markdown_with_math(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "temp")
        output = tmp_path / "output.md"
        content = "# Title\n\nFormula: $x^2 + y^2 = z^2$"

        result = await converter.convert(
            content=content,
            output_format=OutputFormat.MARKDOWN,
            output_path=output,
            has_formulas=True,
        )
        assert result is True


# ==================== _auto_select_template ====================


class TestAutoSelectTemplate:
    """Template auto-selection from manifest."""

    def test_academic_genre(self, tmp_path):
        import json
        manifest = {"metadata": {}, "document_dna": {"genre": "academic_paper"}}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        converter = OutputConverter()
        result = converter._auto_select_template(tmp_path)
        assert result == "academic"

    def test_business_genre(self, tmp_path):
        import json
        manifest = {"metadata": {}, "document_dna": {"genre": "business_report"}}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        converter = OutputConverter()
        result = converter._auto_select_template(tmp_path)
        assert result == "business"

    def test_fiction_genre(self, tmp_path):
        import json
        manifest = {"metadata": {}, "document_dna": {"genre": "novel"}}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        converter = OutputConverter()
        result = converter._auto_select_template(tmp_path)
        assert result == "ebook"

    def test_missing_manifest_defaults_ebook(self, tmp_path):
        converter = OutputConverter()
        result = converter._auto_select_template(tmp_path)
        assert result == "ebook"

    def test_unknown_genre_defaults_ebook(self, tmp_path):
        import json
        manifest = {"metadata": {}, "document_dna": {"genre": "unknown_genre"}}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        converter = OutputConverter()
        result = converter._auto_select_template(tmp_path)
        assert result == "ebook"


# ==================== Cleanup ====================


class TestCleanup:
    """cleanup() method."""

    def test_cleanup_removes_temp_files(self, tmp_path):
        temp_dir = tmp_path / "converter_temp"
        converter = OutputConverter(temp_dir=temp_dir)
        # Create some temp files
        (temp_dir / "test1.txt").write_text("temp")
        (temp_dir / "test2.txt").write_text("temp")
        assert len(list(temp_dir.iterdir())) == 2

        converter.cleanup()
        assert len(list(temp_dir.iterdir())) == 0

    def test_cleanup_handles_empty_dir(self, tmp_path):
        converter = OutputConverter(temp_dir=tmp_path / "empty_temp")
        converter.cleanup()  # Should not raise
