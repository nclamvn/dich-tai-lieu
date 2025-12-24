#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart PDF Input Detector
Automatically detects whether a PDF is native (text-based) or scanned (image-based),
and recommends appropriate OCR mode.
"""

from config.logging_config import get_logger
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

logger = get_logger(__name__)


class PDFType(Enum):
    """PDF type classification"""
    NATIVE = "native"          # Text-based PDF (extractable text)
    SCANNED = "scanned"        # Image-based PDF (needs OCR)
    MIXED = "mixed"            # Contains both native and scanned pages
    UNKNOWN = "unknown"        # Unable to determine


class OCRMode(Enum):
    """Recommended OCR mode"""
    NONE = "none"              # No OCR needed
    PADDLE = "paddle"          # PaddleOCR only
    HYBRID = "hybrid"          # PaddleOCR + MathPix
    AUTO = "auto"              # Let system decide


@dataclass
class DetectionResult:
    """Result of PDF type detection"""
    pdf_type: PDFType
    ocr_needed: bool
    confidence: float          # 0.0-1.0
    recommendation: OCRMode
    details: Dict              # Additional detection details
    page_results: List[Dict]   # Per-page analysis


class SmartDetector:
    """
    Smart PDF input detector using heuristics and layout analysis.

    Detection Strategy:
    1. Extract text from each page using PyMuPDF
    2. Calculate text density (characters per page area)
    3. Classify each page as native/scanned based on threshold
    4. Detect formula-heavy regions using layout analysis
    5. Recommend OCR mode based on results

    Usage:
        detector = SmartDetector()
        result = detector.detect_pdf_type("paper.pdf")

        if result.ocr_needed:
            logger.info(f"OCR recommended: {result.recommendation}")
    """

    # Thresholds for classification
    TEXT_DENSITY_THRESHOLD = 0.001    # chars per square point
    SCANNED_PAGE_THRESHOLD = 0.3      # <30% pages scanned = native
    FORMULA_DENSITY_THRESHOLD = 0.2   # >20% formula blocks = recommend hybrid

    def __init__(self, use_layout_analysis: bool = True):
        """
        Initialize smart detector.

        Args:
            use_layout_analysis: Use LayoutExtractor for advanced analysis
        """
        self.use_layout_analysis = use_layout_analysis

        # Import PyMuPDF
        try:
            import fitz
            self.fitz = fitz
        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) is required for smart detection. Install with:\n"
                "  pip install PyMuPDF"
            )

    def detect_pdf_type(self, pdf_path: Path | str) -> DetectionResult:
        """
        Detect PDF type and recommend OCR mode.

        Args:
            pdf_path: Path to PDF file

        Returns:
            DetectionResult with classification and recommendation
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return DetectionResult(
                pdf_type=PDFType.UNKNOWN,
                ocr_needed=False,
                confidence=0.0,
                recommendation=OCRMode.NONE,
                details={"error": "File not found"},
                page_results=[]
            )

        try:
            # Open PDF
            doc = self.fitz.open(str(pdf_path))
            total_pages = len(doc)

            if total_pages == 0:
                return DetectionResult(
                    pdf_type=PDFType.UNKNOWN,
                    ocr_needed=False,
                    confidence=0.0,
                    recommendation=OCRMode.NONE,
                    details={"error": "Empty PDF"},
                    page_results=[]
                )

            # Analyze each page
            page_results = []
            scanned_count = 0
            native_count = 0
            total_formula_blocks = 0
            total_text_blocks = 0

            for page_num in range(total_pages):
                page = doc[page_num]
                page_result = self._analyze_page(page, page_num)

                page_results.append(page_result)

                if page_result["is_scanned"]:
                    scanned_count += 1
                else:
                    native_count += 1

                total_formula_blocks += page_result.get("formula_blocks", 0)
                total_text_blocks += page_result.get("text_blocks", 0)

            doc.close()

            # Calculate metrics
            scanned_ratio = scanned_count / total_pages
            formula_ratio = total_formula_blocks / max(total_text_blocks, 1)

            # Classify PDF type
            if scanned_ratio < self.SCANNED_PAGE_THRESHOLD:
                pdf_type = PDFType.NATIVE
                ocr_needed = False
            elif scanned_ratio > (1 - self.SCANNED_PAGE_THRESHOLD):
                pdf_type = PDFType.SCANNED
                ocr_needed = True
            else:
                pdf_type = PDFType.MIXED
                ocr_needed = True

            # Recommend OCR mode
            if not ocr_needed:
                recommendation = OCRMode.NONE
            elif formula_ratio > self.FORMULA_DENSITY_THRESHOLD:
                recommendation = OCRMode.HYBRID  # Many formulas → use MathPix
            else:
                recommendation = OCRMode.PADDLE  # Regular text → PaddleOCR is enough

            # Calculate confidence
            # High confidence = clear decision (very native or very scanned)
            confidence = abs(scanned_ratio - 0.5) * 2  # 0.0 at 50%, 1.0 at 0%/100%

            details = {
                "total_pages": total_pages,
                "scanned_pages": scanned_count,
                "native_pages": native_count,
                "scanned_ratio": scanned_ratio,
                "formula_blocks": total_formula_blocks,
                "text_blocks": total_text_blocks,
                "formula_ratio": formula_ratio
            }

            return DetectionResult(
                pdf_type=pdf_type,
                ocr_needed=ocr_needed,
                confidence=confidence,
                recommendation=recommendation,
                details=details,
                page_results=page_results
            )

        except Exception as e:
            logger.error(f"PDF detection failed: {str(e)}")
            return DetectionResult(
                pdf_type=PDFType.UNKNOWN,
                ocr_needed=False,
                confidence=0.0,
                recommendation=OCRMode.NONE,
                details={"error": str(e)},
                page_results=[]
            )

    def _analyze_page(self, page, page_num: int) -> Dict:
        """
        Analyze a single PDF page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            Dictionary with page analysis results
        """
        # Get page dimensions
        rect = page.rect
        page_area = rect.width * rect.height

        # Extract text
        text = page.get_text()
        text_length = len(text.strip())

        # Calculate text density
        text_density = text_length / page_area if page_area > 0 else 0.0

        # Classify page
        is_scanned = text_density < self.TEXT_DENSITY_THRESHOLD

        # Count images (high image count may indicate scanned page)
        images = page.get_images()
        image_count = len(images)

        # Basic formula detection (look for math symbols)
        # More advanced detection would use LayoutExtractor
        formula_indicators = [
            '$', '\\', '∫', '∑', '√', '∞', '≈', '≠', '≤', '≥',
            '∈', '∉', '∀', '∃', '→', '↔', '⇒', '⇔'
        ]
        formula_count = sum(text.count(symbol) for symbol in formula_indicators)
        has_formulas = formula_count > 5  # Arbitrary threshold

        result = {
            "page_num": page_num,
            "text_length": text_length,
            "text_density": text_density,
            "image_count": image_count,
            "is_scanned": is_scanned,
            "has_formulas": has_formulas,
            "formula_count": formula_count
        }

        # Advanced layout analysis (if enabled)
        if self.use_layout_analysis and not is_scanned:
            try:
                layout_info = self._analyze_layout(page)
                result.update(layout_info)
            except Exception as e:
                logger.debug(f"Layout analysis failed for page {page_num}: {str(e)}")

        return result

    def _analyze_layout(self, page) -> Dict:
        """
        Perform advanced layout analysis using LayoutExtractor.

        Args:
            page: PyMuPDF page object

        Returns:
            Dictionary with layout analysis results
        """
        try:
            from ..stem.layout_extractor import LayoutExtractor, BlockType

            # This is a simplified version - full integration would require
            # passing the page to LayoutExtractor
            # For now, use basic block detection from PyMuPDF

            blocks = page.get_text("dict")["blocks"]

            text_blocks = 0
            formula_blocks = 0
            code_blocks = 0

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    text_blocks += 1

                    # Simple heuristic for formulas (contains $ or \)
                    block_text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")

                    if '$' in block_text or '\\' in block_text:
                        formula_blocks += 1

                    # Simple heuristic for code (monospace font, indentation)
                    if any(span.get("font", "").lower().find("mono") >= 0
                           for line in block.get("lines", [])
                           for span in line.get("spans", [])):
                        code_blocks += 1

            return {
                "text_blocks": text_blocks,
                "formula_blocks": formula_blocks,
                "code_blocks": code_blocks
            }

        except Exception as e:
            logger.debug(f"Advanced layout analysis failed: {str(e)}")
            return {
                "text_blocks": 0,
                "formula_blocks": 0,
                "code_blocks": 0
            }

    def recommend_ocr_mode(
        self,
        pdf_path: Path | str,
        has_mathpix_key: bool = False
    ) -> str:
        """
        Get user-friendly OCR mode recommendation.

        Args:
            pdf_path: Path to PDF file
            has_mathpix_key: Whether MathPix API key is available

        Returns:
            Recommendation string for display to user
        """
        result = self.detect_pdf_type(pdf_path)

        if result.pdf_type == PDFType.NATIVE:
            return (
                f"✅ This is a native PDF with extractable text.\n"
                f"   OCR is not needed. Translation will be fast and accurate."
            )

        elif result.pdf_type == PDFType.SCANNED:
            if result.recommendation == OCRMode.HYBRID and has_mathpix_key:
                return (
                    f"📊 This is a scanned PDF with mathematical content.\n"
                    f"   Recommended: Hybrid OCR (PaddleOCR + MathPix)\n"
                    f"   - Best formula recognition accuracy\n"
                    f"   - Estimated time: {result.details['total_pages'] * 3}s"
                )
            else:
                return (
                    f"📄 This is a scanned PDF.\n"
                    f"   Recommended: PaddleOCR (local, free)\n"
                    f"   - Good accuracy for text\n"
                    f"   - Estimated time: {result.details['total_pages'] * 2}s\n"
                    + (f"   💡 Add MathPix key for better formula recognition"
                       if result.recommendation == OCRMode.HYBRID else "")
                )

        elif result.pdf_type == PDFType.MIXED:
            scanned_pages = result.details['scanned_pages']
            return (
                f"🔀 This PDF has mixed content:\n"
                f"   - {scanned_pages} scanned pages (need OCR)\n"
                f"   - {result.details['native_pages']} native pages (direct extraction)\n"
                f"   Recommended: Auto-detect per page\n"
                f"   - OCR only where needed\n"
                f"   - Estimated time: {scanned_pages * 2}s"
            )

        else:
            return (
                f"❓ Unable to analyze PDF.\n"
                f"   You may need to manually select OCR mode."
            )
