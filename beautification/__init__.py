#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Beautification Module

Provides 3-stage document beautification pipeline:
- Stage 1: Sanitization (remove garbage, normalize whitespace)
- Stage 2: Styling (apply professional styles, detect headings)
- Stage 3: Polishing (TOC, metadata, widow/orphan control)
"""

import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def beautify_docx(
    input_docx: str,
    output_docx: Optional[str] = None,
    title: str = "",
    author: str = "",
    enable: bool = True
) -> str:
    """
    Apply 3-stage beautification to DOCX file.

    Args:
        input_docx: Path to input DOCX file
        output_docx: Path to output DOCX file (optional, defaults to input path)
        title: Document title for metadata
        author: Document author for metadata
        enable: Enable beautification (default True)

    Returns:
        Path to beautified DOCX file

    Example:
        beautified = beautify_docx("translated.docx", title="Hoàng Tử Bé", author="Antoine")
    """
    if not enable:
        logger.debug("Beautification disabled, skipping")
        return input_docx

    try:
        from .stage1_sanitization import sanitize_docx
        from .stage2_styling import style_docx
        from .stage3_polishing import polish_docx

        # Use temp files for intermediate stages
        with tempfile.TemporaryDirectory() as tmpdir:
            stage1_output = Path(tmpdir) / "stage1.docx"
            stage2_output = Path(tmpdir) / "stage2.docx"

            # Stage 1: Sanitization
            logger.info(f"📝 Stage 1/3: Sanitizing {input_docx}")
            sanitize_docx(input_docx, str(stage1_output))

            # Stage 2: Styling
            logger.info(f"🎨 Stage 2/3: Applying professional styling")
            style_docx(str(stage1_output), str(stage2_output))

            # Stage 3: Polishing
            final_output = output_docx or input_docx
            logger.info(f"✨ Stage 3/3: Polishing and adding metadata")
            polish_docx(str(stage2_output), final_output, title=title, author=author)

            logger.info(f"✅ Beautification complete: {final_output}")
            return final_output

    except Exception as e:
        logger.warning(f"Beautification failed: {e}. Using original DOCX.")
        return input_docx


__all__ = ['beautify_docx']
