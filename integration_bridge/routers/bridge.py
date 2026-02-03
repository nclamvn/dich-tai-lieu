"""Main bridge API routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from ..models.schemas import (
    TranslationRequest,
    TranslationResponse,
    ExportRequest,
    ExportResponse,
    JobStatusResponse,
    JobStatus,
    JobType,
    BridgeJob
)
from ..services.translation_service import TranslationService
from ..services.export_service import ExportService
from ..services.job_store import job_store


router = APIRouter(prefix="/api/bridge", tags=["Bridge"])

# Service instances
translation_service = TranslationService()
export_service = ExportService()


@router.post("/translate", response_model=TranslationResponse)
async def translate_draft(request: TranslationRequest):
    """
    Translate a Companion Writer draft via AI Publisher Pro.

    This endpoint queues a translation job and returns immediately.
    Use the tracking_url to poll for status, or provide a callback_url
    to receive a webhook when complete.
    """
    return await translation_service.translate(request)


@router.post("/export", response_model=ExportResponse)
async def export_document(request: ExportRequest):
    """
    Export a document to multiple formats.

    Supports PDF, DOCX, EPUB, MD, TXT formats.
    Uses AI Publisher Pro for PDF/DOCX (better quality)
    and Companion Writer for EPUB.
    """
    return await export_service.export(request)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a bridge job.

    Returns current status, progress percentage, and result when complete.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Build status message
    status_messages = {
        JobStatus.PENDING: "Job is pending",
        JobStatus.QUEUED: "Job is queued for processing",
        JobStatus.EXTRACTING: "Extracting content...",
        JobStatus.TRANSLATING: "Translating content...",
        JobStatus.FORMATTING: "Formatting output...",
        JobStatus.EXPORTING: "Exporting files...",
        JobStatus.COMPLETED: "Job completed successfully",
        JobStatus.FAILED: f"Job failed: {job.error_message or 'Unknown error'}"
    }

    return JobStatusResponse(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        message=status_messages.get(job.status, "Processing..."),
        result=job.result,
        error=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum jobs to return")
):
    """
    List bridge jobs with optional filters.
    """
    jobs = job_store.list_jobs(job_type=job_type, status=status, limit=limit)

    return [
        JobStatusResponse(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            message=f"{job.status.value}",
            result=job.result,
            error=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at
        )
        for job in jobs
    ]


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a completed or failed job.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete job that is still processing"
        )

    job_store.delete_job(job_id)
    return {"message": "Job deleted successfully"}


@router.post("/jobs/cleanup")
async def cleanup_jobs(max_age_hours: int = Query(24, ge=1, le=168)):
    """
    Clean up old completed jobs.
    """
    deleted = job_store.cleanup_old_jobs(max_age_hours)
    return {"message": f"Deleted {deleted} old jobs"}
