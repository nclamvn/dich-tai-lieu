#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Incremental PDF Builder - Phase 5.4

Build PDF documents incrementally to reduce memory usage.
Instead of building entire PDF in RAM, write batches to temp files.
"""

from pathlib import Path
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from pypdf import PdfWriter

from config.logging_config import get_logger
logger = get_logger(__name__)

from core.validator import TranslationResult
from .base_builder import BaseIncrementalBuilder


class IncrementalPdfBuilder(BaseIncrementalBuilder):
    """
    Build PDF incrementally in batches

    Instead of:
      - Load ALL results in memory → Build PDF → Save
      - Peak memory: ~1.5GB for large doc

    Do:
      - Build batch 1 PDF → Save to temp
      - Build batch 2 PDF → Save to temp
      - ...
      - Merge all temp PDFs → Final output
      - Peak memory: ~150MB (10x reduction)

    Usage:
        builder = IncrementalPdfBuilder(output_path)

        # Add batches
        for batch in batches:
            temp_file = await builder.add_batch(batch, batch_idx)

        # Merge all batches
        final_file = await builder.merge_all()
    """

    def get_format(self) -> str:
        """Get format identifier"""
        return 'pdf'

    def _verify_pdf(self, file_path: Path) -> None:
        """
        Verify PDF file is valid and readable

        Args:
            file_path: Path to PDF file to verify

        Raises:
            RuntimeError: If PDF is corrupted or unreadable
        """
        try:
            from pypdf import PdfReader

            # Try to open the PDF
            reader = PdfReader(file_path)

            # Verify it has pages
            if len(reader.pages) == 0:
                raise RuntimeError(f"PDF has no pages: {file_path}")

            # Try to extract text from first page to verify readability
            try:
                first_page = reader.pages[0]
                _ = first_page.extract_text()
            except Exception as e:
                raise RuntimeError(f"Cannot read PDF pages: {file_path}: {e}")

        except Exception as e:
            if "corrupted" in str(e).lower() or "invalid" in str(e).lower() or "EOF" in str(e):
                raise RuntimeError(f"PDF file is corrupted: {file_path}: {e}")
            raise RuntimeError(f"Failed to verify PDF: {file_path}: {e}")

    async def add_batch(
        self,
        batch_results: List[TranslationResult],
        batch_idx: int
    ) -> Path:
        """
        Add a batch and save to temp PDF file with comprehensive error handling

        Args:
            batch_results: Translation results for this batch
            batch_idx: Batch index (0-based)

        Returns:
            Path to temp batch PDF file

        Raises:
            RuntimeError: If PDF creation fails
        """
        batch_file = self.temp_dir / f"batch_{batch_idx:04d}.pdf"

        try:
            # Create PDF document for this batch
            doc = SimpleDocTemplate(
                str(batch_file),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )

            # Build story (content)
            story = []
            styles = getSampleStyleSheet()
            style_normal = styles['Normal']

            for result in batch_results:
                try:
                    # Add translated text as paragraph
                    para = Paragraph(result.translated, style_normal)
                    story.append(para)
                    story.append(Spacer(1, 0.2 * inch))
                except Exception as e:
                    logger.warning(f"Failed to add chunk {result.chunk_id} to PDF: {e}")
                    # Add error placeholder
                    error_para = Paragraph(f"[Error: chunk {result.chunk_id} failed]", style_normal)
                    story.append(error_para)
                    continue

            # Build PDF
            doc.build(story)

            # Verify file was created
            if not batch_file.exists():
                raise RuntimeError(f"PDF batch file not created: {batch_file}")

            if batch_file.stat().st_size == 0:
                raise RuntimeError(f"PDF batch file is empty: {batch_file}")

            # Deep verification - check PDF is valid
            self._verify_pdf(batch_file)

            self.batch_files.append(batch_file)
            return batch_file

        except PermissionError as e:
            raise RuntimeError(f"Permission denied writing to {batch_file}: {e}")
        except OSError as e:
            if "No space left" in str(e):
                raise RuntimeError(f"Disk full, cannot create {batch_file}: {e}")
            raise RuntimeError(f"OS error creating PDF batch: {e}")
        except Exception as e:
            # Cleanup partial file
            if batch_file.exists():
                try:
                    batch_file.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"Failed to create PDF batch {batch_idx}: {e}")

    async def merge_all(self) -> Path:
        """
        Merge all batch PDF files into final output with error handling

        Returns:
            Path to final merged PDF

        Raises:
            RuntimeError: If merge fails
        """
        if not self.batch_files:
            raise ValueError("No batch files to merge")

        logger.info(f"Merging {len(self.batch_files)} PDF batches...")

        writer = None
        try:
            # Create PDF writer
            writer = PdfWriter()

            # Merge each batch
            for batch_idx, batch_file in enumerate(self.batch_files):
                if not batch_file.exists():
                    raise RuntimeError(f"Batch file missing: {batch_file}")

                try:
                    writer.append(str(batch_file))
                    logger.debug(f"Batch {batch_idx + 1}/{len(self.batch_files)} merged")
                except Exception as e:
                    raise RuntimeError(f"Failed to merge batch {batch_idx}: {e}")

            # Save final document
            with open(self.output_path, 'wb') as f:
                writer.write(f)

            # Verify output exists
            if not self.output_path.exists():
                raise RuntimeError("Final PDF not created")

            file_size = self.output_path.stat().st_size
            if file_size == 0:
                raise RuntimeError("Final PDF is empty")

            # Deep verification - check final PDF is valid and readable
            self._verify_pdf(self.output_path)

            logger.info(f"Final PDF saved: {self.output_path} ({file_size / 1024 / 1024:.1f} MB)")

            # Cleanup temp files
            await self.cleanup()

            return self.output_path

        except Exception as e:
            # Ensure cleanup even on error
            try:
                await self.cleanup()
            except Exception:
                pass
            raise
        finally:
            if writer:
                writer.close()
