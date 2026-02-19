"""
Quality Gate Agent

THE ENFORCER - ensures book meets all quality standards before publishing.
"""

from typing import Dict, Any
from collections import Counter

from .base import BaseAgent, AgentContext
from ..models import BookBlueprint, QualityCheckResult


class QualityGateAgent(BaseAgent[BookBlueprint, QualityCheckResult]):
    """
    Agent 8: Quality Gate

    THE ENFORCER - ensures delivery quality:
    - Total word count within +/-5% of target
    - Chapter balance (each >= 80% of target)
    - All sections complete
    - Content quality checks
    - Structure integrity

    If checks fail, returns detailed issues for re-processing.
    """

    @property
    def name(self) -> str:
        return "QualityGate"

    @property
    def description(self) -> str:
        return "Verify book meets all quality and quantity standards"

    async def execute(
        self,
        input_data: BookBlueprint,
        context: AgentContext
    ) -> QualityCheckResult:
        blueprint = input_data

        context.report_progress("Running quality checks...", 0)

        issues = []
        recommendations = []

        # Check 1: Total Word Count
        context.report_progress("Checking total word count...", 10)
        word_check = self._check_total_words(blueprint)
        if not word_check["passed"]:
            issues.extend(word_check["issues"])
            recommendations.extend(word_check["recommendations"])

        # Check 2: Chapter Balance
        context.report_progress("Checking chapter balance...", 30)
        balance_check = self._check_chapter_balance(blueprint)
        if not balance_check["passed"]:
            issues.extend(balance_check["issues"])
            recommendations.extend(balance_check["recommendations"])

        # Check 3: Section Coverage
        context.report_progress("Checking section coverage...", 50)
        coverage_check = self._check_section_coverage(blueprint)
        if not coverage_check["passed"]:
            issues.extend(coverage_check["issues"])
            recommendations.extend(coverage_check["recommendations"])

        # Check 4: Content Quality
        context.report_progress("Checking content quality...", 70)
        quality_check = self._check_content_quality(blueprint)
        if not quality_check["passed"]:
            issues.extend(quality_check["issues"])
            recommendations.extend(quality_check["recommendations"])

        # Check 5: Structure Integrity
        context.report_progress("Checking structure integrity...", 90)
        structure_check = self._check_structure_integrity(blueprint)
        if not structure_check["passed"]:
            issues.extend(structure_check["issues"])
            recommendations.extend(structure_check["recommendations"])

        passed = len(issues) == 0

        result = QualityCheckResult(
            passed=passed,
            total_word_check=word_check,
            chapter_balance_check=balance_check,
            section_coverage_check=coverage_check,
            content_quality_check=quality_check,
            structure_integrity_check=structure_check,
            issues=issues,
            recommendations=recommendations,
        )

        if passed:
            context.report_progress("All quality checks passed!", 100)
        else:
            context.report_progress(f"{len(issues)} issues found", 100)

        return result

    def _check_total_words(self, blueprint: BookBlueprint) -> Dict[str, Any]:
        """Check total word count"""

        target = blueprint.target_words
        actual = blueprint.actual_words
        completion = blueprint.completion

        min_threshold = self.config.min_total_completion
        max_threshold = self.config.max_total_completion

        passed = min_threshold <= completion <= max_threshold

        issues = []
        recommendations = []

        if completion < min_threshold:
            gap = target - actual
            issues.append(f"Word count too low: {actual:,} / {target:,} ({completion:.1f}%)")
            recommendations.append(f"Need {gap:,} more words. Expand shortest sections.")
        elif completion > max_threshold:
            excess = actual - target
            issues.append(f"Word count too high: {actual:,} / {target:,} ({completion:.1f}%)")
            recommendations.append(f"Consider trimming {excess:,} words from longest sections.")

        return {
            "passed": passed,
            "target": target,
            "actual": actual,
            "completion": completion,
            "min_threshold": min_threshold,
            "max_threshold": max_threshold,
            "issues": issues,
            "recommendations": recommendations,
        }

    def _check_chapter_balance(self, blueprint: BookBlueprint) -> Dict[str, Any]:
        """Check chapter balance"""

        min_completion = self.config.chapter_balance_threshold

        chapter_stats = []
        issues = []
        recommendations = []

        for chapter in blueprint.all_chapters:
            chapter.update_word_count()
            completion = chapter.word_count.completion

            chapter_stats.append({
                "chapter": f"Chapter {chapter.number}: {chapter.title}",
                "target": chapter.word_count.target,
                "actual": chapter.word_count.actual,
                "completion": completion,
            })

            if completion < min_completion:
                gap = chapter.word_count.remaining
                issues.append(
                    f"Chapter {chapter.number} below threshold: {completion:.1f}% "
                    f"(min: {min_completion}%)"
                )
                recommendations.append(
                    f"Expand Chapter {chapter.number} by ~{gap:,} words"
                )

        passed = len(issues) == 0

        return {
            "passed": passed,
            "min_threshold": min_completion,
            "chapters": chapter_stats,
            "issues": issues,
            "recommendations": recommendations,
        }

    def _check_section_coverage(self, blueprint: BookBlueprint) -> Dict[str, Any]:
        """Check all sections are complete"""

        total = blueprint.total_sections
        complete = sum(
            1 for s in blueprint.all_sections
            if s.content and len(s.content) > 100
        )

        incomplete_sections = [
            s for s in blueprint.all_sections
            if not s.content or len(s.content) < 100
        ]

        passed = len(incomplete_sections) == 0

        issues = []
        recommendations = []

        for section in incomplete_sections[:5]:
            issues.append(f"Section {section.id} ({section.title}) is incomplete")
            recommendations.append(f"Write content for section {section.id}")

        if len(incomplete_sections) > 5:
            issues.append(f"...and {len(incomplete_sections) - 5} more incomplete sections")

        return {
            "passed": passed,
            "total_sections": total,
            "complete_sections": complete,
            "incomplete_count": len(incomplete_sections),
            "issues": issues,
            "recommendations": recommendations,
        }

    def _check_content_quality(self, blueprint: BookBlueprint) -> Dict[str, Any]:
        """Check content quality (repetition, coherence)"""

        issues = []
        recommendations = []

        all_content = " ".join(s.content for s in blueprint.all_sections if s.content)
        words = all_content.lower().split()

        # Check 4-word phrases for repetition
        phrases = [" ".join(words[i:i+4]) for i in range(len(words) - 3)]
        phrase_counts = Counter(phrases)

        repeated = [(phrase, count) for phrase, count in phrase_counts.items() if count > 5]

        if repeated:
            issues.append(f"Found {len(repeated)} repeated phrases (>5 occurrences)")
            recommendations.append("Review and vary repeated phrases")

        # Check for very short paragraphs
        short_para_count = 0
        for section in blueprint.all_sections:
            if section.content:
                paragraphs = section.content.split("\n\n")
                for para in paragraphs:
                    if len(para.split()) < 20:
                        short_para_count += 1

        if short_para_count > 20:
            issues.append(f"Found {short_para_count} very short paragraphs")
            recommendations.append("Expand or combine short paragraphs")

        passed = len(issues) == 0

        return {
            "passed": passed,
            "repetition_issues": len(repeated),
            "short_paragraphs": short_para_count,
            "issues": issues,
            "recommendations": recommendations,
        }

    def _check_structure_integrity(self, blueprint: BookBlueprint) -> Dict[str, Any]:
        """Check structure integrity"""

        issues = []
        recommendations = []

        if len(blueprint.parts) == 0:
            issues.append("No parts defined")
            recommendations.append("Create book structure with parts")

        if blueprint.total_chapters == 0:
            issues.append("No chapters defined")
            recommendations.append("Create chapters within parts")

        if blueprint.total_sections == 0:
            issues.append("No sections defined")
            recommendations.append("Create sections within chapters")

        if self.config.include_preface and not blueprint.front_matter.preface:
            issues.append("Preface is missing")
            recommendations.append("Generate preface")

        if self.config.include_conclusion and not blueprint.back_matter.conclusion:
            issues.append("Conclusion is missing")
            recommendations.append("Generate conclusion")

        passed = len(issues) == 0

        return {
            "passed": passed,
            "parts_count": len(blueprint.parts),
            "chapters_count": blueprint.total_chapters,
            "sections_count": blueprint.total_sections,
            "front_matter_complete": bool(blueprint.front_matter.preface),
            "back_matter_complete": bool(blueprint.back_matter.conclusion),
            "issues": issues,
            "recommendations": recommendations,
        }
