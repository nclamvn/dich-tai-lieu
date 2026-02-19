"""
Job output endpoints — download, preview, PDF detection.

Thin routing layer; business logic lives in api/services/.
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from docx import Document as DocxDocument

from api.deps import queue
from core.job_queue import JobStatus
from core.batch_processor import read_document
from core.post_formatting.heading_detector import HeadingDetector
from api.services.converter import convert_document_format, get_media_type
from api.services.file_handler import (
    resolve_output_path, validate_project_path,
    generate_docx_preview, generate_text_preview,
)
from config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Job Outputs"])

ALLOWED_DOWNLOAD_FORMATS = {"docx", "pdf", "md", "txt", "html", "srt"}


@router.get("/api/jobs/{job_id}/download/{format}")
async def download_job_output(job_id: str, format: str):
    """Download translated output file with on-the-fly conversion."""
    if format not in ALLOWED_DOWNLOAD_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{format}'. Allowed: {', '.join(sorted(ALLOWED_DOWNLOAD_FORMATS))}"
        )

    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. Please check the job ID or view available jobs at /api/jobs"
        )

    if job.status != JobStatus.COMPLETED:
        status_messages = {
            "pending": "Job is queued and waiting to start",
            "running": "Job is currently being translated",
            "paused": "Job has been paused",
            "cancelled": "Job was cancelled before completion",
            "failed": "Job failed during translation"
        }
        status_msg = status_messages.get(job.status, job.status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot download: {status_msg}. Only completed jobs can be downloaded."
        )

    output_path = resolve_output_path(job.output_file)
    output_dir = output_path.parent
    base_name = output_path.stem

    # Check if requested format file already exists
    target_path = output_dir / f"{base_name}.{format}"

    if target_path.exists():
        output_path = target_path
    elif format != job.output_format and output_path.exists():
        try:
            converted_path = await convert_document_format(
                output_path, format, output_dir, base_name,
            )
            if converted_path and converted_path.exists():
                output_path = converted_path
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to convert to {format} format"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Conversion error: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Conversion to {format} failed: {str(e)}"
            )
    elif not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Output file not found. The translation may have failed or the file was deleted."
        )

    media_type = get_media_type(format)

    return FileResponse(
        path=str(output_path),
        media_type=media_type,
        filename=f"{base_name}.{format}"
    )


@router.get("/api/jobs/{job_id}/preview")
async def get_job_preview(job_id: str, limit: int = 2000):
    """Get preview of translated output with structured formatting."""
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot preview: Job status is '{job.status}'. Only completed jobs can be previewed."
        )

    output_path = resolve_output_path(job.output_file)

    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Output file not found: {output_path}"
        )

    try:
        file_extension = output_path.suffix.lower()

        if file_extension == '.docx':
            doc = DocxDocument(str(output_path))
            detector = HeadingDetector()
            result = generate_docx_preview(doc, detector, limit)
            result["format"] = job.output_format
            return result
        else:
            text = read_document(output_path)
            result = generate_text_preview(text, limit)
            result["format"] = job.output_format
            return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.post("/api/pdf/detect")
async def detect_pdf_type(file_path: str, request: Request = None):
    """Detect PDF type (native vs scanned) and recommend OCR mode."""
    from core.ocr import SmartDetector

    try:
        pdf_path = validate_project_path(file_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path outside project directory")

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF not found: {file_path}")

    if not pdf_path.suffix.lower() == '.pdf':
        raise HTTPException(status_code=400, detail=f"File is not a PDF: {file_path}")

    try:
        detector = SmartDetector()
        result = detector.detect_pdf_type(pdf_path)

        return {
            "pdf_type": result.pdf_type.value,
            "ocr_needed": result.ocr_needed,
            "confidence": result.confidence,
            "recommendation": result.recommendation.value,
            "details": result.details,
            "message": detector.recommend_ocr_mode(pdf_path, has_mathpix_key=bool(os.getenv('MATHPIX_APP_ID')))
        }

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Smart detection unavailable. Install OCR dependencies: pip install paddleocr paddlepaddle"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
