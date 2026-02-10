# ═══════════════════════════════════════════════════════════════════
# FILE: api/book_writer_router.py
# PURPOSE: REST endpoints + WebSocket for book writer
# REPLACES: Existing book_writer_router.py (expanded from 6 to 12 endpoints)
# ═══════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, UploadFile, File
from fastapi.responses import FileResponse
from typing import Optional
import logging
import os
import uuid

from .book_writer_models import (
    CreateBookRequest, ApproveOutlineRequest, RegenerateChapterRequest,
    EditChapterRequest, BookProjectResponse, BookListItem,
)
from .book_writer_service import BookWriterService

logger = logging.getLogger("book_writer.router")
router = APIRouter(prefix="/api/v2/books", tags=["Book Writer"])

# Service singleton
_service: Optional[BookWriterService] = None

def get_service() -> BookWriterService:
    global _service
    if _service is None:
        _service = BookWriterService()
    return _service

def init_service(ai_service=None):
    """Called from main.py to initialize with AI service."""
    svc = get_service()
    if ai_service:
        svc.set_ai_service(ai_service)
    return svc


# ─── PROJECT CRUD ───────────────────────────────────────────────

@router.post("/", response_model=BookProjectResponse)
async def create_book(request: CreateBookRequest):
    """Create a new book project. Immediately starts analysis pipeline."""
    try:
        return await get_service().create_project(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create book project")


@router.get("/", response_model=list[BookListItem])
async def list_books(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all book projects."""
    return await get_service().list_projects(limit, offset)


@router.get("/{book_id}", response_model=BookProjectResponse)
async def get_book(book_id: str):
    """Get book project details and current pipeline status."""
    try:
        return await get_service().get_project(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{book_id}")
async def delete_book(book_id: str):
    """Delete a book project and all associated files."""
    if await get_service().delete_project(book_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Book not found")


# ─── PIPELINE CONTROL ──────────────────────────────────────────

@router.post("/{book_id}/approve")
async def approve_outline(book_id: str, request: ApproveOutlineRequest):
    """
    Approve the generated outline and start writing.

    Can optionally include chapter adjustments:
    {
      "approved": true,
      "chapter_adjustments": {
        "3": {"title": "New Title", "word_target": 8000}
      }
    }
    """
    try:
        return await get_service().approve_outline(book_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── CHAPTER OPERATIONS ────────────────────────────────────────

@router.get("/{book_id}/chapters/{chapter_number}")
async def get_chapter(book_id: str, chapter_number: int):
    """Get a specific chapter's content and metadata."""
    try:
        return await get_service().get_chapter(book_id, chapter_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{book_id}/chapters/{chapter_number}")
async def edit_chapter(book_id: str, chapter_number: int, request: EditChapterRequest):
    """Submit manual edits to a chapter."""
    request.chapter_number = chapter_number
    try:
        return await get_service().edit_chapter(book_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{book_id}/chapters/{chapter_number}/regenerate")
async def regenerate_chapter(book_id: str, chapter_number: int, request: RegenerateChapterRequest):
    """Regenerate a specific chapter with optional instructions."""
    request.chapter_number = chapter_number
    try:
        return await get_service().regenerate_chapter(book_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── READER ────────────────────────────────────────────────────

@router.get("/{book_id}/reader-content")
async def get_reader_content(book_id: str):
    """
    Get book content formatted for the in-app reader.
    Converts chapters into ReaderContent format compatible with ReaderLayout.
    """
    import re

    try:
        project = await get_service().get_project(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if project.status not in ("complete", "writing", "enriching", "editing", "compiling"):
        raise HTTPException(status_code=400, detail="Book not ready for reading")

    chapters_data = project.chapters or []
    reader_chapters = []
    total_words = 0
    total_regions = 0

    for ch in chapters_data:
        ch_data = ch if isinstance(ch, dict) else ch.dict() if hasattr(ch, 'dict') else {}
        ch_num = ch_data.get("chapter_number", 0)
        title = ch_data.get("title", f"Chapter {ch_num}")
        content = (
            ch_data.get("final_content")
            or ch_data.get("edited_content")
            or ch_data.get("enriched_content")
            or ch_data.get("content", "")
        )

        if not content:
            continue

        # Parse content into regions (headings, paragraphs)
        regions = []
        paragraphs = content.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Detect markdown headings
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', para)
            if heading_match:
                level = len(heading_match.group(1))
                regions.append({
                    "type": "heading",
                    "content": heading_match.group(2),
                    "level": level,
                })
            else:
                regions.append({
                    "type": "text",
                    "content": para,
                })
            total_regions += 1

        wc = ch_data.get("word_count", len(content.split()))
        total_words += wc

        reader_chapters.append({
            "id": f"ch-{ch_num}",
            "title": title,
            "regions": regions,
        })

    return {
        "job_id": book_id,
        "title": project.title or "Untitled Book",
        "source_language": "",
        "target_language": project.progress.status if project.progress else "",
        "chapters": reader_chapters,
        "metadata": {
            "total_chapters": len(reader_chapters),
            "total_words": total_words,
            "total_regions": total_regions,
            "tables": 0,
            "formulas": 0,
            "has_layout_dna": False,
            "content_source": "book_writer",
        },
        "quality": {},
    }


# ─── DRAFT UPLOAD ──────────────────────────────────────────────

UPLOAD_DIR = "data/uploads"
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload-draft")
async def upload_draft(file: UploadFile = File(...)):
    """Upload a draft file (.txt, .md, .docx) for book creation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Use .txt, .md, or .docx")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = f"{uuid.uuid4().hex[:12]}{ext}"
    path = os.path.join(UPLOAD_DIR, file_id)
    with open(path, "wb") as f:
        f.write(content)

    return {"file_id": file_id, "filename": file.filename, "size": len(content)}


# ─── OUTPUT & DOWNLOAD ─────────────────────────────────────────

@router.get("/{book_id}/download/{format}")
async def download_book(book_id: str, format: str = "docx"):
    """Download compiled book in specified format."""
    try:
        path = await get_service().get_download_url(book_id, format)
        if not path or not __import__("os").path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")

        # Determine content type
        content_types = {
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "epub": "application/epub+zip",
            "pdf": "application/pdf",
            "markdown": "text/markdown",
            "txt": "text/plain",
        }

        import os
        filename = os.path.basename(path)
        return FileResponse(
            path=path,
            filename=filename,
            media_type=content_types.get(format, "application/octet-stream"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── WEBSOCKET ──────────────────────────────────────────────────

@router.websocket("/{book_id}/ws")
async def websocket_endpoint(websocket: WebSocket, book_id: str):
    """
    WebSocket for real-time pipeline progress.

    Events sent:
    - status_change: Pipeline status changed
    - chapter_progress: Chapter writing/enriching/editing progress
    - chapter_complete: A chapter finished
    - pipeline_complete: All done
    - error: Something failed
    """
    await websocket.accept()
    service = get_service()
    service.register_ws(book_id, websocket)

    try:
        # Send current status immediately
        try:
            project = await service.get_project(book_id)
            await websocket.send_json({
                "event": "status_change",
                "book_id": book_id,
                "data": {
                    "status": project.status.value,
                    "progress": project.progress.model_dump() if project.progress else {},
                },
            })
        except ValueError:
            await websocket.send_json({
                "event": "error",
                "book_id": book_id,
                "data": {"message": "Book not found"},
            })

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Client can send "ping" to keep alive
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        pass
    finally:
        service.unregister_ws(book_id, websocket)
