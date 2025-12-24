"""
Agent 3: Professional PDF Renderer
AI Publisher Pro

Renders Markdown from Agent 2 to professional PDF:
1. Ebook Mode - Commercial quality Vietnamese ebook (ReportLab)
2. Academic Mode - LaTeX journal-style paper (XeLaTeX)

Proven working code based on Claude's successful renders:
- 414-page Vietnamese ebook with professional cover
- 26-page math paper with LaTeX formulas

Input: Markdown from Agent 2
Output: Professional PDF ready for publishing
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RenderMode(Enum):
    """PDF rendering modes"""
    EBOOK = "ebook"           # Commercial ebook (novels, biographies)
    ACADEMIC = "academic"     # Journal paper (math, science)
    BUSINESS = "business"     # Business documents with tables


@dataclass
class DocumentMetadata:
    """Document metadata for PDF"""
    title: str = "Untitled"
    author: str = "Unknown"
    subtitle: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    language: str = "vi"
    date: Optional[str] = None

    # Academic specific
    institution: Optional[str] = None
    email: Optional[str] = None
    abstract: Optional[str] = None

    # Ebook specific
    publisher: Optional[str] = None
    isbn: Optional[str] = None


@dataclass
class EbookConfig:
    """Ebook rendering configuration"""
    # Page size - Trade Paperback (140x215mm) is standard
    page_width_mm: float = 140
    page_height_mm: float = 215

    # Margins (in mm)
    margin_top: int = 20
    margin_bottom: int = 25
    margin_left: int = 20
    margin_right: int = 15

    # Typography
    font_size: int = 11
    line_height_ratio: float = 1.5
    first_line_indent: int = 20

    # Features
    include_toc: bool = True
    include_cover: bool = True
    page_numbers: bool = True

    # Font paths (DejaVu Serif - proven Vietnamese support)
    font_regular: str = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    font_bold: str = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
    font_italic: str = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
    font_bold_italic: str = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf"


# =========================================
# EBOOK RENDERER (ReportLab) - Proven Working
# =========================================

class EbookRenderer:
    """
    Commercial Ebook PDF Renderer using ReportLab

    Proven features (from 414-page Sam Altman biography):
    - Trade Paperback size (140x215mm)
    - DejaVu Serif font (full Vietnamese support)
    - Professional cover with decorative elements
    - Table of contents
    - Justified text with first-line indent
    - Page numbers in footer
    - Full metadata
    """

    def __init__(self, config: EbookConfig, metadata: DocumentMetadata):
        self.config = config
        self.metadata = metadata

        # Convert mm to points (1mm = 2.83465pt)
        self.MM = 2.83465
        self.page_width = config.page_width_mm * self.MM
        self.page_height = config.page_height_mm * self.MM

        # Import reportlab
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        self.Paragraph = Paragraph
        self.Spacer = Spacer
        self.PageBreak = PageBreak

        # Register fonts
        self._register_fonts()

        # Create styles
        self.styles = self._create_styles()

        # Content
        self.story = []
        self.toc_entries = []

    def _register_fonts(self):
        """Register DejaVu Serif fonts for Vietnamese support"""
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase.pdfmetrics import registerFontFamily

        try:
            pdfmetrics.registerFont(TTFont('BookFont', self.config.font_regular))
            pdfmetrics.registerFont(TTFont('BookFont-Bold', self.config.font_bold))
            pdfmetrics.registerFont(TTFont('BookFont-Italic', self.config.font_italic))
            pdfmetrics.registerFont(TTFont('BookFont-BoldItalic', self.config.font_bold_italic))

            registerFontFamily('BookFont',
                normal='BookFont',
                bold='BookFont-Bold',
                italic='BookFont-Italic',
                boldItalic='BookFont-BoldItalic'
            )
        except Exception as e:
            print(f"Warning: Font registration failed: {e}")

    def _create_styles(self):
        """Create paragraph styles for ebook"""
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
        from reportlab.lib.colors import HexColor

        styles = getSampleStyleSheet()

        # Body text - justified with first line indent
        styles.add(ParagraphStyle(
            name='BookBody',
            fontName='BookFont',
            fontSize=self.config.font_size,
            leading=self.config.font_size * self.config.line_height_ratio,
            alignment=TA_JUSTIFY,
            firstLineIndent=self.config.first_line_indent,
            spaceBefore=0,
            spaceAfter=6,
        ))

        # First paragraph (no indent after heading)
        styles.add(ParagraphStyle(
            name='BookBodyFirst',
            parent=styles['BookBody'],
            firstLineIndent=0,
        ))

        # Chapter title
        styles.add(ParagraphStyle(
            name='ChapterTitle',
            fontName='BookFont-Bold',
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceBefore=50,
            spaceAfter=30,
            textColor=HexColor('#1a1a1a'),
        ))

        # Section heading (##)
        styles.add(ParagraphStyle(
            name='SectionHeading',
            fontName='BookFont-Bold',
            fontSize=14,
            leading=18,
            alignment=TA_LEFT,
            spaceBefore=20,
            spaceAfter=10,
        ))

        # Subsection heading (###)
        styles.add(ParagraphStyle(
            name='SubsectionHeading',
            fontName='BookFont-Bold',
            fontSize=12,
            leading=15,
            alignment=TA_LEFT,
            spaceBefore=15,
            spaceAfter=8,
        ))

        # Block quote
        styles.add(ParagraphStyle(
            name='BlockQuote',
            fontName='BookFont-Italic',
            fontSize=self.config.font_size - 1,
            leading=(self.config.font_size - 1) * self.config.line_height_ratio,
            alignment=TA_JUSTIFY,
            leftIndent=30,
            rightIndent=30,
            spaceBefore=10,
            spaceAfter=10,
        ))

        # Cover styles
        styles.add(ParagraphStyle(
            name='CoverTitle',
            fontName='BookFont-Bold',
            fontSize=32,
            leading=40,
            alignment=TA_CENTER,
            textColor=HexColor('#000000'),
        ))

        styles.add(ParagraphStyle(
            name='CoverSubtitle',
            fontName='BookFont-Italic',
            fontSize=16,
            leading=22,
            alignment=TA_CENTER,
            textColor=HexColor('#333333'),
        ))

        styles.add(ParagraphStyle(
            name='CoverAuthor',
            fontName='BookFont',
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=HexColor('#444444'),
        ))

        styles.add(ParagraphStyle(
            name='CoverDecorator',
            fontName='BookFont',
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=HexColor('#666666'),
        ))

        # TOC styles
        styles.add(ParagraphStyle(
            name='TOCHeading',
            fontName='BookFont-Bold',
            fontSize=20,
            leading=26,
            alignment=TA_CENTER,
            spaceBefore=30,
            spaceAfter=30,
        ))

        styles.add(ParagraphStyle(
            name='TOCEntry',
            fontName='BookFont',
            fontSize=11,
            leading=18,
            leftIndent=20,
        ))

        styles.add(ParagraphStyle(
            name='TOCEntryLevel2',
            fontName='BookFont',
            fontSize=10,
            leading=16,
            leftIndent=40,
        ))

        return styles

    def _add_cover_page(self):
        """Add professional cover page with decorative elements"""
        # Top spacing
        self.story.append(self.Spacer(1, 80 * self.MM))

        # Decorative line
        self.story.append(self.Paragraph(
            "═" * 25,
            self.styles['CoverDecorator']
        ))
        self.story.append(self.Spacer(1, 8 * self.MM))

        # Title
        self.story.append(self.Paragraph(
            self.metadata.title,
            self.styles['CoverTitle']
        ))

        # Subtitle
        if self.metadata.subtitle:
            self.story.append(self.Spacer(1, 5 * self.MM))
            self.story.append(self.Paragraph(
                self.metadata.subtitle,
                self.styles['CoverSubtitle']
            ))

        # Decorative line
        self.story.append(self.Spacer(1, 8 * self.MM))
        self.story.append(self.Paragraph(
            "═" * 25,
            self.styles['CoverDecorator']
        ))

        # Author
        self.story.append(self.Spacer(1, 25 * self.MM))
        self.story.append(self.Paragraph(
            self.metadata.author,
            self.styles['CoverAuthor']
        ))

        # Publisher/Date at bottom
        if self.metadata.publisher or self.metadata.date:
            self.story.append(self.Spacer(1, 35 * self.MM))
            info_parts = []
            if self.metadata.publisher:
                info_parts.append(self.metadata.publisher)
            if self.metadata.date:
                info_parts.append(self.metadata.date)
            self.story.append(self.Paragraph(
                " • ".join(info_parts),
                self.styles['CoverAuthor']
            ))

        self.story.append(self.PageBreak())

    def _add_toc_page(self):
        """Add table of contents"""
        self.story.append(self.Paragraph("Mục Lục", self.styles['TOCHeading']))
        self.story.append(self.Spacer(1, 10 * self.MM))

        for entry in self.toc_entries:
            level, title = entry
            if level == 0:
                self.story.append(self.Paragraph(title, self.styles['TOCEntry']))
            else:
                self.story.append(self.Paragraph(title, self.styles['TOCEntryLevel2']))

        self.story.append(self.PageBreak())

    def _parse_markdown(self, content: str):
        """Parse markdown and build story"""
        lines = content.split('\n')
        current_para = []
        is_first_para = True
        in_blockquote = False

        for line in lines:
            line = line.rstrip()

            # Chapter heading (#)
            if line.startswith('# ') and not line.startswith('##'):
                if current_para:
                    self._add_paragraph(current_para, is_first_para, in_blockquote)
                    current_para = []

                title = line[2:].strip()
                self.toc_entries.append((0, title))

                self.story.append(self.PageBreak())
                self.story.append(self.Paragraph(title, self.styles['ChapterTitle']))
                self.story.append(self.Spacer(1, 20))
                is_first_para = True
                continue

            # Section heading (##)
            if line.startswith('## '):
                if current_para:
                    self._add_paragraph(current_para, is_first_para, in_blockquote)
                    current_para = []

                title = line[3:].strip()
                self.toc_entries.append((1, title))
                self.story.append(self.Paragraph(title, self.styles['SectionHeading']))
                is_first_para = True
                continue

            # Subsection heading (###)
            if line.startswith('### '):
                if current_para:
                    self._add_paragraph(current_para, is_first_para, in_blockquote)
                    current_para = []

                title = line[4:].strip()
                self.story.append(self.Paragraph(title, self.styles['SubsectionHeading']))
                is_first_para = True
                continue

            # Block quote
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

            # Empty line = paragraph break
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

    def _add_paragraph(self, lines: List[str], is_first: bool, is_quote: bool):
        """Add paragraph to story"""
        text = ' '.join(lines)
        text = self._convert_formatting(text)

        if is_quote:
            style = self.styles['BlockQuote']
        elif is_first:
            style = self.styles['BookBodyFirst']
        else:
            style = self.styles['BookBody']

        self.story.append(self.Paragraph(text, style))

    def _convert_formatting(self, text: str) -> str:
        """Convert markdown formatting to ReportLab markup"""
        # Escape special chars first (preserve bold/italic markers)
        text = text.replace('&', '&amp;')

        # Bold **text**
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

        # Italic *text*
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'(?<![_])_([^_]+)_(?![_])', r'<i>\1</i>', text)

        # Escape remaining special chars
        text = text.replace('<b>', '<<<B>>>').replace('</b>', '<<</B>>>')
        text = text.replace('<i>', '<<<I>>>').replace('</i>', '<<</I>>>')
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('<<<B>>>', '<b>').replace('<<</B>>>', '</b>')
        text = text.replace('<<<I>>>', '<i>').replace('<<</I>>>', '</i>')

        return text

    def _add_page_number(self, canvas, doc):
        """Add page number to footer"""
        canvas.saveState()

        # Skip cover and TOC pages
        if doc.page > 2 and self.config.page_numbers:
            canvas.setFont('BookFont', 9)
            page_num = str(doc.page - 2)
            canvas.drawCentredString(
                self.page_width / 2,
                15 * self.MM,
                page_num
            )

        canvas.restoreState()

    def render(self, markdown_content: str, output_path: str) -> Dict[str, Any]:
        """
        Render markdown to ebook PDF.

        Args:
            markdown_content: Markdown text from Agent 2
            output_path: Output PDF path

        Returns:
            Dict with output info
        """
        from reportlab.platypus import SimpleDocTemplate

        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=(self.page_width, self.page_height),
            leftMargin=self.config.margin_left * self.MM,
            rightMargin=self.config.margin_right * self.MM,
            topMargin=self.config.margin_top * self.MM,
            bottomMargin=self.config.margin_bottom * self.MM,
            title=f"{self.metadata.title} - {self.metadata.author}" if self.metadata.author else self.metadata.title,
            author=self.metadata.author,
            subject=self.metadata.subject or "",
        )

        # Build content
        if self.config.include_cover:
            self._add_cover_page()

        # Parse markdown (builds toc_entries)
        self._parse_markdown(markdown_content)

        # Insert TOC after cover
        if self.config.include_toc and self.toc_entries:
            toc_story = []
            toc_story.append(self.Paragraph("Mục Lục", self.styles['TOCHeading']))
            toc_story.append(self.Spacer(1, 10 * self.MM))

            for entry in self.toc_entries:
                level, title = entry
                style = self.styles['TOCEntry'] if level == 0 else self.styles['TOCEntryLevel2']
                toc_story.append(self.Paragraph(title, style))

            toc_story.append(self.PageBreak())

            # Insert after cover (index 1)
            insert_pos = 1 if self.config.include_cover else 0
            for i, item in enumerate(toc_story):
                self.story.insert(insert_pos + i, item)

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
            "size_bytes": Path(output_path).stat().st_size,
            "format": "ebook",
            "page_size": f"{self.config.page_width_mm}x{self.config.page_height_mm}mm"
        }

    def _get_page_count(self, pdf_path: str) -> int:
        """Get page count from PDF"""
        try:
            result = subprocess.run(
                ['pdfinfo', pdf_path],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except:
            pass
        return 0


# =========================================
# ACADEMIC RENDERER (XeLaTeX) - Proven Working
# =========================================

class AcademicRenderer:
    """
    Academic PDF Renderer using XeLaTeX

    Proven features (from 26-page Erdős paper):
    - AMS article class
    - Latin Modern fonts (Unicode)
    - Proper theorem environments (Vietnamese)
    - Math formulas with unicode-math
    - A4 size, proper margins
    """

    LATEX_TEMPLATE = r'''\documentclass[11pt,a4paper]{amsart}

% XeLaTeX for Unicode support
\usepackage{fontspec}
\setmainfont{Latin Modern Roman}
\setsansfont{Latin Modern Sans}
\setmonofont{Latin Modern Mono}

% Math font
\usepackage{unicode-math}
\setmathfont{Latin Modern Math}

% AMS packages
\usepackage{amsmath,amsthm}
\usepackage{mathtools}

% Page layout
\usepackage[margin=2.5cm]{geometry}

% Hyperlinks
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    citecolor=blue,
    urlcolor=blue
}

% Tables
\usepackage{longtable,booktabs,array}

% Theorem environments (Vietnamese)
\theoremstyle{plain}
\newtheorem{theorem}{Định lý}[section]
\newtheorem{lemma}[theorem]{Bổ đề}
\newtheorem{proposition}[theorem]{Mệnh đề}
\newtheorem{corollary}[theorem]{Hệ quả}

\theoremstyle{definition}
\newtheorem{definition}[theorem]{Định nghĩa}
\newtheorem{example}[theorem]{Ví dụ}
\newtheorem{remark}[theorem]{Nhận xét}

% Custom math commands
\newcommand{\N}{\mathbb{N}}
\newcommand{\Z}{\mathbb{Z}}
\newcommand{\R}{\mathbb{R}}
\newcommand{\C}{\mathbb{C}}
\newcommand{\E}{\mathbb{E}}

% Document info
\title{<<TITLE>>}
\author{<<AUTHOR>>}
<<ADDRESS>>
<<EMAIL>>
\date{<<DATE>>}

\begin{document}

<<ABSTRACT>>

\maketitle
\tableofcontents

<<CONTENT>>

\end{document}
'''

    def __init__(self, metadata: DocumentMetadata):
        self.metadata = metadata

    def _markdown_table_to_latex(self, content: str) -> str:
        """Convert markdown tables to LaTeX longtable format

        Handles:
        - | Col1 | Col2 | Col3 |
        - |------|------|------|
        - | Data | Data | Data |
        """
        lines = content.split('\n')
        result_lines = []
        table_lines = []
        in_table = False

        for line in lines:
            stripped = line.strip()

            # Detect table row (starts and ends with |)
            if stripped.startswith('|') and stripped.endswith('|'):
                # Skip separator row (|---|---|---| or |:--|:--:|--:|)
                if re.match(r'^\|[\s\-:|]+(\|[\s\-:|]+)+\|$', stripped):
                    continue

                if not in_table:
                    in_table = True
                    table_lines = []

                # Parse cells
                cells = [cell.strip() for cell in stripped.split('|')[1:-1]]
                table_lines.append(cells)
            else:
                # End of table
                if in_table and table_lines:
                    result_lines.append(self._create_latex_table(table_lines))
                    table_lines = []
                    in_table = False
                result_lines.append(line)

        # Handle table at end of content
        if in_table and table_lines:
            result_lines.append(self._create_latex_table(table_lines))

        return '\n'.join(result_lines)

    def _create_latex_table(self, rows: list) -> str:
        """Create LaTeX longtable from parsed rows"""
        if not rows:
            return ''

        num_cols = len(rows[0])
        col_spec = '|' + 'l|' * num_cols

        latex_lines = [
            '\\begin{longtable}{' + col_spec + '}',
            '\\hline'
        ]

        for i, row in enumerate(rows):
            # Escape special chars in cells (except &)
            escaped_cells = []
            for cell in row:
                cell = cell.replace('%', '\\%')
                cell = cell.replace('#', '\\#')
                cell = cell.replace('_', '\\_')
                escaped_cells.append(cell)

            row_text = ' & '.join(escaped_cells) + ' \\\\'
            latex_lines.append(row_text)

            # Add hline after header row
            if i == 0:
                latex_lines.append('\\hline\\hline')
            else:
                latex_lines.append('\\hline')

        latex_lines.append('\\end{longtable}')

        return '\n'.join(latex_lines)

    def _markdown_to_latex(self, content: str) -> str:
        """Convert markdown to LaTeX"""
        # Convert tables first (before escaping & chars)
        content = self._markdown_table_to_latex(content)

        # Headers
        content = re.sub(r'^# (.+)$', r'\\section{\1}', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'\\subsection{\1}', content, flags=re.MULTILINE)
        content = re.sub(r'^### (.+)$', r'\\subsubsection{\1}', content, flags=re.MULTILINE)

        # Bold and italic
        content = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', content)
        content = re.sub(r'\*(.+?)\*', r'\\emph{\1}', content)
        content = re.sub(r'_(.+?)_', r'\\emph{\1}', content)

        # Lists
        lines = content.split('\n')
        new_lines = []
        in_itemize = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_itemize:
                    new_lines.append('\\begin{itemize}')
                    in_itemize = True
                item_text = stripped[2:]
                new_lines.append(f'\\item {item_text}')
            else:
                if in_itemize and not stripped:
                    new_lines.append('\\end{itemize}')
                    in_itemize = False
                new_lines.append(line)

        if in_itemize:
            new_lines.append('\\end{itemize}')

        content = '\n'.join(new_lines)

        # Escape special LaTeX chars (not in math mode)
        # Note: Tables already escaped, skip & in table context
        content = content.replace('%', '\\%')
        # Don't escape & globally - tables need it as column separator
        # Only escape & outside of longtable environment
        content = self._escape_ampersand_outside_tables(content)
        content = content.replace('#', '\\#')

        return content

    def _escape_ampersand_outside_tables(self, content: str) -> str:
        """Escape & only outside longtable environments"""
        parts = re.split(r'(\\begin\{longtable\}.*?\\end\{longtable\})', content, flags=re.DOTALL)
        result = []
        for part in parts:
            if part.startswith('\\begin{longtable}'):
                result.append(part)  # Keep tables as-is
            else:
                result.append(part.replace('&', '\\&'))
        return ''.join(result)

    def _create_document(self, content: str) -> str:
        """Create complete LaTeX document"""
        latex = self.LATEX_TEMPLATE

        # Fill metadata
        latex = latex.replace('<<TITLE>>', self.metadata.title)
        latex = latex.replace('<<AUTHOR>>', self.metadata.author)

        if self.metadata.institution:
            latex = latex.replace('<<ADDRESS>>',
                f'\\address{{{self.metadata.institution}}}')
        else:
            latex = latex.replace('<<ADDRESS>>', '')

        if self.metadata.email:
            latex = latex.replace('<<EMAIL>>',
                f'\\email{{{self.metadata.email}}}')
        else:
            latex = latex.replace('<<EMAIL>>', '')

        latex = latex.replace('<<DATE>>',
            self.metadata.date or '\\today')

        if self.metadata.abstract:
            latex = latex.replace('<<ABSTRACT>>',
                f'\\begin{{abstract}}\n{self.metadata.abstract}\n\\end{{abstract}}')
        else:
            latex = latex.replace('<<ABSTRACT>>', '')

        # Convert and insert content
        latex_content = self._markdown_to_latex(content)
        latex = latex.replace('<<CONTENT>>', latex_content)

        return latex

    def render(self, markdown_content: str, output_path: str) -> Dict[str, Any]:
        """
        Render markdown to academic PDF via XeLaTeX.

        Args:
            markdown_content: Markdown text
            output_path: Output PDF path

        Returns:
            Dict with output info
        """
        # Create LaTeX document
        latex_content = self._create_document(markdown_content)

        # Setup temp directory
        output_path = Path(output_path)
        temp_dir = Path(tempfile.mkdtemp())
        tex_file = temp_dir / "document.tex"

        # Write LaTeX
        tex_file.write_text(latex_content, encoding='utf-8')

        # Compile with XeLaTeX (3 passes for cross-refs)
        for i in range(3):
            result = subprocess.run(
                ['xelatex', '-interaction=nonstopmode', 'document.tex'],
                cwd=temp_dir,
                capture_output=True,
                text=True
            )

        # Check output
        pdf_file = temp_dir / "document.pdf"
        if not pdf_file.exists():
            raise RuntimeError(f"LaTeX compilation failed: {result.stderr[:1000]}")

        # Move to final location
        import shutil
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pdf_file), str(output_path))

        # Also save .tex source
        tex_output = output_path.with_suffix('.tex')
        shutil.copy(str(tex_file), str(tex_output))

        # Get page count
        pages = self._get_page_count(str(output_path))

        return {
            "output_path": str(output_path),
            "tex_path": str(tex_output),
            "pages": pages,
            "size_bytes": output_path.stat().st_size,
            "format": "academic",
            "page_size": "A4"
        }

    def _get_page_count(self, pdf_path: str) -> int:
        """Get page count"""
        try:
            result = subprocess.run(
                ['pdfinfo', pdf_path],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except:
            pass
        return 0


# =========================================
# AGENT 3: MAIN INTERFACE
# =========================================

class Agent3_PDFRenderer:
    """
    Agent 3: Professional PDF Renderer

    Takes Markdown from Agent 2 and renders to professional PDF.

    Usage:
        agent = Agent3_PDFRenderer()

        # Ebook (novels, biographies)
        result = agent.render_ebook(
            markdown_content,
            "book.pdf",
            title="Tiểu sử Sam Altman",
            author="Chu Hằng Tinh"
        )

        # Academic (math papers)
        result = agent.render_academic(
            markdown_content,
            "paper.pdf",
            title="Bài toán độ lệch Erdős",
            author="Terence Tao"
        )
    """

    def render_ebook(
        self,
        markdown_content: str,
        output_path: str,
        title: str,
        author: str,
        subtitle: Optional[str] = None,
        subject: Optional[str] = None,
        publisher: Optional[str] = None,
        config: Optional[EbookConfig] = None
    ) -> Dict[str, Any]:
        """
        Render markdown to commercial ebook PDF.

        Features:
        - Trade Paperback size (140x215mm)
        - DejaVu Serif font (Vietnamese support)
        - Professional cover page
        - Table of contents
        - Justified text, first-line indent
        - Page numbers
        """
        metadata = DocumentMetadata(
            title=title,
            author=author,
            subtitle=subtitle,
            subject=subject,
            publisher=publisher,
            date=datetime.now().strftime("%Y")
        )

        config = config or EbookConfig()
        renderer = EbookRenderer(config, metadata)

        start = datetime.now()
        result = renderer.render(markdown_content, output_path)
        result["elapsed_seconds"] = (datetime.now() - start).total_seconds()

        return result

    def render_academic(
        self,
        markdown_content: str,
        output_path: str,
        title: str,
        author: str,
        abstract: Optional[str] = None,
        institution: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Render markdown to academic PDF via XeLaTeX.

        Features:
        - AMS article class
        - Latin Modern fonts
        - Theorem environments (Vietnamese)
        - Math formulas
        - A4 size
        """
        metadata = DocumentMetadata(
            title=title,
            author=author,
            abstract=abstract,
            institution=institution,
            email=email,
            date=datetime.now().strftime("%d/%m/%Y")
        )

        renderer = AcademicRenderer(metadata)

        start = datetime.now()
        result = renderer.render(markdown_content, output_path)
        result["elapsed_seconds"] = (datetime.now() - start).total_seconds()

        return result

    def auto_detect_and_render(
        self,
        markdown_content: str,
        output_path: str,
        title: str,
        author: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Auto-detect document type and render appropriately.

        Detection rules:
        - Contains $$, $, \begin{equation} → Academic
        - Contains theorem/lemma/definition → Academic
        - Otherwise → Ebook
        """
        # Check for math/academic indicators
        academic_patterns = [
            r'\$\$.+?\$\$',           # Display math
            r'\$.+?\$',               # Inline math
            r'\\begin\{equation\}',   # LaTeX environments
            r'\\begin\{theorem\}',
            r'\\begin\{lemma\}',
            r'\\begin\{proof\}',
            r'Định lý',               # Vietnamese theorem
            r'Bổ đề',                 # Vietnamese lemma
            r'Chứng minh',            # Vietnamese proof
        ]

        is_academic = any(
            re.search(pattern, markdown_content, re.IGNORECASE)
            for pattern in academic_patterns
        )

        if is_academic:
            return self.render_academic(
                markdown_content,
                output_path,
                title=title,
                author=author,
                **kwargs
            )
        else:
            return self.render_ebook(
                markdown_content,
                output_path,
                title=title,
                author=author,
                **kwargs
            )


# =========================================
# CONVENIENCE FUNCTIONS
# =========================================

def render_ebook(
    markdown_content: str,
    output_path: str,
    title: str,
    author: str,
    subtitle: Optional[str] = None
) -> Dict[str, Any]:
    """Quick function to render ebook PDF."""
    agent = Agent3_PDFRenderer()
    return agent.render_ebook(
        markdown_content,
        output_path,
        title=title,
        author=author,
        subtitle=subtitle
    )


def render_academic(
    markdown_content: str,
    output_path: str,
    title: str,
    author: str,
    abstract: Optional[str] = None,
    institution: Optional[str] = None
) -> Dict[str, Any]:
    """Quick function to render academic PDF."""
    agent = Agent3_PDFRenderer()
    return agent.render_academic(
        markdown_content,
        output_path,
        title=title,
        author=author,
        abstract=abstract,
        institution=institution
    )


# =========================================
# CLI
# =========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agent 3: PDF Renderer")
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("-o", "--output", required=True, help="Output PDF path")
    parser.add_argument("-m", "--mode", choices=["ebook", "academic", "auto"],
                        default="auto", help="Render mode")
    parser.add_argument("-t", "--title", required=True, help="Document title")
    parser.add_argument("-a", "--author", required=True, help="Author name")
    parser.add_argument("--subtitle", help="Subtitle (ebook)")
    parser.add_argument("--abstract", help="Abstract (academic)")
    parser.add_argument("--institution", help="Institution (academic)")

    args = parser.parse_args()

    # Read input
    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    agent = Agent3_PDFRenderer()

    if args.mode == "ebook":
        result = agent.render_ebook(
            content, args.output,
            title=args.title,
            author=args.author,
            subtitle=args.subtitle
        )
    elif args.mode == "academic":
        result = agent.render_academic(
            content, args.output,
            title=args.title,
            author=args.author,
            abstract=args.abstract,
            institution=args.institution
        )
    else:  # auto
        result = agent.auto_detect_and_render(
            content, args.output,
            title=args.title,
            author=args.author,
            subtitle=args.subtitle,
            abstract=args.abstract,
            institution=args.institution
        )

    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    Agent 3: PDF Render Complete                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   Output:   {result['output_path']:<53} ║
║   Format:   {result['format']:<53} ║
║   Pages:    {result['pages']:<53} ║
║   Size:     {result['size_bytes']:,} bytes{' ' * (44 - len(f"{result['size_bytes']:,}"))}║
║   Time:     {result['elapsed_seconds']:.2f}s{' ' * 50}║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
