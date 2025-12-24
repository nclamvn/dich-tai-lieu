"""
Document Analyzer - Smart Detection for Extraction Routing

Analyzes PDF to determine the best extraction strategy:
- FAST_TEXT: Native text PDFs (novels, articles) → PyMuPDF (FREE, 0.1s/page)
- HYBRID: Mixed content (text + some tables/images) → PyMuPDF + selective Vision
- FULL_VISION: Scanned/complex PDFs → Full Vision API

Performance Impact:
- 700 pages text-only: 3 hours → 8-10 minutes (95% faster)
- Cost: $15-30 → $0.50-1 (97% cheaper)
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class ExtractionStrategy(Enum):
    """Extraction strategy based on document analysis"""
    FAST_TEXT = "fast_text"      # PyMuPDF only - fastest, free
    HYBRID = "hybrid"            # PyMuPDF + Vision for complex pages
    FULL_VISION = "full_vision"  # Vision API for all pages
    OCR = "ocr"                  # PaddleOCR for scanned docs - free, local


@dataclass
class PageAnalysis:
    """Analysis results for a single page"""
    page_number: int
    has_text: bool = False
    text_coverage: float = 0.0  # 0-1, how much of page is text
    has_images: bool = False
    has_tables: bool = False
    has_formulas: bool = False
    is_scanned: bool = False
    needs_vision: bool = False

    # Detailed metrics
    text_blocks: int = 0
    image_count: int = 0
    char_count: int = 0
    sample_text: str = ""  # First 500 chars for content detection


@dataclass
class DocumentAnalysis:
    """Complete document analysis results"""
    file_path: str
    total_pages: int

    # Overall stats
    text_coverage: float = 0.0  # Average across pages
    native_text_pages: int = 0
    scanned_pages: int = 0
    complex_pages: int = 0  # Pages needing Vision

    # Content detection
    has_tables: bool = False
    has_images: bool = False
    has_formulas: bool = False
    has_code: bool = False

    # Page-level details
    pages: List[PageAnalysis] = field(default_factory=list)
    complex_page_numbers: Set[int] = field(default_factory=set)

    # Recommended strategy
    strategy: ExtractionStrategy = ExtractionStrategy.FAST_TEXT
    strategy_reason: str = ""

    # Performance estimates
    estimated_time_fast: float = 0.0  # seconds
    estimated_time_vision: float = 0.0  # seconds
    estimated_cost_vision: float = 0.0  # USD


class DocumentAnalyzer:
    """
    Analyzes PDF documents to determine optimal extraction strategy.

    Usage:
        analyzer = DocumentAnalyzer()
        analysis = analyzer.analyze("/path/to/document.pdf")

        if analysis.strategy == ExtractionStrategy.FAST_TEXT:
            # Use PyMuPDF extraction
        elif analysis.strategy == ExtractionStrategy.HYBRID:
            # Use PyMuPDF for most pages, Vision for complex_page_numbers
        else:
            # Use full Vision API
    """

    # Thresholds for detection
    TEXT_COVERAGE_THRESHOLD = 0.7  # >70% text → likely text-only
    SCANNED_THRESHOLD = 0.1  # <10% text extraction → likely scanned
    COMPLEX_PAGE_THRESHOLD = 0.15  # >15% complex pages → consider hybrid

    # Formula indicators in extracted text
    FORMULA_INDICATORS = [
        '∑', '∫', '∂', '∇', '√', '∞', '≤', '≥', '≠', '≈',
        'α', 'β', 'γ', 'δ', 'θ', 'λ', 'μ', 'σ', 'ω', 'π',
        '∈', '∉', '⊂', '⊃', '∪', '∩', '∀', '∃',
        '²', '³', '⁴', 'ⁿ', '₁', '₂', '₃',
    ]

    # LaTeX-like patterns in text
    LATEX_PATTERNS = [
        '\\frac', '\\sum', '\\int', '\\sqrt', '\\alpha', '\\beta',
        '\\partial', '\\nabla', '\\infty', '\\mathbb', '\\begin{',
    ]

    # Academic paper indicators (suggest formulas even if not directly detected)
    # These patterns indicate the document discusses math, so formulas likely exist as images
    ACADEMIC_KEYWORDS = [
        'theorem', 'lemma', 'proposition', 'corollary', 'proof',
        'equation', 'formula', 'definition', 'conjecture', 'hypothesis',
        'arXiv', 'arxiv', 'Abstract:', 'Keywords:', 'MSC',
        'convergence', 'divergence', 'summation', 'integral',
        'polynomial', 'function f(', 'let n be', 'for all n',
    ]

    # Japanese academic paper indicators
    # These patterns indicate the document is a Japanese academic paper
    ACADEMIC_KEYWORDS_JA = [
        '論文', '研究', '結論', '参考文献', '要約', '抄録',  # Paper structure
        '定理', '証明', '命題', '系', '補題',              # Math terms
        '著者', '共著者',                                  # Authors
        '序論', '緒言', '方法論', '考察',                  # Sections
        '仮説', '実験', '結果',                            # Research
        '学会', '紀要', '大学',                            # Academic institutions
    ]

    def __init__(self, sample_pages: int = 10):
        """
        Args:
            sample_pages: Number of pages to sample for quick analysis
        """
        self.sample_pages = sample_pages

    def analyze(self, pdf_path: str, full_scan: bool = False) -> DocumentAnalysis:
        """
        Analyze a PDF document.

        Args:
            pdf_path: Path to PDF file
            full_scan: If True, analyze all pages. If False, sample pages.

        Returns:
            DocumentAnalysis with strategy recommendation
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"📊 Analyzing document: {path.name}")

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            analysis = DocumentAnalysis(
                file_path=str(path),
                total_pages=total_pages,
            )

            # Determine which pages to analyze
            if full_scan or total_pages <= self.sample_pages * 2:
                pages_to_analyze = list(range(total_pages))
            else:
                # Sample: first few, middle, last few
                pages_to_analyze = self._get_sample_pages(total_pages)

            logger.info(f"  Analyzing {len(pages_to_analyze)}/{total_pages} pages")

            # Analyze each page
            for page_num in pages_to_analyze:
                page_analysis = self._analyze_page(doc[page_num], page_num)
                analysis.pages.append(page_analysis)

                if page_analysis.needs_vision:
                    analysis.complex_page_numbers.add(page_num)

            doc.close()

            # Aggregate results
            self._aggregate_analysis(analysis)

            # Determine strategy
            self._determine_strategy(analysis)

            # Estimate performance
            self._estimate_performance(analysis)

            logger.info(f"  Strategy: {analysis.strategy.value}")
            logger.info(f"  Reason: {analysis.strategy_reason}")

            return analysis

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            # Default to Vision for safety
            return DocumentAnalysis(
                file_path=str(path),
                total_pages=0,
                strategy=ExtractionStrategy.FULL_VISION,
                strategy_reason=f"Analysis failed: {e}",
            )

    def _get_sample_pages(self, total: int) -> List[int]:
        """Get representative sample of pages to analyze"""
        sample = []

        # First 3 pages
        sample.extend(range(min(3, total)))

        # Middle pages
        if total > 10:
            mid = total // 2
            sample.extend([mid - 1, mid, mid + 1])

        # Last 3 pages
        if total > 6:
            sample.extend(range(max(0, total - 3), total))

        # Random samples from remaining
        remaining = self.sample_pages - len(set(sample))
        if remaining > 0 and total > len(sample):
            import random
            available = [i for i in range(total) if i not in sample]
            sample.extend(random.sample(available, min(remaining, len(available))))

        return sorted(set(sample))

    def _analyze_page(self, page: fitz.Page, page_num: int) -> PageAnalysis:
        """Analyze a single page"""
        analysis = PageAnalysis(page_number=page_num)

        # Extract text
        text = page.get_text()
        analysis.char_count = len(text)
        analysis.has_text = len(text.strip()) > 50
        analysis.sample_text = text[:500]  # Store sample for content detection

        # Get text blocks
        blocks = page.get_text("blocks")
        analysis.text_blocks = len([b for b in blocks if b[6] == 0])  # Type 0 = text

        # Calculate text coverage
        page_area = page.rect.width * page.rect.height
        text_area = sum(
            (b[2] - b[0]) * (b[3] - b[1])
            for b in blocks if b[6] == 0
        )
        analysis.text_coverage = text_area / page_area if page_area > 0 else 0

        # Detect images
        images = page.get_images()
        analysis.image_count = len(images)
        analysis.has_images = len(images) > 0

        # Detect tables (heuristic: look for grid-like structures)
        analysis.has_tables = self._detect_tables(page, text)

        # Detect formulas
        analysis.has_formulas = self._detect_formulas(text)

        # Detect if scanned (image-based PDF)
        analysis.is_scanned = (
            analysis.text_coverage < self.SCANNED_THRESHOLD and
            analysis.image_count > 0 and
            analysis.char_count < 100
        )

        # Smart detection: if good text extraction, probably don't need Vision
        # Key insight: decorative images don't prevent good text extraction
        has_good_text = analysis.char_count > 500 and analysis.text_coverage > 0.3

        # Determine if Vision is needed for this page
        # More conservative: only if text extraction is poor
        analysis.needs_vision = (
            analysis.is_scanned or
            (analysis.has_formulas and not has_good_text) or  # Formulas only if text is bad
            (analysis.has_formulas and analysis.image_count > 2)
        )

        return analysis

    def _detect_tables(self, page: fitz.Page, text: str) -> bool:
        """Detect if page contains tables"""
        # Method 1: Look for table-like text patterns
        lines = text.split('\n')
        aligned_lines = 0
        for line in lines:
            # Count consecutive whitespace groups (potential columns)
            parts = line.split()
            if len(parts) >= 3:
                # Check if spacing is relatively even
                aligned_lines += 1

        if aligned_lines > 5:
            return True

        # Method 2: Check for drawings/lines (table borders)
        try:
            drawings = page.get_drawings()
            line_count = sum(1 for d in drawings if d.get("type") == "l")
            if line_count > 10:  # Multiple lines suggest table
                return True
        except:
            pass

        return False

    def _detect_formulas(self, text: str) -> bool:
        """Detect if text contains mathematical formulas"""
        # Check for Unicode math symbols
        for indicator in self.FORMULA_INDICATORS:
            if indicator in text:
                return True

        # Check for LaTeX-like patterns
        for pattern in self.LATEX_PATTERNS:
            if pattern in text:
                return True

        return False

    def _detect_academic_paper(self, text: str, filename: str = "") -> bool:
        """Detect if document is an academic paper with likely formulas as images

        Academic papers (especially arXiv) render formulas as images, so
        PyMuPDF can't extract the formula characters directly. This method
        detects academic papers by context clues.

        Supports both English and Japanese academic papers.
        """
        text_lower = text.lower()
        filename_lower = filename.lower()

        # Check filename for arXiv pattern
        if 'arxiv' in filename_lower:
            return True

        # Count English academic keyword matches
        keyword_count = 0
        for keyword in self.ACADEMIC_KEYWORDS:
            if keyword.lower() in text_lower:
                keyword_count += 1

        # Count Japanese academic keyword matches
        ja_keyword_count = 0
        for keyword in self.ACADEMIC_KEYWORDS_JA:
            if keyword in text:  # Japanese is case-insensitive by nature
                ja_keyword_count += 1

        # If 3+ keywords found (either language), likely an academic paper
        return keyword_count >= 3 or ja_keyword_count >= 2

    def _aggregate_analysis(self, analysis: DocumentAnalysis):
        """Aggregate page-level analysis to document level"""
        if not analysis.pages:
            return

        # Calculate averages
        analysis.text_coverage = sum(p.text_coverage for p in analysis.pages) / len(analysis.pages)

        # Count page types
        analysis.native_text_pages = sum(1 for p in analysis.pages if p.has_text and not p.is_scanned)
        analysis.scanned_pages = sum(1 for p in analysis.pages if p.is_scanned)
        analysis.complex_pages = len(analysis.complex_page_numbers)

        # Detect content types
        analysis.has_tables = any(p.has_tables for p in analysis.pages)
        analysis.has_images = any(p.has_images for p in analysis.pages)
        analysis.has_formulas = any(p.has_formulas for p in analysis.pages)

    def _determine_strategy(self, analysis: DocumentAnalysis):
        """Determine the best extraction strategy"""
        total = analysis.total_pages

        # Case 1: Mostly scanned → Full Vision
        scanned_ratio = analysis.scanned_pages / len(analysis.pages) if analysis.pages else 0
        if scanned_ratio > 0.5:
            analysis.strategy = ExtractionStrategy.FULL_VISION
            analysis.strategy_reason = f"Scanned document ({scanned_ratio:.0%} scanned pages)"
            return

        # Case 1.5: Academic paper detection (arXiv, papers with theorems/equations)
        # These have formulas rendered as images, not extractable by PyMuPDF
        combined_text = " ".join(p.sample_text for p in analysis.pages if p.sample_text)
        filename = Path(analysis.file_path).name if analysis.file_path else ""
        is_academic = self._detect_academic_paper(combined_text, filename)
        if is_academic:
            analysis.has_formulas = True  # Mark as having formulas
            analysis.strategy = ExtractionStrategy.FULL_VISION
            analysis.strategy_reason = "Academic paper detected (formulas likely as images)"
            return

        # Calculate average char count per page (key metric for text quality)
        avg_chars = sum(p.char_count for p in analysis.pages) / len(analysis.pages) if analysis.pages else 0

        # Case 2: Good text extraction → Fast Text (even with images/tables)
        # Key insight: if we can extract 500+ chars per page, PyMuPDF works well
        if avg_chars > 500 and not analysis.has_formulas:
            analysis.strategy = ExtractionStrategy.FAST_TEXT
            analysis.strategy_reason = f"Good text extraction ({avg_chars:.0f} chars/page avg)"
            return

        # Case 3: High text coverage, no complex elements → Fast Text
        if (analysis.text_coverage > self.TEXT_COVERAGE_THRESHOLD and
            not analysis.has_tables and
            not analysis.has_formulas):
            analysis.strategy = ExtractionStrategy.FAST_TEXT
            analysis.strategy_reason = f"Text-only document ({analysis.text_coverage:.0%} text coverage)"
            return

        # Case 3: Some complex pages → Hybrid
        complex_ratio = analysis.complex_pages / len(analysis.pages) if analysis.pages else 0
        if complex_ratio < self.COMPLEX_PAGE_THRESHOLD and analysis.text_coverage > 0.5:
            analysis.strategy = ExtractionStrategy.HYBRID
            analysis.strategy_reason = f"Mixed content ({analysis.complex_pages} complex pages, {analysis.text_coverage:.0%} text)"

            # Extrapolate complex pages for full document
            if len(analysis.pages) < total:
                estimated_complex = int(complex_ratio * total)
                analysis.complex_page_numbers = set(range(estimated_complex))
            return

        # Case 4: High complexity → Full Vision
        if analysis.has_formulas or complex_ratio > 0.3:
            analysis.strategy = ExtractionStrategy.FULL_VISION
            analysis.strategy_reason = f"Complex document (formulas={analysis.has_formulas}, {complex_ratio:.0%} complex)"
            return

        # Default: Fast Text (optimistic)
        analysis.strategy = ExtractionStrategy.FAST_TEXT
        analysis.strategy_reason = f"Default to fast extraction ({analysis.text_coverage:.0%} text)"

    def _estimate_performance(self, analysis: DocumentAnalysis):
        """Estimate time and cost for different strategies"""
        total = analysis.total_pages

        # Fast text: ~0.1s per page
        analysis.estimated_time_fast = total * 0.1

        # Vision: ~10-15s per page
        analysis.estimated_time_vision = total * 12.5

        # Cost: ~$0.02 per page for Vision (gpt-4o)
        analysis.estimated_cost_vision = total * 0.02


def analyze_document(pdf_path: str) -> DocumentAnalysis:
    """Convenience function to analyze a document"""
    analyzer = DocumentAnalyzer()
    return analyzer.analyze(pdf_path)
