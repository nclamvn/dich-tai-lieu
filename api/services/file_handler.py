"""
File handling utilities for job outputs.

Extracted from api/routes/job_outputs.py — pure file I/O helpers,
path resolution, traversal protection.  No FastAPI or HTTP concerns.
"""
import re
from pathlib import Path
from typing import Optional

from config.logging_config import get_logger

logger = get_logger(__name__)

# Project root — computed once at module load
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


def resolve_output_path(output_file: str) -> Path:
    """Resolve a job's output_file string to an absolute Path.

    Handles both absolute and relative (to project root) paths.

    Args:
        output_file: Raw output_file value from the job record.

    Returns:
        Resolved absolute Path.
    """
    p = Path(output_file)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p.resolve()


def validate_project_path(file_path: str) -> Path:
    """Resolve *file_path* and ensure it stays inside PROJECT_ROOT.

    Args:
        file_path: Absolute or project-relative path string.

    Returns:
        Resolved absolute Path.

    Raises:
        ValueError: If resolved path escapes the project root.
    """
    p = Path(file_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p = p.resolve()

    if not str(p).startswith(str(PROJECT_ROOT)):
        raise ValueError("Access denied: path outside project directory")
    return p


_UNSAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(job_id: str, original_name: str, fmt: str) -> str:
    """Generate a download-safe filename.

    Args:
        job_id: Job identifier (used as fallback stem).
        original_name: Original filename (may contain unicode).
        fmt: Target format extension (without dot).

    Returns:
        Sanitised filename string.
    """
    stem = original_name or job_id
    stem = _UNSAFE_RE.sub("_", stem)
    # Collapse runs of underscores
    stem = re.sub(r"_+", "_", stem).strip("_")
    if not stem:
        stem = job_id
    return f"{stem}.{fmt}"


def generate_docx_preview(doc, detector, limit: int = 2000) -> dict:
    """Build a structured preview dict from a python-docx Document.

    Args:
        doc: A ``docx.Document`` instance (already opened).
        detector: A ``HeadingDetector`` instance.
        limit: Maximum word count before truncation.

    Returns:
        dict with keys: preview, total_words, preview_words,
        is_truncated, is_structured.
    """
    structured_preview = []
    word_count = 0
    is_truncated = False

    for para in doc.paragraphs:
        para_text = para.text.strip()
        if not para_text:
            continue

        para_words = len(para_text.split())

        if word_count + para_words > limit:
            is_truncated = True
            if word_count < limit:
                remaining = limit - word_count
                truncated_text = " ".join(para_text.split()[:remaining]) + "..."
                structured_preview.append({
                    "text": truncated_text,
                    "type": "paragraph",
                    "level": None,
                })
            break

        level = detector.detect_heading_level(para_text)
        if level:
            structured_preview.append({
                "text": para_text,
                "type": f"heading{level}",
                "level": level,
            })
        else:
            structured_preview.append({
                "text": para_text,
                "type": "paragraph",
                "level": None,
            })
        word_count += para_words

    total_words = sum(
        len(p.text.split()) for p in doc.paragraphs if p.text.strip()
    )

    return {
        "preview": structured_preview,
        "total_words": total_words,
        "preview_words": word_count,
        "is_truncated": is_truncated,
        "is_structured": True,
    }


def generate_text_preview(text: str, limit: int = 2000) -> dict:
    """Build a plain-text preview dict.

    Args:
        text: Full document text.
        limit: Maximum word count.

    Returns:
        dict with keys: preview, total_words, preview_words,
        is_truncated, is_structured.
    """
    words = text.split()
    total_words = len(words)
    preview_words = words[:limit]

    return {
        "preview": " ".join(preview_words),
        "total_words": total_words,
        "preview_words": len(preview_words),
        "is_truncated": total_words > limit,
        "is_structured": False,
    }
