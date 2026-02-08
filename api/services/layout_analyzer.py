"""
Layout Analyzer — orchestrates table + formula extraction into LayoutDNA.

Takes plain text, detects structural regions (headings, lists, tables,
formulas, code blocks), and produces a LayoutDNA representation.

Pipeline:
  text → heading detection
       → code block detection
       → table extraction (TextTableExtractor)
       → formula extraction (FormulaExtractor)
       → list detection
       → remaining text → TEXT regions
       → assemble LayoutDNA

Standalone module — no extraction or translation imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from config.logging_config import get_logger

from api.services.layout_dna import LayoutDNA, Region, RegionType
from api.services.table_extractor import TextTableExtractor
from api.services.formula_extractor import FormulaExtractor

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Heading: markdown or numbered
_HEADING = re.compile(
    r'^(?:'
    r'(#{1,6})\s+(.+)'           # Markdown: # Title
    r'|(\d+\.)\s+([A-Z].+)'      # Numbered: 1. Introduction
    r'|([A-Z][A-Z\s]{2,})'       # ALL CAPS lines (>=3 chars)
    r')$',
    re.MULTILINE,
)

# Code block: triple backtick fences
_CODE_BLOCK = re.compile(
    r'^```(\w*)\n(.*?)^```',
    re.MULTILINE | re.DOTALL,
)

# List item: bullet or numbered
_LIST_ITEM = re.compile(
    r'^(\s*)([-*+•]|\d+[.)]) (.+)$',
    re.MULTILINE,
)

# Image placeholder: ![alt](url) or [IMAGE: ...]
_IMAGE_REF = re.compile(
    r'!\[([^\]]*)\]\([^)]+\)'
    r'|\[IMAGE:\s*([^\]]+)\]',
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Span: internal tracking of claimed regions
# ---------------------------------------------------------------------------

@dataclass
class _Span:
    """A claimed region of the source text."""
    start: int
    end: int
    region_type: RegionType
    content: str
    level: int = 0
    metadata: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# LayoutAnalyzer
# ---------------------------------------------------------------------------

class LayoutAnalyzer:
    """Analyze text and produce LayoutDNA.

    Usage::

        analyzer = LayoutAnalyzer()
        dna = analyzer.analyze("# Title\\n\\nSome text with $x^2$...")

        print(dna.summary())
        for region in dna.regions:
            print(region.type, region.content[:50])
    """

    def __init__(
        self,
        detect_tables: bool = True,
        detect_formulas: bool = True,
        detect_code: bool = True,
        detect_lists: bool = True,
        detect_images: bool = True,
        min_text_length: int = 5,
    ):
        self.detect_tables = detect_tables
        self.detect_formulas = detect_formulas
        self.detect_code = detect_code
        self.detect_lists = detect_lists
        self.detect_images = detect_images
        self.min_text_length = min_text_length

        self._table_extractor = TextTableExtractor()
        self._formula_extractor = FormulaExtractor()

    def analyze(
        self,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> LayoutDNA:
        """Analyze text and return LayoutDNA.

        Args:
            text: Full document text.
            metadata: Optional document metadata to attach.

        Returns:
            LayoutDNA with typed regions.
        """
        if not text or not text.strip():
            return LayoutDNA(metadata=metadata or {})

        spans: List[_Span] = []

        # 1. Detect code blocks (highest priority — content inside is opaque)
        if self.detect_code:
            spans.extend(self._find_code_blocks(text))

        # 2. Detect tables
        if self.detect_tables:
            spans.extend(self._find_tables(text, spans))

        # 3. Detect formulas (display mode only as regions)
        if self.detect_formulas:
            spans.extend(self._find_formulas(text, spans))

        # 4. Detect image references
        if self.detect_images:
            spans.extend(self._find_images(text, spans))

        # 5. Detect headings
        spans.extend(self._find_headings(text, spans))

        # 6. Detect list blocks
        if self.detect_lists:
            spans.extend(self._find_lists(text, spans))

        # 7. Fill remaining text as TEXT regions
        spans.extend(self._fill_text_gaps(text, spans))

        # Sort by position
        spans.sort(key=lambda s: s.start)

        # Build LayoutDNA
        regions = []
        for span in spans:
            if span.content.strip():
                regions.append(Region(
                    type=span.region_type,
                    content=span.content,
                    level=span.level,
                    metadata=span.metadata,
                    start_offset=span.start,
                    end_offset=span.end,
                ))

        dna = LayoutDNA(regions=regions, metadata=metadata or {})

        logger.info(
            "LayoutAnalyzer: %d chars → %s",
            len(text), dna.summary(),
        )

        return dna

    # -- Detection methods ---------------------------------------------------

    def _find_code_blocks(self, text: str) -> List[_Span]:
        """Find fenced code blocks."""
        spans = []
        for m in _CODE_BLOCK.finditer(text):
            lang = m.group(1) or ""
            code = m.group(2)
            spans.append(_Span(
                start=m.start(),
                end=m.end(),
                region_type=RegionType.CODE,
                content=code.strip(),
                metadata={"language": lang} if lang else {},
            ))
        return spans

    def _find_tables(
        self, text: str, existing: List[_Span],
    ) -> List[_Span]:
        """Find tables that don't overlap existing spans."""
        tables = self._table_extractor.extract(text)
        spans = []
        for table in tables:
            if not self._overlaps(table.start_offset, table.end_offset, existing):
                spans.append(_Span(
                    start=table.start_offset,
                    end=table.end_offset,
                    region_type=RegionType.TABLE,
                    content=table.raw_text,
                    metadata={
                        "format": table.format.value,
                        "rows": table.num_rows,
                        "cols": table.num_cols,
                        "has_header": table.has_header,
                        "caption": table.caption,
                    },
                ))
        return spans

    def _find_formulas(
        self, text: str, existing: List[_Span],
    ) -> List[_Span]:
        """Find display formulas as separate regions.

        Inline formulas stay embedded in their TEXT region.
        """
        formulas = self._formula_extractor.extract(text)
        spans = []
        for f in formulas:
            # Only promote DISPLAY formulas to their own region
            if f.mode.value == "display":
                if not self._overlaps(f.start, f.end, existing):
                    spans.append(_Span(
                        start=f.start,
                        end=f.end,
                        region_type=RegionType.FORMULA,
                        content=f.content,
                        metadata={
                            "kind": f.kind.value,
                            "env_name": f.env_name,
                            "mode": f.mode.value,
                        },
                    ))
        return spans

    def _find_images(
        self, text: str, existing: List[_Span],
    ) -> List[_Span]:
        """Find image references."""
        spans = []
        for m in _IMAGE_REF.finditer(text):
            if not self._overlaps(m.start(), m.end(), existing):
                alt = m.group(1) or m.group(2) or ""
                spans.append(_Span(
                    start=m.start(),
                    end=m.end(),
                    region_type=RegionType.IMAGE,
                    content=m.group(0),
                    metadata={"alt_text": alt.strip()},
                ))
        return spans

    def _find_headings(
        self, text: str, existing: List[_Span],
    ) -> List[_Span]:
        """Find heading lines."""
        spans = []
        for m in _HEADING.finditer(text):
            if self._overlaps(m.start(), m.end(), existing):
                continue

            # Determine level
            if m.group(1):  # Markdown
                level = len(m.group(1))
                content = m.group(2)
            elif m.group(3):  # Numbered
                level = 1
                content = m.group(0).strip()
            else:  # ALL CAPS
                level = 1
                content = m.group(5).strip()

            # Skip very short ALL CAPS that might be false positives
            if not m.group(1) and not m.group(3):
                if len(content.strip()) < 4:
                    continue

            spans.append(_Span(
                start=m.start(),
                end=m.end(),
                region_type=RegionType.HEADING,
                content=content.strip(),
                level=level,
            ))
        return spans

    def _find_lists(
        self, text: str, existing: List[_Span],
    ) -> List[_Span]:
        """Find contiguous list blocks."""
        spans = []
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            m = _LIST_ITEM.match(lines[i])
            if m:
                # Calculate offset
                offset = sum(len(lines[j]) + 1 for j in range(i))
                if self._overlaps(offset, offset + len(lines[i]), existing + spans):
                    i += 1
                    continue

                # Gather contiguous list items
                start_idx = i
                indent = len(m.group(1))
                max_level = 1

                while i < len(lines):
                    lm = _LIST_ITEM.match(lines[i])
                    if lm:
                        item_indent = len(lm.group(1))
                        level = (item_indent // 2) + 1
                        max_level = max(max_level, level)
                        i += 1
                    elif lines[i].strip() == '':
                        # Allow one blank line within a list
                        if i + 1 < len(lines) and _LIST_ITEM.match(lines[i + 1]):
                            i += 1
                        else:
                            break
                    else:
                        break

                if i - start_idx >= 2:
                    list_lines = lines[start_idx:i]
                    content = '\n'.join(list_lines)
                    end_offset = offset + len(content)

                    if not self._overlaps(offset, end_offset, existing + spans):
                        spans.append(_Span(
                            start=offset,
                            end=end_offset,
                            region_type=RegionType.LIST,
                            content=content,
                            level=max_level,
                            metadata={"items": i - start_idx},
                        ))
            else:
                i += 1

        return spans

    def _fill_text_gaps(
        self, text: str, claimed: List[_Span],
    ) -> List[_Span]:
        """Fill unclaimed regions as TEXT."""
        claimed_sorted = sorted(claimed, key=lambda s: s.start)
        gaps: List[_Span] = []
        pos = 0

        for span in claimed_sorted:
            if span.start > pos:
                gap_text = text[pos:span.start]
                if gap_text.strip() and len(gap_text.strip()) >= self.min_text_length:
                    gaps.append(_Span(
                        start=pos,
                        end=span.start,
                        region_type=RegionType.TEXT,
                        content=gap_text.strip(),
                    ))
            pos = max(pos, span.end)

        # Trailing text
        if pos < len(text):
            gap_text = text[pos:]
            if gap_text.strip() and len(gap_text.strip()) >= self.min_text_length:
                gaps.append(_Span(
                    start=pos,
                    end=len(text),
                    region_type=RegionType.TEXT,
                    content=gap_text.strip(),
                ))

        return gaps

    # -- Utilities -----------------------------------------------------------

    def _overlaps(
        self,
        start: int,
        end: int,
        existing: List[_Span],
    ) -> bool:
        """Check if [start, end) overlaps with any existing span."""
        for span in existing:
            if start < span.end and end > span.start:
                return True
        return False
