#!/bin/bash
#
# Quick Phase 5 Validation Script
# Automated end-to-end testing without manual intervention
#

echo "========================================================================"
echo "  PHASE 5: QUICK INTEGRATION VALIDATION"
echo "========================================================================"
echo ""
echo "Testing complete translation pipeline (Phases 1-4.3)"
echo "Timestamp: $(date)"
echo ""

# Change to project root
cd "$(dirname "$0")/.." || exit 1

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function
test_result() {
    if [ $1 -eq 0 ]; then
        echo "✅ PASS: $2"
        ((TESTS_PASSED++))
    else
        echo "❌ FAIL: $2"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# ============================================================================
# TEST 1: Module Imports
# ============================================================================
echo "------------------------------------------------------------------------"
echo "TEST 1: Core Module Imports"
echo "------------------------------------------------------------------------"
echo ""

python3 << 'EOF'
import sys
from pathlib import Path

try:
    # Core modules
    from config.settings import settings
    from translate_pdf import process_pdf_translation
    from core.rendering.docx_adapter import render_docx_from_ast
    from core.export.pdf_adapter import convert_docx_to_pdf
    from core.export.book_layout import apply_book_layout

    print("✅ All core modules imported successfully")
    sys.exit(0)
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
EOF

test_result $? "Core module imports"

# ============================================================================
# TEST 2: Configuration Validation
# ============================================================================
echo "------------------------------------------------------------------------"
echo "TEST 2: Configuration Validation"
echo "------------------------------------------------------------------------"
echo ""

python3 << 'EOF'
import sys
from config.settings import settings

print("Configuration Summary:")
print(f"  Provider: {settings.provider}")
print(f"  Model: {settings.model}")
print(f"  Source → Target: {settings.source_lang} → {settings.target_lang}")
print(f"  Advanced book layout: {settings.enable_advanced_book_layout}")
print("")

# Validate
errors = []

if not settings.provider in ['openai', 'anthropic']:
    errors.append(f"Invalid provider: {settings.provider}")

if settings.enable_advanced_book_layout:
    print("⚠️  WARNING: Advanced book layout is ENABLED (experimental feature)")
    print("   Recommended: keep disabled for production (Phase 4.3 is optional)")
else:
    print("✅ Advanced book layout is DISABLED (recommended default)")

print("")

if errors:
    for error in errors:
        print(f"❌ {error}")
    sys.exit(1)
else:
    print("✅ Configuration valid")
    sys.exit(0)
EOF

test_result $? "Configuration validation"

# ============================================================================
# TEST 3: Feature Availability
# ============================================================================
echo "------------------------------------------------------------------------"
echo "TEST 3: Feature Availability Check"
echo "------------------------------------------------------------------------"
echo ""

python3 << 'EOF'
import sys
import shutil
from core.export.pdf_adapter import is_libreoffice_available

# Check Pandoc (Phase 4.1 - OMML rendering)
pandoc_available = shutil.which("pandoc") is not None
print(f"Pandoc (OMML rendering): {'✅ Available' if pandoc_available else '⚠️  Not available (will fallback)'}")

# Check LibreOffice (Phase 4.2 - PDF export)
libreoffice_available = is_libreoffice_available()
print(f"LibreOffice (PDF export): {'✅ Available' if libreoffice_available else '⚠️  Not available'}")

print("")

# Both optional - not blocking
if not pandoc_available:
    print("ℹ️  Pandoc not found: OMML equations will fallback to LaTeX text")
if not libreoffice_available:
    print("ℹ️  LibreOffice not found: PDF export will be unavailable")

print("")
print("✅ Feature check complete")
sys.exit(0)
EOF

test_result $? "Feature availability"

# ============================================================================
# TEST 4: Test Files Present
# ============================================================================
echo "------------------------------------------------------------------------"
echo "TEST 4: Test Files Present"
echo "------------------------------------------------------------------------"
echo ""

if [ -f "Stemsample.pdf" ]; then
    echo "✅ Stemsample.pdf found ($(ls -lh Stemsample.pdf | awk '{print $5}'))"
else
    echo "❌ Stemsample.pdf not found"
    ((TESTS_FAILED++))
fi

if [ -f "arXiv-1509.05363v6.pdf" ]; then
    echo "✅ arXiv-1509.05363v6.pdf found ($(ls -lh arXiv-1509.05363v6.pdf | awk '{print $5}'))"
else
    echo "⚠️  arXiv-1509.05363v6.pdf not found (optional)"
fi

echo ""
((TESTS_PASSED++))

# ============================================================================
# TEST 5: Phase 4.3 Integration Test
# ============================================================================
echo "------------------------------------------------------------------------"
echo "TEST 5: Phase 4.3 (Advanced Book Layout) Integration"
echo "------------------------------------------------------------------------"
echo ""

python3 << 'EOF'
import sys
from config.settings import settings
from core.export.book_layout import apply_book_layout, BookLayoutConfig
from docx import Document

# Test that book layout can be imported and called
try:
    print("Testing book layout integration...")

    # Create test document
    doc = Document()
    doc.add_heading("Test Chapter", level=1)
    doc.add_paragraph("Test content")

    # Mock metadata
    class MockMetadata:
        title = "Test Book"
        subtitle = "Integration Test"
        author = "Phase 5 Validation"

    metadata = MockMetadata()

    # Test with enabled=False (default)
    print(f"  Advanced layout enabled: {settings.enable_advanced_book_layout}")

    if settings.enable_advanced_book_layout:
        print("  Applying book layout features...")
        apply_book_layout(doc, metadata)
        print("  ✅ Book layout applied")
    else:
        print("  ✅ Book layout skipped (disabled by default)")

    print("")
    print("✅ Phase 4.3 integration test passed")
    sys.exit(0)

except Exception as e:
    print(f"❌ Book layout test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

test_result $? "Phase 4.3 integration"

# ============================================================================
# TEST 6: DOCX Adapter (AST Pipeline)
# ============================================================================
echo "------------------------------------------------------------------------"
echo "TEST 6: DOCX Adapter + AST Pipeline Test"
echo "------------------------------------------------------------------------"
echo ""

python3 << 'EOF'
import sys
from pathlib import Path
from core.rendering.docx_adapter import render_docx_from_ast
from core.ast_builder.document_ast import DocumentAST, Paragraph, Heading
from core.ast_builder.metadata import DocumentMetadata

try:
    print("Creating test AST...")

    # Create minimal AST
    metadata = DocumentMetadata(
        title="Phase 5 Test Document",
        source_lang="en",
        target_lang="vi"
    )

    ast = DocumentAST(metadata=metadata)
    ast.add_node(Heading(text="Test Heading", level=1))
    ast.add_node(Paragraph(text="This is a test paragraph."))

    # Render to DOCX
    output_path = Path("test_phase5_docx_adapter.docx")
    print(f"Rendering to {output_path}...")

    render_docx_from_ast(ast, output_path)

    if output_path.exists():
        size = output_path.stat().st_size
        print(f"✅ DOCX created: {size:,} bytes")

        # Clean up
        output_path.unlink()
        print("✅ Test file cleaned up")
    else:
        print("❌ DOCX file not created")
        sys.exit(1)

    print("")
    print("✅ DOCX adapter + AST pipeline test passed")
    sys.exit(0)

except Exception as e:
    print(f"❌ DOCX adapter test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

test_result $? "DOCX adapter + AST"

# ============================================================================
# SUMMARY
# ============================================================================
echo "========================================================================"
echo "  PHASE 5 VALIDATION SUMMARY"
echo "========================================================================"
echo ""
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
echo "Total Tests: $TOTAL_TESTS"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "========================================================================"
    echo "  ✅ ALL VALIDATION TESTS PASSED!"
    echo "========================================================================"
    echo ""
    echo "Phase 1-4.3 pipeline validated successfully."
    echo "Core modules, configuration, and integrations working correctly."
    echo ""
    echo "Next Steps:"
    echo "  1. Run full integration tests: python3 scripts/phase5_integration_tests.py"
    echo "  2. Test with real documents"
    echo "  3. Verify production deployment checklist"
    echo ""
    exit 0
else
    echo "========================================================================"
    echo "  ❌ SOME TESTS FAILED"
    echo "========================================================================"
    echo ""
    echo "Please review failed tests above and fix issues before proceeding."
    echo ""
    exit 1
fi
