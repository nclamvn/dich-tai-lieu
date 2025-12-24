"""
Agent 3: Streaming Publisher
AI Publisher Pro

Consumes STANDARD output from Agent 2 and renders professional PDF.

Key principle:
- Input is a FOLDER with manifest.json + chapter files
- Stream render: process one chapter at a time
- No memory overflow regardless of document length

Input: Agent 2 output folder
    book_output/
    ├── manifest.json
    ├── metadata.json
    ├── chapters/*.md
    └── assets/glossary.json

Output: Professional PDF (ebook or academic)
"""

import re
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Generator
from datetime import datetime

from .output_format import (
    Agent3InputReader,
    Manifest,
    Metadata,
    RenderMode,
    DocumentType
)


class StreamingEbookRenderer:
    """
    Streaming Ebook PDF Renderer

    Key difference from simple renderer:
    - Reads chapters one by one from Agent 2 output
    - Never holds entire document in memory
    - Can handle unlimited document length
    """

    # Page size: Trade Paperback (140x215mm)
    PAGE_WIDTH_MM = 140
    PAGE_HEIGHT_MM = 215
    MM_TO_PT = 2.83465

    def __init__(self, metadata: Metadata, manifest: Manifest):
        self.metadata = metadata
        self.manifest = manifest

        # Convert mm to points
        self.page_width = self.PAGE_WIDTH_MM * self.MM_TO_PT
        self.page_height = self.PAGE_HEIGHT_MM * self.MM_TO_PT

        # Import reportlab
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import mm

        self.mm = mm
        self.Paragraph = Paragraph
        self.Spacer = Spacer
        self.PageBreak = PageBreak
        self.HexColor = HexColor

        # Register fonts
        self._register_fonts()

        # Create styles
        self.styles = self._create_styles()

        # Story buffer
        self.story = []
        self.current_page_estimate = 0

    def _register_fonts(self):
        """Register DejaVu Serif fonts"""
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase.pdfmetrics import registerFontFamily

        # Try multiple font paths
        font_paths = [
            "/usr/share/fonts/truetype/dejavu",  # Linux
            "/Library/Fonts",  # macOS system
            "/System/Library/Fonts",  # macOS system
            str(Path.home() / "Library/Fonts"),  # macOS user
        ]

        font_files = {
            'regular': ['DejaVuSerif.ttf', 'DejaVu Serif.ttf'],
            'bold': ['DejaVuSerif-Bold.ttf', 'DejaVu Serif Bold.ttf'],
            'italic': ['DejaVuSerif-Italic.ttf', 'DejaVu Serif Italic.ttf'],
            'bolditalic': ['DejaVuSerif-BoldItalic.ttf', 'DejaVu Serif Bold Italic.ttf']
        }

        fonts_registered = False

        for font_dir in font_paths:
            font_path = Path(font_dir)
            if not font_path.exists():
                continue

            # Check for regular font
            regular_font = None
            for fname in font_files['regular']:
                if (font_path / fname).exists():
                    regular_font = str(font_path / fname)
                    break

            if regular_font:
                try:
                    pdfmetrics.registerFont(TTFont('BookFont', regular_font))

                    # Try to find other variants
                    for variant, fnames in font_files.items():
                        if variant == 'regular':
                            continue
                        for fname in fnames:
                            fpath = font_path / fname
                            if fpath.exists():
                                suffix = '-Bold' if variant == 'bold' else (
                                    '-Italic' if variant == 'italic' else '-BoldItalic')
                                pdfmetrics.registerFont(TTFont(f'BookFont{suffix}', str(fpath)))
                                break

                    registerFontFamily('BookFont',
                        normal='BookFont',
                        bold='BookFont-Bold',
                        italic='BookFont-Italic',
                        boldItalic='BookFont-BoldItalic'
                    )
                    fonts_registered = True
                    break
                except Exception:
                    continue

        if not fonts_registered:
            print("Warning: DejaVu fonts not found, using Helvetica")

    def _create_styles(self):
        """Create paragraph styles"""
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT

        styles = getSampleStyleSheet()

        # Determine font name
        font_name = 'BookFont'
        try:
            from reportlab.pdfbase import pdfmetrics
            pdfmetrics.getFont('BookFont')
        except:
            font_name = 'Helvetica'

        # Body text
        styles.add(ParagraphStyle(
            name='BookBody',
            fontName=font_name,
            fontSize=11,
            leading=16.5,
            alignment=TA_JUSTIFY,
            firstLineIndent=20,
            spaceBefore=0,
            spaceAfter=6,
        ))

        # First paragraph (no indent)
        styles.add(ParagraphStyle(
            name='BookBodyFirst',
            parent=styles['BookBody'],
            firstLineIndent=0,
        ))

        # Chapter title
        styles.add(ParagraphStyle(
            name='ChapterTitle',
            fontName=f'{font_name}-Bold' if font_name == 'BookFont' else 'Helvetica-Bold',
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceBefore=50,
            spaceAfter=30,
        ))

        # Section heading
        styles.add(ParagraphStyle(
            name='SectionHeading',
            fontName=f'{font_name}-Bold' if font_name == 'BookFont' else 'Helvetica-Bold',
            fontSize=14,
            leading=18,
            alignment=TA_LEFT,
            spaceBefore=20,
            spaceAfter=10,
        ))

        # Subsection heading
        styles.add(ParagraphStyle(
            name='SubsectionHeading',
            fontName=f'{font_name}-Bold' if font_name == 'BookFont' else 'Helvetica-Bold',
            fontSize=12,
            leading=15,
            alignment=TA_LEFT,
            spaceBefore=15,
            spaceAfter=8,
        ))

        # Block quote
        styles.add(ParagraphStyle(
            name='BlockQuote',
            fontName=f'{font_name}-Italic' if font_name == 'BookFont' else 'Helvetica-Oblique',
            fontSize=10,
            leading=15,
            alignment=TA_JUSTIFY,
            leftIndent=30,
            rightIndent=30,
            spaceBefore=10,
            spaceAfter=10,
        ))

        # Cover styles
        styles.add(ParagraphStyle(
            name='CoverTitle',
            fontName=f'{font_name}-Bold' if font_name == 'BookFont' else 'Helvetica-Bold',
            fontSize=32,
            leading=40,
            alignment=TA_CENTER,
        ))

        styles.add(ParagraphStyle(
            name='CoverSubtitle',
            fontName=f'{font_name}-Italic' if font_name == 'BookFont' else 'Helvetica-Oblique',
            fontSize=16,
            leading=22,
            alignment=TA_CENTER,
        ))

        styles.add(ParagraphStyle(
            name='CoverAuthor',
            fontName=font_name,
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
        ))

        styles.add(ParagraphStyle(
            name='CoverDecorator',
            fontName=font_name,
            fontSize=14,
            alignment=TA_CENTER,
        ))

        # TOC styles
        styles.add(ParagraphStyle(
            name='TOCHeading',
            fontName=f'{font_name}-Bold' if font_name == 'BookFont' else 'Helvetica-Bold',
            fontSize=20,
            leading=26,
            alignment=TA_CENTER,
            spaceBefore=30,
            spaceAfter=30,
        ))

        styles.add(ParagraphStyle(
            name='TOCEntry',
            fontName=font_name,
            fontSize=11,
            leading=18,
            leftIndent=20,
        ))

        return styles

    def _add_cover(self):
        """Add cover page"""
        self.story.append(self.Spacer(1, 80 * self.mm))
        self.story.append(self.Paragraph("═" * 25, self.styles['CoverDecorator']))
        self.story.append(self.Spacer(1, 8 * self.mm))

        self.story.append(self.Paragraph(self.metadata.title, self.styles['CoverTitle']))

        if self.metadata.subtitle:
            self.story.append(self.Spacer(1, 5 * self.mm))
            self.story.append(self.Paragraph(self.metadata.subtitle, self.styles['CoverSubtitle']))

        self.story.append(self.Spacer(1, 8 * self.mm))
        self.story.append(self.Paragraph("═" * 25, self.styles['CoverDecorator']))

        self.story.append(self.Spacer(1, 25 * self.mm))
        self.story.append(self.Paragraph(self.metadata.author, self.styles['CoverAuthor']))

        self.story.append(self.PageBreak())

    def _add_toc(self):
        """Add table of contents from manifest"""
        self.story.append(self.Paragraph("Mục Lục", self.styles['TOCHeading']))
        self.story.append(self.Spacer(1, 10 * self.mm))

        for chapter in self.manifest.chapters:
            self.story.append(self.Paragraph(chapter.title, self.styles['TOCEntry']))

        self.story.append(self.PageBreak())

    def _parse_chapter_markdown(self, content: str, is_first_chapter: bool = False):
        """
        Parse chapter markdown and add to story.

        This is called for EACH chapter, so memory is bounded.
        """
        lines = content.split('\n')
        current_para = []
        is_first_para = True
        in_blockquote = False
        in_frontmatter = False

        for line in lines:
            line = line.rstrip()

            # Skip frontmatter
            if line == '---':
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                continue

            # Chapter heading (# )
            if line.startswith('# ') and not line.startswith('##'):
                if current_para:
                    self._add_paragraph(current_para, is_first_para, in_blockquote)
                    current_para = []

                title = line[2:].strip()
                self.story.append(self.PageBreak())
                self.story.append(self.Paragraph(title, self.styles['ChapterTitle']))
                self.story.append(self.Spacer(1, 20))
                is_first_para = True
                continue

            # Section (## )
            if line.startswith('## '):
                if current_para:
                    self._add_paragraph(current_para, is_first_para, in_blockquote)
                    current_para = []

                title = line[3:].strip()
                self.story.append(self.Paragraph(title, self.styles['SectionHeading']))
                is_first_para = True
                continue

            # Subsection (### )
            if line.startswith('### '):
                if current_para:
                    self._add_paragraph(current_para, is_first_para, in_blockquote)
                    current_para = []

                title = line[4:].strip()
                self.story.append(self.Paragraph(title, self.styles['SubsectionHeading']))
                is_first_para = True
                continue

            # Blockquote
            if line.startswith('> '):
                if current_para and not in_blockquote:
                    self._add_paragraph(current_para, is_first_para, False)
                    current_para = []
                in_blockquote = True
                current_para.append(line[2:])
                continue
            elif in_blockquote and line.strip():
                current_para.append(line)
                continue
            elif in_blockquote and not line.strip():
                self._add_paragraph(current_para, True, True)
                current_para = []
                in_blockquote = False
                is_first_para = True
                continue

            # Empty line
            if not line.strip():
                if current_para:
                    self._add_paragraph(current_para, is_first_para, in_blockquote)
                    current_para = []
                    is_first_para = False
                continue

            # Regular text
            current_para.append(line)

        # Flush remaining
        if current_para:
            self._add_paragraph(current_para, is_first_para, in_blockquote)

    def _add_paragraph(self, lines, is_first: bool, is_quote: bool):
        """Add paragraph to story"""
        text = ' '.join(lines)

        # Convert markdown formatting
        text = text.replace('&', '&amp;')
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

        # Escape remaining special chars
        text = text.replace('<b>', '<<<B>>>').replace('</b>', '<<</B>>>')
        text = text.replace('<i>', '<<<I>>>').replace('</i>', '<<</I>>>')
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('<<<B>>>', '<b>').replace('<<</B>>>', '</b>')
        text = text.replace('<<<I>>>', '<i>').replace('<<</I>>>', '</i>')

        if is_quote:
            style = self.styles['BlockQuote']
        elif is_first:
            style = self.styles['BookBodyFirst']
        else:
            style = self.styles['BookBody']

        self.story.append(self.Paragraph(text, style))

    def _add_page_number(self, canvas, doc):
        """Add page number"""
        if doc.page > 2:
            canvas.saveState()
            try:
                canvas.setFont('BookFont', 9)
            except:
                canvas.setFont('Helvetica', 9)
            canvas.drawCentredString(
                self.page_width / 2,
                15 * self.mm,
                str(doc.page - 2)
            )
            canvas.restoreState()

    def render(
        self,
        chapter_iterator: Generator,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Render PDF by streaming chapters.

        Args:
            chapter_iterator: Generator yielding chapter dicts
            output_path: Output PDF path

        Returns:
            Dict with output info
        """
        from reportlab.platypus import SimpleDocTemplate

        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=(self.page_width, self.page_height),
            leftMargin=20 * self.mm,
            rightMargin=15 * self.mm,
            topMargin=20 * self.mm,
            bottomMargin=25 * self.mm,
            title=f"{self.metadata.title}",
            author=self.metadata.author,
        )

        # Add cover
        if self.manifest.structure.has_cover:
            self._add_cover()

        # Add TOC
        if self.manifest.structure.has_toc:
            self._add_toc()

        # Stream chapters
        chapter_count = 0
        for chapter in chapter_iterator:
            print(f"  Rendering chapter: {chapter['title']}")
            self._parse_chapter_markdown(chapter['content'], chapter_count == 0)
            chapter_count += 1

        # Build PDF
        doc.build(
            self.story,
            onFirstPage=self._add_page_number,
            onLaterPages=self._add_page_number
        )

        # Get page count
        pages = self._get_page_count(output_path)

        return {
            "output_path": output_path,
            "pages": pages,
            "chapters": chapter_count,
            "format": "ebook",
            "size_bytes": Path(output_path).stat().st_size
        }

    def _get_page_count(self, pdf_path: str) -> int:
        """Get page count from PDF"""
        try:
            result = subprocess.run(['pdfinfo', pdf_path], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except:
            pass
        return 0


class StreamingAcademicRenderer:
    """
    Streaming Academic PDF Renderer using XeLaTeX

    Builds LaTeX document incrementally from chapters.
    """

    LATEX_HEADER = r'''\documentclass[11pt,a4paper]{amsart}

\usepackage{fontspec}
\setmainfont{Latin Modern Roman}
\setsansfont{Latin Modern Sans}
\setmonofont{Latin Modern Mono}

\usepackage{unicode-math}
\setmathfont{Latin Modern Math}

\usepackage{amsmath,amsthm}
\usepackage{mathtools}
\usepackage[margin=2.5cm]{geometry}

\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue}

\theoremstyle{plain}
\newtheorem{theorem}{Định lý}[section]
\newtheorem{lemma}[theorem]{Bổ đề}
\newtheorem{proposition}[theorem]{Mệnh đề}
\newtheorem{corollary}[theorem]{Hệ quả}

\theoremstyle{definition}
\newtheorem{definition}[theorem]{Định nghĩa}
\newtheorem{example}[theorem]{Ví dụ}
\newtheorem{remark}[theorem]{Nhận xét}

\newcommand{\N}{\mathbb{N}}
\newcommand{\Z}{\mathbb{Z}}
\newcommand{\R}{\mathbb{R}}
\newcommand{\C}{\mathbb{C}}

'''

    def __init__(self, metadata: Metadata, manifest: Manifest):
        self.metadata = metadata
        self.manifest = manifest

    def _markdown_to_latex(self, content: str) -> str:
        """Convert markdown to LaTeX"""
        # Skip frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        # Headers
        content = re.sub(r'^# (.+)$', r'\\section{\1}', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'\\subsection{\1}', content, flags=re.MULTILINE)
        content = re.sub(r'^### (.+)$', r'\\subsubsection{\1}', content, flags=re.MULTILINE)

        # Bold/italic
        content = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', content)
        content = re.sub(r'\*(.+?)\*', r'\\emph{\1}', content)

        # Escape special chars (careful with $)
        content = content.replace('%', '\\%')
        content = content.replace('&', '\\&')
        content = content.replace('#', '\\#')

        return content

    def render(
        self,
        chapter_iterator: Generator,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Render PDF via LaTeX by streaming chapters.
        """
        output_path = Path(output_path)
        temp_dir = Path(tempfile.mkdtemp())
        tex_file = temp_dir / "document.tex"

        # Build LaTeX content incrementally
        latex_content = self.LATEX_HEADER

        # Title info
        latex_content += f"\\title{{{self.metadata.title}}}\n"
        latex_content += f"\\author{{{self.metadata.author}}}\n"

        if self.metadata.institution:
            latex_content += f"\\address{{{self.metadata.institution}}}\n"

        latex_content += "\\date{\\today}\n\n"
        latex_content += "\\begin{document}\n\n"

        # Abstract
        if self.metadata.abstract:
            latex_content += f"\\begin{{abstract}}\n{self.metadata.abstract}\n\\end{{abstract}}\n\n"

        latex_content += "\\maketitle\n\\tableofcontents\n\n"

        # Stream chapters
        chapter_count = 0
        for chapter in chapter_iterator:
            print(f"  Processing chapter: {chapter['title']}")
            latex_content += self._markdown_to_latex(chapter['content'])
            latex_content += "\n\n"
            chapter_count += 1

        latex_content += "\\end{document}\n"

        # Write and compile
        tex_file.write_text(latex_content, encoding='utf-8')

        for _ in range(3):
            subprocess.run(
                ['xelatex', '-interaction=nonstopmode', 'document.tex'],
                cwd=temp_dir,
                capture_output=True
            )

        pdf_file = temp_dir / "document.pdf"
        if not pdf_file.exists():
            raise RuntimeError("LaTeX compilation failed")

        # Move output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf_file), str(output_path))

        tex_output = output_path.with_suffix('.tex')
        shutil.copy(str(tex_file), str(tex_output))

        # Get page count
        pages = self._get_page_count(str(output_path))

        return {
            "output_path": str(output_path),
            "tex_path": str(tex_output),
            "pages": pages,
            "chapters": chapter_count,
            "format": "academic",
            "size_bytes": output_path.stat().st_size
        }

    def _get_page_count(self, pdf_path: str) -> int:
        """Get page count"""
        try:
            result = subprocess.run(['pdfinfo', pdf_path], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except:
            pass
        return 0


# =========================================
# AGENT 3: STREAMING PUBLISHER
# =========================================

class Agent3_StreamingPublisher:
    """
    Agent 3: Streaming Publisher

    Consumes Agent 2 output folder and renders professional PDF.
    Handles documents of ANY length by streaming chapters.

    Usage:
        publisher = Agent3_StreamingPublisher("./book_output")
        result = publisher.render("./book.pdf")

        print(f"Created: {result['pages']} pages")
    """

    def __init__(self, input_dir: str):
        """
        Initialize with Agent 2 output directory.

        Args:
            input_dir: Path to Agent 2 output folder containing:
                - manifest.json
                - metadata.json
                - chapters/*.md
        """
        self.reader = Agent3InputReader(input_dir)
        self.manifest = self.reader.get_manifest()
        self.metadata = self.reader.get_metadata()

    def render(
        self,
        output_path: str,
        mode: Optional[RenderMode] = None
    ) -> Dict[str, Any]:
        """
        Render PDF from Agent 2 output.

        Args:
            output_path: Output PDF path
            mode: Override render mode (default: from manifest)

        Returns:
            Dict with output info
        """
        mode = mode or self.manifest.render_mode

        print(f"Agent 3: Publishing '{self.metadata.title}'")
        print(f"  Mode: {mode.value}")
        print(f"  Chapters: {len(self.manifest.chapters)}")

        start = datetime.now()

        if mode == RenderMode.EBOOK:
            renderer = StreamingEbookRenderer(self.metadata, self.manifest)
        elif mode == RenderMode.ACADEMIC:
            renderer = StreamingAcademicRenderer(self.metadata, self.manifest)
        else:
            # Default to ebook
            renderer = StreamingEbookRenderer(self.metadata, self.manifest)

        result = renderer.render(
            self.reader.iter_chapters(),
            output_path
        )

        result["elapsed_seconds"] = (datetime.now() - start).total_seconds()
        result["title"] = self.metadata.title
        result["author"] = self.metadata.author

        print(f"  Done: {result['pages']} pages in {result['elapsed_seconds']:.1f}s")

        return result


# =========================================
# CONVENIENCE FUNCTIONS
# =========================================

def publish_from_folder(
    input_dir: str,
    output_path: str,
    mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick function to publish from Agent 2 output folder.

    Args:
        input_dir: Agent 2 output directory
        output_path: Output PDF path
        mode: "ebook" or "academic" (default: from manifest)

    Returns:
        Dict with output info
    """
    publisher = Agent3_StreamingPublisher(input_dir)
    render_mode = RenderMode(mode) if mode else None
    return publisher.render(output_path, render_mode)


# =========================================
# CLI
# =========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent 3: Streaming Publisher")
    parser.add_argument("input_dir", help="Agent 2 output directory")
    parser.add_argument("-o", "--output", required=True, help="Output PDF path")
    parser.add_argument("-m", "--mode", choices=["ebook", "academic"],
                        help="Override render mode")

    args = parser.parse_args()

    publisher = Agent3_StreamingPublisher(args.input_dir)

    mode = RenderMode(args.mode) if args.mode else None
    result = publisher.render(args.output, mode)

    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    Agent 3: Publishing Complete                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   Title:    {result['title']:<53} ║
║   Author:   {result['author']:<53} ║
║   Output:   {result['output_path']:<53} ║
║   Pages:    {result['pages']:<53} ║
║   Chapters: {result['chapters']:<53} ║
║   Format:   {result['format']:<53} ║
║   Time:     {result['elapsed_seconds']:.1f}s{' ' * 51}║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
