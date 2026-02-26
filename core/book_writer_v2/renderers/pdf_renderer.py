"""
PDF Renderer (Sprint K — TIP K5)

MVP approach: Renders DOCX via DocxIllustratedRenderer,
then converts to PDF via LibreOffice (soffice) subprocess.

Falls back to DOCX-only if soffice is not available.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..illustration_models import (
    BookGenre,
    IllustrationPlan,
    LayoutConfig,
)
from ..models import BookBlueprint

logger = logging.getLogger("BookWriter.PdfRenderer")


class PdfIllustratedRenderer:
    """
    PDF renderer for illustrated books.

    Strategy:
    1. Render DOCX using DocxIllustratedRenderer
    2. Convert DOCX → PDF via LibreOffice headless
    3. Return PDF path

    This ensures DOCX and PDF look identical.
    """

    def __init__(
        self,
        config: Optional[LayoutConfig] = None,
        genre: BookGenre = BookGenre.NON_FICTION,
    ):
        self.config = config or LayoutConfig.for_genre(genre)
        self.genre = genre

    def render(
        self,
        blueprint: BookBlueprint,
        plan: Optional[IllustrationPlan],
        image_dir: str,
        output_path: str,
    ) -> str:
        """
        Render illustrated book to PDF.

        Returns the output PDF path.
        Raises RuntimeError if conversion fails and no fallback is possible.
        """
        from .docx_renderer import DocxIllustratedRenderer

        output_path = str(output_path)
        pdf_dir = str(Path(output_path).parent)
        Path(pdf_dir).mkdir(parents=True, exist_ok=True)

        # Step 1: Render DOCX to a temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "book.docx")
            docx_renderer = DocxIllustratedRenderer(self.config, self.genre)
            docx_renderer.render(blueprint, plan, image_dir, docx_path)

            # Step 2: Convert DOCX → PDF
            pdf_result = self._convert_docx_to_pdf(docx_path, pdf_dir)

            if pdf_result and os.path.exists(pdf_result):
                # Move to desired output path
                if pdf_result != output_path:
                    shutil.move(pdf_result, output_path)
                logger.info(f"PDF rendered: {output_path}")
                return output_path

            # Step 3: Fallback — try docx2pdf library
            pdf_result = self._convert_via_docx2pdf(docx_path, output_path)
            if pdf_result:
                logger.info(f"PDF rendered via docx2pdf: {output_path}")
                return output_path

            # Step 4: If all conversion fails, copy DOCX as fallback
            fallback_docx = output_path.replace(".pdf", ".docx")
            shutil.copy2(docx_path, fallback_docx)
            logger.warning(
                f"PDF conversion failed. DOCX saved as fallback: {fallback_docx}"
            )
            return fallback_docx

    def _convert_docx_to_pdf(self, docx_path: str, output_dir: str) -> Optional[str]:
        """Convert DOCX to PDF using LibreOffice headless mode."""
        soffice = self._find_soffice()
        if not soffice:
            logger.info("LibreOffice (soffice) not found, skipping conversion")
            return None

        try:
            result = subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", output_dir,
                    docx_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                pdf_name = Path(docx_path).stem + ".pdf"
                pdf_path = os.path.join(output_dir, pdf_name)
                if os.path.exists(pdf_path):
                    return pdf_path

            logger.warning(
                f"soffice conversion failed (rc={result.returncode}): {result.stderr[:200]}"
            )
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.warning(f"soffice conversion error: {e}")
            return None

    def _convert_via_docx2pdf(self, docx_path: str, output_path: str) -> Optional[str]:
        """Try converting via docx2pdf library (macOS/Windows)."""
        try:
            from docx2pdf import convert
            convert(docx_path, output_path)
            if os.path.exists(output_path):
                return output_path
        except (Exception, SystemExit) as e:
            logger.info(f"docx2pdf not available or failed: {e}")
        return None

    @staticmethod
    def _find_soffice() -> Optional[str]:
        """Find LibreOffice soffice binary."""
        # Check PATH first
        soffice = shutil.which("soffice")
        if soffice:
            return soffice

        # Platform-specific paths
        candidates = [
            # macOS
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            # Linux
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            # Windows
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path

        return None

    @staticmethod
    def can_convert() -> bool:
        """Check if PDF conversion is available."""
        if shutil.which("soffice"):
            return True
        try:
            import docx2pdf  # noqa: F401
            return True
        except ImportError:
            pass
        return False
