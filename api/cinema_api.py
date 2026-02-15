"""
Cinema API - FastAPI Endpoints for Book-to-Cinema Conversion

Provides REST API endpoints for:
- Starting new cinema conversion jobs
- Tracking job progress
- Resuming failed jobs
- Downloading results
"""

import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from core.cinema.models import CinemaStyle, JobStatus
from core.cinema.cinema_orchestrator import CinemaOrchestrator

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/cinema", tags=["Cinema"])

# Global orchestrator instance (will be initialized with LLM client)
_orchestrator: Optional[CinemaOrchestrator] = None

# In-memory job progress tracking for WebSocket updates
_job_progress: dict = {}


def get_orchestrator() -> CinemaOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        # Import LLM client from existing project
        try:
            from ai_providers.unified_client import get_unified_client
            llm_client = get_unified_client()
        except ImportError:
            raise RuntimeError("LLM client not available")
        
        _orchestrator = CinemaOrchestrator(
            llm_client=llm_client,
            video_provider="veo",
            output_dir=Path("outputs/cinema"),
        )
    return _orchestrator


# ==================== Request/Response Models ====================

class CinemaJobRequest(BaseModel):
    """Request to start a cinema conversion job."""
    title: str
    author: str = "Unknown"
    style: str = "blockbuster"  # CinemaStyle enum value
    text: Optional[str] = None  # Direct text input


class JobProgressResponse(BaseModel):
    """Job progress information."""
    job_id: str
    status: str
    progress: float
    current_stage: str
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class JobDetailResponse(BaseModel):
    """Detailed job information."""
    job_id: str
    status: str
    progress: float
    current_stage: str
    style: str
    chunks_count: int
    scenes_count: int
    prompts_count: int
    videos_count: int
    final_video_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str


class JobListResponse(BaseModel):
    """List of jobs."""
    jobs: List[dict]
    total: int


# ==================== API Endpoints ====================

@router.post("/jobs", response_model=JobProgressResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    author: str = Form("Unknown"),
    style: str = Form("blockbuster"),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    """
    Start a new book-to-cinema conversion job.
    
    Upload a file (PDF, DOCX, TXT, EPUB) or provide text directly.
    """
    orchestrator = get_orchestrator()
    
    # Validate input
    if not file and not text:
        raise HTTPException(400, "Either file or text must be provided")
    
    # Validate style
    try:
        cinema_style = CinemaStyle(style.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid style: {style}")
    
    # Get text content
    if file:
        # Save uploaded file
        upload_dir = Path("uploads/cinema")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        content = await file.read()
        file_path.write_bytes(content)
        source = str(file_path)
    else:
        source = text
    
    # Create job tracking entry
    import uuid
    job_id = str(uuid.uuid4())[:8]
    _job_progress[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_stage": "initializing",
    }
    
    # Progress callback
    def progress_callback(progress: float, stage: str, message: str):
        _job_progress[job_id] = {
            "status": "processing",
            "progress": progress,
            "current_stage": stage,
            "message": message,
        }
    
    # Run job in background
    async def run_job():
        try:
            job = await orchestrator.adapt_book(
                source=source,
                title=title,
                author=author,
                style=cinema_style,
                progress_callback=progress_callback,
            )
            _job_progress[job_id] = {
                "status": "complete",
                "progress": 1.0,
                "current_stage": "complete",
                "final_video": str(job.final_video_path) if job.final_video_path else None,
            }
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            _job_progress[job_id] = {
                "status": "failed",
                "progress": _job_progress[job_id]["progress"],
                "current_stage": _job_progress[job_id]["current_stage"],
                "error": str(e),
            }
    
    background_tasks.add_task(run_job)
    
    return JobProgressResponse(
        job_id=job_id,
        status="pending",
        progress=0.0,
        current_stage="initializing",
        created_at=datetime.now().isoformat(),
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs():
    """List all cinema conversion jobs."""
    orchestrator = get_orchestrator()
    jobs = orchestrator.list_jobs()
    
    return JobListResponse(
        jobs=jobs,
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str):
    """Get detailed information about a job."""
    orchestrator = get_orchestrator()
    job_data = orchestrator.get_job(job_id)
    
    if not job_data:
        # Check in-memory progress
        if job_id in _job_progress:
            progress = _job_progress[job_id]
            return JobDetailResponse(
                job_id=job_id,
                status=progress["status"],
                progress=progress["progress"],
                current_stage=progress["current_stage"],
                style="unknown",
                chunks_count=0,
                scenes_count=0,
                prompts_count=0,
                videos_count=0,
                error=progress.get("error"),
                created_at=datetime.now().isoformat(),
            )
        raise HTTPException(404, f"Job {job_id} not found")
    
    return JobDetailResponse(
        job_id=job_data["job_id"],
        status=job_data["status"],
        progress=job_data["progress"],
        current_stage=job_data["current_stage"],
        style=job_data["style"],
        chunks_count=job_data["chunks_count"],
        scenes_count=job_data["scenes_count"],
        prompts_count=job_data["prompts_count"],
        videos_count=job_data["videos_count"],
        final_video_path=job_data.get("final_video_path"),
        error=job_data.get("error"),
        created_at=job_data["created_at"],
    )


@router.get("/jobs/{job_id}/progress")
async def get_job_progress(job_id: str):
    """Get real-time job progress (for polling)."""
    if job_id in _job_progress:
        return _job_progress[job_id]
    
    orchestrator = get_orchestrator()
    job_data = orchestrator.get_job(job_id)
    
    if not job_data:
        raise HTTPException(404, f"Job {job_id} not found")
    
    return {
        "status": job_data["status"],
        "progress": job_data["progress"],
        "current_stage": job_data["current_stage"],
    }


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str, background_tasks: BackgroundTasks):
    """Resume a failed or stopped job."""
    orchestrator = get_orchestrator()
    job_data = orchestrator.get_job(job_id)
    
    if not job_data:
        raise HTTPException(404, f"Job {job_id} not found")
    
    if job_data["status"] == "complete":
        raise HTTPException(400, "Job already completed")
    
    # Progress callback
    def progress_callback(progress: float, stage: str, message: str):
        _job_progress[job_id] = {
            "status": "processing",
            "progress": progress,
            "current_stage": stage,
            "message": message,
        }
    
    async def resume_job_task():
        try:
            job = await orchestrator.adapt_book(
                source=job_data["source_path"],
                title="Resumed Job",
                progress_callback=progress_callback,
                resume_job_id=job_id,
            )
            _job_progress[job_id] = {
                "status": "complete",
                "progress": 1.0,
                "current_stage": "complete",
            }
        except Exception as e:
            _job_progress[job_id] = {
                "status": "failed",
                "error": str(e),
            }
    
    background_tasks.add_task(resume_job_task)
    
    return {"message": f"Resuming job {job_id}", "status": "resuming"}


@router.post("/jobs/{job_id}/retry-videos")
async def retry_failed_videos(job_id: str, background_tasks: BackgroundTasks):
    """Retry failed video segments for a job."""
    orchestrator = get_orchestrator()
    
    async def retry_task():
        try:
            await orchestrator.retry_failed_videos(job_id)
            _job_progress[job_id] = {
                "status": "retrying_complete",
                "progress": 1.0,
            }
        except Exception as e:
            _job_progress[job_id] = {
                "status": "retry_failed",
                "error": str(e),
            }
    
    background_tasks.add_task(retry_task)
    
    return {"message": f"Retrying failed videos for job {job_id}"}


@router.get("/jobs/{job_id}/video")
async def download_video(job_id: str):
    """Download the final video for a completed job."""
    orchestrator = get_orchestrator()
    job_data = orchestrator.get_job(job_id)
    
    if not job_data:
        raise HTTPException(404, f"Job {job_id} not found")
    
    if job_data["status"] != "complete":
        raise HTTPException(400, "Job not yet complete")
    
    video_path = job_data.get("final_video_path")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(404, "Video file not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"cinema_{job_id}.mp4",
    )


@router.get("/jobs/{job_id}/screenplay")
async def download_screenplay(job_id: str, format: str = "txt"):
    """Download the screenplay for a job."""
    orchestrator = get_orchestrator()
    job_data = orchestrator.get_job(job_id)
    
    if not job_data:
        raise HTTPException(404, f"Job {job_id} not found")
    
    output_dir = Path(job_data["output_dir"])
    
    if format == "fountain":
        screenplay_files = list(output_dir.glob("*_screenplay.fountain"))
    else:
        screenplay_files = list(output_dir.glob("*_screenplay.txt"))
    
    if not screenplay_files:
        raise HTTPException(404, "Screenplay not found")
    
    return FileResponse(
        screenplay_files[0],
        media_type="text/plain",
        filename=f"screenplay_{job_id}.{format}",
    )


@router.get("/styles")
async def list_styles():
    """List available cinema styles."""
    return {
        "styles": [
            {
                "id": "blockbuster",
                "name": "Cinematic Blockbuster",
                "description": "Hollywood-style epic cinematography",
            },
            {
                "id": "anime",
                "name": "Anime Style",
                "description": "Japanese animation aesthetic",
            },
            {
                "id": "noir",
                "name": "Film Noir",
                "description": "Classic 1940s detective aesthetic",
            },
            {
                "id": "documentary",
                "name": "Documentary",
                "description": "Realistic observational style",
            },
            {
                "id": "fantasy",
                "name": "Fantasy Epic",
                "description": "Magical fantasy worlds",
            },
            {
                "id": "horror",
                "name": "Horror",
                "description": "Psychological horror atmosphere",
            },
            {
                "id": "romantic",
                "name": "Romantic Drama",
                "description": "Warm, emotional intimacy",
            },
        ]
    }


# ==================== WebSocket for Real-time Progress ====================

from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress updates."""
    await websocket.accept()
    
    try:
        while True:
            # Send current progress
            if job_id in _job_progress:
                await websocket.send_json(_job_progress[job_id])
                
                # Close if complete or failed
                if _job_progress[job_id]["status"] in ["complete", "failed"]:
                    break
            else:
                await websocket.send_json({"status": "unknown", "error": "Job not found"})
                break
            
            # Wait before next update
            import asyncio
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
