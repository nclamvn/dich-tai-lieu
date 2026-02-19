"""
Job CRUD, progress, and cancel endpoints.
"""

import time
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request

from api.deps import queue, manager, get_processor, chunk_cache
from api.models import (
    JobCreate, JobUpdate, JobResponse, JobProgressResponse, ProgressStep
)
from core.job_queue import JobStatus
from config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Jobs"])


@router.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all jobs with optional filtering

    - **status**: Filter by job status (pending/queued/running/completed/failed)
    - **limit**: Maximum number of jobs to return (default: 50)
    - **offset**: Number of jobs to skip (default: 0)
    """
    jobs = queue.list_jobs(status=status, limit=limit, offset=offset)

    return [
        JobResponse(
            job_id=job.job_id,
            job_name=job.job_name,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            source_lang=job.source_lang,
            target_lang=job.target_lang,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            quality_score=job.avg_quality_score,
            total_cost_usd=job.total_cost_usd,
            error_message=job.error_message
        )
        for job in jobs
    ]


@router.post("/api/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    request: Request,
    job_data: JobCreate,
    background_tasks: BackgroundTasks
):
    """
    Create a new translation job

    The job will be added to the queue and processed automatically
    when the batch processor is running.

    UI v1.1: Supports ui_layout_mode, output_formats, and advanced_options.
    """
    limiter = request.app.state.limiter

    # Validate input file exists
    input_path = Path(job_data.input_file)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found: {job_data.input_file}")

    # UI v1.1: Map UI parameters to backend parameters
    layout_mode = job_data.layout_mode
    equation_rendering_mode = job_data.equation_rendering_mode
    use_ast_pipeline = False
    chunk_size = job_data.chunk_size
    concurrency = job_data.concurrency
    cache_enabled = True
    quality_validation = job_data.enable_quality_check
    enable_book_layout = False

    # UI v1.1: Handle ui_layout_mode mapping
    if job_data.ui_layout_mode:
        if job_data.ui_layout_mode == "basic":
            layout_mode = "simple"
            use_ast_pipeline = False
            equation_rendering_mode = "latex_text"
        elif job_data.ui_layout_mode == "professional":
            layout_mode = "simple"
            use_ast_pipeline = True
            equation_rendering_mode = "latex_text"
        elif job_data.ui_layout_mode == "academic":
            layout_mode = "academic"
            use_ast_pipeline = True
            equation_rendering_mode = "omml"
        logger.debug(f"UI v1.1 Layout mode mapping: {job_data.ui_layout_mode} -> layout_mode={layout_mode}, use_ast_pipeline={use_ast_pipeline}, equation_rendering_mode={equation_rendering_mode}")

    # UI v1.1: Handle advanced_options
    if job_data.advanced_options:
        chunk_size = job_data.advanced_options.get('chunk_size', chunk_size)
        concurrency = job_data.advanced_options.get('concurrency', concurrency)
        cache_enabled = job_data.advanced_options.get('cache_enabled', cache_enabled)
        quality_validation = job_data.advanced_options.get('quality_validation', quality_validation)
        enable_book_layout = job_data.advanced_options.get('enable_book_layout', enable_book_layout)
        logger.debug(f"UI v1.1 Advanced options: chunk_size={chunk_size}, concurrency={concurrency}, cache_enabled={cache_enabled}, quality_validation={quality_validation}, enable_book_layout={enable_book_layout}")

    # UI v1.1: Handle output_formats
    output_formats_requested = job_data.output_formats if job_data.output_formats else [job_data.output_format]
    logger.debug(f"UI v1.1 Output formats requested: {output_formats_requested}")

    # Create job metadata
    metadata_dict = {
        'input_type': job_data.input_type,
        'output_mode': job_data.output_mode,
        'enable_ocr': job_data.enable_ocr,
        'ocr_mode': job_data.ocr_mode,
        'mathpix_app_id': job_data.mathpix_app_id,
        'mathpix_app_key': job_data.mathpix_app_key,
        'enable_quality_check': quality_validation,
        'enable_chemical_formulas': job_data.enable_chemical_formulas,
        'academic_mode': (job_data.domain == 'stem'),
        'layout_mode': layout_mode,
        'equation_rendering_mode': equation_rendering_mode,
        'use_ast_pipeline': use_ast_pipeline,
        'cache_enabled': cache_enabled,
        'enable_book_layout': enable_book_layout,
        'output_formats_requested': output_formats_requested,
        'ui_layout_mode': job_data.ui_layout_mode,
        'cover_image': job_data.cover_image,
        'include_images': job_data.include_images,
        'use_vision': job_data.use_vision,
        'api_key': job_data.api_key,
    }
    logger.debug(f"Creating job with metadata: {metadata_dict}")

    job = queue.create_job(
        job_name=job_data.job_name,
        input_file=job_data.input_file,
        output_file=job_data.output_file,
        source_lang=job_data.source_lang,
        target_lang=job_data.target_lang,
        priority=job_data.priority,
        provider=job_data.provider,
        model=job_data.model,
        domain=job_data.domain,
        glossary=job_data.glossary,
        concurrency=concurrency,
        chunk_size=chunk_size,
        input_format=input_path.suffix[1:] if input_path.suffix else 'txt',
        output_format=output_formats_requested[0] if output_formats_requested else job_data.output_format,
        metadata=metadata_dict
    )
    logger.debug(f"Job created, returned metadata: {job.metadata}")

    # Broadcast new job event
    await manager.broadcast({
        "event": "job_created",
        "job_id": job.job_id,
        "job_name": job.job_name
    })

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        quality_score=job.avg_quality_score,
        total_cost_usd=job.total_cost_usd,
        error_message=job.error_message,
        metadata=job.metadata
    )


@router.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get detailed information about a specific job

    - **job_id**: Job ID to retrieve
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        quality_score=job.avg_quality_score,
        total_cost_usd=job.total_cost_usd,
        error_message=job.error_message,
        metadata=job.metadata
    )


@router.get("/api/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(job_id: str):
    """
    Get detailed step-by-step progress for a job (UI v1.1)

    Returns:
        Detailed progress breakdown with current step, individual step statuses,
        time elapsed, estimated remaining, and progress percentage.
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Define processing steps based on job configuration
    metadata = job.metadata or {}
    enable_ocr = metadata.get('enable_ocr', False)
    output_formats = metadata.get('output_formats_requested', [job.output_format])
    equation_rendering = metadata.get('equation_rendering_mode', 'latex_text')

    # Build step list dynamically
    all_steps = []

    # Step 1: Upload/Validation (always)
    all_steps.append({
        'name': 'upload',
        'display_name': 'Tải file và xác thực'
    })

    # Step 2: OCR (if enabled)
    if enable_ocr:
        all_steps.append({
            'name': 'ocr',
            'display_name': 'Trích xuất văn bản OCR'
        })

    # Step 3: Translation (always)
    all_steps.append({
        'name': 'translation',
        'display_name': 'Dịch nội dung'
    })

    # Step 4: DOCX rendering (always)
    all_steps.append({
        'name': 'docx_render',
        'display_name': 'Render DOCX với typography'
    })

    # Step 5: OMML equations (if academic mode)
    if equation_rendering == 'omml':
        all_steps.append({
            'name': 'omml_equations',
            'display_name': 'Render phương trình OMML'
        })

    # Step 6: PDF export (if requested)
    if 'pdf' in output_formats:
        all_steps.append({
            'name': 'pdf_export',
            'display_name': 'Xuất PDF'
        })

    total_steps = len(all_steps)

    # Determine current step based on job status and progress
    if job.status == JobStatus.PENDING or job.status == JobStatus.QUEUED:
        current_step_idx = 0
        step_statuses = ['pending'] * total_steps
    elif job.status == JobStatus.COMPLETED:
        current_step_idx = total_steps - 1
        step_statuses = ['completed'] * total_steps
    elif job.status == JobStatus.FAILED or job.status == JobStatus.CANCELLED:
        current_step_idx = int(job.progress * total_steps)
        step_statuses = ['completed'] * current_step_idx + ['failed'] + ['pending'] * (total_steps - current_step_idx - 1)
    else:  # RUNNING or RETRYING
        if job.progress < 0.1:
            current_step_idx = 0 if not enable_ocr else min(1, int(job.progress * 10))
        elif job.progress < 0.8:
            current_step_idx = (1 if enable_ocr else 0) + 1
        else:
            progress_in_final = (job.progress - 0.8) / 0.2
            steps_before_render = 2 + (1 if enable_ocr else 0)
            current_step_idx = steps_before_render + int(progress_in_final * (total_steps - steps_before_render))

        current_step_idx = min(current_step_idx, total_steps - 1)
        step_statuses = ['completed'] * current_step_idx + ['in_progress'] + ['pending'] * (total_steps - current_step_idx - 1)

    # Build step details
    steps = []
    for i, step_def in enumerate(all_steps):
        step_status = step_statuses[i] if i < len(step_statuses) else 'pending'

        step = ProgressStep(
            name=step_def['name'],
            display_name=step_def['display_name'],
            status=step_status
        )

        # Add progress for in_progress steps
        if step_status == 'in_progress':
            if step_def['name'] == 'translation':
                if job.total_chunks > 0:
                    step.progress = job.completed_chunks / job.total_chunks
                else:
                    step.progress = job.progress
            else:
                step.progress = (job.progress * total_steps - i) if job.progress * total_steps > i else 0.0
                step.progress = max(0.0, min(1.0, step.progress))

        steps.append(step)

    # Calculate elapsed time
    elapsed_seconds = 0.0
    if job.started_at:
        if job.completed_at:
            elapsed_seconds = job.completed_at - job.started_at
        else:
            elapsed_seconds = time.time() - job.started_at

    # Estimate remaining time
    estimated_remaining = None
    if job.status == JobStatus.RUNNING and job.progress > 0.01 and elapsed_seconds > 0:
        total_estimated = elapsed_seconds / job.progress
        estimated_remaining = max(0, total_estimated - elapsed_seconds)

    # Calculate overall progress percentage
    progress_percent = int(job.progress * 100)

    # Determine output file
    output_file = None
    if job.status == JobStatus.COMPLETED:
        output_file = job.output_file

    return JobProgressResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        current_step=current_step_idx + 1,
        total_steps=total_steps,
        progress_percent=progress_percent,
        steps=steps,
        elapsed_seconds=elapsed_seconds,
        estimated_remaining_seconds=estimated_remaining,
        output_file=output_file
    )


@router.patch("/api/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    update: JobUpdate,
    request: Request = None
):
    """
    Update a job's status or priority

    - **job_id**: Job ID to update
    - **status**: New status (optional)
    - **priority**: New priority (optional)
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if update.status:
        job.status = update.status
    if update.priority is not None:
        job.priority = update.priority

    queue.update_job(job)

    # Broadcast update event
    await manager.broadcast({
        "event": "job_updated",
        "job_id": job.job_id,
        "status": job.status,
        "priority": job.priority
    })

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        source_lang=job.source_lang,
        target_lang=job.target_lang,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        quality_score=job.avg_quality_score,
        total_cost_usd=job.total_cost_usd,
        error_message=job.error_message,
        metadata=job.metadata
    )


@router.delete("/api/jobs/{job_id}")
async def delete_job(
    job_id: str,
    request: Request = None
):
    """
    Delete a job (only if completed, failed, or cancelled)

    - **job_id**: Job ID to delete
    """
    if queue.delete_job(job_id):
        # Broadcast delete event
        await manager.broadcast({
            "event": "job_deleted",
            "job_id": job_id
        })
        return {"message": f"Job {job_id} deleted successfully"}
    else:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete job (only completed/failed/cancelled jobs can be deleted)"
        )


@router.post("/api/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    request: Request = None
):
    """
    Cancel a pending, queued, or running job

    - **job_id**: Job ID to cancel
    """
    job = queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    processor = get_processor()

    # If job is running, check processor status
    if job.status == "running":
        # If processor is not running, force cancel immediately
        if processor is None or not processor.is_running:
            job.status = JobStatus.CANCELLED
            job.updated_at = time.time()
            queue.update_job(job)

            await manager.broadcast({
                "event": "job_cancelled",
                "job_id": job_id,
                "message": "Job force-cancelled (processor stopped)"
            })
            return {"message": f"Job {job_id} force-cancelled (processor was stopped)", "status": "cancelled"}

        # If processor is running, request graceful cancellation
        else:
            job.request_cancellation()
            queue.update_job(job)

            await manager.broadcast({
                "event": "job_cancelling",
                "job_id": job_id,
                "message": "Cancellation requested, stopping translation..."
            })
            return {"message": f"Job {job_id} cancellation requested (stopping...)", "status": "cancelling"}

    # For pending/queued jobs, cancel immediately
    elif queue.cancel_job(job_id):
        await manager.broadcast({
            "event": "job_cancelled",
            "job_id": job_id
        })
        return {"message": f"Job {job_id} cancelled successfully", "status": "cancelled"}

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in status: {job.status}"
        )
