"""
Batch Processing API Router

FastAPI endpoints for multi-file batch translation jobs.
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .aps_v2_service import get_v2_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/batch", tags=["Batch Processing"])


# ==================== MODELS ====================

class BatchFileResponse(BaseModel):
    """Single file in batch response"""
    file_id: str
    filename: str
    status: str
    progress: float
    job_id: Optional[str] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    """Batch job response"""
    batch_id: str
    status: str
    total_files: int
    completed_files: int
    failed_files: int
    overall_progress: float
    current_file: Optional[str] = None
    files: List[BatchFileResponse]
    source_language: str
    target_language: str
    profile_id: str
    output_formats: List[str]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    zip_available: bool = False


class BatchListResponse(BaseModel):
    """List of batches response"""
    batches: List[BatchResponse]
    total: int


# ==================== IN-MEMORY BATCH STORAGE ====================
# For production, this should use a database

from core_v2.batch_processor import BatchProcessor, BatchJob

_batch_processor: Optional[BatchProcessor] = None
_active_batches: dict = {}


def get_batch_processor() -> BatchProcessor:
    """Get or create batch processor"""
    global _batch_processor
    if _batch_processor is None:
        service = get_v2_service()
        # Ensure publisher is initialized
        service._ensure_publisher()
        _batch_processor = BatchProcessor(
            publisher=service._publisher,
            output_dir="outputs/batch",
            max_concurrent=2,
        )
    return _batch_processor


# ==================== ENDPOINTS ====================

@router.post(
    "/create",
    response_model=BatchResponse,
    summary="Create batch job with multiple files",
)
async def create_batch(
    files: List[UploadFile] = File(..., description="Multiple files to translate"),
    source_language: str = Form(default="en"),
    target_language: str = Form(default="vi"),
    profile_id: str = Form(default="novel"),
    output_formats: str = Form(default="docx"),  # Comma-separated
    use_vision: bool = Form(default=True),
):
    """
    Upload multiple files and create a batch translation job.

    **Limits:**
    - Maximum 10 files per batch
    - Maximum 50MB per file

    **Supported Formats:**
    - PDF (uses Claude Vision)
    - DOCX
    - TXT
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")

    service = get_v2_service()
    processor = get_batch_processor()

    # Save uploaded files
    saved_files = []
    for upload_file in files:
        try:
            content = await upload_file.read()
            if len(content) > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(
                    status_code=400,
                    detail=f"File {upload_file.filename} exceeds 50MB limit"
                )

            file_path = await service.save_upload(upload_file.filename, content)
            saved_files.append((upload_file.filename, str(file_path)))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save {upload_file.filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save {upload_file.filename}"
            )

    # Parse output formats
    formats = [f.strip() for f in output_formats.split(",") if f.strip()]
    if not formats:
        formats = ["docx"]

    # Create batch
    batch = processor.create_batch(
        files=saved_files,
        source_language=source_language,
        target_language=target_language,
        profile_id=profile_id,
        output_formats=formats,
        use_vision=use_vision,
    )

    logger.info(f"[Batch:{batch.batch_id}] Created with {len(saved_files)} files")

    return _batch_to_response(batch)


@router.post(
    "/{batch_id}/start",
    response_model=BatchResponse,
    summary="Start processing a batch",
)
async def start_batch(
    batch_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Start processing a pending batch job.

    Processing happens in the background. Use GET /batch/{batch_id}/status
    to monitor progress.
    """
    processor = get_batch_processor()
    batch = processor.get_batch(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    try:
        # Start batch processing in background
        batch = await processor.start_batch(batch_id)

        logger.info(f"[Batch:{batch_id}] Started processing")
        return _batch_to_response(batch)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[Batch:{batch_id}] Failed to start: {e}")
        raise HTTPException(status_code=500, detail="Failed to start batch")


@router.get(
    "/{batch_id}/status",
    response_model=BatchResponse,
    summary="Get batch status",
)
async def get_batch_status(batch_id: str):
    """
    Get current status and progress of a batch job.

    Poll this endpoint to monitor batch processing progress.
    """
    processor = get_batch_processor()
    batch = processor.get_batch(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    return _batch_to_response(batch)


@router.post(
    "/{batch_id}/cancel",
    response_model=BatchResponse,
    summary="Cancel a running batch",
)
async def cancel_batch(batch_id: str):
    """
    Cancel a running batch job.

    Files that have already completed will remain available.
    """
    processor = get_batch_processor()
    batch = processor.get_batch(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    if processor.cancel_batch(batch_id):
        logger.info(f"[Batch:{batch_id}] Cancelled")
        # Refresh batch status
        batch = processor.get_batch(batch_id)

    return _batch_to_response(batch)


@router.get(
    "/{batch_id}/download",
    response_class=FileResponse,
    summary="Download batch results as ZIP",
)
async def download_batch(batch_id: str):
    """
    Download all completed translations as a ZIP file.

    Only available after batch is complete or partially complete.
    """
    processor = get_batch_processor()
    batch = processor.get_batch(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    if not batch.zip_path or not batch.zip_path.exists():
        raise HTTPException(
            status_code=404,
            detail="ZIP file not available. Batch may still be processing."
        )

    return FileResponse(
        path=str(batch.zip_path),
        filename=f"batch_{batch_id}_translations.zip",
        media_type="application/zip",
    )


@router.get(
    "",
    response_model=BatchListResponse,
    summary="List all batches",
)
async def list_batches():
    """
    List all batch jobs (active and completed).
    """
    processor = get_batch_processor()
    batches = processor.list_batches()

    return BatchListResponse(
        batches=[BatchResponse(**b) for b in batches],
        total=len(batches),
    )


@router.delete(
    "/{batch_id}",
    summary="Delete a batch",
)
async def delete_batch(batch_id: str):
    """
    Delete a batch and its associated files.

    Cannot delete a batch that is currently processing.
    """
    processor = get_batch_processor()
    batch = processor.get_batch(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    if batch.status.value == "processing":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a batch that is processing. Cancel it first."
        )

    if processor.clear_batch(batch_id):
        logger.info(f"[Batch:{batch_id}] Deleted")
        return {"message": f"Batch {batch_id} deleted"}

    raise HTTPException(status_code=500, detail="Failed to delete batch")


# ==================== HELPERS ====================

def _batch_to_response(batch: BatchJob) -> BatchResponse:
    """Convert BatchJob to API response"""
    return BatchResponse(
        batch_id=batch.batch_id,
        status=batch.status.value,
        total_files=batch.total_files,
        completed_files=batch.completed_files,
        failed_files=batch.failed_files,
        overall_progress=batch.overall_progress,
        current_file=batch.current_file,
        files=[
            BatchFileResponse(
                file_id=f.file_id,
                filename=f.filename,
                status=f.status,
                progress=f.progress,
                job_id=f.job_id,
                error=f.error,
            )
            for f in batch.files
        ],
        source_language=batch.source_language,
        target_language=batch.target_language,
        profile_id=batch.profile_id,
        output_formats=batch.output_formats,
        created_at=batch.created_at.isoformat(),
        started_at=batch.started_at.isoformat() if batch.started_at else None,
        completed_at=batch.completed_at.isoformat() if batch.completed_at else None,
        zip_available=batch.zip_path is not None and batch.zip_path.exists(),
    )
