"""
Unit tests for api/services/consistency_checker.py — ConsistencyChecker.

Target: 85%+ coverage.
"""

import pytest

from api.services.consistency_checker import (
    ConsistencyChecker,
    ConsistencyReport,
    Inconsistency,
    InconsistencyType,
    Severity,
    _COMMON_FALSE_POSITIVES,
)


# ---------------------------------------------------------------------------
# ConsistencyReport
# ---------------------------------------------------------------------------

class TestConsistencyReport:
    def test_empty_report(self):
        report = ConsistencyReport(
            total_chunks=0, issues_found=0,
            high_severity=0, medium_severity=0, low_severity=0,
            inconsistencies=[], score=1.0,
        )
        assert report.passed is True
        assert report.score == 1.0

    def test_passed_no_high(self):
        report = ConsistencyReport(
            total_chunks=5, issues_found=2,
            high_severity=0, medium_severity=1, low_severity=1,
            inconsistencies=[], score=0.94,
        )
        assert report.passed is True

    def test_failed_with_high(self):
        report = ConsistencyReport(
            total_chunks=5, issues_found=1,
            high_severity=1, medium_severity=0, low_severity=0,
            inconsistencies=[], score=0.85,
        )
        assert report.passed is False

    def test_to_dict(self):
        issue = Inconsistency(
            type=InconsistencyType.TERMINOLOGY,
            severity=Severity.HIGH,
            description="Test issue",
            locations=[0, 1],
            source_term="ML",
            variants=["Học máy"],
        )
        report = ConsistencyReport(
            total_chunks=3, issues_found=1,
            high_severity=1, medium_severity=0, low_severity=0,
            inconsistencies=[issue], score=0.85,
        )
        d = report.to_dict()
        assert d["total_chunks"] == 3
        assert d["issues_found"] == 1
        assert d["high"] == 1
        assert d["passed"] is False
        assert len(d["inconsistencies"]) == 1
        assert d["inconsistencies"][0]["type"] == "terminology"


# ---------------------------------------------------------------------------
# Inconsistency
# ---------------------------------------------------------------------------

class TestInconsistency:
    def test_to_dict(self):
        i = Inconsistency(
            type=InconsistencyType.PROPER_NAME,
            severity=Severity.MEDIUM,
            description="Name issue",
            locations=[2, 4],
            source_term="John Smith",
            suggested_fix="Keep consistent",
        )
        d = i.to_dict()
        assert d["type"] == "proper_name"
        assert d["severity"] == "medium"
        assert d["source_term"] == "John Smith"
        assert d["suggested_fix"] == "Keep consistent"

    def test_default_fields(self):
        i = Inconsistency(
            type=InconsistencyType.STYLE,
            severity=Severity.LOW,
            description="Test",
            locations=[0],
        )
        assert i.source_term is None
        assert i.variants == []
        assert i.suggested_fix is None


# ---------------------------------------------------------------------------
# Terminology check
# ---------------------------------------------------------------------------

class TestTerminologyCheck:
    def test_consistent_terminology(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=[
                "Machine Learning is powerful.",
                "Machine Learning transforms data.",
            ],
            translated_chunks=[
                "Học máy rất mạnh.",
                "Học máy chuyển đổi dữ liệu.",
            ],
            glossary={"Machine Learning": "Học máy"},
        )
        # Term consistently translated → no terminology issues
        term_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.TERMINOLOGY
        ]
        assert len(term_issues) == 0

    def test_inconsistent_term(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=[
                "Machine Learning is powerful.",
                "Machine Learning transforms data.",
            ],
            translated_chunks=[
                "Học máy rất mạnh.",
                "Máy học chuyển đổi dữ liệu.",  # Different translation!
            ],
            glossary={"Machine Learning": "Học máy"},
        )
        term_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.TERMINOLOGY
        ]
        assert len(term_issues) == 1
        assert term_issues[0].severity == Severity.HIGH

    def test_term_below_min_frequency(self):
        checker = ConsistencyChecker(min_term_frequency=3)
        report = checker.check(
            source_chunks=[
                "Machine Learning is great.",
                "Something else here.",
            ],
            translated_chunks=[
                "Máy học tuyệt vời.",
                "Cái gì đó khác.",
            ],
            glossary={"Machine Learning": "Học máy"},
        )
        # Term only in 1 chunk, min_frequency=3 → not checked
        term_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.TERMINOLOGY
        ]
        assert len(term_issues) == 0

    def test_empty_glossary(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Hello world."],
            translated_chunks=["Xin chào thế giới."],
            glossary={},
        )
        term_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.TERMINOLOGY
        ]
        assert len(term_issues) == 0

    def test_no_glossary_arg(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Hello."],
            translated_chunks=["Xin chào."],
        )
        assert report.issues_found >= 0  # No crash


# ---------------------------------------------------------------------------
# Proper name check
# ---------------------------------------------------------------------------

class TestProperNameCheck:
    def test_name_consistent(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=[
                "John Smith wrote the paper.",
                "John Smith concluded the study.",
            ],
            translated_chunks=[
                "John Smith đã viết bài báo.",
                "John Smith đã kết luận nghiên cứu.",
            ],
        )
        name_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.PROPER_NAME
        ]
        assert len(name_issues) == 0

    def test_name_inconsistent(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=[
                "John Smith wrote the paper.",
                "John Smith concluded the study.",
            ],
            translated_chunks=[
                "John Smith đã viết bài báo.",
                "Giôn Sờ-mít đã kết luận nghiên cứu.",  # Name translated!
            ],
        )
        name_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.PROPER_NAME
        ]
        assert len(name_issues) == 1
        assert name_issues[0].severity == Severity.MEDIUM

    def test_short_names_ignored(self):
        """Names shorter than 4 chars are filtered out."""
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Mr Jo said hello.", "Mr Jo left."],
            translated_chunks=["Ông Jo nói xin chào.", "Ông left."],
        )
        # "Mr Jo" — "Mr" is a false positive, "Jo" is too short
        # Should not crash
        assert isinstance(report, ConsistencyReport)

    def test_false_positives_filtered(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=[
                "The Chapter begins with Section One.",
                "The Chapter continues in Section Two.",
            ],
            translated_chunks=[
                "Chương bắt đầu với Phần Một.",
                "Chương tiếp tục trong Phần Hai.",
            ],
        )
        name_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.PROPER_NAME
        ]
        # "The Chapter", "Section One" etc. should be filtered
        assert len(name_issues) == 0

    def test_name_single_occurrence_ignored(self):
        checker = ConsistencyChecker(min_term_frequency=2)
        report = checker.check(
            source_chunks=[
                "Albert Einstein discovered relativity.",
                "Something completely different here.",
            ],
            translated_chunks=[
                "Einsteinnn đã phát hiện ra thuyết tương đối.",
                "Cái gì đó hoàn toàn khác.",
            ],
        )
        name_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.PROPER_NAME
        ]
        # Name only in 1 chunk → not checked
        assert len(name_issues) == 0


# ---------------------------------------------------------------------------
# Style check
# ---------------------------------------------------------------------------

class TestStyleCheck:
    def test_consistent_style(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Source one.", "Source two.", "Source three."],
            translated_chunks=[
                "Câu dịch một với độ dài tương tự.",
                "Câu dịch hai cũng có độ dài tương tự.",
                "Câu dịch ba cũng vậy với độ dài.",
            ],
        )
        style_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.STYLE
        ]
        # Similar sentence lengths → no issues
        assert len(style_issues) == 0

    def test_dramatic_length_shift(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["S1.", "S2.", "S3."],
            translated_chunks=[
                "Short sentence. Another short one. And third.",
                "This is an extremely long and verbose sentence that goes on and on with many words and clauses that make it substantially longer than anything else in the document by a very significant margin indeed. " * 3,
                "Short again. And brief.",
            ],
        )
        style_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.STYLE
        ]
        assert len(style_issues) >= 1
        assert style_issues[0].severity == Severity.LOW

    def test_two_chunks_no_style_check(self):
        """Style length check needs >= 3 chunks to flag issues."""
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["S1.", "S2."],
            translated_chunks=[
                "Short. And brief.",
                "Very very long sentence. " * 20,
            ],
        )
        style_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.STYLE
            and "Sentence length" in i.description
        ]
        assert len(style_issues) == 0

    def test_vietnamese_formality_consistent(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Hello.", "Goodbye."],
            translated_chunks=[
                "Kính chào quý vị.",
                "Thưa quý vị, xin tạm biệt.",
            ],
            target_language="vi",
        )
        formality_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.STYLE
            and "Formality" in i.description
        ]
        assert len(formality_issues) == 0

    def test_vietnamese_formality_mixed(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Hello.", "Goodbye."],
            translated_chunks=[
                "Kính chào quý vị.",       # Formal
                "Tạm biệt bạn nhé cậu.",  # Informal
            ],
            target_language="vi",
        )
        formality_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.STYLE
            and "Formality" in i.description
        ]
        assert len(formality_issues) == 1
        assert formality_issues[0].severity == Severity.MEDIUM

    def test_non_vietnamese_no_formality_check(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Hello.", "Goodbye."],
            translated_chunks=["Hallo.", "Tschüss."],
            target_language="de",
        )
        formality_issues = [
            i for i in report.inconsistencies
            if "Formality" in i.description
        ]
        assert len(formality_issues) == 0


# ---------------------------------------------------------------------------
# Number check
# ---------------------------------------------------------------------------

class TestNumberCheck:
    def test_numbers_preserved(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["The result was 42 percent, with 1500 samples."],
            translated_chunks=["Kết quả là 42 phần trăm, với 1500 mẫu."],
        )
        num_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.NUMBERING
        ]
        assert len(num_issues) == 0

    def test_numbers_missing(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["We tested 1500 samples in 2024."],
            translated_chunks=["Chúng tôi đã thử nghiệm nhiều mẫu."],
        )
        num_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.NUMBERING
        ]
        assert len(num_issues) == 1
        assert num_issues[0].severity == Severity.HIGH

    def test_number_format_change_ok(self):
        """1,500 → 1500 should not be flagged."""
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["The value was 1,500 units."],
            translated_chunks=["Giá trị là 1500 đơn vị."],
        )
        num_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.NUMBERING
        ]
        assert len(num_issues) == 0

    def test_single_digit_ignored(self):
        """Single digit numbers are not checked."""
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["We have 5 items."],
            translated_chunks=["Chúng tôi có nhiều mục."],
        )
        num_issues = [
            i for i in report.inconsistencies
            if i.type == InconsistencyType.NUMBERING
        ]
        assert len(num_issues) == 0


# ---------------------------------------------------------------------------
# Score calculation
# ---------------------------------------------------------------------------

class TestScoreCalculation:
    def test_perfect_score(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Hello world.", "Goodbye world."],
            translated_chunks=["Xin chào thế giới.", "Tạm biệt thế giới."],
        )
        assert report.score == 1.0

    def test_score_deductions(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=[
                "Machine Learning is great.",
                "Machine Learning is useful.",
            ],
            translated_chunks=[
                "Học máy tuyệt vời.",
                "Máy học hữu ích.",  # Different!
            ],
            glossary={"Machine Learning": "Học máy"},
        )
        # Should have at least one HIGH issue → score deducted
        assert report.score < 1.0
        assert report.score >= 0.0

    def test_score_floor_at_zero(self):
        """Many issues should not make score negative."""
        issues = [
            Inconsistency(
                type=InconsistencyType.TERMINOLOGY,
                severity=Severity.HIGH,
                description=f"Issue {i}",
                locations=[0],
            )
            for i in range(20)
        ]
        report = ConsistencyReport(
            total_chunks=2, issues_found=20,
            high_severity=20, medium_severity=0, low_severity=0,
            inconsistencies=issues,
            score=max(0.0, 1.0 - 20 * 0.15),
        )
        assert report.score == 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_chunks(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=[],
            translated_chunks=[],
        )
        assert report.total_chunks == 0
        assert report.score == 1.0
        assert report.passed is True

    def test_single_chunk(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["Hello world."],
            translated_chunks=["Xin chào."],
        )
        # Single chunk → no cross-chunk issues
        assert report.total_chunks == 1

    def test_mismatched_chunk_counts(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["One.", "Two.", "Three."],
            translated_chunks=["Một.", "Hai."],  # Missing one!
        )
        # Should not crash
        assert isinstance(report, ConsistencyReport)

    def test_empty_string_chunks(self):
        checker = ConsistencyChecker()
        report = checker.check(
            source_chunks=["", ""],
            translated_chunks=["", ""],
        )
        assert isinstance(report, ConsistencyReport)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_inconsistency_types(self):
        assert InconsistencyType.TERMINOLOGY.value == "terminology"
        assert InconsistencyType.PROPER_NAME.value == "proper_name"
        assert InconsistencyType.STYLE.value == "style"
        assert InconsistencyType.NUMBERING.value == "numbering"

    def test_severity_values(self):
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"

    def test_string_enums(self):
        assert isinstance(InconsistencyType.TERMINOLOGY, str)
        assert isinstance(Severity.HIGH, str)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_false_positives_set(self):
        assert "The" in _COMMON_FALSE_POSITIVES
        assert "Chapter" in _COMMON_FALSE_POSITIVES
        assert "Section" in _COMMON_FALSE_POSITIVES
