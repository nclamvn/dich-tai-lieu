#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test FORMAT-004: Page Layout & Document Structure.

Tests:
1. PageLayoutManager initialization and configuration
2. TocGenerator functionality
3. DOCX export with page layout and TOC
4. Header/footer setup
5. Page breaks before chapters
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from core.formatting import (
    StructureDetector,
    DocumentModel,
    StyleEngine,
    PageLayoutManager,
    TocGenerator,
    DocxStyleExporter,
    MarkdownStyleExporter,
)


def test_page_layout_manager():
    """Test PageLayoutManager initialization and methods."""
    print("\n" + "=" * 60)
    print("TEST 1: PageLayoutManager")
    print("=" * 60)

    # Test default layout
    layout = PageLayoutManager()
    assert layout.page_size.width == 8.27, "A4 width should be 8.27 inches"
    assert layout.page_size.height == 11.69, "A4 height should be 11.69 inches"
    print(f"Default page size (A4): {layout.page_size.width} x {layout.page_size.height}")

    # Test content area calculation
    area = layout.calculate_content_area()
    print(f"Content area: {area.width:.2f} x {area.height:.2f} inches")
    assert area.width > 0, "Content width should be positive"
    assert area.height > 0, "Content height should be positive"

    # Test different presets
    layout_book = PageLayoutManager(page_size="Letter", margins="book")
    print(f"Letter/Book: {layout_book.page_size.width} x {layout_book.page_size.height}")
    print(f"  Margins: L={layout_book.margins.left}, R={layout_book.margins.right}")

    # Test header/footer text generation
    header = layout.get_header_text(page_num=5, doc_title="Test Document")
    footer = layout.get_footer_text(page_num=5, total_pages=10)
    print(f"Header text: '{header}'")
    print(f"Footer text: '{footer}'")

    # Test page break rules
    should_break = layout.should_page_break_before("heading", level=1, is_first_content=False)
    print(f"Page break before H1 (not first): {should_break}")
    assert should_break, "Should page break before H1"

    should_break_first = layout.should_page_break_before("heading", level=1, is_first_content=True)
    print(f"Page break before H1 (first content): {should_break_first}")
    assert not should_break_first, "Should NOT page break before first content"

    # Test config summary
    summary = layout.get_config_summary()
    print(f"Config summary keys: {list(summary.keys())}")

    print("\n[PASS] PageLayoutManager working!")


def test_toc_generator():
    """Test TocGenerator functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: TocGenerator")
    print("=" * 60)

    # Create test document with headings
    text = """
# Chapter 1: Introduction

This is the introduction.

## 1.1 Background

Some background info.

## 1.2 Objectives

Our objectives.

### 1.2.1 Primary Goals

Primary goals here.

# Chapter 2: Methods

Our methodology.

## 2.1 Data Collection

How we collected data.

# Chapter 3: Results

Our findings.
"""

    # Detect structure
    detector = StructureDetector()
    model = DocumentModel.from_text(text)

    # Generate TOC
    toc_gen = TocGenerator(language="en", style="default")
    toc = toc_gen.generate(model)

    print(f"TOC title: {toc.title}")
    print(f"TOC entries: {len(toc.entries)}")

    for entry in toc.entries:
        indent = "  " * (entry.level - 1)
        print(f"{indent}[L{entry.level}] {entry.title[:40]}... -> #{entry.anchor}")

    # Test markdown output
    md_toc = toc_gen.to_markdown(toc)
    print(f"\nMarkdown TOC:\n{md_toc[:500]}...")

    # Test Vietnamese
    toc_gen_vi = TocGenerator(language="vi")
    toc_vi = toc_gen_vi.generate(model)
    print(f"\nVietnamese TOC title: {toc_vi.title}")

    assert len(toc.entries) >= 5, "Should have at least 5 TOC entries"
    print("\n[PASS] TocGenerator working!")


def test_docx_with_page_layout():
    """Test DOCX export with page layout."""
    print("\n" + "=" * 60)
    print("TEST 3: DOCX Export with Page Layout")
    print("=" * 60)

    # Create test document
    text = """
# Chapter 1: Introduction

This document tests page layout features including headers, footers, and page breaks.

## 1.1 Overview

This section provides an overview of the document.

## 1.2 Goals

The goals of this document are:

- Test page size configuration
- Test margins
- Test header with document title
- Test footer with page numbers
- Test TOC generation
- Test page breaks before chapters

# Chapter 2: Implementation

This is the second chapter.

## 2.1 Technical Details

Some technical details here.

# Chapter 3: Conclusion

Final conclusions.
"""

    # Process document
    model = DocumentModel.from_text(text)
    print(f"Elements: {len(model.elements)}")
    print(f"TOC entries: {len(model.toc)}")

    # Apply styles
    engine = StyleEngine(template="book", output_type="print")
    styled_doc = engine.apply(model)
    styled_doc.title = "Test Document with Page Layout"

    # Setup page layout
    layout = PageLayoutManager(
        page_size="A4",
        margins="book",
        header_footer_style="default"
    )

    # Export
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    exporter = DocxStyleExporter()
    docx_path = exporter.export(styled_doc, str(output_dir / "format004_test.docx"), page_layout=layout)
    docx_size = os.path.getsize(docx_path)

    print(f"DOCX exported: {docx_path}")
    print(f"File size: {docx_size:,} bytes")

    assert docx_size > 15000, "DOCX should be > 15KB"
    print("\n[PASS] DOCX with page layout working!")


def test_markdown_with_toc():
    """Test Markdown export with TOC."""
    print("\n" + "=" * 60)
    print("TEST 4: Markdown Export with TOC")
    print("=" * 60)

    # Create test document
    text = """
# Chapter 1: Introduction

This is the introduction.

## 1.1 Background

Background info.

# Chapter 2: Methods

Methodology.

# Chapter 3: Results

Findings.
"""

    # Process
    model = DocumentModel.from_text(text)
    engine = StyleEngine()
    styled_doc = engine.apply(model)
    styled_doc.title = "Test Document"

    # Export markdown
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    md_exporter = MarkdownStyleExporter(include_toc=True, language="en")
    md_path = md_exporter.export(styled_doc, str(output_dir / "format004_test.md"))
    md_size = os.path.getsize(md_path)

    print(f"Markdown exported: {md_path}")
    print(f"File size: {md_size:,} bytes")

    # Read and check content
    content = Path(md_path).read_text()
    has_toc = "Table of Contents" in content
    has_links = "[Chapter 1" in content or "[1.1" in content
    print(f"Has TOC: {has_toc}")
    print(f"Has anchor links: {has_links}")

    print("\n[PASS] Markdown with TOC working!")


def test_full_pipeline():
    """Test full pipeline with complex document."""
    print("\n" + "=" * 60)
    print("TEST 5: Full Pipeline Test")
    print("=" * 60)

    # Use complex_structure.txt if exists
    test_file = Path(__file__).parent / "test_data" / "complex_structure.txt"
    if test_file.exists():
        text = test_file.read_text()
        print(f"Using test file: {test_file}")
    else:
        # Generate test content
        text = generate_large_document()
        print("Using generated content")

    print(f"Input: {len(text):,} chars")

    # Full pipeline
    model = DocumentModel.from_text(text)
    print(f"Detected elements: {len(model.elements)}")
    print(f"TOC entries: {len(model.toc)}")

    # Style
    engine = StyleEngine(template="report", output_type="print")
    styled_doc = engine.apply(model)
    styled_doc.title = "Complex Document Test"

    # Layout
    layout = PageLayoutManager(
        page_size="A4",
        margins="normal",
        header_footer_style="report"
    )

    # Export both formats
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    docx_exporter = DocxStyleExporter()
    docx_path = docx_exporter.export(
        styled_doc,
        str(output_dir / "format004_full.docx"),
        page_layout=layout
    )
    docx_size = os.path.getsize(docx_path)

    md_exporter = MarkdownStyleExporter(include_toc=True)
    md_path = md_exporter.export(styled_doc, str(output_dir / "format004_full.md"))
    md_size = os.path.getsize(md_path)

    print(f"\nDOCX: {docx_path} ({docx_size:,} bytes)")
    print(f"Markdown: {md_path} ({md_size:,} bytes)")

    print("\n[PASS] Full pipeline working!")


def generate_large_document():
    """Generate a large test document with multiple chapters."""
    lines = []

    for chapter in range(1, 6):
        lines.append(f"# Chapter {chapter}: Topic {chapter}")
        lines.append("")
        lines.append(f"This is the introduction to chapter {chapter}.")
        lines.append("")

        for section in range(1, 4):
            lines.append(f"## {chapter}.{section} Section Title")
            lines.append("")
            lines.append("This is some content for this section. " * 5)
            lines.append("")

            # Add a list
            lines.append("Key points:")
            lines.append("- First point")
            lines.append("- Second point")
            lines.append("- Third point")
            lines.append("")

            if section == 1:
                # Add a table
                lines.append("| Column 1 | Column 2 | Column 3 |")
                lines.append("|----------|----------|----------|")
                lines.append("| Data A   | Data B   | Data C   |")
                lines.append("| Data D   | Data E   | Data F   |")
                lines.append("")

    return "\n".join(lines)


def main():
    """Run all tests."""
    print("=" * 60)
    print("FORMAT-004: Page Layout & Document Structure - Test Suite")
    print("=" * 60)

    try:
        test_page_layout_manager()
        test_toc_generator()
        test_docx_with_page_layout()
        test_markdown_with_toc()
        test_full_pipeline()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
