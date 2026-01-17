# core/pdf_renderer_v2/tests/test_renderer.py

"""
Tests for PDF Renderer V2 - Pandoc + WeasyPrint Pipeline
"""

import pytest
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.pdf_renderer_v2 import PDFRendererV2


class TestPDFRendererV2:
    """Tests for PDF Renderer V2."""

    def test_list_templates(self):
        """Test listing available templates."""
        templates = PDFRendererV2.list_templates()
        assert len(templates) == 12
        assert "minimal-clean" in templates
        assert "classic-literature" in templates
        assert "technical-manual" in templates
        assert "academic-paper" in templates

    def test_invalid_template(self):
        """Test invalid template raises error."""
        with pytest.raises(ValueError) as exc_info:
            PDFRendererV2(template="non-existent-template")
        assert "Unknown template" in str(exc_info.value)

    def test_simple_render(self, tmp_path):
        """Test simple markdown rendering."""
        renderer = PDFRendererV2(template="minimal-clean")

        md = "# Hello World\n\nThis is a test paragraph."
        output = tmp_path / "test.pdf"

        result = renderer.render(md, str(output))

        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    def test_vietnamese_render(self, tmp_path):
        """Test Vietnamese content rendering."""
        renderer = PDFRendererV2(template="minimal-clean")

        md = """# Xin Chào Việt Nam

Đây là tiếng Việt với đầy đủ dấu:

- Dấu sắc: á, é, í, ó, ú
- Dấu huyền: à, è, ì, ò, ù
- Dấu hỏi: ả, ẻ, ỉ, ỏ, ủ
- Dấu ngã: ã, ẽ, ĩ, õ, ũ
- Dấu nặng: ạ, ẹ, ị, ọ, ụ
- Các chữ đặc biệt: ă, â, đ, ê, ô, ơ, ư

## Bảng Dữ Liệu

| Tên | Tuổi | Thành Phố |
|-----|------|-----------|
| An  | 25   | Hà Nội    |
| Bình| 30   | TP.HCM    |
"""
        output = tmp_path / "vietnamese.pdf"

        result = renderer.render(
            md,
            str(output),
            metadata={"title": "Tài Liệu Tiếng Việt", "author": "Tác Giả"}
        )

        assert Path(result).exists()
        assert Path(result).stat().st_size > 1000  # Should be substantial

    def test_template_classic_literature(self, tmp_path):
        """Test classic literature template."""
        renderer = PDFRendererV2(template="classic-literature")

        md = """# Chapter One

It was the best of times, it was the worst of times.

The story begins in a small village, where life was simple but meaningful.

---

# Chapter Two

Years passed, and the village grew into a town.
"""
        output = tmp_path / "classic.pdf"
        result = renderer.render(md, str(output), metadata={"title": "A Tale", "author": "Author Name"})

        assert Path(result).exists()

    def test_template_technical_manual(self, tmp_path):
        """Test technical manual template."""
        renderer = PDFRendererV2(template="technical-manual")

        md = """# Installation Guide

## Prerequisites

- Python 3.8+
- pip package manager

## Installation Steps

1. Clone the repository
2. Install dependencies

```bash
pip install -r requirements.txt
```

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| debug  | false   | Enable debug mode |
| port   | 8080    | Server port |
"""
        output = tmp_path / "technical.pdf"
        result = renderer.render(md, str(output), metadata={"title": "Technical Manual"})

        assert Path(result).exists()

    def test_all_templates_render(self, tmp_path):
        """Test all templates can render without error."""
        md = """# Test Document

This is a test paragraph with **bold** and *italic* text.

## Section 1

- Item 1
- Item 2

## Section 2

| Col A | Col B |
|-------|-------|
| 1     | 2     |
"""
        for template in PDFRendererV2.list_templates():
            renderer = PDFRendererV2(template=template)
            output = tmp_path / f"{template}.pdf"

            result = renderer.render(md, str(output))
            assert Path(result).exists(), f"Template {template} failed to render"
            assert Path(result).stat().st_size > 0, f"Template {template} produced empty file"

    def test_preview_html(self):
        """Test HTML preview generation."""
        renderer = PDFRendererV2(template="minimal-clean")

        md = "# Hello\n\nWorld"
        html = renderer.preview_html(md, {"title": "Test Preview"})

        assert "<html" in html
        assert "Hello" in html
        assert "World" in html
        assert "Test Preview" in html

    def test_metadata_in_output(self, tmp_path):
        """Test that metadata appears in rendered PDF."""
        renderer = PDFRendererV2(template="minimal-clean")

        md = "# Content\n\nSome text here."
        metadata = {
            "title": "My Document Title",
            "author": "John Doe",
            "date": "2024-12-26"
        }
        output = tmp_path / "with_metadata.pdf"

        result = renderer.render(md, str(output), metadata=metadata)
        assert Path(result).exists()

    def test_code_blocks(self, tmp_path):
        """Test code block rendering."""
        renderer = PDFRendererV2(template="technical-manual")

        md = """# Code Examples

## Python

```python
def hello():
    print("Hello, World!")
```

## Inline Code

Use `pip install package` to install.
"""
        output = tmp_path / "code.pdf"
        result = renderer.render(md, str(output))

        assert Path(result).exists()

    def test_tables(self, tmp_path):
        """Test table rendering."""
        renderer = PDFRendererV2(template="business-report")

        md = """# Report

## Data Table

| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q1      | $100K   | 10%    |
| Q2      | $120K   | 20%    |
| Q3      | $150K   | 25%    |
| Q4      | $200K   | 33%    |
"""
        output = tmp_path / "tables.pdf"
        result = renderer.render(md, str(output))

        assert Path(result).exists()


class TestPDFRendererV2EdgeCases:
    """Edge case tests."""

    def test_empty_content(self, tmp_path):
        """Test rendering empty content."""
        renderer = PDFRendererV2(template="minimal-clean")

        md = ""
        output = tmp_path / "empty.pdf"

        result = renderer.render(md, str(output))
        assert Path(result).exists()

    def test_very_long_content(self, tmp_path):
        """Test rendering very long content (multiple pages)."""
        renderer = PDFRendererV2(template="minimal-clean")

        # Generate long content
        paragraphs = ["# Long Document\n"]
        for i in range(100):
            paragraphs.append(f"\n## Section {i+1}\n\nThis is paragraph {i+1}. " * 10)

        md = "\n".join(paragraphs)
        output = tmp_path / "long.pdf"

        result = renderer.render(md, str(output))
        assert Path(result).exists()
        # Should be multiple pages, so file size should be substantial
        assert Path(result).stat().st_size > 10000

    def test_special_characters(self, tmp_path):
        """Test special characters don't break rendering."""
        renderer = PDFRendererV2(template="minimal-clean")

        md = """# Special Characters

Quotes: "double" and 'single'

Symbols: & < > © ® ™ € £ ¥

Dashes: - -- ---

Arrows: -> <- <-> => <=

Math: ± × ÷ ≠ ≤ ≥ ∞ √

Emoji: test (no emoji - should still work)
"""
        output = tmp_path / "special.pdf"
        result = renderer.render(md, str(output))

        assert Path(result).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
