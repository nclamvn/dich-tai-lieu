"""
Fast Text Extractor - PyMuPDF-based PDF Extraction

Extracts text from native PDF documents using PyMuPDF.
FREE and extremely fast (~0.1s/page vs ~12s/page for Vision).

Performance:
- 700 pages: ~70 seconds (vs 175 minutes with Vision)
- Cost: FREE (vs ~$15-30 with Vision API)

Best for:
- Novels, fiction, articles
- Native text PDFs (not scanned)
- Documents without complex tables/formulas
"""

import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """Content extracted from a single page"""
    page_number: int
    content: str
    word_count: int = 0
    has_headers: bool = False
    has_lists: bool = False


@dataclass
class ExtractedDocument:
    """Complete extracted document"""
    source_file: str
    total_pages: int
    pages: List[ExtractedPage] = field(default_factory=list)
    extraction_time: float = 0.0

    @property
    def full_content(self) -> str:
        """Combine all pages into single document"""
        return "\n\n".join(page.content for page in self.pages)

    @property
    def total_words(self) -> int:
        return sum(page.word_count for page in self.pages)


class FastTextExtractor:
    """
    Fast PDF text extraction using PyMuPDF.

    Features:
    - Preserves paragraph structure
    - Detects headers and sections
    - Cleans up hyphenation and line breaks
    - Maintains reading order

    Usage:
        extractor = FastTextExtractor()
        doc = await extractor.extract("/path/to/document.pdf")
        print(doc.full_content)
    """

    def __init__(self):
        # Patterns for structure detection
        self.header_patterns = [
            r'^(Chapter|CHAPTER)\s+\d+',
            r'^(Part|PART)\s+\d+',
            r'^(Section|SECTION)\s+\d+',
            r'^\d+\.\s+[A-Z]',  # Numbered sections
            r'^[IVXLC]+\.\s+',  # Roman numerals
        ]

    async def extract(
        self,
        pdf_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        page_range: Optional[tuple] = None,
    ) -> ExtractedDocument:
        """
        Extract text from PDF.

        Args:
            pdf_path: Path to PDF file
            progress_callback: Optional callback(progress, stage)
            page_range: Optional (start, end) page range

        Returns:
            ExtractedDocument with all extracted content
        """
        import time
        start_time = time.time()

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"📖 Fast extracting: {path.name}")

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # Determine page range
            start_page = page_range[0] if page_range else 0
            end_page = page_range[1] if page_range else total_pages

            result = ExtractedDocument(
                source_file=str(path),
                total_pages=total_pages,
            )

            for i, page_num in enumerate(range(start_page, end_page)):
                # Progress callback
                if progress_callback:
                    progress = (i + 1) / (end_page - start_page)
                    progress_callback(progress * 0.5, f"Extracting page {page_num + 1}/{total_pages}")

                # Extract page content
                page_content = self._extract_page(doc[page_num], page_num)
                result.pages.append(page_content)

            doc.close()

            result.extraction_time = time.time() - start_time
            logger.info(f"  ✅ Extracted {len(result.pages)} pages in {result.extraction_time:.1f}s")
            logger.info(f"  📊 Total words: {result.total_words:,}")

            return result

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise

    def _extract_page(self, page: fitz.Page, page_num: int) -> ExtractedPage:
        """Extract content from a single page"""
        # Get text with layout preservation
        text = page.get_text("text")

        # Clean up the text
        cleaned = self._clean_text(text)

        # Detect structure
        has_headers = any(re.search(p, cleaned, re.MULTILINE) for p in self.header_patterns)
        has_lists = bool(re.search(r'^\s*[-•*]\s+', cleaned, re.MULTILINE))

        # Word count
        words = len(cleaned.split())

        return ExtractedPage(
            page_number=page_num,
            content=cleaned,
            word_count=words,
            has_headers=has_headers,
            has_lists=has_lists,
        )

    def _clean_text(self, text: str) -> str:
        """Clean extracted text for better readability"""
        # Fix hyphenation at line breaks
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

        # Join lines within paragraphs (lines not ending with sentence-ending punctuation)
        lines = text.split('\n')
        cleaned_lines = []
        buffer = []

        for line in lines:
            line = line.strip()
            if not line:
                # Empty line = paragraph break
                if buffer:
                    cleaned_lines.append(' '.join(buffer))
                    buffer = []
                cleaned_lines.append('')
            elif self._is_paragraph_end(line):
                buffer.append(line)
                cleaned_lines.append(' '.join(buffer))
                buffer = []
            else:
                buffer.append(line)

        if buffer:
            cleaned_lines.append(' '.join(buffer))

        # Join consecutive empty lines
        result = '\n'.join(cleaned_lines)
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result.strip()

    def _is_paragraph_end(self, line: str) -> bool:
        """Check if line ends a paragraph"""
        if not line:
            return False

        # Ends with sentence-ending punctuation
        if line[-1] in '.!?:;':
            return True

        # Ends with closing quote after punctuation
        if len(line) >= 2 and line[-1] in '"\'' and line[-2] in '.!?':
            return True

        return False

    def extract_with_structure(
        self,
        pdf_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Extract with additional structure detection.

        Returns:
            Dict with:
            - content: Full text content
            - chapters: List of detected chapters
            - metadata: Document metadata
        """
        import asyncio
        doc = asyncio.get_event_loop().run_until_complete(
            self.extract(pdf_path, progress_callback)
        )

        # Detect chapters
        chapters = self._detect_chapters(doc.full_content)

        # Extract metadata
        with fitz.open(pdf_path) as pdf_doc:
            metadata = pdf_doc.metadata

        return {
            "content": doc.full_content,
            "pages": doc.pages,
            "total_pages": doc.total_pages,
            "total_words": doc.total_words,
            "chapters": chapters,
            "metadata": metadata,
            "extraction_time": doc.extraction_time,
        }

    def _detect_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Detect chapter boundaries in content"""
        chapters = []

        # Common chapter patterns
        patterns = [
            (r'^(Chapter|CHAPTER)\s+(\d+)[:\.]?\s*(.*)$', 'chapter'),
            (r'^(Part|PART)\s+(\d+)[:\.]?\s*(.*)$', 'part'),
            (r'^(\d+)\.\s+([A-Z][^.!?\n]+)$', 'section'),
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines):
            for pattern, chapter_type in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    chapters.append({
                        "type": chapter_type,
                        "number": match.group(2) if len(match.groups()) > 1 else i,
                        "title": match.group(3) if len(match.groups()) > 2 else match.group(2),
                        "line_number": i,
                    })
                    break

        return chapters


async def fast_extract(pdf_path: str) -> ExtractedDocument:
    """Convenience function for fast extraction"""
    extractor = FastTextExtractor()
    return await extractor.extract(pdf_path)
