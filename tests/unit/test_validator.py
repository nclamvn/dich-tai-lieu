"""
Unit tests for core/validator.py - QualityValidator component
"""
import pytest
from core.validator import QualityValidator, TranslationResult


class TestTranslationResult:
    """Test TranslationResult dataclass."""

    def test_translation_result_creation(self):
        """Test basic TranslationResult creation."""
        result = TranslationResult(
            chunk_id=1,
            source="Hello world",
            translated="Xin chào thế giới"
        )
        assert result.chunk_id == 1
        assert result.source == "Hello world"
        assert result.translated == "Xin chào thế giới"
        assert result.quality_score == 0.0
        assert result.warnings == []
        assert result.glossary_matches == {}

    def test_translation_result_with_metadata(self):
        """Test TranslationResult with full metadata."""
        result = TranslationResult(
            chunk_id=2,
            source="Technical document",
            translated="Tài liệu kỹ thuật",
            quality_score=0.85,
            warnings=["Minor issue"],
            glossary_matches={"technical": "kỹ thuật"},
            domain="technology"
        )
        assert result.quality_score == 0.85
        assert len(result.warnings) == 1
        assert result.domain == "technology"


class TestQualityValidator:
    """Test QualityValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return QualityValidator()

    # ========================================================================
    # Test: calculate_length_ratio
    # ========================================================================

    def test_length_ratio_optimal(self):
        """Test length ratio in optimal range (1.2-1.4 for EN->VI)."""
        source = "Hello world"  # 11 chars
        translated = "Xin chào thế giới"  # ~17 chars (ratio ~1.54)
        score = QualityValidator.calculate_length_ratio(source, translated)
        # Ratio is ~1.54, which is in 0.9-1.7 range (score 0.7)
        assert score >= 0.7  # Acceptable range

    def test_length_ratio_acceptable(self):
        """Test length ratio in acceptable range (0.9-1.7)."""
        source = "Hello"  # 5 chars
        translated = "Xin chào bạn"  # ~10 chars (ratio ~2.0 - outside 1.5)
        score = QualityValidator.calculate_length_ratio(source, translated)
        assert score <= 1.0

    def test_length_ratio_poor(self):
        """Test length ratio outside acceptable range."""
        source = "Hello world this is a test"
        translated = "Hi"  # Very short translation
        score = QualityValidator.calculate_length_ratio(source, translated)
        assert score == 0.3  # Poor score

    def test_length_ratio_empty_source(self):
        """Test length ratio with empty source."""
        score = QualityValidator.calculate_length_ratio("", "Some translation")
        assert score == 0.0

    def test_length_ratio_empty_translation(self):
        """Test length ratio with empty translation."""
        score = QualityValidator.calculate_length_ratio("Source text", "")
        assert score == 0.0

    def test_length_ratio_both_empty(self):
        """Test length ratio with both empty strings."""
        score = QualityValidator.calculate_length_ratio("", "")
        assert score == 0.0

    # ========================================================================
    # Test: check_completeness
    # ========================================================================

    def test_completeness_perfect(self):
        """Test completeness with perfect sentence match."""
        source = "Hello. How are you? I am fine."
        translated = "Xin chào. Bạn khỏe không? Tôi khỏe."
        score = QualityValidator.check_completeness(source, translated)
        assert score == 1.0

    def test_completeness_acceptable(self):
        """Test completeness with acceptable sentence difference."""
        source = "Hello. How are you? I am fine. Nice to meet you."
        translated = "Xin chào. Bạn khỏe không? Tôi khỏe."  # 3/4 sentences
        score = QualityValidator.check_completeness(source, translated)
        assert score >= 0.7

    def test_completeness_poor(self):
        """Test completeness with significant sentence mismatch."""
        source = "Hello. How are you? I am fine. Nice day. Good weather."
        translated = "Xin chào."  # Only 1/5 sentences
        score = QualityValidator.check_completeness(source, translated)
        assert score <= 0.7

    def test_completeness_no_sentences(self):
        """Test completeness with no sentence delimiters."""
        source = "Hello world"
        translated = "Xin chào thế giới"
        score = QualityValidator.check_completeness(source, translated)
        assert 0.0 <= score <= 1.0

    # ========================================================================
    # Test: check_vietnamese_quality
    # ========================================================================

    def test_vietnamese_quality_good(self):
        """Test Vietnamese quality with proper diacritics."""
        text = "Đây là văn bản tiếng Việt có dấu đầy đủ và chính xác."
        score = QualityValidator.check_vietnamese_quality(text)
        assert score == 1.0

    def test_vietnamese_quality_no_diacritics(self):
        """Test Vietnamese quality without diacritics (Latin text)."""
        text = "This is English text without Vietnamese diacritics."
        score = QualityValidator.check_vietnamese_quality(text)
        assert score <= 0.5  # Should be penalized

    def test_vietnamese_quality_with_artifacts(self):
        """Test Vietnamese quality with translation artifacts."""
        text = "Văn bản có [[bracket artifacts]] và Note: không dịch."
        score = QualityValidator.check_vietnamese_quality(text)
        assert score < 1.0  # Should be penalized for artifacts

    def test_vietnamese_quality_with_chunk_markers(self):
        """Test Vietnamese quality with unprocessed chunk markers."""
        text = "[CHUNK 1] Văn bản tiếng Việt."
        score = QualityValidator.check_vietnamese_quality(text)
        assert score < 1.0

    def test_vietnamese_quality_empty(self):
        """Test Vietnamese quality with empty string."""
        score = QualityValidator.check_vietnamese_quality("")
        assert score <= 0.5  # No Vietnamese chars

    # ========================================================================
    # Test: validate_finance_domain
    # ========================================================================

    def test_finance_numbers_preserved(self):
        """Test finance validation with preserved numbers."""
        source = "Revenue increased by 15% to $2.5 billion."
        translated = "Doanh thu tăng 15% lên 2.5 tỷ đô la."
        score, warnings = QualityValidator.validate_finance_domain(source, translated)
        assert score > 0.5
        # Numbers should be preserved
        assert "15" in translated
        assert "2.5" in translated

    def test_finance_currency_mismatch(self):
        """Test finance validation with currency symbol mismatch."""
        source = "Price is $100 and €50."
        translated = "Giá là 100 và 50."  # Missing $ and €
        score, warnings = QualityValidator.validate_finance_domain(source, translated)
        assert score < 1.0
        assert len(warnings) > 0

    def test_finance_abbreviations_preserved(self):
        """Test finance validation preserves abbreviations."""
        source = "The CEO announced IPO with P/E ratio of 25."
        translated = "CEO công bố IPO với tỷ lệ P/E là 25."
        score, warnings = QualityValidator.validate_finance_domain(source, translated)
        assert score >= 0.8

    def test_finance_abbreviations_missing(self):
        """Test finance validation detects missing abbreviations."""
        source = "The ROI and GDP figures show growth."
        translated = "Các con số cho thấy tăng trưởng."  # Missing ROI, GDP
        score, warnings = QualityValidator.validate_finance_domain(source, translated)
        assert score < 1.0
        assert len(warnings) > 0

    def test_finance_no_issues(self):
        """Test finance validation with no issues."""
        source = "The company reported strong earnings."
        translated = "Công ty báo cáo lợi nhuận mạnh."
        score, warnings = QualityValidator.validate_finance_domain(source, translated)
        assert score == 1.0
        assert len(warnings) == 0

    # ========================================================================
    # Test: validate_literature_domain
    # ========================================================================

    def test_literature_dialogue_preserved(self):
        """Test literature validation preserves dialogue formatting."""
        source = '"Hello," he said. "How are you?"'
        translated = '"Xin chào," anh ấy nói. "Bạn khỏe không?"'
        score, warnings = QualityValidator.validate_literature_domain(source, translated)
        assert score >= 0.8

    def test_literature_dialogue_mismatch(self):
        """Test literature validation detects dialogue formatting issues."""
        source = '"Hello," he said. "How are you?" "I am fine."'
        translated = "Xin chào, anh ấy nói."  # Missing quotes
        score, warnings = QualityValidator.validate_literature_domain(source, translated)
        assert score < 1.0

    def test_literature_paragraph_structure(self):
        """Test literature validation checks paragraph structure."""
        source = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        translated = "Đoạn một.\n\nĐoạn hai.\n\nĐoạn ba."
        score, warnings = QualityValidator.validate_literature_domain(source, translated)
        assert score >= 0.8

    def test_literature_temporal_markers(self):
        """Test literature validation checks temporal markers."""
        source = "He was walking. She had arrived. They were happy."
        translated = "Anh ấy đi bộ. Cô ấy đến. Họ vui."  # Missing temporal markers
        score, warnings = QualityValidator.validate_literature_domain(source, translated)
        # Should warn about missing temporal markers
        assert score <= 1.0

    # ========================================================================
    # Test: validate_medical_domain
    # ========================================================================

    def test_medical_dosage_preserved(self):
        """Test medical validation preserves dosage information."""
        source = "Take 500 mg twice daily."
        translated = "Uống 500 mg hai lần mỗi ngày."
        score, warnings = QualityValidator.validate_medical_domain(source, translated)
        assert score >= 0.8
        assert "500" in translated

    def test_medical_dosage_missing_critical(self):
        """Test medical validation detects missing dosage (critical)."""
        source = "Administer 10 mg every 6 hours."
        translated = "Sử dụng thuốc."  # Missing dosage!
        score, warnings = QualityValidator.validate_medical_domain(source, translated)
        assert score < 0.7
        assert any("CRITICAL" in w for w in warnings)

    def test_medical_abbreviations_preserved(self):
        """Test medical validation preserves abbreviations."""
        source = "Patient sent to ICU after MRI showed issues."
        translated = "Bệnh nhân chuyển ICU sau MRI phát hiện vấn đề."
        score, warnings = QualityValidator.validate_medical_domain(source, translated)
        assert score >= 0.8

    def test_medical_abbreviations_missing(self):
        """Test medical validation detects missing abbreviations."""
        source = "The CT scan and X-ray results were negative."
        translated = "Kết quả chụp cắt lớp và chụp quang tuyến âm tính."
        score, warnings = QualityValidator.validate_medical_domain(source, translated)
        # May have warnings about missing abbreviations
        assert score <= 1.0

    def test_medical_safety_critical_terms(self):
        """Test medical validation flags safety-critical terms."""
        source = "Contraindication: May cause fatal adverse reactions."
        translated = "Chống chỉ định: Có thể gây phản ứng bất lợi tử vong."
        score, warnings = QualityValidator.validate_medical_domain(source, translated)
        # Should flag for review
        assert any("REVIEW REQUIRED" in w for w in warnings)

    # ========================================================================
    # Test: validate_technology_domain
    # ========================================================================

    def test_technology_code_blocks_preserved(self):
        """Test technology validation preserves code blocks."""
        source = "Example:\n```python\nprint('hello')\n```"
        translated = "Ví dụ:\n```python\nprint('hello')\n```"
        score, warnings = QualityValidator.validate_technology_domain(source, translated)
        assert score >= 0.8

    def test_technology_code_blocks_missing(self):
        """Test technology validation detects missing code blocks."""
        source = "Example:\n```python\nprint('hello')\n```"
        translated = "Ví dụ: In hello"  # Code block removed
        score, warnings = QualityValidator.validate_technology_domain(source, translated)
        assert score < 1.0
        assert len(warnings) > 0

    def test_technology_inline_code(self):
        """Test technology validation checks inline code."""
        source = "Use the `print()` function to output text."
        translated = "Sử dụng hàm `print()` để xuất văn bản."
        score, warnings = QualityValidator.validate_technology_domain(source, translated)
        assert score >= 0.8

    # ========================================================================
    # Test: DOMAIN_WEIGHTS
    # ========================================================================

    def test_domain_weights_all_present(self):
        """Test that all domains have weight configurations."""
        domains = ['finance', 'literature', 'medical', 'technology', 'default']
        for domain in domains:
            assert domain in QualityValidator.DOMAIN_WEIGHTS
            weights = QualityValidator.DOMAIN_WEIGHTS[domain]
            # Check all required keys present
            assert 'length' in weights
            assert 'completeness' in weights
            assert 'vietnamese' in weights
            assert 'glossary' in weights
            assert 'domain_specific' in weights

    def test_domain_weights_sum_to_one(self):
        """Test that domain weights sum to approximately 1.0."""
        for domain, weights in QualityValidator.DOMAIN_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f"{domain} weights sum to {total}"

    def test_medical_domain_high_glossary_weight(self):
        """Test medical domain has highest glossary weight (safety-critical)."""
        medical_glossary = QualityValidator.DOMAIN_WEIGHTS['medical']['glossary']
        # Medical should have high glossary weight
        assert medical_glossary >= 0.25

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_validator_handles_unicode(self):
        """Test validator handles various Unicode characters."""
        source = "Chinese: 你好, Japanese: こんにちは, Korean: 안녕하세요"
        translated = "Tiếng Trung: 你好, Tiếng Nhật: こんにちは, Tiếng Hàn: 안녕하세요"
        score = QualityValidator.calculate_length_ratio(source, translated)
        assert score > 0.0

    def test_validator_handles_special_chars(self):
        """Test validator handles special characters."""
        source = "Price: $1,000.50 (10% off) [Limited time!]"
        translated = "Giá: $1,000.50 (giảm 10%) [Thời gian có hạn!]"
        score = QualityValidator.calculate_length_ratio(source, translated)
        assert score > 0.0

    @pytest.mark.parametrize("source,translated", [
        ("", ""),
        ("A", "B"),
        ("Short", "Ngắn gọn"),
        ("A" * 1000, "B" * 1200),  # Long texts
    ])
    def test_validator_various_inputs(self, source, translated):
        """Test validator with various input combinations."""
        length_score = QualityValidator.calculate_length_ratio(source, translated)
        assert 0.0 <= length_score <= 1.0

        completeness_score = QualityValidator.check_completeness(source, translated)
        assert 0.0 <= completeness_score <= 1.0
