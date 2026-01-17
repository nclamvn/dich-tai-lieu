from fastapi import APIRouter, HTTPException, Depends
from core.editor.service import get_editor_service, EditorService
from core.editor.schemas import EditorJobResponse, UpdateSegmentRequest

router = APIRouter(prefix="/editor", tags=["editor"])

@router.get("/jobs/{job_id}/segments", response_model=EditorJobResponse)
async def get_job_segments(
    job_id: str,
    service: EditorService = Depends(get_editor_service)
):
    """
    Get all translation segments for a job.
    Used by the Proofreading Studio (CAT Tool).
    """
    response = service.get_job_segments(job_id)
    if not response:
        raise HTTPException(status_code=404, detail="Job not found or no checkpoint available")
    return response

@router.patch("/jobs/{job_id}/segments/{chunk_id}")
async def update_segment(
    job_id: str,
    chunk_id: str,
    body: UpdateSegmentRequest,
    service: EditorService = Depends(get_editor_service)
):
    """
    Update a specific translation segment.
    """
    success = service.update_segment(job_id, chunk_id, body.translated_text)
    if not success:
        raise HTTPException(status_code=404, detail="Segment or Job not found")
    return {"status": "success", "message": "Segment updated"}

@router.post("/jobs/{job_id}/regenerate")
async def regenerate_document(
    job_id: str,
    service: EditorService = Depends(get_editor_service)
):
    """
    Trigger regeneration of the document from the current segments.
    (Stub: In a real implementation, this would enqueue a new 'assemble' job)
    """
    # For now, we return a message telling the frontend to just "Resume" the job
    # because the BatchProcessor logic automatically picks up changes from Checkpoint.
    return {
        "status": "ready",
        "message": "To regenerate, please use the standard 'Resume/Retry' or 'Export' button in the main UI."
    }
