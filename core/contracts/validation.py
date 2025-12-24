#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contract Validation Layer

Provides utilities for validating contracts between agents.

Version: 1.0.0
"""

from typing import List, Dict, Any, TypeVar
import logging

from .base import BaseContract, ContractValidationError
from .manuscript_output import ManuscriptCoreOutput
from .layout_intent import LayoutIntentPackage

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseContract)


class ContractValidator:
    """
    Validates contracts between agents.

    Usage:
        validator = ContractValidator()

        # Validate single contract
        errors = validator.validate(manuscript_output)

        # Validate and raise error
        validator.validate_or_raise(manuscript_output)

        # Validate chain
        validator.validate_chain(manuscript_output, layout_intent)
    """

    def __init__(self, strict: bool = True):
        """
        Initialize validator.

        Args:
            strict: If True, raise errors on validation failure
        """
        self.strict = strict

    def validate(self, contract: BaseContract) -> List[str]:
        """
        Validate a contract.

        Args:
            contract: Contract to validate

        Returns:
            List of validation errors
        """
        errors = contract.validate()

        if errors:
            logger.warning(f"Contract validation failed: {errors}")
        else:
            logger.debug(f"Contract validated: {contract.metadata.source_agent}")

        return errors

    def validate_or_raise(self, contract: BaseContract) -> None:
        """
        Validate contract and raise error if invalid.

        Args:
            contract: Contract to validate

        Raises:
            ContractValidationError: If validation fails
        """
        errors = self.validate(contract)

        if errors:
            raise ContractValidationError(errors)

        logger.info(f"Contract validated successfully: {contract.metadata.source_agent}")

    def validate_chain(
        self,
        *contracts: BaseContract,
    ) -> Dict[str, List[str]]:
        """
        Validate a chain of contracts (Agent #1 -> #2 -> #3).

        Args:
            contracts: Contracts in order

        Returns:
            Dict of contract type to errors
        """
        results = {}

        for i, contract in enumerate(contracts):
            contract_type = type(contract).__name__
            errors = self.validate(contract)
            results[f"{i}_{contract_type}"] = errors

            if errors and self.strict:
                raise ContractValidationError(errors)

        return results

    def verify_checksum(self, contract: BaseContract, expected: str) -> bool:
        """
        Verify contract checksum.

        Args:
            contract: Contract to verify
            expected: Expected checksum

        Returns:
            True if checksum matches
        """
        data = contract.to_dict()
        # Calculate checksum without the checksum field itself
        actual = contract.metadata.calculate_checksum(data)

        if actual != expected:
            logger.warning(f"Checksum mismatch: expected {expected}, got {actual}")
            return False

        logger.debug(f"Checksum verified: {actual}")
        return True

    def validate_manuscript_output(self, output: ManuscriptCoreOutput) -> List[str]:
        """
        Validate a ManuscriptCoreOutput with additional checks.

        Args:
            output: Manuscript output to validate

        Returns:
            List of validation errors
        """
        errors = output.validate()

        # Additional checks
        if output.segments:
            # Check for reasonable confidence scores
            low_confidence = [s for s in output.segments if s.confidence < 0.3]
            if len(low_confidence) > len(output.segments) * 0.5:
                errors.append("More than 50% of segments have very low confidence")

            # Check for empty translations
            empty_translations = [s for s in output.segments if s.original_text and not s.translated_text]
            if empty_translations:
                errors.append(f"{len(empty_translations)} segments have original text but no translation")

        return errors

    def validate_layout_intent(self, lip: LayoutIntentPackage) -> List[str]:
        """
        Validate a LayoutIntentPackage with additional checks.

        Args:
            lip: Layout intent package to validate

        Returns:
            List of validation errors
        """
        errors = lip.validate()

        # Additional checks
        if lip.blocks:
            # Check for empty content blocks
            empty_content = [b for b in lip.blocks if not b.content and b.type.value not in ['separator', 'scene_break', 'page_number']]
            if empty_content:
                errors.append(f"{len(empty_content)} content blocks have no content")

            # Check TOC consistency
            toc_entries = lip.get_toc_entries()
            for entry in toc_entries:
                if entry.toc_level < 0:
                    errors.append(f"Block {entry.id} has invalid toc_level: {entry.toc_level}")

        # Check sections
        if lip.sections:
            block_ids = {b.id for b in lip.blocks}
            for section in lip.sections:
                if section.start_block_id not in block_ids:
                    errors.append(f"Section start_block_id '{section.start_block_id}' not found in blocks")
                if section.end_block_id not in block_ids:
                    errors.append(f"Section end_block_id '{section.end_block_id}' not found in blocks")

        return errors


def validate_manuscript_to_lip(
    manuscript: ManuscriptCoreOutput,
    lip: LayoutIntentPackage,
) -> List[str]:
    """
    Validate that a LayoutIntentPackage correctly represents a ManuscriptCoreOutput.

    Args:
        manuscript: Source manuscript output
        lip: Generated layout intent package

    Returns:
        List of validation errors
    """
    errors = []

    # Check segment count matches block count (approximately)
    manuscript_segment_count = len(manuscript.segments)
    lip_content_blocks = [b for b in lip.blocks if b.content]

    # Allow 20% variance due to splitting/merging
    if manuscript_segment_count > 0:
        variance = abs(manuscript_segment_count - len(lip_content_blocks)) / manuscript_segment_count
        if variance > 0.2:
            errors.append(
                f"Block count variance too high: {len(lip_content_blocks)} blocks for {manuscript_segment_count} segments ({variance:.1%} variance)"
            )

    # Check all text is preserved (approximately)
    manuscript_text = manuscript.get_full_text()
    lip_text = lip.get_full_text()

    # Simple length check (within 5%)
    if len(manuscript_text) > 0:
        length_diff = abs(len(manuscript_text) - len(lip_text)) / len(manuscript_text)
        if length_diff > 0.05:
            errors.append(f"Text content may have been lost in transformation ({length_diff:.1%} difference)")

    # Check structure alignment
    if manuscript.structure.has_front_matter:
        front_sections = [s for s in lip.sections if s.type.value in ['foreword', 'preface', 'dedication', 'acknowledgments']]
        if not front_sections:
            errors.append("Manuscript has front matter but LIP has no front sections")

    if manuscript.structure.total_chapters > 0:
        lip_chapters = lip.get_chapters()
        if len(lip_chapters) < manuscript.structure.total_chapters * 0.8:
            errors.append(f"LIP has fewer chapters ({len(lip_chapters)}) than manuscript ({manuscript.structure.total_chapters})")

    return errors


def create_contract_summary(contract: BaseContract) -> Dict[str, Any]:
    """
    Create a human-readable summary of a contract.

    Args:
        contract: Contract to summarize

    Returns:
        Summary dictionary
    """
    summary = {
        "type": type(contract).__name__,
        "source_agent": contract.metadata.source_agent,
        "target_agent": contract.metadata.target_agent,
        "version": contract.metadata.version,
        "is_valid": contract.is_valid(),
    }

    if isinstance(contract, ManuscriptCoreOutput):
        summary.update({
            "segments": len(contract.segments),
            "source_language": contract.source_language,
            "target_language": contract.target_language,
            "quality_score": contract.quality.overall_score,
            "has_adn": bool(contract.adn),
            "has_stem": bool(contract.stem.get("formulas") or contract.stem.get("code_blocks")),
        })

    elif isinstance(contract, LayoutIntentPackage):
        summary.update({
            "blocks": len(contract.blocks),
            "sections": len(contract.sections),
            "title": contract.title,
            "template": contract.template,
            "consistency_issues": contract.consistency.unresolved_count,
        })

    return summary
