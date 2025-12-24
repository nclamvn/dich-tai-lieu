"""
Placeholder Management Module

Manages the replacement and restoration of formulas and code blocks
during translation to preserve their exact content.
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Union
from .formula_detector import FormulaMatch, FormulaType
from .code_detector import CodeMatch, CodeType


@dataclass
class ProcessedContent:
    """Result of preprocessing text with placeholders"""
    text: str  # Text with placeholders
    mapping: Dict[str, Dict]  # Placeholder -> original content mapping
    formula_count: int
    code_count: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'text': self.text,
            'mapping': self.mapping,
            'formula_count': self.formula_count,
            'code_count': self.code_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedContent':
        """Create from dictionary"""
        return cls(**data)


class PlaceholderManager:
    """
    Manages placeholders for formulas and code blocks

    Workflow:
    1. Detect formulas and code in text
    2. Replace them with stable placeholders
    3. Send preprocessed text to LLM for translation
    4. Restore original formulas/code from placeholders
    """

    # Placeholder format: ⟪STEM_TYPE_HASH⟫
    # Using unicode brackets to avoid conflicts with common text
    PLACEHOLDER_PREFIX = "⟪STEM"
    PLACEHOLDER_SUFFIX = "⟫"

    def __init__(self):
        """Initialize placeholder manager"""
        pass

    def preprocess(
        self,
        text: str,
        formula_matches: List[FormulaMatch],
        code_matches: List[CodeMatch]
    ) -> ProcessedContent:
        """
        Replace formulas and code blocks with placeholders

        Args:
            text: Original text
            formula_matches: Detected formula matches
            code_matches: Detected code matches

        Returns:
            ProcessedContent with placeholders and mapping
        """
        # Combine all matches and sort by position (reverse order for replacement)
        all_matches = []

        for match in formula_matches:
            all_matches.append({
                'type': 'formula',
                'match': match,
                'start': match.start,
                'end': match.end
            })

        for match in code_matches:
            all_matches.append({
                'type': 'code',
                'match': match,
                'start': match.start,
                'end': match.end
            })

        # Sort by position (descending) to replace from end to start
        all_matches.sort(key=lambda x: x['start'], reverse=True)

        # Build mapping and replace text
        mapping = {}
        processed_text = text

        for item in all_matches:
            match_obj = item['match']
            content_type = item['type']

            # Generate placeholder
            placeholder = self._generate_placeholder(
                content=match_obj.content,
                content_type=content_type,
                match=match_obj
            )

            # Store mapping
            mapping[placeholder] = {
                'type': content_type,
                'content': match_obj.content,
                'meta': self._extract_metadata(match_obj)
            }

            # Replace in text
            processed_text = (
                processed_text[:match_obj.start] +
                placeholder +
                processed_text[match_obj.end:]
            )

        return ProcessedContent(
            text=processed_text,
            mapping=mapping,
            formula_count=len(formula_matches),
            code_count=len(code_matches)
        )

    def restore(
        self,
        translated_text: str,
        mapping: Dict[str, Dict]
    ) -> str:
        """
        Restore original formulas and code from placeholders

        Args:
            translated_text: Text with placeholders
            mapping: Placeholder -> content mapping

        Returns:
            Text with restored formulas and code
        """
        restored_text = translated_text

        for placeholder, info in mapping.items():
            original_content = info['content']
            # Replace placeholder with original content
            restored_text = restored_text.replace(placeholder, original_content)

        return restored_text

    def _generate_placeholder(
        self,
        content: str,
        content_type: str,
        match: Union[FormulaMatch, CodeMatch]
    ) -> str:
        """
        Generate a stable, unique placeholder

        Format: ⟪STEM_FORMULA_abc123⟫ or ⟪STEM_CODE_xyz789⟫

        Args:
            content: Original content
            content_type: 'formula' or 'code'
            match: Match object with metadata

        Returns:
            Placeholder string
        """
        # Create hash of content for uniqueness
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]

        # Get subtype
        if content_type == 'formula':
            subtype = match.formula_type.value.upper()
        else:  # code
            subtype = match.code_type.value.upper()

        # Format: ⟪STEM_FORMULA_INLINE_abc123⟫
        placeholder = (
            f"{self.PLACEHOLDER_PREFIX}_{content_type.upper()}_"
            f"{subtype}_{content_hash}{self.PLACEHOLDER_SUFFIX}"
        )

        return placeholder

    def _extract_metadata(self, match: Union[FormulaMatch, CodeMatch]) -> dict:
        """Extract metadata from match object"""
        meta = {
            'start': match.start,
            'end': match.end,
        }

        if isinstance(match, FormulaMatch):
            meta['formula_type'] = match.formula_type.value
            if match.environment_name:
                meta['environment'] = match.environment_name
        elif isinstance(match, CodeMatch):
            meta['code_type'] = match.code_type.value
            if match.language:
                meta['language'] = match.language
            if match.indent_level:
                meta['indent_level'] = match.indent_level

        return meta

    def verify_restoration(
        self,
        original_text: str,
        restored_text: str,
        formula_matches: List[FormulaMatch],
        code_matches: List[CodeMatch]
    ) -> dict:
        """
        Verify that all formulas and code were correctly restored

        Args:
            original_text: Original text before processing
            restored_text: Text after translation and restoration
            formula_matches: Original formula matches
            code_matches: Original code matches

        Returns:
            Verification result with statistics
        """
        # Count placeholders remaining in restored text
        remaining_placeholders = restored_text.count(self.PLACEHOLDER_PREFIX)

        # Check if all formulas are present
        formula_preservation = []
        for match in formula_matches:
            if match.content in restored_text:
                formula_preservation.append(True)
            else:
                formula_preservation.append(False)

        # Check if all code blocks are present
        code_preservation = []
        for match in code_matches:
            if match.content in restored_text:
                code_preservation.append(True)
            else:
                code_preservation.append(False)

        return {
            'success': remaining_placeholders == 0,
            'remaining_placeholders': remaining_placeholders,
            'formulas_preserved': sum(formula_preservation),
            'formulas_total': len(formula_matches),
            'formulas_lost': len(formula_matches) - sum(formula_preservation),
            'code_preserved': sum(code_preservation),
            'code_total': len(code_matches),
            'code_lost': len(code_matches) - sum(code_preservation),
            'preservation_rate': (
                (sum(formula_preservation) + sum(code_preservation)) /
                (len(formula_matches) + len(code_matches))
                if (formula_matches or code_matches) else 1.0
            )
        }

    def get_stem_stats(self, processed: ProcessedContent) -> dict:
        """Get statistics about STEM content"""
        return {
            'total_items': processed.formula_count + processed.code_count,
            'formulas': processed.formula_count,
            'code_blocks': processed.code_count,
            'placeholders': len(processed.mapping),
            'text_length_original': len(processed.text),
        }

    def is_stem_heavy(
        self,
        formula_count: int,
        code_count: int,
        text_length: int,
        threshold: float = 0.05
    ) -> bool:
        """
        Determine if content is STEM-heavy

        Args:
            formula_count: Number of formulas
            code_count: Number of code blocks
            text_length: Total text length
            threshold: STEM content ratio threshold (default 5%)

        Returns:
            True if content is STEM-heavy
        """
        # Rough estimate: average formula/code is ~100 chars
        stem_content_length = (formula_count + code_count) * 100
        stem_ratio = stem_content_length / text_length if text_length > 0 else 0

        # Also check absolute count
        is_heavy = (
            stem_ratio >= threshold or
            formula_count >= 5 or
            code_count >= 3
        )

        return is_heavy

    def create_debug_output(
        self,
        original_text: str,
        processed: ProcessedContent,
        translated_text: str = None,
        restored_text: str = None
    ) -> str:
        """
        Create debug output showing the full pipeline

        Args:
            original_text: Original input text
            processed: ProcessedContent object
            translated_text: (Optional) Translated text with placeholders
            restored_text: (Optional) Final restored text

        Returns:
            Formatted debug output
        """
        output = []
        output.append("=" * 80)
        output.append("STEM TRANSLATION DEBUG OUTPUT")
        output.append("=" * 80)
        output.append("")

        output.append("STATISTICS:")
        output.append(f"  Formulas: {processed.formula_count}")
        output.append(f"  Code blocks: {processed.code_count}")
        output.append(f"  Total placeholders: {len(processed.mapping)}")
        output.append("")

        output.append("ORIGINAL TEXT:")
        output.append("-" * 80)
        output.append(original_text[:500] + ("..." if len(original_text) > 500 else ""))
        output.append("")

        output.append("PROCESSED TEXT (with placeholders):")
        output.append("-" * 80)
        output.append(processed.text[:500] + ("..." if len(processed.text) > 500 else ""))
        output.append("")

        output.append("PLACEHOLDER MAPPING:")
        output.append("-" * 80)
        for placeholder, info in list(processed.mapping.items())[:10]:  # Show first 10
            content_preview = info['content'][:60] + "..." if len(info['content']) > 60 else info['content']
            output.append(f"  {placeholder}")
            output.append(f"    Type: {info['type']}")
            output.append(f"    Content: {content_preview}")
            output.append("")

        if len(processed.mapping) > 10:
            output.append(f"  ... and {len(processed.mapping) - 10} more placeholders")
            output.append("")

        if translated_text:
            output.append("TRANSLATED TEXT (with placeholders):")
            output.append("-" * 80)
            output.append(translated_text[:500] + ("..." if len(translated_text) > 500 else ""))
            output.append("")

        if restored_text:
            output.append("RESTORED TEXT (final output):")
            output.append("-" * 80)
            output.append(restored_text[:500] + ("..." if len(restored_text) > 500 else ""))
            output.append("")

        output.append("=" * 80)

        return "\n".join(output)
