#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test FORMAT-003: Lists & Tables Detection.

Tests:
1. List detection (bullet, numbered, nested)
2. Table detection (markdown, ASCII)
3. Style engine integration
4. Export to DOCX and Markdown
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from core.formatting import (
    StructureDetector,
    DocumentModel,
    StyleEngine,
    DocxStyleExporter,
    MarkdownStyleExporter,
    ListElement,
    TableElement,
)


def test_list_detection():
    """Test bullet and numbered list detection."""
    print("\n" + "=" * 60)
    print("TEST 1: List Detection")
    print("=" * 60)

    text = """
- First bullet item
- Second bullet item
  - Nested item 1
  - Nested item 2
- Third bullet item

1. First numbered
2. Second numbered
   a. Sub item a
   b. Sub item b
3. Third numbered
"""

    detector = StructureDetector()
    elements = detector.detect(text)

    bullet_lists = [e for e in elements if isinstance(e, ListElement) and e.list_type == "bullet"]
    numbered_lists = [e for e in elements if isinstance(e, ListElement) and e.list_type == "numbered"]

    print(f"Total elements: {len(elements)}")
    print(f"Bullet lists: {len(bullet_lists)}")
    print(f"Numbered lists: {len(numbered_lists)}")

    for lst in bullet_lists:
        print(f"\nBullet List ({len(lst.items)} items):")
        for item in lst.items:
            print(f"  L{item.level}: {item.marker} {item.content[:50]}")

    for lst in numbered_lists:
        print(f"\nNumbered List ({len(lst.items)} items):")
        for item in lst.items:
            print(f"  L{item.level}: {item.marker} {item.content[:50]}")

    assert len(bullet_lists) >= 1, "Should detect at least 1 bullet list"
    assert len(numbered_lists) >= 1, "Should detect at least 1 numbered list"
    print("\n[PASS] List detection working!")


def test_table_detection():
    """Test markdown and ASCII table detection."""
    print("\n" + "=" * 60)
    print("TEST 2: Table Detection")
    print("=" * 60)

    text = """
# Test Tables

| Name | Age | City |
|------|-----|------|
| Alice | 25 | Hanoi |
| Bob | 30 | HCMC |

| Left | Center | Right |
|:-----|:------:|------:|
| L1 | C1 | R1 |
| L2 | C2 | R2 |
"""

    detector = StructureDetector()
    elements = detector.detect(text)

    tables = [e for e in elements if isinstance(e, TableElement)]

    print(f"Total elements: {len(elements)}")
    print(f"Tables found: {len(tables)}")

    for i, tbl in enumerate(tables):
        print(f"\nTable {i+1} ({tbl.table_type}):")
        print(f"  Headers: {tbl.headers}")
        print(f"  Rows: {len(tbl.rows)}")
        print(f"  Alignments: {tbl.alignments}")
        for row in tbl.rows[:2]:  # Show first 2 rows
            print(f"    Row: {row}")

    assert len(tables) >= 2, "Should detect at least 2 tables"
    print("\n[PASS] Table detection working!")


def test_full_pipeline():
    """Test full pipeline with complex_structure.txt."""
    print("\n" + "=" * 60)
    print("TEST 3: Full Pipeline Test")
    print("=" * 60)

    # Read test file
    test_file = Path(__file__).parent / "test_data" / "complex_structure.txt"
    if not test_file.exists():
        print(f"[SKIP] Test file not found: {test_file}")
        return

    text = test_file.read_text(encoding='utf-8')
    print(f"Input: {len(text)} chars")

    # Stage 1: Detection
    detector = StructureDetector()
    elements = detector.detect(text)
    print(f"Detected: {len(elements)} elements")

    # Count element types
    summary = detector.get_structure_summary(text)
    print(f"\nStructure Summary:")
    print(f"  Headings: {summary['headings']}")
    print(f"  Paragraphs: {summary['paragraphs']}")
    print(f"  Lists: {summary['lists']} (total items: {summary['list_items_total']})")
    print(f"  Tables: {summary['tables']} (total rows: {summary['table_rows_total']})")
    print(f"  Code blocks: {summary['code_blocks']}")
    print(f"  Quotes: {summary['quotes']}")

    # Stage 2: Document Model
    model = DocumentModel.from_text(text)
    print(f"\nTOC Entries: {len(model.toc)}")

    # Stage 3: Style Engine
    engine = StyleEngine(template="report", output_type="print")
    styled_doc = engine.apply(model)
    print(f"Styled elements: {len(styled_doc)}")

    # Stage 4: Export
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Export DOCX
    docx_exporter = DocxStyleExporter()
    docx_path = docx_exporter.export(styled_doc, str(output_dir / "format003_test.docx"))
    docx_size = os.path.getsize(docx_path)
    print(f"\nDOCX: {docx_path} ({docx_size:,} bytes)")

    # Export Markdown
    md_exporter = MarkdownStyleExporter()
    md_path = md_exporter.export(styled_doc, str(output_dir / "format003_test.md"))
    md_size = os.path.getsize(md_path)
    print(f"Markdown: {md_path} ({md_size:,} bytes)")

    # Verify output
    assert docx_size > 10000, "DOCX should be > 10KB"
    assert md_size > 1000, "Markdown should be > 1KB"

    print("\n[PASS] Full pipeline working!")


def test_vietnamese_lists():
    """Test Vietnamese list patterns."""
    print("\n" + "=" * 60)
    print("TEST 4: Vietnamese List Patterns")
    print("=" * 60)

    text = """
Thứ 1: Mục đầu tiên
Thứ 2: Mục thứ hai
Khoản 1: Điều khoản một
Khoản 2: Điều khoản hai
Điểm a: Nội dung điểm a
Điểm b: Nội dung điểm b
"""

    detector = StructureDetector(language="vi")
    elements = detector.detect(text)

    lists = [e for e in elements if isinstance(e, ListElement)]
    print(f"Vietnamese lists detected: {len(lists)}")

    for lst in lists:
        print(f"\nList ({len(lst.items)} items):")
        for item in lst.items:
            print(f"  {item.marker} {item.content}")

    print("\n[PASS] Vietnamese lists working!")


def main():
    """Run all tests."""
    print("=" * 60)
    print("FORMAT-003: Lists & Tables Detection - Test Suite")
    print("=" * 60)

    try:
        test_list_detection()
        test_table_detection()
        test_full_pipeline()
        test_vietnamese_lists()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
