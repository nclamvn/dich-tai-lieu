"""Webhook endpoints for receiving callbacks"""
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any

from ..models.schemas import APPWebhookPayload, JobStatus
from ..services.job_store import job_store


router = APIRouter(prefix="/api/bridge/webhooks", tags=["Webhooks"])


@router.post("/app/translation-complete")
async def app_translation_complete(payload: APPWebhookPayload):
    """
    Webhook called by AI Publisher Pro when translation is complete.
    """
    job = job_store.get_job_by_app_id(payload.app_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = JobStatus.COMPLETED if payload.status == "completed" else JobStatus.FAILED

    job_store.update_job(
        job.job_id,
        status=status,
        progress=100 if status == JobStatus.COMPLETED else job.progress,
        result=payload.result,
        error_message=payload.error
    )

    return {"message": "Webhook processed", "job_id": job.job_id}


@router.post("/app/progress")
async def app_progress_update(payload: Dict[str, Any]):
    """
    Webhook for progress updates from AI Publisher Pro.
    """
    app_job_id = payload.get("app_job_id")
    if not app_job_id:
        raise HTTPException(status_code=400, detail="Missing app_job_id")

    job = job_store.get_job_by_app_id(app_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    progress = payload.get("progress", job.progress)
    status_str = payload.get("status", "")

    # Map APP status to bridge status
    status_map = {
        "extracting": JobStatus.EXTRACTING,
        "translating": JobStatus.TRANSLATING,
        "formatting": JobStatus.FORMATTING,
        "completed": JobStatus.COMPLETED,
        "failed": JobStatus.FAILED
    }

    new_status = status_map.get(status_str.lower())
    if new_status:
        job_store.update_job(job.job_id, status=new_status, progress=progress)
    else:
        job_store.update_job(job.job_id, progress=progress)

    return {"message": "Progress updated", "job_id": job.job_id}


@router.post("/cw/export-complete")
async def cw_export_complete(payload: Dict[str, Any]):
    """
    Webhook called by Companion Writer when export is complete.
    """
    job_id = payload.get("bridge_job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing bridge_job_id")

    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = payload.get("status", "completed")

    if status == "completed":
        job_store.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=payload.get("result")
        )
    else:
        job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            error_message=payload.get("error")
        )

    return {"message": "Webhook processed", "job_id": job_id}


@router.post("/test")
async def test_webhook(request: Request):
    """
    Test endpoint for debugging webhooks.
    """
    body = await request.json()
    print(f"Received test webhook: {body}")
    return {"message": "Test webhook received", "payload": body}
