#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MOBI/Kindle Exporter

Exports translated documents to MOBI format for Kindle devices.
Uses EPUB as intermediate format, then converts with Calibre's ebook-convert.

Requirements:
    - calibre: Install with `brew install calibre` (macOS) or system package manager
    - Alternative: Amazon's kindlegen (deprecated but still works)
"""

import os
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MobiMetadata:
    """Metadata for MOBI ebook."""
    title: str = "Untitled"
    author: str = "AI Publisher Pro"
    language: str = "vi"
    publisher: str = "AI Publisher Pro"
    description: str = ""
    subject: str = ""
    isbn: str = ""
    cover_image: Optional[Path] = None

    # Kindle-specific
    asin: str = ""  # Amazon Standard Identification Number

    # Advanced options
    toc_title: str = "Mục Lục"
    enable_heuristics: bool = True
    output_profile: str = "kindle"  # kindle, kindle_dx, kindle_fire, kindle_oasis


@dataclass
class MobiExportConfig:
    """Configuration for MOBI export."""
    metadata: MobiMetadata = field(default_factory=MobiMetadata)

    # Output options
    compress: bool = True
    embed_fonts: bool = False  # Kindles have their own fonts
    linearize: bool = True  # For better Kindle rendering

    # Format options
    mobi_file_type: str = "both"  # "old" (MOBI 6), "new" (KF8), or "both"
    personal_doc: bool = False  # Add [PDOC] tag for personal documents

    # Chapter detection
    chapter_mark: str = "pagebreak"  # pagebreak, rule, both, none
    page_breaks_before: str = "//*[name()='h1' or name()='h2']"  # XPath

    # Cleanup
    remove_paragraph_spacing: bool = False
    remove_first_image: bool = False  # Sometimes cover is duplicated


class MobiExporter:
    """
    Exports documents to MOBI format.

    Workflow:
    1. Generate EPUB from content
    2. Convert EPUB to MOBI using ebook-convert (Calibre)
    """

    def __init__(self):
        """Initialize exporter."""
        self._calibre_path = self._find_calibre()
        self._kindlegen_path = self._find_kindlegen()

    def _find_calibre(self) -> Optional[Path]:
        """Find Calibre's ebook-convert tool."""
        # Check common locations
        paths = [
            "/Applications/calibre.app/Contents/MacOS/ebook-convert",  # macOS
            "/usr/bin/ebook-convert",  # Linux
            "C:\\Program Files\\Calibre2\\ebook-convert.exe",  # Windows
            "C:\\Program Files (x86)\\Calibre2\\ebook-convert.exe",
        ]

        for path in paths:
            if os.path.isfile(path):
                return Path(path)

        # Try PATH
        result = shutil.which("ebook-convert")
        if result:
            return Path(result)

        return None

    def _find_kindlegen(self) -> Optional[Path]:
        """Find Amazon's kindlegen tool (fallback)."""
        paths = [
            "/usr/local/bin/kindlegen",
            os.path.expanduser("~/bin/kindlegen"),
        ]

        for path in paths:
            if os.path.isfile(path):
                return Path(path)

        result = shutil.which("kindlegen")
        if result:
            return Path(result)

        return None

    def is_available(self) -> bool:
        """Check if MOBI export is available."""
        return self._calibre_path is not None or self._kindlegen_path is not None

    def get_converter_info(self) -> Dict[str, Any]:
        """Get information about available converters."""
        return {
            "calibre_available": self._calibre_path is not None,
            "calibre_path": str(self._calibre_path) if self._calibre_path else None,
            "kindlegen_available": self._kindlegen_path is not None,
            "kindlegen_path": str(self._kindlegen_path) if self._kindlegen_path else None,
            "preferred": "calibre" if self._calibre_path else ("kindlegen" if self._kindlegen_path else None),
        }

    def export_from_epub(
        self,
        epub_path: Path,
        output_path: Path,
        config: Optional[MobiExportConfig] = None
    ) -> Path:
        """
        Convert EPUB to MOBI.

        Args:
            epub_path: Path to source EPUB file
            output_path: Path for output MOBI file
            config: Export configuration

        Returns:
            Path to generated MOBI file

        Raises:
            RuntimeError: If conversion fails
            FileNotFoundError: If no converter is available
        """
        if not self.is_available():
            raise FileNotFoundError(
                "No MOBI converter found. Please install Calibre: "
                "brew install calibre (macOS) or apt install calibre (Linux)"
            )

        config = config or MobiExportConfig()

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prefer Calibre for better results
        if self._calibre_path:
            return self._convert_with_calibre(epub_path, output_path, config)
        else:
            return self._convert_with_kindlegen(epub_path, output_path, config)

    def _convert_with_calibre(
        self,
        epub_path: Path,
        output_path: Path,
        config: MobiExportConfig
    ) -> Path:
        """Convert using Calibre's ebook-convert."""
        cmd = [
            str(self._calibre_path),
            str(epub_path),
            str(output_path),
        ]

        # Add metadata
        meta = config.metadata
        if meta.title:
            cmd.extend(["--title", meta.title])
        if meta.author:
            cmd.extend(["--authors", meta.author])
        if meta.language:
            cmd.extend(["--language", meta.language])
        if meta.publisher:
            cmd.extend(["--publisher", meta.publisher])
        if meta.description:
            cmd.extend(["--comments", meta.description])
        if meta.cover_image and meta.cover_image.exists():
            cmd.extend(["--cover", str(meta.cover_image)])

        # Output profile
        cmd.extend(["--output-profile", meta.output_profile])

        # MOBI-specific options
        cmd.extend(["--mobi-file-type", config.mobi_file_type])

        if config.personal_doc:
            cmd.append("--personal-doc")

        # Chapter handling
        cmd.extend(["--chapter-mark", config.chapter_mark])
        if config.page_breaks_before:
            cmd.extend(["--page-breaks-before", config.page_breaks_before])

        # Heuristics for better formatting
        if meta.enable_heuristics:
            cmd.append("--enable-heuristics")

        # Run conversion
        logger.info(f"Converting to MOBI: {epub_path} -> {output_path}")
        logger.debug(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"Calibre error: {result.stderr}")
                raise RuntimeError(f"MOBI conversion failed: {result.stderr}")

            logger.info(f"MOBI created: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            raise RuntimeError("MOBI conversion timed out")

    def _convert_with_kindlegen(
        self,
        epub_path: Path,
        output_path: Path,
        config: MobiExportConfig
    ) -> Path:
        """Convert using Amazon's kindlegen (fallback)."""
        # Kindlegen outputs to same directory as input
        temp_dir = tempfile.mkdtemp()
        temp_epub = Path(temp_dir) / "input.epub"
        shutil.copy(epub_path, temp_epub)

        cmd = [
            str(self._kindlegen_path),
            str(temp_epub),
            "-c1" if config.compress else "-c0",
            "-verbose",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Kindlegen returns 1 for warnings, 2 for errors
            if result.returncode > 1:
                logger.error(f"Kindlegen error: {result.stderr}")
                raise RuntimeError(f"MOBI conversion failed: {result.stderr}")

            # Move output to desired location
            temp_mobi = temp_epub.with_suffix(".mobi")
            if temp_mobi.exists():
                shutil.move(str(temp_mobi), str(output_path))
                logger.info(f"MOBI created: {output_path}")
                return output_path
            else:
                raise RuntimeError("Kindlegen did not produce output file")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def export_from_html(
        self,
        html_content: str,
        output_path: Path,
        config: Optional[MobiExportConfig] = None
    ) -> Path:
        """
        Export HTML content to MOBI.

        Creates an intermediate EPUB, then converts to MOBI.
        """
        from .epub_exporter import EpubExporter

        config = config or MobiExportConfig()

        # Create temporary EPUB
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            temp_epub = Path(tmp.name)

        try:
            # Generate EPUB
            epub_exporter = EpubExporter()
            epub_exporter.export_from_html(
                html_content,
                temp_epub,
                title=config.metadata.title,
                author=config.metadata.author,
                language=config.metadata.language,
            )

            # Convert to MOBI
            return self.export_from_epub(temp_epub, output_path, config)

        finally:
            # Cleanup temp file
            if temp_epub.exists():
                temp_epub.unlink()

    def export_from_docx(
        self,
        docx_path: Path,
        output_path: Path,
        config: Optional[MobiExportConfig] = None
    ) -> Path:
        """
        Export DOCX to MOBI.

        Uses Calibre to convert directly if available.
        """
        if not self._calibre_path:
            raise FileNotFoundError("DOCX to MOBI conversion requires Calibre")

        config = config or MobiExportConfig()

        cmd = [
            str(self._calibre_path),
            str(docx_path),
            str(output_path),
        ]

        # Add same options as EPUB conversion
        meta = config.metadata
        if meta.title:
            cmd.extend(["--title", meta.title])
        if meta.author:
            cmd.extend(["--authors", meta.author])
        if meta.language:
            cmd.extend(["--language", meta.language])
        if meta.cover_image and meta.cover_image.exists():
            cmd.extend(["--cover", str(meta.cover_image)])

        cmd.extend(["--output-profile", meta.output_profile])
        cmd.extend(["--mobi-file-type", config.mobi_file_type])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise RuntimeError(f"Conversion failed: {result.stderr}")

        return output_path


# Convenience function
def export_to_mobi(
    input_path: Path,
    output_path: Optional[Path] = None,
    title: str = "Untitled",
    author: str = "AI Publisher Pro",
    **kwargs
) -> Path:
    """
    Export a document to MOBI format.

    Args:
        input_path: Path to input file (EPUB, DOCX, or HTML)
        output_path: Path for output MOBI (optional, defaults to input path with .mobi)
        title: Book title
        author: Book author
        **kwargs: Additional metadata

    Returns:
        Path to generated MOBI file
    """
    exporter = MobiExporter()

    if output_path is None:
        output_path = input_path.with_suffix(".mobi")

    config = MobiExportConfig(
        metadata=MobiMetadata(
            title=title,
            author=author,
            **kwargs
        )
    )

    suffix = input_path.suffix.lower()

    if suffix == ".epub":
        return exporter.export_from_epub(input_path, output_path, config)
    elif suffix == ".docx":
        return exporter.export_from_docx(input_path, output_path, config)
    elif suffix in [".html", ".htm"]:
        content = input_path.read_text(encoding="utf-8")
        return exporter.export_from_html(content, output_path, config)
    else:
        raise ValueError(f"Unsupported input format: {suffix}")
