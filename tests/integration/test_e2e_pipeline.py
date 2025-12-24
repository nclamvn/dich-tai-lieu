#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E-001: End-to-End Pipeline Test

Tests the complete pipeline from detection through export:
1. Structure Detection (Formatting Engine)
2. STEM Detection (Code + Formulas)
3. Style Application
4. DOCX Export
5. Markdown Export

Run with: python tests/integration/test_e2e_pipeline.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports
from core.formatting import (
    StructureDetector,
    DocumentModel,
    StyleEngine,
    CodeBlockElement,
    FormulaElement,
    ListElement,
    TableElement,
    BlockquoteElement,
)
from core.formatting.exporters import DocxStyleExporter, MarkdownStyleExporter
from core.formatting.utils.stem_integration import get_stem_integration
from core.shared import ElementType, DetectionResult


# =============================================================================
# TEST FIXTURES
# =============================================================================

FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "stem_test" / "sample_stem_document.md"


def load_fixture():
    """Load the sample STEM document fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return f.read()


# =============================================================================
# TEST CASES
# =============================================================================

def test_1_stem_integration_available():
    """Test 1: Verify STEM integration is available."""
    print("\n[Test 1] STEM Integration Available")
    print("-" * 40)

    stem = get_stem_integration()
    available = stem.is_available()

    print(f"  STEM module available: {available}")

    assert available, "STEM module should be available"
    print("  ✅ PASSED")
    return True


def test_2_structure_detection():
    """Test 2: Verify structure detection works."""
    print("\n[Test 2] Structure Detection")
    print("-" * 40)

    text = load_fixture()
    detector = StructureDetector(use_stem=True)
    elements = detector.detect(text)

    # Count element types
    headings = [e for e in elements if e.type == "heading"]
    paragraphs = [e for e in elements if e.type == "paragraph"]
    code_blocks = [e for e in elements if isinstance(e, CodeBlockElement)]
    lists = [e for e in elements if isinstance(e, ListElement)]
    tables = [e for e in elements if isinstance(e, TableElement)]
    quotes = [e for e in elements if isinstance(e, BlockquoteElement)]

    print(f"  Total elements: {len(elements)}")
    print(f"  Headings: {len(headings)}")
    print(f"  Paragraphs: {len(paragraphs)}")
    print(f"  Code blocks: {len(code_blocks)}")
    print(f"  Lists: {len(lists)}")
    print(f"  Tables: {len(tables)}")
    print(f"  Blockquotes: {len(quotes)}")

    # Assertions
    assert len(headings) >= 10, f"Expected at least 10 headings, got {len(headings)}"
    assert len(code_blocks) >= 4, f"Expected at least 4 code blocks, got {len(code_blocks)}"
    assert len(lists) >= 2, f"Expected at least 2 lists, got {len(lists)}"
    assert len(tables) >= 2, f"Expected at least 2 tables, got {len(tables)}"

    print("  ✅ PASSED")
    return elements


def test_3_stem_detection():
    """Test 3: Verify STEM detection (formulas + code)."""
    print("\n[Test 3] STEM Detection")
    print("-" * 40)

    text = load_fixture()
    stem = get_stem_integration()

    # Detect code
    code_results = stem.detect_code(text)
    print(f"  Code elements detected: {len(code_results)}")

    # Detect formulas
    formula_results = stem.detect_formulas(text)
    print(f"  Formula elements detected: {len(formula_results)}")

    # Count types
    code_blocks = [r for r in code_results if r.element_type == ElementType.CODE_BLOCK]
    code_inline = [r for r in code_results if r.element_type == ElementType.CODE_INLINE]
    formula_blocks = [r for r in formula_results if r.element_type == ElementType.FORMULA_BLOCK]
    formula_inline = [r for r in formula_results if r.element_type == ElementType.FORMULA_INLINE]
    chemical = [r for r in formula_results if r.element_type == ElementType.CHEMICAL_FORMULA]

    print(f"    - Code blocks: {len(code_blocks)}")
    print(f"    - Code inline: {len(code_inline)}")
    print(f"    - Formula blocks: {len(formula_blocks)}")
    print(f"    - Formula inline: {len(formula_inline)}")
    print(f"    - Chemical formulas: {len(chemical)}")

    # Assertions
    assert len(code_blocks) >= 4, f"Expected at least 4 code blocks, got {len(code_blocks)}"
    assert len(code_inline) >= 3, f"Expected at least 3 inline code, got {len(code_inline)}"
    assert len(formula_blocks) >= 3, f"Expected at least 3 display formulas, got {len(formula_blocks)}"
    assert len(formula_inline) >= 3, f"Expected at least 3 inline formulas, got {len(formula_inline)}"

    print("  ✅ PASSED")
    return code_results, formula_results


def test_4_document_model():
    """Test 4: Verify document model building."""
    print("\n[Test 4] Document Model")
    print("-" * 40)

    text = load_fixture()

    # Build document model using from_text (which internally uses StructureDetector)
    model = DocumentModel.from_text(text)

    print(f"  Model built: {model is not None}")
    print(f"  Elements in model: {len(model.elements)}")
    print(f"  Headings in model: {len([e for e in model.elements if e.type == 'heading'])}")

    # Check TOC generation
    toc = model.toc
    print(f"  TOC entries: {len(toc)}")

    assert len(model.elements) > 0, "Model should have elements"
    assert len(toc) >= 5, f"Expected at least 5 TOC entries, got {len(toc)}"

    print("  ✅ PASSED")
    return model


def test_5_style_application():
    """Test 5: Verify style application."""
    print("\n[Test 5] Style Application")
    print("-" * 40)

    text = load_fixture()
    model = DocumentModel.from_text(text)

    # Apply styles
    style_engine = StyleEngine()
    styled_doc = style_engine.apply(model)

    print(f"  Styled document created: {styled_doc is not None}")
    print(f"  Styled elements: {len(styled_doc.elements)}")

    # Check for styled code blocks
    styled_code = [e for e in styled_doc.elements if hasattr(e, 'language')]
    print(f"  Styled code blocks: {len(styled_code)}")

    assert styled_doc is not None, "Styled document should be created"
    assert len(styled_doc.elements) > 0, "Styled document should have elements"

    print("  ✅ PASSED")
    return styled_doc


def test_6_docx_export():
    """Test 6: Verify DOCX export."""
    print("\n[Test 6] DOCX Export")
    print("-" * 40)

    text = load_fixture()
    model = DocumentModel.from_text(text)
    style_engine = StyleEngine()
    styled_doc = style_engine.apply(model)

    # Export to DOCX
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        output_path = f.name

    try:
        exporter = DocxStyleExporter()
        exporter.export(styled_doc, output_path)

        # Verify file created
        file_exists = os.path.exists(output_path)
        file_size = os.path.getsize(output_path) if file_exists else 0

        print(f"  DOCX file created: {file_exists}")
        print(f"  DOCX file size: {file_size:,} bytes")

        assert file_exists, "DOCX file should be created"
        assert file_size > 5000, f"DOCX file too small: {file_size} bytes"

        print("  ✅ PASSED")
        return output_path, file_size
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise


def test_7_markdown_export():
    """Test 7: Verify Markdown export."""
    print("\n[Test 7] Markdown Export")
    print("-" * 40)

    text = load_fixture()
    model = DocumentModel.from_text(text)
    style_engine = StyleEngine()
    styled_doc = style_engine.apply(model)

    # Export to Markdown
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode='w') as f:
        output_path = f.name

    try:
        exporter = MarkdownStyleExporter()
        exporter.export(styled_doc, output_path)

        # Verify file created
        file_exists = os.path.exists(output_path)
        file_size = os.path.getsize(output_path) if file_exists else 0

        print(f"  Markdown file created: {file_exists}")
        print(f"  Markdown file size: {file_size:,} bytes")

        # Read and check content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify key content preserved
        has_code = "```python" in content or "```" in content
        has_formulas = "$" in content or "\\[" in content
        has_tables = "|" in content
        has_headings = content.startswith("#") or "\n# " in content or "\n## " in content

        print(f"  Content checks:")
        print(f"    - Code blocks: {'✓' if has_code else '✗'}")
        print(f"    - Formulas: {'✓' if has_formulas else '✗'}")
        print(f"    - Tables: {'✓' if has_tables else '✗'}")
        print(f"    - Headings: {'✓' if has_headings else '✗'}")

        assert file_exists, "Markdown file should be created"
        assert file_size > 1000, f"Markdown file too small: {file_size} bytes"

        print("  ✅ PASSED")
        return output_path, file_size, content
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise


# =============================================================================
# VERIFICATION CHECKS
# =============================================================================

def verify_preservation(docx_path, md_content):
    """Verify that key elements are preserved through the pipeline."""
    print("\n[Verification] Element Preservation")
    print("-" * 40)

    results = {
        "formulas_preserved": False,
        "code_preserved": False,
        "structure_preserved": False,
        "tables_preserved": False,
    }

    # Check Markdown content for preservation
    # Formulas
    if "$" in md_content or "\\(" in md_content:
        results["formulas_preserved"] = True
        print("  Formulas preserved: ✅")
    else:
        print("  Formulas preserved: ❌")

    # Code blocks
    if "```" in md_content:
        results["code_preserved"] = True
        print("  Code preserved: ✅")
    else:
        print("  Code preserved: ❌")

    # Structure (headings)
    if "# " in md_content and "## " in md_content:
        results["structure_preserved"] = True
        print("  Structure preserved: ✅")
    else:
        print("  Structure preserved: ❌")

    # Tables
    if "|" in md_content and "---" in md_content:
        results["tables_preserved"] = True
        print("  Tables preserved: ✅")
    else:
        print("  Tables preserved: ❌")

    return results


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Run all E2E tests and return summary."""
    print("=" * 60)
    print("E2E-001: END-TO-END PIPELINE TEST")
    print("=" * 60)

    results = {
        "passed": 0,
        "failed": 0,
        "tests": {},
        "outputs": {},
    }

    tests = [
        ("test_1_stem_integration", test_1_stem_integration_available),
        ("test_2_structure_detection", test_2_structure_detection),
        ("test_3_stem_detection", test_3_stem_detection),
        ("test_4_document_model", test_4_document_model),
        ("test_5_style_application", test_5_style_application),
        ("test_6_docx_export", test_6_docx_export),
        ("test_7_markdown_export", test_7_markdown_export),
    ]

    docx_path = None
    md_content = None

    for name, test_func in tests:
        try:
            result = test_func()
            results["tests"][name] = "PASSED"
            results["passed"] += 1

            # Capture output paths
            if name == "test_6_docx_export":
                docx_path, docx_size = result
                results["outputs"]["docx_path"] = docx_path
                results["outputs"]["docx_size"] = docx_size
            elif name == "test_7_markdown_export":
                md_path, md_size, md_content = result
                results["outputs"]["md_path"] = md_path
                results["outputs"]["md_size"] = md_size

        except Exception as e:
            results["tests"][name] = f"FAILED: {e}"
            results["failed"] += 1
            print(f"  ❌ FAILED: {e}")

    # Run verification if exports succeeded
    if docx_path and md_content:
        preservation = verify_preservation(docx_path, md_content)
        results["preservation"] = preservation

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {results['passed']}/{len(tests)}")
    print(f"Tests failed: {results['failed']}/{len(tests)}")

    if results.get("outputs"):
        print(f"\nOutput files:")
        if "docx_path" in results["outputs"]:
            print(f"  DOCX: {results['outputs']['docx_size']:,} bytes")
        if "md_path" in results["outputs"]:
            print(f"  Markdown: {results['outputs']['md_size']:,} bytes")

    if results.get("preservation"):
        print(f"\nPreservation:")
        for key, value in results["preservation"].items():
            status = "✅" if value else "❌"
            print(f"  {key}: {status}")

    print("=" * 60)

    return results


if __name__ == "__main__":
    results = run_all_tests()

    # Exit with error code if any tests failed
    sys.exit(0 if results["failed"] == 0 else 1)
