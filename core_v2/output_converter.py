"""
Output Converter - FIXED

Properly handles LaTeX formulas:
- For PDF: Use pdflatex (native LaTeX rendering)
- For DOCX: Use pandoc with --mathml flag
- For EPUB: Use pandoc with math rendering
"""

import asyncio
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


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
    ) -> bool:
        """Convert Markdown with LaTeX math ($...$) to EPUB"""

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

    def cleanup(self):
        """Clean up temp files."""
        if self.temp_dir.exists():
            for f in self.temp_dir.iterdir():
                try:
                    f.unlink()
                except:
                    pass
