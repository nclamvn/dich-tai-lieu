"""
Legacy batch queue endpoints (multi-file processing).

Self-contained module with its own in-memory state.
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks

from config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Batch Legacy"])

# In-memory batch queue storage (for demo - use Redis in production)
batch_jobs_db: Dict[str, Dict] = {}
batch_queue_running = False


@router.get("/api/batch/status")
async def get_batch_status():
    """Get batch queue status"""
    pending = sum(1 for j in batch_jobs_db.values() if j["status"] == "pending")
    processing = sum(1 for j in batch_jobs_db.values() if j["status"] == "processing")
    completed = sum(1 for j in batch_jobs_db.values() if j["status"] == "completed")
    failed = sum(1 for j in batch_jobs_db.values() if j["status"] == "failed")

    total_pages = sum(j.get("total_pages", 0) for j in batch_jobs_db.values())
    completed_pages = sum(j.get("completed_pages", 0) for j in batch_jobs_db.values())
    total_cost = sum(j.get("cost", 0) for j in batch_jobs_db.values())

    return {
        "is_running": batch_queue_running,
        "jobs": {
            "total": len(batch_jobs_db),
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed
        },
        "pages": {
            "total": total_pages,
            "completed": completed_pages,
            "progress": (completed_pages / total_pages * 100) if total_pages > 0 else 0
        },
        "cost": {
            "total": round(total_cost, 4)
        }
    }


@router.post("/api/batch/upload")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    mode: str = "balanced"
):
    """Upload multiple PDF files to batch queue"""
    created_jobs = []

    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue

        # Generate job ID
        job_id = str(uuid.uuid4())[:8]

        # Save file
        upload_dir = Path("./uploads/batch")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{job_id}_{file.filename}"

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Estimate pages (10 pages per MB)
        pages = max(1, int(len(content) / (1024 * 1024) * 10))

        # Cost per page based on mode
        costs = {"economy": 0.001, "balanced": 0.004, "quality": 0.05}

        # Create job
        job = {
            "id": job_id,
            "name": file.filename.replace(".pdf", ""),
            "file_path": str(file_path),
            "status": "pending",
            "priority": 2,
            "total_pages": pages,
            "completed_pages": 0,
            "progress": 0,
            "elapsed": 0,
            "cost": 0,
            "pages_per_min": 0,
            "error": None,
            "output_path": None,
            "settings": {
                "mode": mode,
                "source_lang": "Chinese",
                "target_lang": "Vietnamese",
                "output_format": "docx"
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        batch_jobs_db[job_id] = job
        created_jobs.append(job)

    estimated_cost = sum(
        j["total_pages"] * costs.get(j["settings"]["mode"], 0.004)
        for j in created_jobs
    )

    return {
        "success": True,
        "jobs_created": len(created_jobs),
        "jobs": created_jobs,
        "estimated_cost": round(estimated_cost, 4)
    }


@router.get("/api/batch/jobs")
async def list_batch_jobs():
    """List all batch jobs"""
    jobs = list(batch_jobs_db.values())

    # Sort: processing > pending > paused > failed > completed > cancelled
    order = {"processing": 0, "preparing": 1, "pending": 2, "paused": 3, "failed": 4, "completed": 5, "cancelled": 6}
    jobs.sort(key=lambda j: (order.get(j["status"], 99), -j["priority"]))

    return {"jobs": jobs}


@router.get("/api/batch/jobs/{job_id}")
async def get_batch_job(job_id: str):
    """Get batch job details"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return batch_jobs_db[job_id]


@router.patch("/api/batch/jobs/{job_id}")
async def update_batch_job(job_id: str, status: str = None, priority: int = None):
    """Update batch job (pause, resume, cancel, set priority)"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    job = batch_jobs_db[job_id]

    if status:
        job["status"] = status
    if priority:
        job["priority"] = priority

    job["updated_at"] = datetime.now().isoformat()
    return job


@router.delete("/api/batch/jobs/{job_id}")
async def delete_batch_job(job_id: str):
    """Delete/cancel batch job"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    job = batch_jobs_db[job_id]

    if job["status"] == "processing":
        job["status"] = "cancelled"
    else:
        del batch_jobs_db[job_id]

    return {"success": True, "message": "Job deleted"}


@router.post("/api/batch/jobs/{job_id}/retry")
async def retry_batch_job(job_id: str):
    """Retry a failed batch job"""
    if job_id not in batch_jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    job = batch_jobs_db[job_id]

    if job["status"] not in ["failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Can only retry failed or cancelled jobs")

    job["status"] = "pending"
    job["progress"] = 0
    job["completed_pages"] = 0
    job["error"] = None
    job["updated_at"] = datetime.now().isoformat()

    return job


@router.post("/api/batch/queue/start")
async def start_batch_queue(background_tasks: BackgroundTasks):
    """Start batch queue processing"""
    global batch_queue_running

    if batch_queue_running:
        return {"success": False, "message": "Batch queue already running"}

    batch_queue_running = True
    background_tasks.add_task(process_batch_queue)

    return {"success": True, "message": "Batch queue started"}


@router.post("/api/batch/queue/pause")
async def pause_batch_queue():
    """Pause batch queue processing"""
    global batch_queue_running
    batch_queue_running = False
    return {"success": True, "message": "Batch queue paused"}


@router.post("/api/batch/queue/clear")
async def clear_batch_completed():
    """Clear completed and cancelled batch jobs"""
    to_remove = [
        job_id for job_id, job in batch_jobs_db.items()
        if job["status"] in ["completed", "cancelled"]
    ]

    for job_id in to_remove:
        del batch_jobs_db[job_id]

    return {"success": True, "cleared": len(to_remove)}


async def process_batch_queue():
    """Background task to process batch jobs"""
    global batch_queue_running

    while batch_queue_running:
        # Get processing count
        processing = [j for j in batch_jobs_db.values() if j["status"] == "processing"]

        # Start new jobs if slots available (max 2 concurrent)
        if len(processing) < 2:
            pending = sorted(
                [j for j in batch_jobs_db.values() if j["status"] == "pending"],
                key=lambda j: -j["priority"]
            )

            if pending:
                job = pending[0]
                job["status"] = "processing"
                asyncio.create_task(process_batch_job(job["id"]))

        await asyncio.sleep(1)


async def process_batch_job(job_id: str):
    """Process a single batch job (simulated for demo)"""
    if job_id not in batch_jobs_db:
        return

    job = batch_jobs_db[job_id]
    costs = {"economy": 0.001, "balanced": 0.004, "quality": 0.05}

    try:
        while job["status"] == "processing":
            # Simulate progress (3 pages per second)
            job["completed_pages"] = min(
                job["completed_pages"] + 3,
                job["total_pages"]
            )
            job["progress"] = (job["completed_pages"] / job["total_pages"]) * 100
            job["elapsed"] += 1

            mode = job["settings"]["mode"]
            job["cost"] = job["completed_pages"] * costs.get(mode, 0.004)

            if job["elapsed"] > 0:
                job["pages_per_min"] = (job["completed_pages"] / job["elapsed"]) * 60

            job["updated_at"] = datetime.now().isoformat()

            # Check if done
            if job["completed_pages"] >= job["total_pages"]:
                job["status"] = "completed"
                job["progress"] = 100

                # Output path
                output_dir = Path("./outputs/batch")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{job_id}_output.{job['settings']['output_format']}"
                job["output_path"] = str(output_path)

                # Create placeholder output
                with open(output_path, "w") as f:
                    f.write(f"Translated document: {job['name']}")

                break

            await asyncio.sleep(1)

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
