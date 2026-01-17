# core/pdf_renderer_v2/renderer.py

"""
PDF Renderer V2 - Pandoc + WeasyPrint Pipeline

Pipeline: Markdown -> HTML (Pandoc) -> PDF (WeasyPrint)
Quality target: 95%+ (vs 40-70% with ReportLab)
"""

from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import tempfile
import logging

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class PDFRendererV2:
    """
    New PDF renderer using Pandoc + WeasyPrint pipeline.

    Usage:
        renderer = PDFRendererV2(template="classic-literature")
        renderer.render(markdown_content, "output.pdf", metadata={"title": "My Book"})
    """

    TEMPLATES = {
        # Literary - Book-style templates
        "classic-literature": "literary",
        "modern-novel": "literary",
        "poetry-collection": "literary",
        "children-book": "literary",
        "memoir-biography": "literary",
        "commercial-novel": "literary",  # NEW: Commercial ebook (Dan Brown style)
        # Professional
        "business-report": "professional",
        "technical-manual": "professional",
        "academic-paper": "professional",
        "legal-document": "professional",
        "newsletter": "professional",
        "presentation-handout": "professional",
        "minimal-clean": "professional",
        "claude-style": "professional",  # Claude-style clean rendering
    }

    def __init__(self, template: str = "minimal-clean"):
        """
        Initialize renderer with template.

        Args:
            template: Template name (e.g., "classic-literature", "minimal-clean")
        """
        self.template = template
        self.templates_dir = Path(__file__).parent / "templates"
        self._validate_template()
        self._setup_jinja()

    def _validate_template(self):
        """Validate template exists."""
        if self.template not in self.TEMPLATES:
            available = ", ".join(self.TEMPLATES.keys())
            raise ValueError(f"Unknown template: {self.template}. Available: {available}")

    def _setup_jinja(self):
        """Setup Jinja2 environment."""
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )

    def render(
        self,
        markdown_content: str,
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render Markdown to PDF.

        Args:
            markdown_content: Markdown string
            output_path: Output PDF path
            metadata: Optional dict with title, author, date, language

        Returns:
            Path to generated PDF
        """
        metadata = metadata or {}

        logger.info(f"Rendering PDF with template: {self.template}")

        # Step 1: MD -> HTML via Pandoc
        html_body = self._md_to_html(markdown_content)

        # Step 2: Apply Jinja2 template
        full_html = self._apply_template(html_body, metadata)

        # Step 3: HTML -> PDF via WeasyPrint
        self._html_to_pdf(full_html, output_path)

        logger.info(f"PDF generated: {output_path}")
        return output_path

    def _md_to_html(self, markdown: str) -> str:
        """Convert Markdown to HTML using Pandoc."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown)
            md_path = f.name

        try:
            result = subprocess.run(
                [
                    'pandoc',
                    md_path,
                    '-f', 'markdown+smart+pipe_tables+fenced_code_blocks+backtick_code_blocks+definition_lists+footnotes+strikeout+superscript+subscript',
                    '-t', 'html5',
                    '--wrap=none',
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Pandoc error: {e.stderr}")
            raise RuntimeError(f"Pandoc conversion failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("Pandoc not found. Please install: brew install pandoc (macOS) or apt-get install pandoc (Linux)")
        finally:
            Path(md_path).unlink(missing_ok=True)

    def _apply_template(self, html_body: str, metadata: dict) -> str:
        """Apply Jinja2 HTML template."""
        template = self.jinja_env.get_template("base.html")

        category = self.TEMPLATES[self.template]
        css_path = f"css/{category}/{self.template}.css"

        return template.render(
            content=html_body,
            title=metadata.get('title', 'Document'),
            subtitle=metadata.get('subtitle', ''),
            author=metadata.get('author', ''),
            date=metadata.get('date', ''),
            language=metadata.get('language', 'vi'),
            template_name=self.template,
            template_css=css_path,
            custom_css=metadata.get('custom_css', ''),
            # Front matter options (for book-style documents)
            include_title_page=metadata.get('include_title_page', False),
            include_copyright=metadata.get('include_copyright', False),
            publisher=metadata.get('publisher', ''),
            copyright_text=metadata.get('copyright_text', ''),
            isbn=metadata.get('isbn', ''),
        )

    def _html_to_pdf(self, html: str, output_path: str):
        """Convert HTML to PDF using WeasyPrint."""
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            raise RuntimeError("WeasyPrint not found. Please install: pip install weasyprint")

        # Base URL for resolving CSS paths
        base_url = str(self.templates_dir) + '/'

        # Get CSS files
        css_files = [
            CSS(filename=str(self.templates_dir / 'css' / 'base.css')),
            CSS(filename=str(self.templates_dir / 'css' / 'print.css')),
        ]

        # Add template-specific CSS
        category = self.TEMPLATES[self.template]
        template_css_path = self.templates_dir / 'css' / category / f'{self.template}.css'
        if template_css_path.exists():
            css_files.append(CSS(filename=str(template_css_path)))

        # Render PDF
        HTML(string=html, base_url=base_url).write_pdf(
            output_path,
            stylesheets=css_files
        )

    def preview_html(self, markdown_content: str, metadata: dict = None) -> str:
        """
        Generate HTML for browser preview (debugging).

        Returns:
            Full HTML string that can be saved and opened in browser
        """
        metadata = metadata or {}
        html_body = self._md_to_html(markdown_content)
        return self._apply_template(html_body, metadata)

    @classmethod
    def list_templates(cls) -> list:
        """List all available templates."""
        return list(cls.TEMPLATES.keys())
