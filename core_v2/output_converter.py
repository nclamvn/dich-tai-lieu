"""
Output Converter - FIXED

Properly handles LaTeX formulas:
- For PDF: Use pdflatex (native LaTeX rendering)
- For DOCX: Use pandoc with --mathml flag
- For EPUB: Use pandoc with math rendering
"""

import asyncio
import os
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Union
from enum import Enum

# Professional DOCX rendering
from core.docx_engine import DocxRenderer, create_template

# Professional PDF rendering
from core.pdf_engine import PdfRenderer, create_pdf_template

from core_v2.aio_utils import run_blocking

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Output pipeline selection (Option A, stage 3) — flag-gated, default-safe.
# --------------------------------------------------------------------------- #
def _output_pipeline() -> str:
    """Resolve the active output pipeline, lowercased.

    A live ``OUTPUT_PIPELINE`` env var wins (ops-flippable without a restart and
    test-friendly), else the ``output_pipeline`` setting, else ``"engine"``.
    """
    value = os.getenv("OUTPUT_PIPELINE")
    if value is None:
        try:
            from config.settings import settings

            value = getattr(settings, "output_pipeline", None)
        except Exception:  # pragma: no cover - settings optional
            value = None
    return (value or "engine").strip().lower()


def _ast_pipeline_enabled() -> bool:
    """True when the live DOCX/PDF export should route through the AST stack."""
    return _output_pipeline() == "ast"


def _ast_template(template: str) -> str:
    """Map a professional-template name to an AST adapter template, defaulting
    unknown / ``auto`` to ``ebook``."""
    key = (template or "").strip().lower()
    return key if key in ("ebook", "academic", "business") else "ebook"


class OutputFormat(Enum):
    DOCX = "docx"
    PDF = "pdf"
    EPUB = "epub"
    HTML = "html"
    LATEX = "latex"
    MARKDOWN = "md"


class OutputConverter:
    """
    Convert Claude output to publication formats.

    FIXED: Proper formula rendering for STEM documents.
    """

    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "aps_converter"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required tools are installed"""
        self.has_pandoc = shutil.which("pandoc") is not None
        self.has_pdflatex = shutil.which("pdflatex") is not None
        self.has_xelatex = shutil.which("xelatex") is not None

        if not self.has_pandoc:
            logger.warning("pandoc not found - some conversions will fail")
        if not self.has_pdflatex and not self.has_xelatex:
            logger.warning("pdflatex/xelatex not found - LaTeX to PDF will use pandoc")

    async def convert(
        self,
        content: str,
        output_format: OutputFormat,
        output_path: Path,
        title: str = "Document",
        author: str = "",
        metadata: Optional[dict] = None,
        has_formulas: bool = False,
    ) -> bool:
        """
        Convert content to target format with proper formula handling.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Determine source format
            is_latex = "\\begin{document}" in content or "\\documentclass" in content
            source_format = "latex" if is_latex else "markdown"

            # For content with formulas, route through formula-aware conversion
            if has_formulas or is_latex:
                return await self._convert_with_formulas(
                    content, source_format, output_format, output_path, title, author
                )
            else:
                return await self._convert_simple(
                    content, output_format, output_path, title, author, metadata
                )
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return False

    async def _convert_with_formulas(
        self,
        content: str,
        source_format: str,
        target: OutputFormat,
        output_path: Path,
        title: Optional[str],
        author: Optional[str],
    ) -> bool:
        """
        Convert content with mathematical formulas.

        FIXED: Proper format detection and conversion.
        - For markdown with $...$: use pandoc with tex_math_dollars (preserves math)
        - For full LaTeX: use native LaTeX compilation
        """

        # Detect if content is full LaTeX or Markdown with LaTeX math
        is_full_latex = "\\begin{document}" in content or "\\documentclass" in content
        has_dollar_math = "$" in content

        logger.info(f"Converting: is_full_latex={is_full_latex}, has_dollar_math={has_dollar_math}, target={target.value}")

        # Route based on source format and target
        if target == OutputFormat.PDF:
            if is_full_latex:
                return await self._latex_to_pdf(content, output_path)
            else:
                # Markdown with $...$ → wrap in LaTeX → PDF
                latex_content = await self._markdown_to_latex(content, title, author)
                return await self._latex_to_pdf(latex_content, output_path)

        elif target == OutputFormat.DOCX:
            if is_full_latex:
                return await self._latex_to_docx(content, output_path)
            else:
                # KEY FIX: Markdown with $...$ → pandoc with tex_math_dollars
                return await self._markdown_math_to_docx(content, output_path, title, author)

        elif target == OutputFormat.HTML:
            if is_full_latex:
                return await self._latex_to_html(content, output_path)
            else:
                return await self._markdown_math_to_html(content, output_path, title, author)

        elif target == OutputFormat.LATEX:
            if is_full_latex:
                output_path.write_text(content, encoding='utf-8')
            else:
                latex_content = await self._markdown_to_latex(content, title, author)
                output_path.write_text(latex_content, encoding='utf-8')
            return True

        elif target == OutputFormat.EPUB:
            if is_full_latex:
                return await self._latex_to_epub(content, output_path)
            else:
                return await self._markdown_math_to_epub(content, output_path, title, author)

        elif target == OutputFormat.MARKDOWN:
            output_path.write_text(content, encoding='utf-8')
            return True

        else:
            # Fallback
            return await self._markdown_math_to_docx(content, output_path, title, author)

    async def _markdown_to_latex(
        self,
        content: str,
        title: Optional[str],
        author: Optional[str],
    ) -> str:
        """Convert markdown with formulas to LaTeX"""

        # Use pandoc to convert markdown to latex
        if self.has_pandoc:
            temp_input = self.temp_dir / "temp_input.md"
            temp_input.write_text(content, encoding='utf-8')

            try:
                proc = await asyncio.create_subprocess_exec(
                    "pandoc", str(temp_input), "-f", "markdown", "-t", "latex",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode == 0:
                    latex_body = stdout.decode('utf-8')
                    return self._wrap_latex_document(latex_body, title, author, use_xelatex=self.has_xelatex)
            except Exception as e:
                logger.warning(f"pandoc markdown->latex failed: {e}")
            finally:
                temp_input.unlink(missing_ok=True)

        # Fallback: simple conversion
        return self._wrap_latex_document(content, title, author, use_xelatex=self.has_xelatex)

    def _wrap_latex_document(
        self,
        body: str,
        title: Optional[str],
        author: Optional[str],
        use_xelatex: bool = True,
    ) -> str:
        """Wrap content in a complete LaTeX document"""

        if use_xelatex and self.has_xelatex:
            # XeLaTeX preamble - full Unicode support (macOS compatible)
            preamble = r"""
\documentclass[11pt,a4paper]{article}

% XeLaTeX Unicode support
\usepackage{fontspec}
\defaultfontfeatures{Ligatures=TeX}
\setmainfont{Times New Roman}
\setsansfont{Helvetica}
\setmonofont{Courier New}

% Math packages
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{mathtools}

% Graphics
\usepackage{graphicx}

% Tables
\usepackage{booktabs}
\usepackage{longtable}

% Links
\usepackage{hyperref}

% Page layout
\usepackage[margin=2.5cm]{geometry}

"""
        else:
            # pdfLaTeX preamble - ASCII only
            preamble = r"""
\documentclass[11pt,a4paper]{article}

% Encoding
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}

% Math packages
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{mathtools}

% Graphics
\usepackage{graphicx}

% Tables
\usepackage{booktabs}
\usepackage{longtable}

% Links
\usepackage{hyperref}

% Page layout
\usepackage[margin=2.5cm]{geometry}

"""

        # Add title/author if provided
        if title or author:
            preamble += f"""
\\title{{{title or 'Document'}}}
\\author{{{author or ''}}}
\\date{{\\today}}
"""

        # Build document
        doc = preamble + "\n\\begin{document}\n"

        if title:
            doc += "\\maketitle\n\n"

        doc += body
        doc += "\n\\end{document}"

        return doc

    async def _latex_to_pdf(self, content: str, output_path: Path) -> bool:
        """
        Convert LaTeX to PDF using pdflatex or xelatex.

        This gives the best formula rendering quality.
        """

        # Prefer xelatex for better Unicode support
        latex_cmd = "xelatex" if self.has_xelatex else "pdflatex"

        if not self.has_pdflatex and not self.has_xelatex:
            # Fallback to pandoc
            logger.warning("No LaTeX compiler, using pandoc for PDF")
            return await self._pandoc_latex_to_pdf(content, output_path)

        temp_tex = self.temp_dir / "document.tex"
        temp_tex.write_text(content, encoding='utf-8')

        try:
            # Run LaTeX compiler (twice for references)
            for i in range(2):
                proc = await asyncio.create_subprocess_exec(
                    latex_cmd,
                    "-interaction=nonstopmode",
                    "-output-directory", str(self.temp_dir),
                    str(temp_tex),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.temp_dir),
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode != 0 and i == 1:
                    logger.warning(f"LaTeX warning: {stderr.decode()[:500]}")

            # Check for PDF output
            pdf_file = self.temp_dir / "document.pdf"
            if pdf_file.exists():
                shutil.copy(pdf_file, output_path)
                logger.info(f"PDF created: {output_path}")
                return True
            else:
                logger.error(f"LaTeX failed, no PDF produced")
                # Try pandoc fallback
                return await self._pandoc_latex_to_pdf(content, output_path)
        finally:
            # Cleanup temp files
            for ext in ['.tex', '.aux', '.log', '.out', '.toc']:
                (self.temp_dir / f"document{ext}").unlink(missing_ok=True)

    async def _pandoc_latex_to_pdf(self, content: str, output_path: Path) -> bool:
        """Fallback: Use pandoc for LaTeX to PDF"""

        temp_input = self.temp_dir / "temp_latex.tex"
        temp_input.write_text(content, encoding='utf-8')

        # Use xelatex for better Unicode support
        pdf_engine = "xelatex" if self.has_xelatex else "pdflatex"

        try:
            proc = await asyncio.create_subprocess_exec(
                "pandoc", str(temp_input),
                "-f", "latex",
                "-o", str(output_path),
                f"--pdf-engine={pdf_engine}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc failed: {stderr.decode()}")
                return False

            return output_path.exists()
        finally:
            temp_input.unlink(missing_ok=True)

    async def _latex_to_docx(self, content: str, output_path: Path) -> bool:
        """
        Convert LaTeX to DOCX with proper formula rendering.

        Uses pandoc with --mathml for equation support.
        """

        if not self.has_pandoc:
            logger.error("pandoc required for DOCX conversion")
            return False

        temp_input = self.temp_dir / "temp_latex.tex"
        temp_input.write_text(content, encoding='utf-8')

        try:
            # Use --mathml for formula rendering in DOCX
            proc = await asyncio.create_subprocess_exec(
                "pandoc", str(temp_input),
                "-f", "latex",
                "-t", "docx",
                "-o", str(output_path),
                "--mathml",  # KEY: Render formulas as MathML
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc DOCX error: {stderr.decode()}")
                return False

            logger.info(f"DOCX created with MathML: {output_path}")
            return output_path.exists()

        finally:
            temp_input.unlink(missing_ok=True)

    async def _latex_to_html(self, content: str, output_path: Path) -> bool:
        """Convert LaTeX to HTML with MathJax formulas"""

        if not self.has_pandoc:
            logger.error("pandoc required for HTML conversion")
            return False

        temp_input = self.temp_dir / "temp_latex.tex"
        temp_input.write_text(content, encoding='utf-8')

        try:
            proc = await asyncio.create_subprocess_exec(
                "pandoc", str(temp_input),
                "-f", "latex",
                "-t", "html5",
                "-o", str(output_path),
                "--standalone",
                "--mathjax",  # Use MathJax for formulas
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc HTML failed: {stderr.decode()}")
                return False

            return output_path.exists()
        finally:
            temp_input.unlink(missing_ok=True)

    async def _latex_to_epub(self, content: str, output_path: Path) -> bool:
        """Convert LaTeX to EPUB with formula rendering"""

        if not self.has_pandoc:
            logger.error("pandoc required for EPUB conversion")
            return False

        temp_input = self.temp_dir / "temp_latex.tex"
        temp_input.write_text(content, encoding='utf-8')

        try:
            proc = await asyncio.create_subprocess_exec(
                "pandoc", str(temp_input),
                "-f", "latex",
                "-t", "epub3",
                "-o", str(output_path),
                "--mathml",  # MathML for EPUB
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc EPUB failed: {stderr.decode()}")
                return False

            return output_path.exists()
        finally:
            temp_input.unlink(missing_ok=True)

    # =========================================================================
    # NEW METHODS: Markdown with LaTeX math ($...$) conversion
    # KEY FIX: Use -f markdown+tex_math_dollars to parse $...$ as math
    # =========================================================================

    async def _markdown_math_to_docx(
        self,
        content: str,
        output_path: Path,
        title: Optional[str],
        author: Optional[str],
    ) -> bool:
        """
        Convert Markdown with LaTeX math ($...$) to DOCX.

        KEY FIX: Use -f markdown+tex_math_dollars to parse $...$ as math
        """

        if not self.has_pandoc:
            logger.error("pandoc required for DOCX conversion")
            return False

        # Create temp file WITHOUT YAML frontmatter (avoids --- parsing issues)
        temp_input = self.temp_dir / "temp_markdown.md"
        temp_input.write_text(content, encoding='utf-8')

        try:
            # KEY FIX: Use markdown-yaml_metadata_block to avoid --- parsing issues
            # Pass metadata via command line instead of YAML frontmatter
            cmd = [
                "pandoc", str(temp_input),
                "-f", "markdown-yaml_metadata_block+tex_math_dollars+tex_math_single_backslash",
                "-t", "docx",
                "-o", str(output_path),
                "--mathml",  # Render math as MathML (Word equations)
            ]
            if title:
                cmd.extend(["-M", f"title={title}"])
            if author:
                cmd.extend(["-M", f"author={author}"])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc DOCX error: {stderr.decode()}")
                return False

            logger.info(f"DOCX created with MathML: {output_path}")
            return output_path.exists()

        finally:
            temp_input.unlink(missing_ok=True)

    async def _markdown_math_to_html(
        self,
        content: str,
        output_path: Path,
        title: Optional[str],
        author: Optional[str],
    ) -> bool:
        """Convert Markdown with LaTeX math ($...$) to HTML with MathJax"""

        if not self.has_pandoc:
            logger.error("pandoc required for HTML conversion")
            return False

        temp_input = self.temp_dir / "temp_markdown.md"
        temp_input.write_text(content, encoding='utf-8')

        try:
            # Use -yaml_metadata_block to avoid --- parsing issues
            cmd = [
                "pandoc", str(temp_input),
                "-f", "markdown-yaml_metadata_block+tex_math_dollars+tex_math_single_backslash",
                "-t", "html5",
                "-o", str(output_path),
                "--standalone",
                "--mathjax",  # Use MathJax for rendering
            ]
            if title:
                cmd.extend(["-M", f"title={title}"])
            if author:
                cmd.extend(["-M", f"author={author}"])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc HTML failed: {stderr.decode()}")
                return False

            logger.info(f"HTML created with MathJax: {output_path}")
            return output_path.exists()

        finally:
            temp_input.unlink(missing_ok=True)

    async def _markdown_math_to_epub(
        self,
        content: str,
        output_path: Path,
        title: Optional[str],
        author: Optional[str],
        cover_image: Optional[Path] = None,
    ) -> bool:
        """Convert Markdown to EPUB via the AST renderer (ebooklib) — no pandoc
        required. Falls back to pandoc (MathML) only if the ebooklib path fails
        and pandoc is available.
        """
        try:
            from core.rendering.document_extractor import extract_to_ast
            from core.rendering.epub_adapter import render_epub_from_ast
            from core_v2.aio_utils import run_blocking

            temp_input = self.temp_dir / "temp_markdown_epub.md"
            temp_input.write_text(content, encoding="utf-8")
            try:
                ast = await run_blocking(extract_to_ast, temp_input)
            finally:
                temp_input.unlink(missing_ok=True)

            if title:
                ast.metadata.title = title
            if author:
                ast.metadata.author = author

            from functools import partial
            await run_blocking(
                partial(render_epub_from_ast, ast, output_path, title, cover_image=cover_image)
            )
            logger.info(f"EPUB created via ebooklib (no pandoc): {output_path}")
            return output_path.exists()
        except Exception as e:
            logger.error(f"ebooklib EPUB failed: {e}")
            if self.has_pandoc:
                logger.info("Falling back to pandoc for EPUB")
                return await self._markdown_math_to_epub_pandoc(content, output_path, title, author)
            return False

    async def _markdown_math_to_epub_pandoc(
        self,
        content: str,
        output_path: Path,
        title: Optional[str],
        author: Optional[str],
    ) -> bool:
        """Convert Markdown with LaTeX math ($...$) to EPUB via pandoc (MathML fallback)."""

        if not self.has_pandoc:
            logger.error("pandoc required for EPUB conversion")
            return False

        temp_input = self.temp_dir / "temp_markdown.md"
        temp_input.write_text(content, encoding='utf-8')

        try:
            # Use -yaml_metadata_block to avoid --- parsing issues
            cmd = [
                "pandoc", str(temp_input),
                "-f", "markdown-yaml_metadata_block+tex_math_dollars",
                "-t", "epub3",
                "-o", str(output_path),
                "--mathml",  # MathML for EPUB
            ]
            if title:
                cmd.extend(["-M", f"title={title}"])
            if author:
                cmd.extend(["-M", f"author={author}"])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc EPUB failed: {stderr.decode()}")
                return False

            logger.info(f"EPUB created with MathML: {output_path}")
            return output_path.exists()

        finally:
            temp_input.unlink(missing_ok=True)

    async def _convert_simple(
        self,
        content: str,
        target: OutputFormat,
        output_path: Path,
        title: Optional[str],
        author: Optional[str],
        metadata: Optional[dict],
    ) -> bool:
        """Simple conversion for non-formula content"""

        if target == OutputFormat.MARKDOWN:
            output_path.write_text(content, encoding='utf-8')
            return True

        if target == OutputFormat.LATEX:
            latex = self._wrap_latex_document(content, title, author)
            output_path.write_text(latex, encoding='utf-8')
            return True

        if not self.has_pandoc:
            if target == OutputFormat.HTML:
                # Fallback HTML
                html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title or 'Document'}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 2em; }}
        pre {{ background: #f4f4f4; padding: 1em; overflow-x: auto; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""
                output_path.write_text(html, encoding='utf-8')
                return True
            logger.error("pandoc required for conversion")
            return False

        # Create temp markdown WITHOUT frontmatter (avoids --- parsing issues)
        temp_md = self.temp_dir / "temp_simple.md"
        temp_md.write_text(content, encoding='utf-8')

        try:
            # Use -yaml_metadata_block to avoid parsing issues with --- in content
            # Pass metadata via command line instead of YAML frontmatter
            cmd = ["pandoc", str(temp_md), "-f", "markdown-yaml_metadata_block", "-o", str(output_path)]

            # Add metadata via command line
            if title:
                cmd.extend(["-M", f"title={title}"])
            if author:
                cmd.extend(["-M", f"author={author}"])
            if metadata:
                for k, v in metadata.items():
                    cmd.extend(["-M", f"{k}={v}"])

            if target == OutputFormat.PDF:
                # Use xelatex for Unicode support (Vietnamese, etc.)
                pdf_engine = "xelatex" if self.has_xelatex else "pdflatex"
                cmd.extend([f"--pdf-engine={pdf_engine}"])
            elif target == OutputFormat.HTML:
                cmd.extend(["--standalone"])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"pandoc failed: {stderr.decode()}")
                return False

            return output_path.exists()
        finally:
            temp_md.unlink(missing_ok=True)

    async def convert_batch(
        self,
        content: str,
        source_format: str,
        targets: List[OutputFormat],
        output_dir: Path,
        base_name: str,
        has_formulas: bool = False,
        title: str = "Document",
        author: str = "",
    ) -> Dict[str, Path]:
        """Convert to multiple formats"""

        results = {}
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for target in targets:
            ext = target.value
            if ext == "latex":
                ext = "tex"

            output_path = output_dir / f"{base_name}.{ext}"

            try:
                success = await self.convert(
                    content,
                    target,
                    output_path,
                    title=title,
                    author=author,
                    has_formulas=has_formulas,
                )
                if success:
                    results[target.value] = output_path
                    logger.info(f"Created: {output_path}")
                else:
                    results[target.value] = None
            except Exception as e:
                logger.error(f"Failed to convert to {target.value}: {e}")
                results[target.value] = None

        return results

    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        formats = ["md", "html"]  # Always available

        if self.has_pandoc:
            formats.extend(["docx", "epub"])

        if self.has_pdflatex or self.has_xelatex or self.has_pandoc:
            formats.append("pdf")

        if self.has_pdflatex or self.has_xelatex:
            formats.append("latex")

        return formats

    # =========================================================================
    # Professional DOCX Rendering - Using DOCX Template Engine
    # =========================================================================

    async def convert_to_docx_professional(
        self,
        source_folder: Path,
        output_path: Path,
        template: str = "auto",
        include_toc: bool = True,
        include_glossary: bool = True,
    ) -> Path:
        """
        Convert Agent 2 output folder to professional DOCX using Template Engine.

        Args:
            source_folder: Path to Agent 2 output (contains manifest.json, chapters/)
            output_path: Target .docx file path
            template: Template name ('ebook', 'academic', 'business') or 'auto'
            include_toc: Whether to include table of contents
            include_glossary: Whether to include glossary section

        Returns:
            Path to created DOCX file
        """
        source_folder = Path(source_folder)
        output_path = Path(output_path)

        # Auto-select template if needed
        if template == "auto":
            template = self._auto_select_template(source_folder)
            logger.info(f"Auto-selected template: {template}")

        # Create renderer with selected template
        renderer = DocxRenderer(template=template)

        # Render document
        result_path = renderer.render(
            source_folder=str(source_folder),
            output_path=str(output_path),
            include_toc=include_toc,
            include_glossary=include_glossary,
        )

        logger.info(f"Professional DOCX created: {result_path}")
        return result_path

    def _auto_select_template(self, source_folder: Path) -> str:
        """
        Auto-select template based on document DNA from manifest.json.

        Logic:
        - novel/fiction → ebook
        - academic/research/technical → academic
        - business/report/memo → business
        - default → ebook
        """
        import json

        manifest_path = source_folder / "manifest.json"
        if not manifest_path.exists():
            return "ebook"  # Default

        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            meta = manifest.get("meta", {})
            dna = manifest.get("document_dna", {})

            # Check genre
            genre = dna.get("genre", "").lower()
            tone = dna.get("tone", "").lower()

            # Academic indicators
            academic_keywords = ["academic", "research", "paper", "thesis", "dissertation",
                               "journal", "scientific", "study", "analysis", "technical"]
            if any(kw in genre for kw in academic_keywords) or any(kw in tone for kw in academic_keywords):
                return "academic"

            # Business indicators
            business_keywords = ["business", "report", "memo", "proposal", "corporate",
                               "executive", "presentation", "brief", "white paper"]
            if any(kw in genre for kw in business_keywords) or any(kw in tone for kw in business_keywords):
                return "business"

            # Fiction/narrative indicators → ebook
            fiction_keywords = ["novel", "fiction", "story", "narrative", "memoir",
                              "biography", "autobiography", "essay", "literary"]
            if any(kw in genre for kw in fiction_keywords) or any(kw in tone for kw in fiction_keywords):
                return "ebook"

            # Default to ebook (most versatile)
            return "ebook"

        except Exception as e:
            logger.warning(f"Error reading manifest for template selection: {e}")
            return "ebook"

    # =========================================================================
    # AST pipeline (Option A, stage 3) — flag-gated alternative renderers.
    # Selected by OUTPUT_PIPELINE=ast; the public converters below wrap these in
    # a fallback to the legacy engine so a failure here never loses the output.
    # =========================================================================

    async def _markdown_to_docx_via_ast(
        self,
        markdown_content: str,
        output_path: Path,
        template: str,
        title: str,
        author: str,
        language: str,
    ) -> Path:
        """Render professional DOCX through the DocumentAST + core/rendering stack.

        Mirrors the legacy professional output (template + title page + TOC +
        running header/footer) but drives it from the single AST.
        """
        from core.rendering.docx_adapter import render_docx_from_ast
        from core.rendering.document_extractor import extract_to_ast

        output_path = Path(output_path)
        temp_input = self.temp_dir / "temp_markdown_docx_ast.md"
        temp_input.write_text(markdown_content, encoding="utf-8")
        try:
            ast = await run_blocking(extract_to_ast, temp_input)
        finally:
            temp_input.unlink(missing_ok=True)

        if title:
            ast.metadata.title = title
        if author:
            ast.metadata.author = author
        if language:
            ast.metadata.language = language

        tmpl = _ast_template(template)

        def _render() -> Path:
            render_docx_from_ast(
                ast, output_path, title=title, template=tmpl,
                title_page=True, toc=True, header_footer=True,
            )
            return output_path

        result = await run_blocking(_render)
        logger.info(f"Professional DOCX via AST pipeline: {result}")
        return result

    async def _markdown_to_pdf_via_ast(
        self,
        markdown_content: str,
        output_path: Path,
        template: str,
        title: str,
        author: str,
        language: str,
    ) -> Path:
        """Render professional PDF through the DocumentAST + core/rendering stack
        (serif/sans template parity with the DOCX path)."""
        from core.rendering.document_extractor import extract_to_ast
        from core.rendering.pdf_adapter import render_pdf_from_ast

        output_path = Path(output_path)
        temp_input = self.temp_dir / "temp_markdown_pdf_ast.md"
        temp_input.write_text(markdown_content, encoding="utf-8")
        try:
            ast = await run_blocking(extract_to_ast, temp_input)
        finally:
            temp_input.unlink(missing_ok=True)

        if title:
            ast.metadata.title = title
        if author:
            ast.metadata.author = author
        if language:
            ast.metadata.language = language

        tmpl = _ast_template(template)

        def _render() -> Path:
            render_pdf_from_ast(
                ast, output_path, title=title, template=tmpl,
                title_page=True, toc=True, header_footer=True,
            )
            return output_path

        result = await run_blocking(_render)
        logger.info(f"Professional PDF via AST pipeline: {result}")
        return result

    def _apply_cover(self, path, fmt, cover_template, title, author, language, cover_image=None) -> None:
        """Engine-agnostic post-process: stamp a template cover — or a user's own
        cover image — onto a finished PDF/DOCX. No-op when neither is set; never
        raises. (EPUB covers are baked at build time, not here.)"""
        if not cover_template and not cover_image:
            return
        try:
            from core.rendering.cover_apply import apply_cover
            apply_cover(path, fmt, cover_template=cover_template, cover_image=cover_image,
                        title=title, author=author, language=language)
        except Exception as e:  # pragma: no cover - cover is best-effort
            logger.warning("cover apply (%s) failed: %s", fmt, e)

    async def convert_markdown_to_docx_professional(
        self,
        markdown_content: str,
        output_path: Path,
        template: str = "ebook",
        title: str = "Untitled",
        author: str = "Unknown",
        language: str = "vi",
        cover_template: Optional[str] = None,
        cover_image: Optional[str] = None,
    ) -> Path:
        """
        Convert markdown content directly to professional DOCX.

        Args:
            markdown_content: Markdown text
            output_path: Target .docx file path
            template: Template name ('ebook', 'academic', 'business')
            title: Document title
            author: Document author
            language: Document language code for i18n strings

        Returns:
            Path to created DOCX file
        """
        output_path = Path(output_path)

        if _ast_pipeline_enabled():
            try:
                produced = await self._markdown_to_docx_via_ast(
                    markdown_content, output_path, template, title, author, language
                )
                self._apply_cover(produced, "docx", cover_template, title, author, language, cover_image=cover_image)
                return produced
            except Exception as e:
                logger.warning(
                    "AST DOCX pipeline failed (%s); falling back to legacy engine", e
                )

        from core.docx_engine.models import DocumentMeta
        from core.i18n import get_string

        def _render():
            # Create renderer with selected template
            renderer = DocxRenderer(template=template)

            # Build meta with language so renderers use correct i18n strings
            meta = DocumentMeta(title=title, author=author, language=language)

            # Render from markdown with language-aware meta
            normalizer = renderer.normalizer
            doc = normalizer.from_markdown(markdown_content, meta)

            # Update TOC/glossary/bibliography titles based on language
            doc.toc.title = get_string("table_of_contents", language)
            if doc.glossary:
                doc.glossary.title = get_string("glossary", language)
            if doc.bibliography:
                doc.bibliography.title = get_string("references", language)

            return renderer.render_document(doc, str(output_path))

        result_path = await run_blocking(_render)

        self._apply_cover(result_path, "docx", cover_template, title, author, language, cover_image=cover_image)
        logger.info(f"Professional DOCX from markdown: {result_path}")
        return result_path

    # =========================================================================
    # Professional PDF Rendering - Using PDF Template Engine
    # =========================================================================

    async def convert_to_pdf_professional(
        self,
        source_folder: Path,
        output_path: Path,
        template: str = "auto",
        include_toc: bool = True,
        include_glossary: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> Path:
        """
        Convert Agent 2 output folder to professional PDF using Template Engine.

        Uses ReportLab for portable PDF generation with Vietnamese support.

        Args:
            source_folder: Path to Agent 2 output (contains manifest.json, chapters/)
            output_path: Target .pdf file path
            template: Template name ('ebook', 'academic', 'business') or 'auto'
            include_toc: Whether to include table of contents
            include_glossary: Whether to include glossary section
            progress_callback: Optional callback(current, total, message)

        Returns:
            Path to created PDF file
        """
        source_folder = Path(source_folder)
        output_path = Path(output_path)

        # Auto-select template if needed
        if template == "auto":
            template = self._auto_select_template(source_folder)
            logger.info(f"Auto-selected PDF template: {template}")

        # Create renderer with selected template
        renderer = PdfRenderer(template=template)

        # Render document
        result_path = renderer.render_from_folder(
            source_folder=str(source_folder),
            output_path=str(output_path),
            include_toc=include_toc,
            include_glossary=include_glossary,
            progress_callback=progress_callback,
        )

        logger.info(f"Professional PDF created: {result_path}")
        return result_path

    async def convert_markdown_to_pdf_professional(
        self,
        markdown_content: str,
        output_path: Path,
        template: str = "ebook",
        title: str = "Untitled",
        author: str = "Unknown",
        language: str = "vi",
        cover_template: Optional[str] = None,
        cover_image: Optional[str] = None,
    ) -> Path:
        """
        Convert markdown content directly to professional PDF.

        Args:
            markdown_content: Markdown text
            output_path: Target .pdf file path
            template: Template name ('ebook', 'academic', 'business')
            title: Document title
            author: Document author
            language: Document language code for i18n strings

        Returns:
            Path to created PDF file
        """
        output_path = Path(output_path)

        if _ast_pipeline_enabled():
            try:
                produced = await self._markdown_to_pdf_via_ast(
                    markdown_content, output_path, template, title, author, language
                )
                self._apply_cover(produced, "pdf", cover_template, title, author, language, cover_image=cover_image)
                return produced
            except Exception as e:
                logger.warning(
                    "AST PDF pipeline failed (%s); falling back to legacy engine", e
                )

        from core.docx_engine.models import DocumentMeta
        from core.docx_engine.normalizer import DocumentNormalizer
        from core.i18n import get_string

        def _render():
            # Create renderer with selected template
            renderer = PdfRenderer(template=template)

            # Build document with language-aware meta
            normalizer = DocumentNormalizer()
            meta = DocumentMeta(title=title, author=author, language=language)
            document = normalizer.from_markdown(markdown_content, meta)

            # Update section titles based on language
            document.toc.title = get_string("table_of_contents", language)
            if document.glossary:
                document.glossary.title = get_string("glossary", language)
            if document.bibliography:
                document.bibliography.title = get_string("references", language)

            return renderer.render(document, str(output_path), include_toc=True, include_glossary=False)

        result_path = await run_blocking(_render)

        self._apply_cover(result_path, "pdf", cover_template, title, author, language, cover_image=cover_image)
        logger.info(f"Professional PDF from markdown: {result_path}")
        return result_path

    async def convert_markdown_to_epub_professional(
        self,
        markdown_content: str,
        output_path: Path,
        template: str = "ebook",
        title: str = "Untitled",
        author: str = "Unknown",
        language: str = "vi",
        cover_template: Optional[str] = None,
        cover_image: Optional[str] = None,
    ) -> Path:
        """EPUB with a baked-in cover. A user ``cover_image`` wins over a
        ``cover_template`` (rendered to an image); EPUB covers must be set at
        build time (ebooklib's read→write round-trip is unreliable)."""
        output_path = Path(output_path)
        resolved_cover: Optional[Path] = None
        if cover_image and Path(cover_image).is_file():
            resolved_cover = Path(cover_image)
        elif cover_template:
            try:
                from types import SimpleNamespace

                from core.rendering.cover_templates import has_template, render_cover_image

                if has_template(cover_template):
                    meta = SimpleNamespace(
                        title=title, author=author, language=language,
                        page_width_mm=210.0, page_height_mm=297.0,
                    )
                    png = self.temp_dir / "epub_cover.png"
                    await run_blocking(render_cover_image, cover_template, meta, png)
                    resolved_cover = png
            except Exception as e:  # pragma: no cover - cover is best-effort
                logger.warning("EPUB cover render failed (%s); building coverless", e)

        await self._markdown_math_to_epub(
            markdown_content, output_path, title, author, cover_image=resolved_cover
        )
        logger.info(f"Professional EPUB from markdown: {output_path}")
        return output_path

    def cleanup(self):
        """Clean up temp files."""
        if self.temp_dir.exists():
            for f in self.temp_dir.iterdir():
                try:
                    f.unlink()
                except OSError:
                    # File may be in use or already deleted
                    pass
