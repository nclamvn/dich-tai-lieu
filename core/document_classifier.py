#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Type Classifier - Phase 2.1.1
Intelligent document detection for automatic pipeline selection

Automatically detects:
- arXiv papers (filename patterns, .tar.gz sources)
- STEM documents (mathematical content)
- General documents

Returns optimal translation settings based on document type.
"""

import re
from pathlib import Path
from typing import Dict, Optional
import fitz  # PyMuPDF


class DocumentClassifier:
    """Intelligent document type detection and pipeline recommendation"""

    # arXiv filename patterns
    ARXIV_PATTERNS = [
        r'arxiv[_-]?\d+\.\d+',  # arXiv-1509.05363, arxiv_1509.05363
        r'^\d{4}\.\d{4,5}',     # 1509.05363 (bare arXiv ID)
    ]

    # LaTeX source extensions
    LATEX_SOURCE_EXTENSIONS = ['.tex', '.zip', '.tar.gz', '.tar', '.tgz']

    # STEM indicators in text
    STEM_INDICATORS = [
        # Math symbols and operators
        r'∫', r'∑', r'∏', r'√', r'∂', r'∇', r'≈', r'≠', r'≤', r'≥',
        r'∈', r'∉', r'⊂', r'⊃', r'∪', r'∩', r'∅',
        r'α', r'β', r'γ', r'δ', r'ε', r'θ', r'λ', r'μ', r'π', r'σ', r'ω',

        # Math keywords
        r'\btheorem\b', r'\blemma\b', r'\bcorollary\b', r'\bproof\b',
        r'\bproposition\b', r'\bdefinition\b',
        r'\bequation\b', r'\bformula\b',

        # Common math notation patterns
        r'\bf\(.*?\)',  # f(x) notation
        r'[a-z]\^\d',   # x^2 notation
        r'[a-z]_\d',    # x_1 notation
    ]

    @classmethod
    def classify(cls, file_path: str, check_content: bool = True) -> Dict:
        """
        Classify document and recommend optimal translation settings

        Args:
            file_path: Path to input file
            check_content: If True, analyze PDF content for STEM detection
                          (slower but more accurate)

        Returns:
            dict: {
                'document_type': 'arxiv' | 'stem' | 'general',
                'confidence': float (0.0-1.0),
                'recommended_settings': {
                    'domain': str,
                    'layout_mode': str,
                    'equation_rendering': str,
                    'ocr_backend': str
                },
                'reasons': list[str]  # Why this classification was made
            }
        """
        path = Path(file_path)
        reasons = []
        document_type = 'general'
        confidence = 0.5  # Default confidence

        # Check 1: Is it a LaTeX source file?
        if any(str(path).endswith(ext) for ext in cls.LATEX_SOURCE_EXTENSIONS):
            reasons.append(f"LaTeX source file detected: {path.suffix}")
            document_type = 'arxiv'
            confidence = 0.9

        # Check 2: Does filename match arXiv pattern?
        filename = path.stem.lower()
        for pattern in cls.ARXIV_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                reasons.append(f"Filename matches arXiv pattern: {pattern}")
                document_type = 'arxiv'
                confidence = max(confidence, 0.95)
                break

        # Check 3: Analyze PDF content for STEM indicators
        if check_content and path.suffix.lower() == '.pdf':
            stem_score = cls._analyze_pdf_content(file_path)
            if stem_score > 0.3:
                reasons.append(f"STEM content detected (score: {stem_score:.2f})")
                # If already classified as arXiv, keep it; otherwise upgrade to STEM
                if document_type == 'general':
                    document_type = 'stem'
                    confidence = stem_score

        # Generate recommended settings based on classification
        recommended_settings = cls._get_recommended_settings(document_type)

        return {
            'document_type': document_type,
            'confidence': confidence,
            'recommended_settings': recommended_settings,
            'reasons': reasons
        }

    @classmethod
    def _analyze_pdf_content(cls, pdf_path: str, max_pages: int = 5) -> float:
        """
        Analyze PDF content to detect STEM indicators

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to analyze (for performance)

        Returns:
            float: STEM score (0.0-1.0), higher = more likely STEM document
        """
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            pages_to_check = min(max_pages, total_pages)

            # Extract text from first few pages
            text = ""
            for page_num in range(pages_to_check):
                page = doc[page_num]
                text += page.get_text()

            doc.close()

            # Count STEM indicators
            indicator_count = 0
            for pattern in cls.STEM_INDICATORS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                indicator_count += len(matches)

            # Normalize score (capped at 1.0)
            # Heuristic: 10+ indicators = likely STEM
            stem_score = min(1.0, indicator_count / 10.0)

            return stem_score

        except Exception as e:
            # If content analysis fails, return low score
            print(f"⚠️  Warning: Could not analyze PDF content: {e}")
            return 0.0

    @classmethod
    def _get_recommended_settings(cls, document_type: str) -> Dict:
        """
        Get recommended translation settings for document type

        Args:
            document_type: 'arxiv', 'stem', or 'general'

        Returns:
            dict: Recommended settings for translate_pdf.py
        """
        if document_type == 'arxiv':
            # arXiv papers: Full academic treatment with OMML equations
            return {
                'domain': 'stem',
                'layout_mode': 'academic',
                'equation_rendering': 'omml',
                'ocr_backend': 'auto'
            }

        elif document_type == 'stem':
            # STEM documents: Academic layout with OMML, but auto OCR
            return {
                'domain': 'stem',
                'layout_mode': 'academic',
                'equation_rendering': 'omml',
                'ocr_backend': 'auto'
            }

        else:  # general
            # General documents: Simple layout, plain text equations
            return {
                'domain': 'general',
                'layout_mode': 'simple',
                'equation_rendering': 'latex_text',
                'ocr_backend': 'auto'
            }


def classify_document(file_path: str, check_content: bool = True) -> Dict:
    """
    Convenience function for document classification

    Args:
        file_path: Path to input file
        check_content: If True, analyze PDF content (slower but more accurate)

    Returns:
        Classification result dictionary
    """
    return DocumentClassifier.classify(file_path, check_content)


# CLI testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 core/document_classifier.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    result = classify_document(file_path)

    print("\n" + "="*70)
    print("DOCUMENT CLASSIFICATION RESULT")
    print("="*70)
    print(f"File: {file_path}")
    print(f"Document Type: {result['document_type'].upper()}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"\nReasons:")
    for reason in result['reasons']:
        print(f"  - {reason}")
    print(f"\nRecommended Settings:")
    for key, value in result['recommended_settings'].items():
        print(f"  --{key.replace('_', '-')}: {value}")
    print("="*70 + "\n")
