#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADN (Content DNA) Module

Extracts content DNA from documents for consistent translation
and publishing. This is part of Agent #1 (Manuscript Core).

The ADN includes:
- Proper nouns (people, places, organizations)
- Characters and their relationships
- Terminology with translations
- Structural patterns (chapters, sections, lists, dialogue)

Usage:
    from core.adn import ADNExtractor, ContentADN

    # Create extractor
    extractor = ADNExtractor(source_lang='ja', target_lang='vi')

    # Extract from segments
    segments = ["Chapter 1: Introduction", "John Smith walked in.", ...]
    adn = extractor.extract(segments, document_type='book')

    # Get JSON output (for Agent #2)
    json_output = adn.to_json()

    # Or get dictionary
    dict_output = adn.to_dict()

Version: 1.0.0
Author: AI Translator Pro Team
"""

from .schema import (
    ContentADN,
    ProperNoun,
    ProperNounType,
    Character,
    Term,
    Pattern,
    PatternType,
)
from .extractor import ADNExtractor
from .extractor_optimized import OptimizedADNExtractor, ADNExtractorOptimized
from .proper_nouns import ProperNounExtractor
from .patterns import PatternDetector

__all__ = [
    # Main orchestrator
    "ADNExtractor",

    # Optimized extractor
    "OptimizedADNExtractor",
    "ADNExtractorOptimized",

    # Schema classes
    "ContentADN",
    "ProperNoun",
    "ProperNounType",
    "Character",
    "Term",
    "Pattern",
    "PatternType",

    # Sub-extractors (for advanced usage)
    "ProperNounExtractor",
    "PatternDetector",
]

__version__ = "1.0.0"
