"""
Content Analyzer - Fine-tuned Thresholds
AI Publisher Pro

Analyzes content to route to appropriate model tier.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .tiered_config import ContentType, TieredConfig, MODELS


@dataclass
class ContentAnalysis:
    """Result of content analysis"""
    content_type: ContentType
    confidence: float

    # Detected features
    has_math: bool = False
    has_code: bool = False
    has_table: bool = False
    has_formatting: bool = False

    # Counts
    math_symbols: int = 0
    latex_patterns: int = 0
    code_keywords: int = 0
    table_indicators: int = 0

    # Metrics
    text_length: int = 0
    complexity_score: float = 0.0

    # Recommended model
    recommended_model: str = "gpt-4o-mini"
    recommended_temperature: float = 0.3


class ContentAnalyzer:
    """
    Analyzes content to determine optimal model routing.

    Fine-tuned thresholds based on extensive testing.
    """

    # =========================================
    # Detection Patterns
    # =========================================

    # Math symbols (Unicode)
    MATH_SYMBOLS = set(
        '∫∑∂∞√≈≤≥±×÷∈∉∀∃∅∩∪⊂⊃⊆⊇'  # Set theory, calculus
        'αβγδεζηθικλμνξοπρστυφχψω'    # Greek lowercase
        'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'    # Greek uppercase
        '→←↔⇒⇐⇔'                      # Arrows
        '≡≠≪≫∝∞'                      # Relations
        '∇∆∂'                         # Operators
    )

    # LaTeX patterns
    LATEX_PATTERNS = [
        r'\\frac\{',
        r'\\int',
        r'\\sum',
        r'\\prod',
        r'\\lim',
        r'\\sqrt',
        r'\\partial',
        r'\\infty',
        r'\\alpha|\\beta|\\gamma|\\delta',
        r'\\begin\{equation\}',
        r'\\begin\{align\}',
        r'\$\$.*\$\$',
        r'\$[^$]+\$',
        r'\\left[(\[{]',
        r'\\right[)\]}]',
        r'\\mathbb\{',
        r'\\mathcal\{',
        r'\\vec\{',
        r'\\hat\{',
        r'\\overline\{',
    ]

    # Code keywords
    CODE_KEYWORDS = [
        r'\bdef\s+\w+\s*\(',
        r'\bfunction\s+\w+\s*\(',
        r'\bclass\s+\w+',
        r'\bimport\s+\w+',
        r'\bfrom\s+\w+\s+import',
        r'\breturn\s+',
        r'\bif\s+__name__\s*==',
        r'#!/',
        r'```\w*\n',
        r'\bconst\s+\w+\s*=',
        r'\blet\s+\w+\s*=',
        r'\bvar\s+\w+\s*=',
        r'\bpublic\s+\w+',
        r'\bprivate\s+\w+',
        r'\bstatic\s+\w+',
        r'=>',
        r'\basync\s+',
        r'\bawait\s+',
    ]

    # Table indicators
    TABLE_INDICATORS = [
        r'\|[-=]+\|',           # |---|
        r'\+[-=]+\+',           # +---+
        r'│',                   # Box drawing
        r'┌|┐|└|┘|├|┤|┬|┴|┼',  # Box corners
        r'─|━',                 # Horizontal lines
        r'\|\s*\w+\s*\|',       # | text |
    ]

    # Formatting indicators
    FORMAT_INDICATORS = [
        r'^#{1,6}\s+',          # Markdown headers
        r'^\*{1,3}[^*]+\*{1,3}', # Bold/italic
        r'^[-*+]\s+',           # Lists
        r'^\d+\.\s+',           # Numbered lists
        r'^\>\s+',              # Blockquotes
        r'\[.+\]\(.+\)',        # Links
    ]

    def __init__(self, config: Optional[TieredConfig] = None):
        self.config = config or TieredConfig()

        # Compile patterns for efficiency
        self._latex_re = [re.compile(p, re.IGNORECASE) for p in self.LATEX_PATTERNS]
        self._code_re = [re.compile(p, re.MULTILINE) for p in self.CODE_KEYWORDS]
        self._table_re = [re.compile(p, re.MULTILINE) for p in self.TABLE_INDICATORS]
        self._format_re = [re.compile(p, re.MULTILINE) for p in self.FORMAT_INDICATORS]

    def analyze(self, text: str) -> ContentAnalysis:
        """
        Analyze content and determine optimal routing.

        Args:
            text: Content to analyze

        Returns:
            ContentAnalysis with recommendations
        """
        if not text or not text.strip():
            return ContentAnalysis(
                content_type=ContentType.PLAIN_TEXT,
                confidence=1.0,
                text_length=0,
                recommended_model=self.config.default_model
            )

        # Count features
        math_symbols = self._count_math_symbols(text)
        latex_patterns = self._count_latex_patterns(text)
        code_keywords = self._count_code_keywords(text)
        table_indicators = self._count_table_indicators(text)
        format_indicators = self._count_format_indicators(text)

        text_length = len(text)

        # Calculate ratios
        math_ratio = math_symbols / max(text_length, 1)

        # Determine content type based on thresholds
        content_type = self._determine_content_type(
            math_symbols=math_symbols,
            latex_patterns=latex_patterns,
            code_keywords=code_keywords,
            table_indicators=table_indicators,
            format_indicators=format_indicators,
            text_length=text_length,
            math_ratio=math_ratio
        )

        # Calculate complexity score
        complexity_score = self._calculate_complexity(
            math_symbols=math_symbols,
            latex_patterns=latex_patterns,
            code_keywords=code_keywords,
            table_indicators=table_indicators,
            text_length=text_length
        )

        # Get recommended model
        model_config = self.config.get_model_for_content(content_type)
        temperature = self.config.get_temperature(content_type)

        # Calculate confidence
        confidence = self._calculate_confidence(
            content_type=content_type,
            complexity_score=complexity_score,
            text_length=text_length
        )

        return ContentAnalysis(
            content_type=content_type,
            confidence=confidence,
            has_math=(math_symbols > 0 or latex_patterns > 0),
            has_code=(code_keywords >= self.config.code_keyword_count),
            has_table=(table_indicators >= self.config.table_indicator_count),
            has_formatting=(format_indicators > 0),
            math_symbols=math_symbols,
            latex_patterns=latex_patterns,
            code_keywords=code_keywords,
            table_indicators=table_indicators,
            text_length=text_length,
            complexity_score=complexity_score,
            recommended_model=model_config.model_id,
            recommended_temperature=temperature
        )

    def _count_math_symbols(self, text: str) -> int:
        """Count math symbols in text"""
        return sum(1 for c in text if c in self.MATH_SYMBOLS)

    def _count_latex_patterns(self, text: str) -> int:
        """Count LaTeX patterns in text"""
        count = 0
        for pattern in self._latex_re:
            count += len(pattern.findall(text))
        return count

    def _count_code_keywords(self, text: str) -> int:
        """Count code keywords in text"""
        count = 0
        for pattern in self._code_re:
            count += len(pattern.findall(text))
        return count

    def _count_table_indicators(self, text: str) -> int:
        """Count table indicators in text"""
        count = 0
        for pattern in self._table_re:
            count += len(pattern.findall(text))
        return count

    def _count_format_indicators(self, text: str) -> int:
        """Count formatting indicators in text"""
        count = 0
        for pattern in self._format_re:
            count += len(pattern.findall(text))
        return count

    def _determine_content_type(
        self,
        math_symbols: int,
        latex_patterns: int,
        code_keywords: int,
        table_indicators: int,
        format_indicators: int,
        text_length: int,
        math_ratio: float
    ) -> ContentType:
        """Determine content type based on analysis"""

        # Complex math: high math ratio OR many LaTeX patterns
        if (math_ratio > self.config.math_symbol_ratio or
            latex_patterns >= self.config.latex_pattern_count * 2):
            return ContentType.MATH_COMPLEX

        # Simple math: some math symbols or LaTeX
        if (math_symbols > 5 or
            latex_patterns >= self.config.latex_pattern_count):
            return ContentType.MATH_SIMPLE

        # Code: significant code keywords
        if code_keywords >= self.config.code_keyword_count:
            return ContentType.CODE

        # Table: table indicators
        if table_indicators >= self.config.table_indicator_count:
            return ContentType.TABLE

        # Formatted text: has formatting but not code/math
        if format_indicators > 2:
            return ContentType.FORMATTED_TEXT

        # Check for mixed content
        indicators = sum([
            1 if math_symbols > 2 else 0,
            1 if code_keywords > 0 else 0,
            1 if table_indicators > 0 else 0,
            1 if format_indicators > 0 else 0
        ])

        if indicators >= 2:
            return ContentType.MIXED

        # Default: plain text
        return ContentType.PLAIN_TEXT

    def _calculate_complexity(
        self,
        math_symbols: int,
        latex_patterns: int,
        code_keywords: int,
        table_indicators: int,
        text_length: int
    ) -> float:
        """Calculate complexity score (0-1)"""

        # Weighted scoring
        score = 0.0

        # Math contribution (highest weight)
        math_score = min((math_symbols + latex_patterns * 5) / 50, 1.0)
        score += math_score * 0.4

        # Code contribution
        code_score = min(code_keywords / 10, 1.0)
        score += code_score * 0.3

        # Table contribution
        table_score = min(table_indicators / 5, 1.0)
        score += table_score * 0.2

        # Length contribution (longer = potentially more complex)
        length_score = min(text_length / 2000, 1.0)
        score += length_score * 0.1

        return min(score, 1.0)

    def _calculate_confidence(
        self,
        content_type: ContentType,
        complexity_score: float,
        text_length: int
    ) -> float:
        """Calculate confidence in the classification"""

        # Base confidence
        confidence = 0.8

        # Higher confidence for plain text (most common)
        if content_type == ContentType.PLAIN_TEXT:
            confidence = 0.95

        # Lower confidence for mixed content
        elif content_type == ContentType.MIXED:
            confidence = 0.7

        # Adjust for text length (very short = less confident)
        if text_length < 50:
            confidence *= 0.8
        elif text_length < 100:
            confidence *= 0.9

        return confidence

    def analyze_batch(self, texts: List[str]) -> List[ContentAnalysis]:
        """Analyze multiple texts"""
        return [self.analyze(text) for text in texts]

    def get_model_distribution(
        self,
        analyses: List[ContentAnalysis]
    ) -> Dict[str, int]:
        """Get distribution of recommended models"""
        distribution = {}
        for a in analyses:
            model = a.recommended_model
            distribution[model] = distribution.get(model, 0) + 1
        return distribution

    def estimate_batch_cost(
        self,
        analyses: List[ContentAnalysis],
        avg_tokens_per_page: int = 800
    ) -> Dict[str, float]:
        """Estimate cost for a batch of content"""

        total_tokens = 0
        model_tokens = {}

        for a in analyses:
            tokens = avg_tokens_per_page
            total_tokens += tokens

            model = a.recommended_model
            model_tokens[model] = model_tokens.get(model, 0) + tokens

        # Calculate cost per model
        total_cost = 0
        cost_breakdown = {}

        for model_id, tokens in model_tokens.items():
            # Find model config
            model_config = None
            for m in MODELS.values():
                if m.model_id == model_id:
                    model_config = m
                    break

            if model_config:
                input_cost = (tokens / 1_000_000) * model_config.input_cost
                output_cost = (tokens / 1_000_000) * model_config.output_cost
                model_cost = input_cost + output_cost

                cost_breakdown[model_id] = {
                    "tokens": tokens,
                    "cost": round(model_cost, 4)
                }
                total_cost += model_cost

        return {
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 2),
            "cost_per_page": round(total_cost / len(analyses), 4) if analyses else 0,
            "model_breakdown": cost_breakdown
        }


# =========================================
# Quick Test
# =========================================

def test_analyzer():
    """Test the analyzer with sample content"""

    analyzer = ContentAnalyzer()

    samples = {
        "Plain text": """
        Hôm nay trời đẹp quá. Tôi đi dạo trong công viên
        và thấy rất nhiều hoa đẹp.
        """,

        "Math simple": """
        The equation E = mc² describes the relationship
        between energy and mass. We also know that F = ma.
        """,

        "Math complex": """
        Consider the integral:
        $$\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$

        Using Fubini's theorem with ∑_{n=1}^{∞} and ∂f/∂x...
        """,

        "Code": """
        def calculate_sum(numbers):
            total = 0
            for n in numbers:
                total += n
            return total

        if __name__ == "__main__":
            result = calculate_sum([1, 2, 3])
        """,

        "Table": """
        | Name    | Age | City     |
        |---------|-----|----------|
        | Alice   | 25  | New York |
        | Bob     | 30  | London   |
        """,

        "Mixed": """
        # Machine Learning Formula

        The loss function is: $L = \\frac{1}{n}\\sum_{i=1}^{n}(y_i - \\hat{y}_i)^2$

        ```python
        def compute_loss(y_true, y_pred):
            return np.mean((y_true - y_pred) ** 2)
        ```
        """
    }

    print("\n📊 Content Analysis Test")
    print("=" * 70)

    for name, text in samples.items():
        analysis = analyzer.analyze(text)
        print(f"\n{name}:")
        print(f"  Type: {analysis.content_type.value}")
        print(f"  Model: {analysis.recommended_model}")
        print(f"  Confidence: {analysis.confidence:.2f}")
        print(f"  Complexity: {analysis.complexity_score:.2f}")
        print(f"  Math: {analysis.math_symbols} symbols, {analysis.latex_patterns} LaTeX")
        print(f"  Code: {analysis.code_keywords} keywords")
        print(f"  Table: {analysis.table_indicators} indicators")


if __name__ == "__main__":
    test_analyzer()
