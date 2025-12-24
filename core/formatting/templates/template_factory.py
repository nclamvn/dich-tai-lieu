#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template Factory - Factory for creating and managing templates.

Provides centralized template management with auto-detection capability
to automatically select the best template based on document content.
"""

import re
from typing import Dict, List, Optional, TYPE_CHECKING

from .base_template import BaseTemplate
from .book_template import BookTemplate
from .report_template import ReportTemplate
from .legal_template import LegalTemplate
from .academic_template import AcademicTemplate

if TYPE_CHECKING:
    from ..document_model import DocumentModel


class TemplateFactory:
    """
    Factory for creating and managing document templates.

    Provides:
    - Template registration and retrieval
    - Listing available templates
    - Auto-detection based on document content

    Usage:
        # Get specific template
        template = TemplateFactory.get_template("book")

        # Auto-detect template
        template_name = TemplateFactory.auto_detect(document_text)
        template = TemplateFactory.get_template(template_name)

        # List all templates
        names = TemplateFactory.list_templates()
    """

    _templates: Dict[str, BaseTemplate] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls):
        """Ensure default templates are registered."""
        if not cls._initialized:
            cls._register_defaults()
            cls._initialized = True

    @classmethod
    def _register_defaults(cls):
        """Register default templates."""
        cls.register(BookTemplate())
        cls.register(ReportTemplate())
        cls.register(LegalTemplate())
        cls.register(AcademicTemplate())

    @classmethod
    def register(cls, template: BaseTemplate):
        """
        Register a template.

        Args:
            template: Template instance to register
        """
        cls._templates[template.name] = template

    @classmethod
    def unregister(cls, name: str):
        """
        Unregister a template.

        Args:
            name: Template name to remove
        """
        if name in cls._templates:
            del cls._templates[name]

    @classmethod
    def get_template(cls, name: str) -> BaseTemplate:
        """
        Get template by name.

        Args:
            name: Template identifier

        Returns:
            Template instance

        Raises:
            ValueError: If template not found
        """
        cls._ensure_initialized()

        if name not in cls._templates:
            available = cls.list_templates()
            raise ValueError(
                f"Unknown template: '{name}'. "
                f"Available templates: {available}"
            )
        return cls._templates[name]

    @classmethod
    def list_templates(cls) -> List[str]:
        """
        List all available template names.

        Returns:
            List of template identifiers
        """
        cls._ensure_initialized()
        return list(cls._templates.keys())

    @classmethod
    def get_all_templates(cls) -> Dict[str, BaseTemplate]:
        """
        Get all registered templates.

        Returns:
            Dictionary mapping names to template instances
        """
        cls._ensure_initialized()
        return cls._templates.copy()

    @classmethod
    def get_template_info(cls) -> List[Dict]:
        """
        Get information about all templates.

        Returns:
            List of template info dictionaries
        """
        cls._ensure_initialized()
        return [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
            }
            for t in cls._templates.values()
        ]

    @classmethod
    def auto_detect(cls, text: str, model: Optional['DocumentModel'] = None) -> str:
        """
        Auto-detect best template based on document content.

        Uses heuristics to identify document type:
        - Legal: "Article", "Điều", "Clause", "Khoản", "Contract"
        - Academic: "Abstract", "References", "Methodology"
        - Book: "Chapter", "Chương", "Part", "Prologue"
        - Report: "Executive Summary", "Findings", "Recommendations"

        Args:
            text: Document text content
            model: Optional DocumentModel for additional analysis

        Returns:
            Template name (default: "report")
        """
        cls._ensure_initialized()

        text_lower = text.lower()

        # Legal indicators (Vietnamese and English)
        legal_patterns = [
            r'\barticle\s+\d+',
            r'\bđiều\s+\d+',
            r'\bclause\s+\d+',
            r'\bkhoản\s+\d+',
            r'\bcontract\b',
            r'\bhợp đồng\b',
            r'\bagreement\b',
            r'\bthỏa thuận\b',
            r'\bterms and conditions\b',
            r'\bđiều khoản\b',
            r'\bparty\s+[ab12]\b',
            r'\bbên\s+[ab12]\b',
            r'\bhereby\b',
            r'\bwhereas\b',
        ]
        legal_score = sum(1 for p in legal_patterns if re.search(p, text_lower))

        # Academic indicators
        academic_patterns = [
            r'\babstract\b',
            r'\btóm tắt\b',
            r'\breferences\b',
            r'\btài liệu tham khảo\b',
            r'\bbibliography\b',
            r'\bconclusion\b',
            r'\bkết luận\b',
            r'\bintroduction\b',
            r'\bgiới thiệu\b',
            r'\bmethodology\b',
            r'\bphương pháp\b',
            r'\bliterature review\b',
            r'\btổng quan\b',
            r'\bhypothesis\b',
            r'\bgiả thuyết\b',
            r'\bfindings\b',
            r'\bkết quả nghiên cứu\b',
        ]
        academic_score = sum(1 for p in academic_patterns if re.search(p, text_lower))

        # Book indicators
        book_patterns = [
            r'\bchapter\s+\d+',
            r'\bchương\s+\d+',
            r'\bpart\s+[ivxlc\d]+',
            r'\bphần\s+\d+',
            r'\bprologue\b',
            r'\blời nói đầu\b',
            r'\bepilogue\b',
            r'\blời kết\b',
            r'\bpreface\b',
            r'\blời tựa\b',
            r'\bforeword\b',
            r'\bafterword\b',
        ]
        book_score = sum(1 for p in book_patterns if re.search(p, text_lower))

        # Report indicators
        report_patterns = [
            r'\bexecutive summary\b',
            r'\btóm tắt điều hành\b',
            r'\brecommendation\b',
            r'\bđề xuất\b',
            r'\bfindings\b',
            r'\bkết quả\b',
            r'\banalysis\b',
            r'\bphân tích\b',
            r'\bstakeholder\b',
            r'\bkpi\b',
            r'\broi\b',
            r'\bbudget\b',
            r'\bngân sách\b',
            r'\bquarterly\b',
            r'\bannual report\b',
            r'\bbáo cáo\b',
        ]
        report_score = sum(1 for p in report_patterns if re.search(p, text_lower))

        # Calculate scores
        scores = {
            "legal": legal_score,
            "academic": academic_score,
            "book": book_score,
            "report": report_score,
        }

        # Get highest score
        max_score = max(scores.values())

        # Default to report if no strong indicators
        if max_score == 0:
            return "report"

        # Return template with highest score
        # In case of tie, priority: legal > academic > book > report
        priority = ["legal", "academic", "book", "report"]
        for template_name in priority:
            if scores[template_name] == max_score:
                return template_name

        return "report"

    @classmethod
    def auto_detect_with_confidence(
        cls, text: str, model: Optional['DocumentModel'] = None
    ) -> tuple:
        """
        Auto-detect template with confidence score.

        Args:
            text: Document text content
            model: Optional DocumentModel

        Returns:
            Tuple of (template_name, confidence_score)
            Confidence is 0.0-1.0
        """
        cls._ensure_initialized()

        text_lower = text.lower()

        # Run same detection as auto_detect
        patterns = {
            "legal": [
                r'\barticle\s+\d+', r'\bđiều\s+\d+', r'\bclause\b',
                r'\bcontract\b', r'\bhợp đồng\b', r'\bagreement\b',
            ],
            "academic": [
                r'\babstract\b', r'\btóm tắt\b', r'\breferences\b',
                r'\bmethodology\b', r'\bhypothesis\b', r'\bconclusion\b',
            ],
            "book": [
                r'\bchapter\s+\d+', r'\bchương\s+\d+', r'\bpart\s+[ivxlc\d]+',
                r'\bprologue\b', r'\bepilogue\b', r'\bpreface\b',
            ],
            "report": [
                r'\bexecutive summary\b', r'\brecommendation\b',
                r'\banalysis\b', r'\bfindings\b', r'\bkpi\b', r'\bbudget\b',
            ],
        }

        scores = {}
        for name, pattern_list in patterns.items():
            scores[name] = sum(1 for p in pattern_list if re.search(p, text_lower))

        max_score = max(scores.values())
        total_patterns = sum(len(p) for p in patterns.values())

        if max_score == 0:
            return ("report", 0.5)  # Default with medium confidence

        # Find winner
        winner = max(scores, key=scores.get)

        # Calculate confidence based on:
        # 1. How many patterns matched
        # 2. How much higher winner is than second place
        sorted_scores = sorted(scores.values(), reverse=True)
        second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0

        # Confidence formula
        match_ratio = max_score / len(patterns[winner])
        dominance = (max_score - second_score) / max(max_score, 1)
        confidence = (match_ratio * 0.6) + (dominance * 0.4)
        confidence = min(1.0, max(0.0, confidence))

        return (winner, confidence)
