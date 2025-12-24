"""
Vision Reader - TRUE Claude-Native Document Processing

Claude SEES documents like a human does:
- No text extraction tools
- No information loss
- Visual understanding of formulas, tables, layouts

Philosophy: "Let Claude BE the solution, not use tools FOR Claude"
"""

import asyncio
import base64
import logging
import io
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Content extracted from a single page via Vision"""
    page_number: int
    content: str  # Markdown with LaTeX
    has_formulas: bool = False
    has_tables: bool = False
    has_figures: bool = False
    confidence: float = 1.0


@dataclass
class VisionDocument:
    """Complete document processed via Vision"""
    source_file: str
    total_pages: int
    pages: List[PageContent] = field(default_factory=list)

    @property
    def full_content(self) -> str:
        """Combine all pages into single document"""
        return "\n\n".join(page.content for page in self.pages)

    @property
    def has_formulas(self) -> bool:
        return any(page.has_formulas for page in self.pages)


# =============================================================================
# VISION PROMPTS - CLAUDE READS LIKE A HUMAN
# =============================================================================

PAGE_READING_PROMPT = """You are reading a page from an academic/technical document.
Your task is to perfectly transcribe the content into Markdown format with LaTeX math.

CRITICAL INSTRUCTIONS FOR MATHEMATICAL CONTENT:

1. **CONVERT ALL MATH TO LATEX NOTATION:**

   Visual → LaTeX conversion examples:
   - Summation symbol (∑) with limits → $\\sum_{j=1}^{n}$
   - Integral (∫) with limits → $\\int_{a}^{b}$
   - Fraction → $\\frac{numerator}{denominator}$
   - Square root → $\\sqrt{x}$ or $\\sqrt[n]{x}$
   - Subscripts (xᵢ, x₁) → $x_i$, $x_1$
   - Superscripts (x², xⁿ) → $x^2$, $x^n$
   - Greek letters (α, β, γ, θ, λ, μ, σ, ω) → $\\alpha$, $\\beta$, etc.
   - Set membership (∈, ∉) → $\\in$, $\\notin$
   - Real numbers (ℝ) → $\\mathbb{R}$
   - Natural numbers (ℕ) → $\\mathbb{N}$
   - Infinity (∞) → $\\infty$
   - Partial derivative (∂) → $\\partial$
   - Gradient (∇) → $\\nabla$
   - Norm (‖x‖) → $\\|x\\|$
   - Inner product (⟨x,y⟩) → $\\langle x, y \\rangle$

2. **USE CORRECT DELIMITERS:**
   - Inline math (within text): $...$
   - Display math (standalone equations): $$...$$
   - Numbered equations: Use $$...$$ on its own line

3. **PRESERVE DOCUMENT STRUCTURE:**
   - Section headings → ## Heading
   - Subsections → ### Subheading
   - Theorem/Lemma/Definition → **Theorem X.X:** or use blockquote
   - Proof → *Proof:* ... □
   - Lists → Proper markdown lists
   - Tables → Markdown tables with alignment

4. **HANDLE SPECIAL ELEMENTS:**
   - Citations [1], [Author2024] → Keep as-is
   - Figure references → (Figure X), (Fig. X)
   - Equation references → (X) or Eq. (X)
   - Footnotes → [^1] format

5. **QUALITY REQUIREMENTS:**
   - Transcribe EVERY word and symbol
   - Maintain paragraph structure
   - Keep original formatting intent
   - If uncertain about a symbol, make best reasonable guess

OUTPUT: Markdown text with LaTeX math notation. No explanations or meta-commentary."""


FORMULA_RECONSTRUCTION_PROMPT = """You are reconstructing mathematical formulas from visual representation.

VISUAL INPUT: An image containing mathematical expressions.

YOUR TASK: Convert EVERY mathematical expression to proper LaTeX notation.

CONVERSION RULES:

1. **Identify all mathematical content** - anything that looks like math
2. **Convert to LaTeX** using standard notation
3. **Preserve semantic meaning** - the LaTeX should render identically to the visual

COMMON PATTERNS:

| Visual | LaTeX |
|--------|-------|
| ∑ᵢ₌₁ⁿ | \\sum_{i=1}^{n} |
| ∫₀^∞ | \\int_{0}^{\\infty} |
| ∂f/∂x | \\frac{\\partial f}{\\partial x} |
| √(x+1) | \\sqrt{x+1} |
| x̄ (x-bar) | \\bar{x} |
| x̂ (x-hat) | \\hat{x} |
| ẋ (x-dot) | \\dot{x} |
| x⃗ (x-vec) | \\vec{x} |
| lim x→∞ | \\lim_{x \\to \\infty} |
| max/min | \\max, \\min |
| log, ln, exp | \\log, \\ln, \\exp |
| sin, cos, tan | \\sin, \\cos, \\tan |
| ≤, ≥, ≠ | \\leq, \\geq, \\neq |
| ≈, ∼, ≡ | \\approx, \\sim, \\equiv |
| ∀, ∃ | \\forall, \\exists |
| ∩, ∪ | \\cap, \\cup |
| ⊂, ⊃, ⊆, ⊇ | \\subset, \\supset, \\subseteq, \\supseteq |
| ×, ·, ∘ | \\times, \\cdot, \\circ |
| ⊗, ⊕ | \\otimes, \\oplus |
| ℝⁿ | \\mathbb{R}^n |
| 𝔼[X] | \\mathbb{E}[X] |
| ℙ(A) | \\mathbb{P}(A) |
| O(n²) | O(n^2) |
| ‖x‖₂ | \\|x\\|_2 |
| xᵀ (transpose) | x^T or x^\\top |
| A⁻¹ (inverse) | A^{-1} |

OUTPUT: Complete LaTeX representation of all formulas seen."""


MULTI_PAGE_ASSEMBLY_PROMPT = """You are assembling multiple pages into a coherent document.

PAGES:
{pages_content}

TASK:
1. Combine pages maintaining logical flow
2. Fix any page-break issues (words split across pages)
3. Ensure section numbering is continuous
4. Verify all LaTeX math notation is consistent
5. Merge split paragraphs/sentences

OUTPUT: Single coherent Markdown document with all LaTeX preserved.
Do not add any explanations - just the assembled document."""


class VisionReader:
    """
    Claude Vision-based Document Reader

    TRUE Claude-native: Claude SEES the document, no extraction tools.
    """

    def __init__(self, llm_client):
        """
        Initialize Vision Reader

        Args:
            llm_client: LLM client with async chat method (supports vision)
        """
        self.llm_client = llm_client
        self.max_tokens = 8192
        self._current_prompt = None  # Override prompt for specialized reading

    async def read_pdf(
        self,
        pdf_path: Path,
        dpi: int = 150,
        max_pages: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ) -> VisionDocument:
        """
        Read PDF using Claude Vision

        Claude sees each page as an image and extracts content
        with perfect formula reconstruction.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering (higher = better formula clarity)
            max_pages: Limit pages to process (None = all)
            progress_callback: Called with (current_page, total_pages)

        Returns:
            VisionDocument with all content as Markdown+LaTeX
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise RuntimeError("PyMuPDF required: pip install pymupdf")

        pdf_path = Path(pdf_path)
        logger.info(f"[Vision] Reading PDF: {pdf_path.name}")

        # Open PDF
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)

        if max_pages:
            total_pages = min(total_pages, max_pages)

        logger.info(f"[Vision] Processing {total_pages} pages at {dpi} DPI")

        # Process each page with Vision
        pages = []
        for page_num in range(total_pages):
            if progress_callback:
                progress_callback(page_num + 1, total_pages)

            page = doc[page_num]

            # Render page to image
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # Scale matrix
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            # Claude reads the page
            page_content = await self._read_page_image(
                img_bytes,
                page_num + 1,
                total_pages
            )

            pages.append(page_content)
            logger.info(f"[Vision] Page {page_num + 1}/{total_pages} complete ({len(page_content.content)} chars)")

            # Small delay to avoid rate limits
            if page_num < total_pages - 1:
                await asyncio.sleep(1)

        doc.close()

        return VisionDocument(
            source_file=pdf_path.name,
            total_pages=total_pages,
            pages=pages,
        )

    async def read_image(
        self,
        image_path: Path,
    ) -> PageContent:
        """
        Read a single image using Claude Vision

        Args:
            image_path: Path to image file (PNG, JPG, etc.)

        Returns:
            PageContent with extracted text and LaTeX
        """
        image_path = Path(image_path)

        # Read image bytes
        img_bytes = image_path.read_bytes()

        # Detect media type
        suffix = image_path.suffix.lower()
        media_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        media_type = media_types.get(suffix, 'image/png')

        return await self._read_page_image(img_bytes, 1, 1, media_type)

    async def read_images(
        self,
        image_paths: List[Path],
        progress_callback: Optional[Callable] = None,
    ) -> VisionDocument:
        """
        Read multiple images as a document

        Args:
            image_paths: List of image file paths
            progress_callback: Called with (current, total)

        Returns:
            VisionDocument with all pages
        """
        total = len(image_paths)
        pages = []

        for i, img_path in enumerate(image_paths):
            if progress_callback:
                progress_callback(i + 1, total)

            page_content = await self.read_image(img_path)
            page_content.page_number = i + 1
            pages.append(page_content)

            # Small delay to avoid rate limits
            if i < total - 1:
                await asyncio.sleep(1)

        return VisionDocument(
            source_file=image_paths[0].name if image_paths else "images",
            total_pages=total,
            pages=pages,
        )

    async def read_pdf_novel(
        self,
        pdf_path: Path,
        dpi: int = 150,
        max_pages: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ) -> VisionDocument:
        """
        Read PDF optimized for novels/literature

        Uses NOVEL_PAGE_READING_PROMPT for better literary preservation.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering
            max_pages: Limit pages to process
            progress_callback: Called with (current_page, total_pages)

        Returns:
            VisionDocument with literary content preserved
        """
        from .prompts import NOVEL_PAGE_READING_PROMPT

        # Store original prompt
        original_prompt = self._current_prompt

        # Override with novel prompt
        self._current_prompt = NOVEL_PAGE_READING_PROMPT

        try:
            return await self.read_pdf(pdf_path, dpi, max_pages, progress_callback)
        finally:
            self._current_prompt = original_prompt

    async def read_pdf_business(
        self,
        pdf_path: Path,
        dpi: int = 200,  # Higher DPI for tables
        max_pages: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ) -> VisionDocument:
        """
        Read PDF optimized for business documents with tables

        Uses BUSINESS_PAGE_READING_PROMPT for better table extraction.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering (higher for tables)
            max_pages: Limit pages to process
            progress_callback: Called with (current_page, total_pages)

        Returns:
            VisionDocument with tables properly extracted
        """
        from .prompts import BUSINESS_PAGE_READING_PROMPT

        # Override with business prompt
        self._current_prompt = BUSINESS_PAGE_READING_PROMPT

        try:
            return await self.read_pdf(pdf_path, dpi, max_pages, progress_callback)
        finally:
            self._current_prompt = None

    async def _read_page_image(
        self,
        img_bytes: bytes,
        page_num: int,
        total_pages: int,
        media_type: str = "image/png",
    ) -> PageContent:
        """
        Have Claude read a single page image

        Args:
            img_bytes: Image data as bytes
            page_num: Current page number
            total_pages: Total pages in document
            media_type: MIME type of image

        Returns:
            PageContent with Markdown + LaTeX
        """
        # Encode image
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Use current prompt (may be overridden for novel/business reading)
        prompt = self._current_prompt if self._current_prompt else PAGE_READING_PROMPT
        if total_pages > 1:
            prompt += f"\n\nThis is page {page_num} of {total_pages}."

        # Call Claude Vision
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
                            "text": prompt,
                        }
                    ]
                }],
                max_tokens=self.max_tokens,
            )

            content = response.content.strip()

        except Exception as e:
            logger.error(f"[Vision] Page {page_num} failed: {e}")
            content = f"[VISION ERROR: Page {page_num}]"

        # Detect content features
        has_formulas = '$' in content or '\\' in content
        has_tables = ('<table' in content.lower()) or ('|' in content and '---' in content)
        has_figures = 'figure' in content.lower() or 'fig.' in content.lower() or '[chart' in content.lower()

        return PageContent(
            page_number=page_num,
            content=content,
            has_formulas=has_formulas,
            has_tables=has_tables,
            has_figures=has_figures,
        )

    async def reconstruct_formulas(
        self,
        image_bytes: bytes,
        media_type: str = "image/png",
    ) -> str:
        """
        Specifically reconstruct formulas from an image

        Use this for images that are primarily mathematical content.

        Args:
            image_bytes: Image containing formulas
            media_type: MIME type

        Returns:
            LaTeX representation of formulas
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
                            "text": FORMULA_RECONSTRUCTION_PROMPT,
                        }
                    ]
                }],
                max_tokens=4096,
            )

            return response.content.strip()

        except Exception as e:
            logger.error(f"[Vision] Formula reconstruction failed: {e}")
            return "[FORMULA RECONSTRUCTION ERROR]"

    async def assemble_document(
        self,
        vision_doc: VisionDocument,
    ) -> str:
        """
        Assemble multi-page Vision document into coherent whole

        Claude reviews all pages and fixes:
        - Page break issues
        - Split paragraphs
        - Inconsistent formatting

        Args:
            vision_doc: VisionDocument from read_pdf/read_images

        Returns:
            Final assembled Markdown+LaTeX content
        """
        if len(vision_doc.pages) == 1:
            return vision_doc.pages[0].content

        # For very large documents, just join directly
        total_chars = sum(len(p.content) for p in vision_doc.pages)
        if total_chars > 30000:
            logger.info(f"[Vision] Large document ({total_chars} chars), using simple join")
            return vision_doc.full_content

        # Build pages summary for assembly
        pages_content = ""
        for page in vision_doc.pages:
            pages_content += f"\n\n--- PAGE {page.page_number} ---\n\n"
            pages_content += page.content

        # Have Claude assemble
        prompt = MULTI_PAGE_ASSEMBLY_PROMPT.format(pages_content=pages_content)

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens * 2,  # Larger for assembly
            )

            assembled = response.content.strip()

            # Verify assembly didn't lose content
            if len(assembled) < total_chars * 0.7:
                logger.warning(f"[Vision] Assembly lost content ({len(assembled)} vs {total_chars}), using simple join")
                return vision_doc.full_content

            return assembled

        except Exception as e:
            logger.warning(f"[Vision] Assembly failed, using simple join: {e}")
            return vision_doc.full_content


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def read_pdf_with_vision(
    llm_client,
    pdf_path: str,
    dpi: int = 150,
    assemble: bool = True,
    max_pages: Optional[int] = None,
) -> str:
    """
    Convenience function to read PDF with Vision

    Args:
        llm_client: LLM client with async chat method
        pdf_path: Path to PDF
        dpi: Resolution (150 recommended, 200 for complex formulas)
        assemble: Whether to assemble pages into coherent document
        max_pages: Limit number of pages

    Returns:
        Markdown content with LaTeX math
    """
    reader = VisionReader(llm_client)
    doc = await reader.read_pdf(Path(pdf_path), dpi=dpi, max_pages=max_pages)

    if assemble and len(doc.pages) > 1:
        return await reader.assemble_document(doc)

    return doc.full_content


async def extract_formulas_from_image(
    llm_client,
    image_path: str,
) -> str:
    """
    Extract LaTeX formulas from an image

    Args:
        llm_client: LLM client
        image_path: Path to image with formulas

    Returns:
        LaTeX representation
    """
    reader = VisionReader(llm_client)
    img_bytes = Path(image_path).read_bytes()
    return await reader.reconstruct_formulas(img_bytes)
