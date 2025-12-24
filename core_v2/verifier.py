"""
Quality Verifier - Claude Self-Verification

Claude verifies its own output against quality criteria.
No hardcoded rules - just intelligent review.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class QualityLevel(Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_REVISION = "needs_revision"
    POOR = "poor"


@dataclass
class VerificationResult:
    """Result of quality verification."""

    overall_quality: QualityLevel
    score: float  # 0.0 to 1.0

    # Dimension scores
    accuracy: float = 0.0
    fluency: float = 0.0
    style_match: float = 0.0
    terminology: float = 0.0
    formatting: float = 0.0

    # Issues found
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # Metadata
    verified_chunks: int = 0
    total_chunks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_quality": self.overall_quality.value,
            "score": self.score,
            "dimensions": {
                "accuracy": self.accuracy,
                "fluency": self.fluency,
                "style_match": self.style_match,
                "terminology": self.terminology,
                "formatting": self.formatting,
            },
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


VERIFICATION_PROMPT = """Review this translation for quality. Compare the source and translation.

Source ({source_lang}):
{source_text}

Translation ({target_lang}):
{translated_text}

Publishing Profile: {profile_name}

Rate each dimension from 0.0 to 1.0:
- accuracy: Does translation accurately convey the meaning?
- fluency: Does it read naturally in the target language?
- style_match: Does it match the expected style for this genre?
- terminology: Are domain-specific terms translated correctly?
- formatting: Is formatting preserved appropriately?

Respond in JSON:
{{
    "accuracy": 0.0-1.0,
    "fluency": 0.0-1.0,
    "style_match": 0.0-1.0,
    "terminology": 0.0-1.0,
    "formatting": 0.0-1.0,
    "issues": ["list of specific issues found"],
    "suggestions": ["list of improvement suggestions"]
}}
"""


class QualityVerifier:
    """
    Verifies translation quality using Claude.

    Strategy:
    - Sample verification for large documents
    - Full verification for critical sections
    - Claude judges against publishing standards
    """

    def __init__(self, llm_client: Any, sample_rate: float = 0.2):
        """
        Args:
            llm_client: LLM client with async chat method
            sample_rate: Fraction of chunks to verify (0.0-1.0)
        """
        self.llm_client = llm_client
        self.sample_rate = sample_rate

    async def verify(
        self,
        source_chunks: List[str],
        translated_chunks: List[str],
        source_lang: str,
        target_lang: str,
        profile_name: str = "general",
    ) -> VerificationResult:
        """
        Verify translation quality.

        Args:
            source_chunks: Original text chunks
            translated_chunks: Translated text chunks
            source_lang: Source language code
            target_lang: Target language code
            profile_name: Publishing profile used

        Returns:
            VerificationResult with quality assessment
        """
        if len(source_chunks) != len(translated_chunks):
            return VerificationResult(
                overall_quality=QualityLevel.POOR,
                score=0.0,
                issues=["Chunk count mismatch between source and translation"],
            )

        # Select chunks to verify
        total = len(source_chunks)
        sample_size = max(1, int(total * self.sample_rate))

        # Always include first, last, and random middle chunks
        indices = self._select_sample_indices(total, sample_size)

        # Verify selected chunks
        results = []
        for idx in indices:
            result = await self._verify_chunk(
                source_chunks[idx],
                translated_chunks[idx],
                source_lang,
                target_lang,
                profile_name,
            )
            results.append(result)

        # Aggregate results
        return self._aggregate_results(results, len(indices), total)

    def _select_sample_indices(self, total: int, sample_size: int) -> List[int]:
        """Select indices for sample verification."""
        if total <= sample_size:
            return list(range(total))

        indices = [0, total - 1]  # First and last

        # Add evenly spaced middle samples
        if sample_size > 2:
            step = total // (sample_size - 1)
            for i in range(1, sample_size - 1):
                idx = i * step
                if idx not in indices:
                    indices.append(idx)

        return sorted(indices)[:sample_size]

    async def _verify_chunk(
        self,
        source: str,
        translated: str,
        source_lang: str,
        target_lang: str,
        profile_name: str,
    ) -> Dict[str, Any]:
        """Verify a single chunk."""
        prompt = VERIFICATION_PROMPT.format(
            source_lang=source_lang,
            source_text=source[:2000],  # Limit size
            target_lang=target_lang,
            translated_text=translated[:2000],
            profile_name=profile_name,
        )

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            return json.loads(response.content)

        except Exception as e:
            return {
                "accuracy": 0.5,
                "fluency": 0.5,
                "style_match": 0.5,
                "terminology": 0.5,
                "formatting": 0.5,
                "issues": [f"Verification error: {str(e)}"],
                "suggestions": [],
            }

    def _aggregate_results(
        self,
        results: List[Dict],
        verified: int,
        total: int,
    ) -> VerificationResult:
        """Aggregate verification results."""
        if not results:
            return VerificationResult(
                overall_quality=QualityLevel.ACCEPTABLE,
                score=0.5,
            )

        # Average scores
        dims = ["accuracy", "fluency", "style_match", "terminology", "formatting"]
        scores = {d: sum(r.get(d, 0.5) for r in results) / len(results) for d in dims}

        # Overall score (weighted average)
        weights = {"accuracy": 0.3, "fluency": 0.25, "style_match": 0.2, "terminology": 0.15, "formatting": 0.1}
        overall = sum(scores[d] * weights[d] for d in dims)

        # Determine quality level
        if overall >= 0.9:
            quality = QualityLevel.EXCELLENT
        elif overall >= 0.75:
            quality = QualityLevel.GOOD
        elif overall >= 0.6:
            quality = QualityLevel.ACCEPTABLE
        elif overall >= 0.4:
            quality = QualityLevel.NEEDS_REVISION
        else:
            quality = QualityLevel.POOR

        # Collect issues and suggestions
        all_issues = []
        all_suggestions = []
        for r in results:
            all_issues.extend(r.get("issues", []))
            all_suggestions.extend(r.get("suggestions", []))

        return VerificationResult(
            overall_quality=quality,
            score=overall,
            accuracy=scores["accuracy"],
            fluency=scores["fluency"],
            style_match=scores["style_match"],
            terminology=scores["terminology"],
            formatting=scores["formatting"],
            issues=list(set(all_issues))[:10],
            suggestions=list(set(all_suggestions))[:5],
            verified_chunks=verified,
            total_chunks=total,
        )


def quick_verify(source: str, translated: str) -> bool:
    """
    Quick verification without LLM (for testing).

    Basic sanity checks:
    - Translation not empty
    - Translation not same as source (unless very short)
    - Reasonable length ratio
    """
    if not translated or not translated.strip():
        return False

    if len(source) > 100 and source == translated:
        return False

    # Check length ratio (translated should be within 0.5x to 3x of source)
    ratio = len(translated) / max(len(source), 1)
    if ratio < 0.3 or ratio > 5:
        return False

    return True
