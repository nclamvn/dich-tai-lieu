"""
Book Writer v2.0 API Routes

FastAPI router for the 9-agent book generation pipeline.
"""

import os
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, UploadFile, File as FileParam
from fastapi.responses import FileResponse

from api.schemas.book_writer_v2 import (
    BookCreateRequest,
    BookProjectResponse,
    BookListResponse,
    StructurePreviewResponse,
    BookContentResponse,
    DraftAnalysisResponse,
)
from api.services.book_writer_v2_service import (
    get_book_writer_v2_service,
    BookWriterV2Service,
)
from core.book_writer_v2.progress import progress_tracker

logger = logging.getLogger("API.BookWriterV2")

router = APIRouter(
    prefix="/api/v2/books-v2",
    tags=["Book Writer v2"],
)


def get_service() -> BookWriterV2Service:
    """Dependency injection for the service."""
    return get_book_writer_v2_service()


# === CRUD Endpoints ===

@router.post("/", response_model=BookProjectResponse, status_code=201)
async def create_book(
    request: BookCreateRequest,
    service: BookWriterV2Service = Depends(get_service),
):
    """
    Create a new book project and start the 9-agent pipeline.

    Progress can be tracked via WebSocket at /api/v2/books-v2/{id}/ws
    """
    try:
        project = await service.create_book(
            title=request.title,
            description=request.description,
            target_pages=request.target_pages,
            genre=request.genre.value,
            audience=request.audience or "",
            subtitle=request.subtitle or "",
            author_name=request.author_name or "AI Publisher Pro",
            language=request.language,
            output_formats=[fmt.value for fmt in request.output_formats],
            words_per_page=request.words_per_page,
            sections_per_chapter=request.sections_per_chapter,
        )
        return _to_response(project)

    except Exception as e:
        logger.error(f"Failed to create book: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=BookListResponse)
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    service: BookWriterV2Service = Depends(get_service),
):
    """List book projects with pagination."""
    projects, total = await service.list_projects(page=page, page_size=page_size, status=status)
    return BookListResponse(
        items=[_to_response(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=BookProjectResponse)
async def get_book(
    project_id: str,
    include_blueprint: bool = Query(False),
    service: BookWriterV2Service = Depends(get_service),
):
    """Get book project details."""
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Book not found")
    return _to_response(project, include_blueprint=include_blueprint)


@router.delete("/{project_id}")
async def delete_book(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Delete a book project."""
    success = await service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted", "id": project_id}


# === Draft Upload & Analysis ===

UPLOAD_DIR = Path("data/uploads")
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload-draft")
async def upload_draft(file: UploadFile = FileParam(...)):
    """Upload a draft file for continue-from-draft feature."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    filepath = UPLOAD_DIR / file_id
    filepath.write_bytes(content)

    return {"file_id": file_id, "filename": file.filename, "size": len(content)}


@router.post("/analyze-draft", response_model=DraftAnalysisResponse)
async def analyze_draft(file: UploadFile = FileParam(...)):
    """Upload and analyze a draft file — returns chapter breakdown."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Save temporarily for parsing
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    filepath = UPLOAD_DIR / file_id
    filepath.write_bytes(content)

    try:
        from core_v2.agents.ghostwriter.document_parser import DocumentParser
        parser = DocumentParser()
        parsed = parser.parse_file(filepath)

        return DraftAnalysisResponse(
            file_id=file_id,
            filename=file.filename,
            total_chapters=parsed.total_chapters,
            total_words=parsed.total_words,
            chapters=[
                {"chapter_number": ch.chapter_number, "title": ch.title, "word_count": ch.word_count}
                for ch in parsed.chapters
            ],
        )
    except Exception as e:
        logger.error(f"Draft analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze draft: {str(e)}")


# === Content Endpoints ===

@router.get("/{project_id}/content", response_model=BookContentResponse)
async def get_book_content(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Get full book content for reading."""
    content = await service.get_book_content(project_id)
    if not content:
        raise HTTPException(status_code=404, detail="Book content not available")
    return content


@router.get("/{project_id}/reader-content")
async def get_reader_content(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Get book content formatted for the in-app reader component."""
    content = await service.get_book_content(project_id)
    if not content:
        raise HTTPException(status_code=404, detail="Book content not available")

    reader = {"title": content["title"], "author": content["author"], "chapters": []}
    chapter_num = 0
    for part in content["parts"]:
        for chapter in part["chapters"]:
            chapter_num += 1
            html_parts = []
            for section in chapter["sections"]:
                html_parts.append(f"<h3>{section['title']}</h3>")
                for para in section["content"].split("\n\n"):
                    if para.strip():
                        html_parts.append(f"<p>{para.strip()}</p>")
            reader["chapters"].append({
                "number": chapter_num,
                "title": f"Chapter {chapter['number']}: {chapter['title']}",
                "content": "\n".join(html_parts),
            })
    return reader


# === Download Endpoints ===

@router.get("/{project_id}/download/{fmt}")
async def download_book(
    project_id: str,
    fmt: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Download book in specified format (docx, markdown, html, pdf)."""
    valid = ["docx", "pdf", "markdown", "html"]
    if fmt not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid format. Must be one of: {valid}")

    filepath = await service.get_download_path(project_id, fmt)
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File not available in {fmt} format")

    media = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "markdown": "text/markdown",
        "html": "text/html",
    }
    return FileResponse(path=filepath, media_type=media.get(fmt, "application/octet-stream"),
                        filename=os.path.basename(filepath))


# === Preview & Control ===

@router.post("/preview-structure", response_model=StructurePreviewResponse)
async def preview_structure(
    target_pages: int = Query(..., ge=50, le=1000),
    service: BookWriterV2Service = Depends(get_service),
):
    """Preview book structure without creating a project."""
    return await service.get_structure_preview(target_pages)


@router.post("/{project_id}/pause")
async def pause_book(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Pause a running book generation."""
    if not await service.pause_project(project_id):
        raise HTTPException(status_code=400, detail="Cannot pause project")
    return {"message": "Project paused", "id": project_id}


# === WebSocket ===

@router.websocket("/{project_id}/ws")
async def book_progress_ws(websocket: WebSocket, project_id: str):
    """
    Real-time progress updates via WebSocket.

    Messages are JSON objects with: project_id, agent, message, percentage, timestamp.
    Send "ping" to receive "pong".
    """
    await websocket.accept()
    try:
        await progress_tracker.register_websocket(project_id, websocket)
        latest = progress_tracker.get_latest(project_id)
        if latest:
            await websocket.send_json(latest)

        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    finally:
        await progress_tracker.unregister_websocket(project_id, websocket)


# === Helpers ===

def _to_response(project, include_blueprint: bool = False) -> BookProjectResponse:
    """Convert BookProject to API response."""
    data = {
        "id": project.id,
        "status": project.status.value,
        "current_agent": project.current_agent or "",
        "current_task": project.current_task or "",
        "sections_completed": project.sections_completed,
        "sections_total": project.sections_total,
        "progress_percentage": project.progress_percentage,
        "word_progress": project.word_progress,
        "expansion_rounds": project.expansion_rounds,
        "output_files": project.output_files,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "completed_at": project.completed_at,
        "errors": project.errors[-10:],
    }
    if include_blueprint and project.blueprint:
        data["blueprint"] = project.blueprint.to_dict()
    return BookProjectResponse(**data)
