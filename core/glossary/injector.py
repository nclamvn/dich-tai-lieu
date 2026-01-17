"""
Glossary Injector
Inject glossary terms into translation prompts.
"""
import logging
from typing import List, Dict, Optional

from .matcher import TermMatch, get_matcher

logger = logging.getLogger(__name__)


class GlossaryInjector:
    """
    Inject glossary terms into LLM translation prompts.

    Adds a glossary section to prompts that instructs the LLM
    to use specific translations for matched terms.
    """

    # Template for glossary injection
    GLOSSARY_TEMPLATE = """
## GLOSSARY - Thuật ngữ bắt buộc

Khi dịch, BẮT BUỘC sử dụng các thuật ngữ sau đây:

{terms}

**QUAN TRỌNG:** Sử dụng CHÍNH XÁC các bản dịch trên cho các thuật ngữ này. KHÔNG được thay đổi hoặc dịch khác đi.
"""

    GLOSSARY_TEMPLATE_EN = """
## GLOSSARY - Required Terminology

When translating, you MUST use the following translations:

{terms}

**IMPORTANT:** Use the EXACT translations above for these terms. Do NOT change or translate them differently.
"""

    def __init__(self, language: str = "vi"):
        """
        Initialize injector.

        Args:
            language: Language for instructions (vi, en)
        """
        self.language = language
        self.matcher = get_matcher()

    def create_glossary_section(
        self,
        matches: List[TermMatch],
        format: str = "bullet",
    ) -> str:
        """
        Create glossary section for prompt injection.

        Args:
            matches: List of matched terms
            format: Format style (bullet, table, inline)

        Returns:
            Formatted glossary section
        """
        if not matches:
            return ""

        # Get unique terms (deduplicate)
        unique_terms = self.matcher.get_unique_terms(matches)

        if not unique_terms:
            return ""

        # Format terms based on style
        if format == "table":
            terms_text = self._format_as_table(unique_terms)
        elif format == "inline":
            terms_text = self._format_as_inline(unique_terms)
        else:  # bullet
            terms_text = self._format_as_bullets(unique_terms)

        # Use appropriate template
        template = self.GLOSSARY_TEMPLATE if self.language == "vi" else self.GLOSSARY_TEMPLATE_EN

        return template.format(terms=terms_text)

    def _format_as_bullets(self, terms: Dict[str, str]) -> str:
        """Format terms as bullet list."""
        lines = []
        for source, target in terms.items():
            lines.append(f"- \"{source}\" → \"{target}\"")
        return "\n".join(lines)

    def _format_as_table(self, terms: Dict[str, str]) -> str:
        """Format terms as markdown table."""
        lines = ["| Source | Target |", "|--------|--------|"]
        for source, target in terms.items():
            lines.append(f"| {source} | {target} |")
        return "\n".join(lines)

    def _format_as_inline(self, terms: Dict[str, str]) -> str:
        """Format terms as inline list."""
        pairs = [f"\"{s}\"=\"{t}\"" for s, t in terms.items()]
        return ", ".join(pairs)

    def inject_into_prompt(
        self,
        original_prompt: str,
        glossary_ids: List[str],
        source_text: str,
        format: str = "bullet",
    ) -> tuple:
        """
        Inject glossary terms into translation prompt.

        Args:
            original_prompt: Original translation prompt
            glossary_ids: List of glossary IDs to use
            source_text: Source text being translated
            format: Format style for terms

        Returns:
            Tuple of (modified_prompt, matches)
        """
        if not glossary_ids or not source_text:
            return original_prompt, []

        # Find matches in source text
        matches = self.matcher.find_matches(source_text, glossary_ids)

        if not matches:
            return original_prompt, []

        # Create glossary section
        glossary_section = self.create_glossary_section(matches, format)

        # Inject into prompt
        # Strategy: Add glossary section before the source text
        if "```" in original_prompt:
            # If prompt has code blocks, insert before first code block
            parts = original_prompt.split("```", 1)
            modified_prompt = parts[0] + glossary_section + "\n```" + parts[1]
        else:
            # Otherwise, add at the end
            modified_prompt = original_prompt + "\n" + glossary_section

        logger.info(f"Injected {len(matches)} glossary terms into prompt")

        return modified_prompt, matches

    def verify_translation(
        self,
        translation: str,
        matches: List[TermMatch],
    ) -> Dict:
        """
        Verify that translation contains required terms.

        Args:
            translation: Translated text
            matches: Expected term matches

        Returns:
            Dict with verification results
        """
        if not matches:
            return {"verified": True, "missing": [], "found": []}

        unique_terms = self.matcher.get_unique_terms(matches)
        found = []
        missing = []

        for source, target in unique_terms.items():
            if target.lower() in translation.lower():
                found.append({"source": source, "target": target})
            else:
                missing.append({"source": source, "target": target})

        verified = len(missing) == 0

        return {
            "verified": verified,
            "found": found,
            "missing": missing,
            "found_count": len(found),
            "missing_count": len(missing),
        }


# Global instance
_injector: Optional[GlossaryInjector] = None


def get_injector(language: str = "vi") -> GlossaryInjector:
    """Get or create the global injector instance."""
    global _injector
    if _injector is None:
        _injector = GlossaryInjector(language)
    return _injector
