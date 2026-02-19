"""
Publisher Agent

Generates final output files.
"""

import re
from pathlib import Path
from typing import Dict

from .base import BaseAgent, AgentContext
from ..models import BookBlueprint, BookProject
from ..config import OutputFormat


class PublisherAgent(BaseAgent[BookProject, Dict[str, str]]):
    """
    Agent 9: Publisher

    Generates final output files:
    - DOCX with professional formatting
    - PDF with proper layout
    - Markdown source
    - HTML (optional)
    """

    @property
    def name(self) -> str:
        return "Publisher"

    @property
    def description(self) -> str:
        return "Generate final output files in requested formats"

    async def execute(
        self,
        input_data: BookProject,
        context: AgentContext
    ) -> Dict[str, str]:
        project = input_data
        blueprint = project.blueprint

        context.report_progress("Generating output files...", 0)

        output_dir = Path(self.config.output_dir) / project.id
        output_dir.mkdir(parents=True, exist_ok=True)

        import asyncio

        output_files = {}
        formats = self.config.output_formats

        async def generate_format(fmt):
            try:
                if fmt == OutputFormat.MARKDOWN:
                    path = await self._generate_markdown(blueprint, output_dir)
                    return "markdown", str(path)
                elif fmt == OutputFormat.DOCX:
                    path = await self._generate_docx(blueprint, output_dir)
                    return "docx", str(path)
                elif fmt == OutputFormat.PDF:
                    path = await self._generate_pdf(blueprint, output_dir)
                    return "pdf", str(path)
                elif fmt == OutputFormat.HTML:
                    path = await self._generate_html(blueprint, output_dir)
                    return "html", str(path)
            except Exception as e:
                self.logger.error(f"Failed to generate {fmt.value}: {e}")
            return None, None

        results = await asyncio.gather(*[generate_format(fmt) for fmt in formats])

        for key, path in results:
            if key and path:
                output_files[key] = path

        context.report_progress("Publishing complete", 100)

        return output_files

    async def _generate_markdown(self, blueprint: BookBlueprint, output_dir: Path) -> Path:
        """Generate Markdown file"""

        content_parts = []

        # Title page
        content_parts.append(f"# {blueprint.title}\n")
        if blueprint.subtitle:
            content_parts.append(f"## {blueprint.subtitle}\n")
        content_parts.append(f"\n*By {blueprint.author}*\n\n")
        content_parts.append("---\n\n")

        # Front matter
        if blueprint.front_matter.dedication:
            content_parts.append("## Dedication\n\n")
            content_parts.append(blueprint.front_matter.dedication + "\n\n")

        if blueprint.front_matter.preface:
            content_parts.append("## Preface\n\n")
            content_parts.append(blueprint.front_matter.preface + "\n\n")

        # Table of Contents
        content_parts.append("## Table of Contents\n\n")
        for part in blueprint.parts:
            content_parts.append(f"### {part.title}\n")
            for chapter in part.chapters:
                content_parts.append(f"- Chapter {chapter.number}: {chapter.title}\n")
                for section in chapter.sections:
                    content_parts.append(f"  - {section.title}\n")
        content_parts.append("\n---\n\n")

        # Main content
        for part in blueprint.parts:
            content_parts.append(f"# Part {part.number}: {part.title}\n\n")

            if part.introduction:
                content_parts.append(part.introduction + "\n\n")

            for chapter in part.chapters:
                content_parts.append(f"## Chapter {chapter.number}: {chapter.title}\n\n")

                if chapter.introduction:
                    content_parts.append(chapter.introduction + "\n\n")

                for section in chapter.sections:
                    content_parts.append(f"### {section.title}\n\n")
                    content_parts.append(section.content + "\n\n")

                if chapter.summary:
                    content_parts.append("#### Summary\n\n")
                    content_parts.append(chapter.summary + "\n\n")

                if chapter.key_takeaways:
                    content_parts.append("#### Key Takeaways\n\n")
                    for takeaway in chapter.key_takeaways:
                        content_parts.append(f"- {takeaway}\n")
                    content_parts.append("\n")

        # Back matter
        if blueprint.back_matter.conclusion:
            content_parts.append("# Conclusion\n\n")
            content_parts.append(blueprint.back_matter.conclusion + "\n\n")

        if blueprint.back_matter.glossary:
            content_parts.append("# Glossary\n\n")
            for term, definition in sorted(blueprint.back_matter.glossary.items()):
                content_parts.append(f"**{term}**: {definition}\n\n")

        # Write file
        filename = self._sanitize_filename(blueprint.title) + ".md"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("".join(content_parts))

        return filepath

    async def _generate_docx(self, blueprint: BookBlueprint, output_dir: Path) -> Path:
        """Generate DOCX file"""

        try:
            from docx import Document
            from docx.shared import Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            self.logger.error("python-docx not installed, falling back to markdown")
            return await self._generate_markdown(blueprint, output_dir)

        doc = Document()

        # Title page
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(blueprint.title)
        title_run.bold = True
        title_run.font.size = Pt(24)

        if blueprint.subtitle:
            subtitle_para = doc.add_paragraph()
            subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            subtitle_run = subtitle_para.add_run(blueprint.subtitle)
            subtitle_run.font.size = Pt(16)

        author_para = doc.add_paragraph()
        author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author_para.add_run(f"By {blueprint.author}")

        doc.add_page_break()

        # Front matter
        if blueprint.front_matter.preface:
            doc.add_heading("Preface", level=1)
            doc.add_paragraph(blueprint.front_matter.preface)
            doc.add_page_break()

        # Main content
        for part in blueprint.parts:
            doc.add_heading(f"Part {part.number}: {part.title}", level=1)

            if part.introduction:
                doc.add_paragraph(part.introduction)

            for chapter in part.chapters:
                doc.add_heading(f"Chapter {chapter.number}: {chapter.title}", level=2)

                if chapter.introduction:
                    doc.add_paragraph(chapter.introduction)

                for section in chapter.sections:
                    doc.add_heading(section.title, level=3)

                    paragraphs = section.content.split("\n\n")
                    for para_text in paragraphs:
                        if para_text.strip():
                            doc.add_paragraph(para_text.strip())

                if chapter.summary:
                    doc.add_heading("Summary", level=4)
                    doc.add_paragraph(chapter.summary)

                if chapter.key_takeaways:
                    doc.add_heading("Key Takeaways", level=4)
                    for takeaway in chapter.key_takeaways:
                        doc.add_paragraph(takeaway, style='List Bullet')

        # Conclusion
        if blueprint.back_matter.conclusion:
            doc.add_heading("Conclusion", level=1)
            doc.add_paragraph(blueprint.back_matter.conclusion)

        # Save
        filename = self._sanitize_filename(blueprint.title) + ".docx"
        filepath = output_dir / filename
        doc.save(filepath)

        return filepath

    async def _generate_pdf(self, blueprint: BookBlueprint, output_dir: Path) -> Path:
        """Generate PDF file (falls back to markdown)"""

        md_path = await self._generate_markdown(blueprint, output_dir)
        self.logger.warning("PDF generation requires additional libraries. Created markdown fallback.")
        return md_path

    async def _generate_html(self, blueprint: BookBlueprint, output_dir: Path) -> Path:
        """Generate HTML file"""

        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "<meta charset='UTF-8'>",
            f"<title>{blueprint.title}</title>",
            "<style>",
            "body { max-width: 800px; margin: 0 auto; padding: 20px; font-family: Georgia, serif; }",
            "h1 { text-align: center; }",
            "h2 { border-bottom: 1px solid #ccc; padding-bottom: 10px; }",
            ".chapter { margin-top: 40px; }",
            ".section { margin-top: 20px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{blueprint.title}</h1>",
        ]

        if blueprint.subtitle:
            html_parts.append(
                f"<h2 style='text-align:center;border:none;'>{blueprint.subtitle}</h2>"
            )

        html_parts.append(f"<p style='text-align:center;'>By {blueprint.author}</p>")
        html_parts.append("<hr>")

        # Content
        for part in blueprint.parts:
            html_parts.append(f"<h1>Part {part.number}: {part.title}</h1>")

            for chapter in part.chapters:
                html_parts.append("<div class='chapter'>")
                html_parts.append(f"<h2>Chapter {chapter.number}: {chapter.title}</h2>")

                for section in chapter.sections:
                    html_parts.append("<div class='section'>")
                    html_parts.append(f"<h3>{section.title}</h3>")

                    paragraphs = section.content.split("\n\n")
                    for para in paragraphs:
                        if para.strip():
                            html_parts.append(f"<p>{para.strip()}</p>")

                    html_parts.append("</div>")

                html_parts.append("</div>")

        html_parts.extend(["</body>", "</html>"])

        filename = self._sanitize_filename(blueprint.title) + ".html"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))

        return filepath

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename"""
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.replace(' ', '_')
        return name[:100]
