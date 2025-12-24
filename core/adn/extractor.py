#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADN Extractor - Main Orchestrator

Coordinates all ADN extraction components to produce
complete Content ADN for a document.

This is part of Agent #1 (Manuscript Core) output.

Version: 1.0.0
"""

from typing import List, Dict, Optional
import logging

from .schema import ContentADN, Character, Term, ProperNoun, Pattern, ProperNounType
from .proper_nouns import ProperNounExtractor
from .patterns import PatternDetector

logger = logging.getLogger(__name__)


class ADNExtractor:
    """
    Main ADN extraction orchestrator.

    Coordinates proper noun extraction, pattern detection, and
    terminology management to produce complete Content ADN.

    Usage:
        extractor = ADNExtractor(source_lang='ja', target_lang='vi')
        adn = extractor.extract(segments)
        json_output = adn.to_json()
    """

    def __init__(
        self,
        source_lang: str = 'en',
        target_lang: str = 'vi',
        glossary: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize ADN extractor.

        Args:
            source_lang: Source language code (en, vi, ja, zh, ko)
            target_lang: Target language code
            glossary: Optional existing glossary for terms {original: translation}
        """
        self.source_lang = source_lang.lower()[:2]
        self.target_lang = target_lang.lower()[:2]
        self.glossary = glossary or {}

        # Initialize sub-extractors
        self.proper_noun_extractor = ProperNounExtractor(self.source_lang)
        self.pattern_detector = PatternDetector(self.source_lang)

        logger.info(f"ADNExtractor initialized: {self.source_lang} -> {self.target_lang}")

    def extract(
        self,
        segments: List[str],
        document_type: str = "unknown",
    ) -> ContentADN:
        """
        Extract complete Content ADN from document segments.

        Args:
            segments: List of text segments (paragraphs, chunks, etc.)
            document_type: Type of document (book, article, report, technical, etc.)

        Returns:
            ContentADN object with all extracted information
        """
        logger.info(f"Extracting ADN from {len(segments)} segments")

        # Create ADN container
        adn = ContentADN(
            source_language=self.source_lang,
            target_language=self.target_lang,
            document_type=document_type,
            total_segments=len(segments),
        )

        # 1. Extract proper nouns
        logger.info("Step 1/4: Extracting proper nouns...")
        proper_nouns = self.proper_noun_extractor.extract_from_segments(segments)
        proper_nouns = self.proper_noun_extractor.find_variants(proper_nouns)
        adn.proper_nouns = proper_nouns
        logger.info(f"  Found {len(proper_nouns)} proper nouns")

        # 2. Extract structural patterns
        logger.info("Step 2/4: Detecting structural patterns...")
        patterns = self.pattern_detector.detect(segments)
        custom_patterns = self.pattern_detector.detect_custom_patterns(segments)
        adn.patterns = patterns + custom_patterns
        logger.info(f"  Found {len(adn.patterns)} patterns ({len(patterns)} standard, {len(custom_patterns)} custom)")

        # 3. Extract characters (from proper nouns of type PERSON)
        logger.info("Step 3/4: Identifying characters...")
        adn.characters = self._extract_characters(proper_nouns, segments)
        logger.info(f"  Found {len(adn.characters)} characters")

        # 4. Process terminology from glossary
        logger.info("Step 4/4: Processing terminology...")
        adn.terms = self._extract_terms(segments)
        adn.unique_terms = len(adn.terms)
        logger.info(f"  Found {len(adn.terms)} terms from glossary")

        # Calculate statistics
        adn.total_characters = sum(len(s) for s in segments)

        logger.info("ADN extraction complete")
        return adn

    def _extract_characters(
        self,
        proper_nouns: List[ProperNoun],
        segments: List[str],
    ) -> List[Character]:
        """
        Extract character entities from proper nouns.

        Args:
            proper_nouns: List of extracted proper nouns
            segments: Original text segments

        Returns:
            List of Character objects
        """
        characters = []

        # Filter person-type proper nouns
        person_nouns = [
            pn for pn in proper_nouns
            if pn.type == ProperNounType.PERSON
        ]

        for pn in person_nouns:
            # Determine role based on occurrence frequency
            occurrence_count = len(pn.occurrences)

            if occurrence_count >= 10:
                role = "main"
            elif occurrence_count >= 5:
                role = "supporting"
            elif occurrence_count >= 2:
                role = "minor"
            else:
                role = "mentioned"

            characters.append(Character(
                name=pn.text,
                variants=pn.variants,
                role=role,
                first_appearance=min(pn.occurrences) if pn.occurrences else 0,
                occurrences=pn.occurrences,
            ))

        # Sort by first appearance
        characters.sort(key=lambda c: c.first_appearance)

        return characters

    def _extract_terms(self, segments: List[str]) -> List[Term]:
        """
        Extract and count terminology from glossary.

        Args:
            segments: Text segments

        Returns:
            List of Term objects with frequency counts
        """
        if not self.glossary:
            return []

        terms = []
        full_text = ' '.join(segments).lower()

        for original, translation in self.glossary.items():
            # Count occurrences (case-insensitive)
            frequency = full_text.count(original.lower())

            if frequency > 0:
                # Find example contexts
                examples = self._find_term_examples(original, segments, max_examples=3)

                terms.append(Term(
                    original=original,
                    translation=translation,
                    frequency=frequency,
                    context_examples=examples,
                ))

        # Sort by frequency (most frequent first)
        terms.sort(key=lambda t: t.frequency, reverse=True)

        return terms

    def _find_term_examples(
        self,
        term: str,
        segments: List[str],
        max_examples: int = 3
    ) -> List[str]:
        """Find example sentences containing a term."""
        examples = []
        term_lower = term.lower()

        for segment in segments:
            if term_lower in segment.lower():
                # Extract sentence containing the term
                sentences = segment.replace('\n', ' ').split('.')
                for sentence in sentences:
                    if term_lower in sentence.lower():
                        clean_sentence = sentence.strip()
                        if 10 <= len(clean_sentence) <= 200:
                            examples.append(clean_sentence + '.')
                            if len(examples) >= max_examples:
                                return examples

        return examples

    def extract_to_json(
        self,
        segments: List[str],
        document_type: str = "unknown",
        indent: int = 2,
    ) -> str:
        """
        Extract ADN and return as JSON string.

        Convenience method for direct JSON output.

        Args:
            segments: Text segments
            document_type: Type of document
            indent: JSON indentation

        Returns:
            JSON string representation of ADN
        """
        adn = self.extract(segments, document_type)
        return adn.to_json(indent=indent)

    def extract_to_dict(
        self,
        segments: List[str],
        document_type: str = "unknown",
    ) -> Dict:
        """
        Extract ADN and return as dictionary.

        Args:
            segments: Text segments
            document_type: Type of document

        Returns:
            Dictionary representation of ADN
        """
        adn = self.extract(segments, document_type)
        return adn.to_dict()

    def update_glossary(self, terms: Dict[str, str]) -> None:
        """
        Update the glossary with new terms.

        Args:
            terms: Dictionary of {original: translation} pairs
        """
        self.glossary.update(terms)
        logger.info(f"Glossary updated: now contains {len(self.glossary)} terms")

    def get_statistics(self, segments: List[str]) -> Dict:
        """
        Get extraction statistics without full extraction.

        Useful for quick analysis.

        Args:
            segments: Text segments

        Returns:
            Dictionary with statistics
        """
        # Quick pattern analysis
        structure = self.pattern_detector.get_document_structure_summary(segments)

        # Quick proper noun count
        all_nouns = self.proper_noun_extractor.extract_from_segments(segments)
        person_count = sum(1 for n in all_nouns if n.type == ProperNounType.PERSON)
        place_count = sum(1 for n in all_nouns if n.type == ProperNounType.PLACE)
        org_count = sum(1 for n in all_nouns if n.type == ProperNounType.ORGANIZATION)

        return {
            'total_segments': len(segments),
            'total_characters': sum(len(s) for s in segments),
            'total_words': sum(len(s.split()) for s in segments),
            'proper_nouns': {
                'total': len(all_nouns),
                'persons': person_count,
                'places': place_count,
                'organizations': org_count,
            },
            'structure': structure,
            'glossary_terms': len(self.glossary),
        }
