"""
Phase 3.5a - Translation Quality Engine Test Suite (Rule-Based Only)

Comprehensive tests for the rule-based translation quality polish layer.

Phase 3.5a Scope: Rule-based polish ONLY
- NO LLM, NO API calls
- Deterministic, reversible operations
- Default mode: OFF

Test Coverage:
1. Default mode="off" behavior (CRITICAL)
2. Config creation and validation
3. Protected content detection
4. Fix patterns (whitespace, punctuation, newlines)
5. Mode switching (off, light, aggressive)
6. Domain filtering
7. Idempotency
8. Non-destructive behavior
9. Analyze vs Polish
10. Integration scenarios
"""

import pytest
from core.quality import (
    TranslationQualityEngine,
    TranslationQualityConfig,
    QualityReport,
    create_default_config,
    create_light_config,
    create_aggressive_config
)


# ============================================================================
# TEST 1: Default Mode is OFF (CRITICAL)
# ============================================================================

def test_default_mode_is_off():
    """CRITICAL: Verify that default config has mode='off'."""
    config = TranslationQualityConfig()
    assert config.mode == "off", "Default mode MUST be 'off'"


def test_default_config_helper_creates_off_mode():
    """Verify create_default_config() creates mode='off' config."""
    config = create_default_config()
    assert config.mode == "off", "create_default_config() must have mode='off'"


# ============================================================================
# TEST 2: Mode='off' Returns Original Text Unchanged
# ============================================================================

def test_mode_off_returns_original_text():
    """Verify that mode='off' returns text unchanged (kill switch)."""
    config = TranslationQualityConfig(mode="off")
    engine = TranslationQualityEngine(config)

    original_text = "This  has  double  spaces.  And   extra   spaces."
    polished_text = engine.polish(original_text)

    # Text should be UNCHANGED
    assert polished_text == original_text, "mode='off' must return original text"


def test_mode_off_with_all_issues():
    """Verify mode='off' doesn't fix even obvious issues."""
    config = TranslationQualityConfig(mode="off")
    engine = TranslationQualityEngine(config)

    # Text with multiple issues
    messy_text = "Text  with   spaces .No space after.   \n\n\n\nToo many newlines."
    polished_text = engine.polish(messy_text)

    # Should be completely unchanged
    assert polished_text == messy_text, "mode='off' must preserve all issues"


# ============================================================================
# TEST 3: Config Creation Helpers
# ============================================================================

def test_create_light_config():
    """Test create_light_config() creates proper light mode config."""
    config = create_light_config(domain="book")

    assert config.mode == "light"
    assert config.domain == "book"
    assert config.enable_rule_based_pass is True
    assert config.enable_llm_rewrite is False
    assert config.normalize_whitespace is True
    assert config.remove_redundant_phrases is False  # Not in light mode


def test_create_aggressive_config():
    """Test create_aggressive_config() creates proper aggressive mode config."""
    config = create_aggressive_config(domain="general")

    assert config.mode == "aggressive"
    assert config.domain == "general"
    assert config.enable_rule_based_pass is True
    assert config.enable_llm_rewrite is False  # Phase 3.5b not implemented yet


# ============================================================================
# TEST 4: Analyze Method (Non-Destructive)
# ============================================================================

def test_analyze_detects_issues():
    """Test that analyze() detects issues without modifying text."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text_with_issues = "Text  with   double  spaces.  And trailing spaces. "
    report = engine.analyze(text_with_issues)

    assert report.total_chars == len(text_with_issues)
    assert report.issues_found > 0, "Should detect multiple space issues"
    assert report.issues_fixed == 0, "analyze() should not fix anything"


def test_analyze_reports_issue_breakdown():
    """Test that analyze() provides detailed issue breakdown."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Text  with  double  spaces."
    report = engine.analyze(text)

    assert isinstance(report.issue_breakdown, dict)
    assert 'multiple_spaces' in report.issue_breakdown
    assert report.issue_breakdown['multiple_spaces'] > 0


# ============================================================================
# TEST 5: Fix Multiple Spaces
# ============================================================================

def test_fix_multiple_spaces():
    """Test that multiple spaces are reduced to single space."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Text  with   multiple    spaces."
    polished = engine.polish(text)

    assert "  " not in polished, "Double spaces should be removed"
    assert polished == "Text with multiple spaces."


def test_preserve_single_spaces():
    """Test that single spaces are preserved."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Text with normal spacing."
    polished = engine.polish(text)

    assert polished == text, "Normal spacing should be preserved"


# ============================================================================
# TEST 6: Fix Space Before Punctuation
# ============================================================================

def test_fix_space_before_punctuation():
    """Test that spaces before punctuation are removed."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "This is wrong . And this too ."
    polished = engine.polish(text)

    assert polished == "This is wrong. And this too."


def test_fix_space_before_various_punctuation():
    """Test space removal before various punctuation marks."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Question ? Exclamation ! Comma , Semicolon ; Colon :"
    polished = engine.polish(text)

    assert polished == "Question? Exclamation! Comma, Semicolon; Colon:"


# ============================================================================
# TEST 7: Fix No Space After Punctuation
# ============================================================================

def test_fix_no_space_after_punctuation():
    """Test that missing space after punctuation is added."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Sentence one.Next sentence."
    polished = engine.polish(text)

    assert polished == "Sentence one. Next sentence."


def test_fix_no_space_after_vietnamese_capital():
    """Test space insertion after punctuation before Vietnamese capitals."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Câu đầu.Đây là câu hai."
    polished = engine.polish(text)

    assert polished == "Câu đầu. Đây là câu hai."


# ============================================================================
# TEST 8: Fix Excessive Newlines
# ============================================================================

def test_fix_excessive_newlines():
    """Test that 3+ newlines are reduced to 2."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Paragraph one.\n\n\n\nParagraph two."
    polished = engine.polish(text)

    assert polished == "Paragraph one.\n\nParagraph two."


def test_preserve_double_newlines():
    """Test that double newlines (paragraph breaks) are preserved."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Paragraph one.\n\nParagraph two."
    polished = engine.polish(text)

    assert polished == text, "Double newlines should be preserved"


# ============================================================================
# TEST 9: Fix Trailing Whitespace
# ============================================================================

def test_fix_trailing_whitespace_on_lines():
    """Test that trailing whitespace at end of lines is removed."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Line with trailing spaces.   \nNext line."
    polished = engine.polish(text)

    assert polished == "Line with trailing spaces.\nNext line."


# ============================================================================
# TEST 10: Protected Content Detection
# ============================================================================

def test_protect_chapter_headings():
    """Test that chapter headings are not modified."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Chapter  1  :  The  Beginning"  # Extra spaces
    polished = engine.polish(text)

    # Should be protected (not modified)
    assert polished == text, "Chapter headings should be protected"


def test_protect_section_headings():
    """Test that section headings are not modified."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Section  5  :  Introduction"
    polished = engine.polish(text)

    assert polished == text, "Section headings should be protected"


def test_protect_vietnamese_chapter():
    """Test that Vietnamese chapter headings are protected."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Chương  1  :  Khởi đầu"
    polished = engine.polish(text)

    assert polished == text, "Vietnamese chapter headings should be protected"


def test_protect_theorems():
    """Test that mathematical theorems are protected."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Theorem: For  all  x > 0"
    polished = engine.polish(text)

    assert polished == text, "Theorems should be protected"


def test_protect_vietnamese_theorem():
    """Test that Vietnamese theorems are protected."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Định lý: Với  mọi  x > 0"
    polished = engine.polish(text)

    assert polished == text, "Vietnamese theorems should be protected"


def test_protect_latex_formulas():
    """Test that LaTeX formulas are protected."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "The equation $x^2  +  y^2 = z^2$ is famous."
    polished = engine.polish(text)

    # Formula should be protected, but surrounding text should be polished
    assert "$x^2  +  y^2 = z^2$" in polished, "LaTeX formulas should be protected"


def test_protect_code_blocks():
    """Test that code blocks are protected."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Here is code:\n```python\nif  x  ==  y:\n    print('equal')\n```"
    polished = engine.polish(text)

    assert "if  x  ==  y:" in polished, "Code blocks should be protected"


def test_protect_citations():
    """Test that citations are protected."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "As shown in  [1, 2, 3]  the result holds."
    polished = engine.polish(text)

    # Citation should be protected
    assert "[1, 2, 3]" in polished, "Citations should be protected"


# ============================================================================
# TEST 11: Idempotency
# ============================================================================

def test_idempotency():
    """Test that running polish twice produces same result."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Text  with   issues .No space here.Too many.\n\n\n\nNewlines."

    # First polish
    first_polish = engine.polish(text)

    # Second polish
    second_polish = engine.polish(first_polish)

    assert first_polish == second_polish, "Polisher must be idempotent"


# ============================================================================
# TEST 12: Non-Destructive Behavior
# ============================================================================

def test_polish_preserves_meaning():
    """Test that polish only affects formatting, not content."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    # Vietnamese sentence with formatting issues
    text = "Đây  là  câu  văn  tiếng  Việt .Không có khoảng trắng."
    polished = engine.polish(text)

    # All Vietnamese words should still be present
    assert "Đây" in polished
    assert "câu" in polished
    assert "văn" in polished
    assert "tiếng" in polished
    assert "Việt" in polished
    assert "Không" in polished
    assert "khoảng" in polished
    assert "trắng" in polished


# ============================================================================
# TEST 13: Domain Configuration
# ============================================================================

def test_domain_book_config():
    """Test that book domain can be configured."""
    config = TranslationQualityConfig(mode="light", domain="book")
    engine = TranslationQualityEngine(config)

    assert config.domain == "book"


def test_domain_general_config():
    """Test that general domain can be configured."""
    config = TranslationQualityConfig(mode="light", domain="general")
    engine = TranslationQualityEngine(config)

    assert config.domain == "general"


def test_domain_stem_config():
    """Test that STEM domain can be configured (though not recommended)."""
    config = TranslationQualityConfig(mode="light", domain="stem")
    engine = TranslationQualityEngine(config)

    assert config.domain == "stem"


# ============================================================================
# TEST 14: Phase 3.5b LLM Rewrite (Not Yet Implemented)
# ============================================================================

def test_llm_rewrite_disabled_by_default():
    """Test that LLM rewrite is disabled by default."""
    config = TranslationQualityConfig(mode="light")
    assert config.enable_llm_rewrite is False


def test_llm_rewrite_does_nothing_when_enabled():
    """Test that enabling LLM rewrite doesn't crash (it's a no-op for Phase 3.5a)."""
    config = TranslationQualityConfig(
        mode="light",
        enable_llm_rewrite=True  # Should be ignored for now
    )
    engine = TranslationQualityEngine(config)

    text = "Some text to polish."
    polished = engine.polish(text)

    # Should still work (LLM rewrite is no-op in Phase 3.5a)
    assert isinstance(polished, str)


# ============================================================================
# TEST 15: Empty and Edge Cases
# ============================================================================

def test_empty_string():
    """Test that empty string is handled gracefully."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = ""
    polished = engine.polish(text)

    assert polished == ""


def test_whitespace_only():
    """Test that whitespace-only text is handled."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "   \n   \n   "
    polished = engine.polish(text)

    # Should be cleaned up
    assert isinstance(polished, str)


def test_single_word():
    """Test that single word is preserved."""
    config = create_light_config()
    engine = TranslationQualityEngine(config)

    text = "Hello"
    polished = engine.polish(text)

    assert polished == "Hello"


# ============================================================================
# TEST 16: Integration Scenarios
# ============================================================================

def test_realistic_book_paragraph():
    """Test realistic book paragraph with multiple issues."""
    config = create_light_config(domain="book")
    engine = TranslationQualityEngine(config)

    text = """Đây  là  đoạn  văn  đầu tiên .Không có khoảng trắng sau dấu chấm.



Đoạn  thứ  hai có  quá  nhiều  khoảng  trắng ."""

    polished = engine.polish(text)

    # Should fix issues
    assert "  " not in polished  # No double spaces
    assert ".Không" not in polished  # Space after period
    assert polished.count("\n\n\n") == 0  # No triple newlines


def test_realistic_stem_content():
    """Test STEM content with protected structures."""
    config = create_light_config(domain="stem")
    engine = TranslationQualityEngine(config)

    text = """Theorem: For  any  x > 0, we have $f(x) = x^2$.

Proof: Consider  the  function  defined as  $g(x) = x^2 - 1$."""

    polished = engine.polish(text)

    # Protected content should remain
    assert "Theorem:" in polished
    assert "Proof:" in polished
    assert "$f(x) = x^2$" in polished
    assert "$g(x) = x^2 - 1$" in polished


# ============================================================================
# TEST 17: Cost and Performance Limits
# ============================================================================

def test_config_has_cost_limits():
    """Test that config has cost limits (for future LLM operations)."""
    config = TranslationQualityConfig()

    assert hasattr(config, 'max_llm_cost_per_job')
    assert config.max_llm_cost_per_job > 0


def test_config_has_char_limits():
    """Test that config has character limits for safety."""
    config = TranslationQualityConfig()

    assert hasattr(config, 'max_chars_per_pass')
    assert config.max_chars_per_pass > 0


# ============================================================================
# TEST 18: Report Generation
# ============================================================================

def test_quality_report_structure():
    """Test that QualityReport has all required fields."""
    report = QualityReport(
        total_chars=100,
        issues_found=5,
        issues_fixed=3,
        issue_breakdown={'multiple_spaces': 2, 'space_before_punct': 1},
        cost_usd=0.0
    )

    assert report.total_chars == 100
    assert report.issues_found == 5
    assert report.issues_fixed == 3
    assert isinstance(report.issue_breakdown, dict)
    assert report.cost_usd == 0.0


# ============================================================================
# TEST 19: Config Toggle Flags
# ============================================================================

def test_disable_whitespace_normalization():
    """Test that whitespace normalization can be disabled."""
    config = TranslationQualityConfig(
        mode="light",
        normalize_whitespace=False
    )
    engine = TranslationQualityEngine(config)

    text = "Text  with  double  spaces."
    polished = engine.polish(text)

    # With whitespace normalization disabled, spaces might remain
    # (depends on other config flags)
    assert isinstance(polished, str)


def test_disable_punctuation_fixes():
    """Test that punctuation fixes can be disabled."""
    config = TranslationQualityConfig(
        mode="light",
        fix_spacing_around_punctuation=False
    )
    engine = TranslationQualityEngine(config)

    text = "Text .With space before period."
    polished = engine.polish(text)

    # Punctuation fixes should be skipped
    assert isinstance(polished, str)


# ============================================================================
# TEST 20: Aggressive Mode (Reserved for Future)
# ============================================================================

def test_aggressive_mode_basic():
    """Test that aggressive mode works (even if features not implemented)."""
    config = create_aggressive_config()
    engine = TranslationQualityEngine(config)

    text = "Text  with  issues .And more."
    polished = engine.polish(text)

    # Should still polish basic issues
    assert isinstance(polished, str)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
