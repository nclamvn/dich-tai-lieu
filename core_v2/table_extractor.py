"""
Table Extractor - Claude Vision-based Table Extraction

Extracts tables from document pages with support for:
- Simple tables (Markdown)
- Complex tables with merged cells (HTML)
- Multi-page tables
- Table metadata (headers, footers, captions)
"""

import logging
import base64
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class TableComplexity(Enum):
    """Table complexity levels"""
    SIMPLE = "simple"           # Basic grid, no merging
    MODERATE = "moderate"       # Some merged cells
    COMPLEX = "complex"         # Heavy merging, nested structures
    MATRIX = "matrix"           # Data matrix with row/col headers


@dataclass
class TableCell:
    """Represents a single table cell"""
    content: str
    row_span: int = 1
    col_span: int = 1
    is_header: bool = False
    alignment: str = "left"     # left, center, right
    style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedTable:
    """Represents an extracted table"""
    table_id: str
    caption: Optional[str]
    headers: List[List[TableCell]]
    rows: List[List[TableCell]]
    complexity: TableComplexity
    source_page: int

    # Formatting hints
    has_merged_cells: bool = False
    has_nested_content: bool = False
    suggested_format: str = "markdown"  # markdown, html, or docx_native

    def to_markdown(self) -> str:
        """Convert to Markdown table (simple tables only)"""
        if self.has_merged_cells:
            logger.warning(f"Table {self.table_id} has merged cells, Markdown may lose structure")

        lines = []

        # Caption
        if self.caption:
            lines.append(f"**{self.caption}**\n")

        # Headers
        if self.headers:
            header_row = self.headers[0]
            header_line = "| " + " | ".join(cell.content for cell in header_row) + " |"
            lines.append(header_line)

            # Separator with alignment
            separators = []
            for cell in header_row:
                if cell.alignment == "center":
                    separators.append(":---:")
                elif cell.alignment == "right":
                    separators.append("---:")
                else:
                    separators.append("---")
            lines.append("| " + " | ".join(separators) + " |")

        # Data rows
        for row in self.rows:
            row_line = "| " + " | ".join(cell.content for cell in row) + " |"
            lines.append(row_line)

        return "\n".join(lines)

    def to_html(self) -> str:
        """Convert to HTML table (supports merged cells)"""
        lines = ['<table border="1" cellpadding="5" cellspacing="0">']

        # Caption
        if self.caption:
            lines.append(f'  <caption>{self.caption}</caption>')

        # Headers
        if self.headers:
            lines.append('  <thead>')
            for header_row in self.headers:
                lines.append('    <tr>')
                for cell in header_row:
                    attrs = []
                    if cell.row_span > 1:
                        attrs.append(f'rowspan="{cell.row_span}"')
                    if cell.col_span > 1:
                        attrs.append(f'colspan="{cell.col_span}"')
                    if cell.alignment != "left":
                        attrs.append(f'style="text-align: {cell.alignment}"')

                    attr_str = " " + " ".join(attrs) if attrs else ""
                    lines.append(f'      <th{attr_str}>{cell.content}</th>')
                lines.append('    </tr>')
            lines.append('  </thead>')

        # Body
        lines.append('  <tbody>')
        for row in self.rows:
            lines.append('    <tr>')
            for cell in row:
                attrs = []
                if cell.row_span > 1:
                    attrs.append(f'rowspan="{cell.row_span}"')
                if cell.col_span > 1:
                    attrs.append(f'colspan="{cell.col_span}"')
                if cell.alignment != "left":
                    attrs.append(f'style="text-align: {cell.alignment}"')

                attr_str = " " + " ".join(attrs) if attrs else ""
                tag = "th" if cell.is_header else "td"
                lines.append(f'      <{tag}{attr_str}>{cell.content}</{tag}>')
            lines.append('    </tr>')
        lines.append('  </tbody>')

        lines.append('</table>')
        return "\n".join(lines)


# =============================================================================
# VISION PROMPTS FOR TABLE EXTRACTION
# =============================================================================

TABLE_DETECTION_PROMPT = """Analyze this document page and identify ALL tables present.

For EACH table found, provide:
1. Location (top/middle/bottom of page)
2. Complexity level:
   - SIMPLE: Basic grid, no merged cells
   - MODERATE: Some merged headers or cells
   - COMPLEX: Heavy merging, nested content
3. Approximate dimensions (rows x columns)
4. Whether it continues to next page

OUTPUT FORMAT (JSON):
{
  "tables_found": [
    {
      "table_id": "table_1",
      "location": "top",
      "complexity": "moderate",
      "dimensions": "5x4",
      "has_caption": true,
      "caption_text": "Table 1: Revenue by Region",
      "continues_next_page": false,
      "has_merged_cells": true,
      "has_numeric_data": true
    }
  ],
  "total_tables": 1
}

If no tables found, return {"tables_found": [], "total_tables": 0}"""


TABLE_EXTRACTION_PROMPT = """Extract the table from this document page into structured format.

CRITICAL INSTRUCTIONS:

1. **PRESERVE EXACT DATA** - Every number, text, symbol exactly as shown
2. **CAPTURE MERGED CELLS** - Note rowspan/colspan for merged headers
3. **IDENTIFY HEADERS** - Mark header rows/columns
4. **PRESERVE ALIGNMENT** - Note left/center/right alignment

OUTPUT FORMAT (JSON):
{
  "table_id": "table_1",
  "caption": "Table 1: Quarterly Revenue",
  "complexity": "moderate",
  "headers": [
    [
      {"content": "Region", "rowspan": 2, "colspan": 1, "is_header": true},
      {"content": "Revenue ($M)", "rowspan": 1, "colspan": 3, "is_header": true},
      {"content": "Total", "rowspan": 2, "colspan": 1, "is_header": true}
    ],
    [
      {"content": "Q1", "is_header": true},
      {"content": "Q2", "is_header": true},
      {"content": "Q3", "is_header": true}
    ]
  ],
  "rows": [
    [
      {"content": "North", "is_header": false},
      {"content": "1.2", "alignment": "right"},
      {"content": "1.5", "alignment": "right"},
      {"content": "1.8", "alignment": "right"},
      {"content": "4.5", "alignment": "right"}
    ],
    [
      {"content": "South"},
      {"content": "0.8", "alignment": "right"},
      {"content": "0.9", "alignment": "right"},
      {"content": "1.1", "alignment": "right"},
      {"content": "2.8", "alignment": "right"}
    ]
  ],
  "has_merged_cells": true,
  "suggested_format": "html"
}

IMPORTANT:
- For merged cells, only include the cell once with correct rowspan/colspan
- Use "alignment": "right" for numeric columns
- Set "suggested_format": "html" if merged cells exist, else "markdown"
"""


TABLE_TRANSLATION_PROMPT = """Translate the text content in this table from {source_lang} to {target_lang}.

CRITICAL RULES:
1. **PRESERVE ALL NUMBERS** - Do not translate or modify any numbers
2. **PRESERVE STRUCTURE** - Keep rowspan, colspan, alignment intact
3. **TRANSLATE HEADERS** - Translate column/row headers
4. **PRESERVE UNITS** - Keep $, %, EUR, etc. as-is
5. **PRESERVE CODES** - Keep product codes, IDs, abbreviations

INPUT TABLE:
{table_json}

OUTPUT: Same JSON structure with translated text content only.
Do not change: numbers, structure, formatting, codes, units."""


class TableExtractor:
    """
    Claude Vision-based Table Extractor

    Extracts tables with support for complex formatting.
    """

    def __init__(self, llm_client):
        """
        Initialize Table Extractor

        Args:
            llm_client: LLM client with async chat method
        """
        self.llm_client = llm_client
        self.max_tokens = 4096

    async def detect_tables(
        self,
        image_bytes: bytes,
        media_type: str = "image/png",
    ) -> Dict[str, Any]:
        """
        Detect tables in a page image

        Returns dict with table metadata without full extraction.
        """
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')

        try:
            response = await self.llm_client.chat(
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_base64,
                            }
                        },
                        {
                            "type": "text",
                            "text": TABLE_DETECTION_PROMPT,
                        }
                    ]
                }],
                max_tokens=2048,
            )

            result_text = response.content.strip()

            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                return json.loads(json_match.group())
            return {"tables_found": [], "total_tables": 0}

        except Exception as e:
            logger.error(f"Table detection failed: {e}")
            return {"tables_found": [], "total_tables": 0}

    async def extract_table(
        self,
        image_bytes: bytes,
        table_id: str = "table_1",
        media_type: str = "image/png",
    ) -> Optional[ExtractedTable]:
        """
        Extract a single table from page image

        Args:
            image_bytes: Page image containing the table
            table_id: Identifier for the table
            media_type: MIME type of image

        Returns:
            ExtractedTable object or None if extraction fails
        """
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')

        try:
            response = await self.llm_client.chat(
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_base64,
                            }
                        },
                        {
                            "type": "text",
                            "text": TABLE_EXTRACTION_PROMPT,
                        }
                    ]
                }],
                max_tokens=self.max_tokens,
            )

            result_text = response.content.strip()

            # Parse JSON
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            # Convert to ExtractedTable
            headers = []
            for header_row in data.get("headers", []):
                cells = [
                    TableCell(
                        content=cell.get("content", ""),
                        row_span=cell.get("rowspan", 1),
                        col_span=cell.get("colspan", 1),
                        is_header=cell.get("is_header", True),
                        alignment=cell.get("alignment", "left"),
                    )
                    for cell in header_row
                ]
                headers.append(cells)

            rows = []
            for data_row in data.get("rows", []):
                cells = [
                    TableCell(
                        content=cell.get("content", ""),
                        row_span=cell.get("rowspan", 1),
                        col_span=cell.get("colspan", 1),
                        is_header=cell.get("is_header", False),
                        alignment=cell.get("alignment", "left"),
                    )
                    for cell in data_row
                ]
                rows.append(cells)

            complexity_str = data.get("complexity", "simple")
            try:
                complexity = TableComplexity(complexity_str)
            except ValueError:
                complexity = TableComplexity.SIMPLE

            has_merged = data.get("has_merged_cells", False)

            return ExtractedTable(
                table_id=data.get("table_id", table_id),
                caption=data.get("caption"),
                headers=headers,
                rows=rows,
                complexity=complexity,
                source_page=0,
                has_merged_cells=has_merged,
                suggested_format=data.get("suggested_format", "markdown"),
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse table extraction: {e}")
            return None
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            return None

    async def translate_table(
        self,
        table: ExtractedTable,
        source_lang: str,
        target_lang: str,
    ) -> ExtractedTable:
        """
        Translate table content while preserving structure

        Args:
            table: ExtractedTable to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated ExtractedTable
        """
        # Convert table to JSON for translation
        table_json = {
            "caption": table.caption,
            "headers": [
                [{"content": c.content, "is_header": c.is_header} for c in row]
                for row in table.headers
            ],
            "rows": [
                [{"content": c.content} for c in row]
                for row in table.rows
            ],
        }

        prompt = TABLE_TRANSLATION_PROMPT.format(
            source_lang=source_lang,
            target_lang=target_lang,
            table_json=json.dumps(table_json, ensure_ascii=False, indent=2),
        )

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
            )

            result_text = response.content.strip()

            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if not json_match:
                return table

            translated = json.loads(json_match.group())

            # Update table content
            if translated.get("caption"):
                table.caption = translated["caption"]

            for i, header_row in enumerate(translated.get("headers", [])):
                for j, cell_data in enumerate(header_row):
                    if i < len(table.headers) and j < len(table.headers[i]):
                        table.headers[i][j].content = cell_data.get("content", "")

            for i, data_row in enumerate(translated.get("rows", [])):
                for j, cell_data in enumerate(data_row):
                    if i < len(table.rows) and j < len(table.rows[i]):
                        table.rows[i][j].content = cell_data.get("content", "")

            return table

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Table translation parse failed: {e}")
            return table
        except Exception as e:
            logger.warning(f"Table translation failed: {e}")
            return table


def table_to_output(table: ExtractedTable) -> str:
    """
    Convert table to best output format based on complexity

    Args:
        table: ExtractedTable to convert

    Returns:
        String representation (Markdown or HTML)
    """
    if table.has_merged_cells or table.suggested_format == "html":
        return table.to_html()
    return table.to_markdown()
