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
    ImageUploadResponse,
    ImageManifestResponse,
    IllustrationPlanResponse,
    IllustrationPlanUpdateRequest,
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
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
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


# === Illustration Endpoints (Sprint K) ===

IMAGE_UPLOAD_DIR = Path("data/uploads/books")
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB per image
MAX_IMAGES_PER_PROJECT = 50


@router.post("/{project_id}/images/upload", response_model=ImageUploadResponse)
async def upload_images(
    project_id: str,
    files: list[UploadFile] = FileParam(...),
    service: BookWriterV2Service = Depends(get_service),
):
    """Upload images for illustrated book output."""
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Book not found")

    if len(files) > MAX_IMAGES_PER_PROJECT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_IMAGES_PER_PROJECT} images allowed",
        )

    image_dir = IMAGE_UPLOAD_DIR / project_id / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    saved_filenames = []
    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type: {ext}. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
            )
        content = await f.read()
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail=f"Image too large: {f.filename} (max 20MB)")

        safe_name = f"{uuid.uuid4().hex[:8]}_{f.filename}"
        (image_dir / safe_name).write_bytes(content)
        saved_filenames.append(safe_name)

    # Track uploaded images on the project
    existing = project.uploaded_images or []
    project.uploaded_images = existing + [str(image_dir / fn) for fn in saved_filenames]
    await service.save_project(project)

    return ImageUploadResponse(
        uploaded=len(saved_filenames),
        filenames=saved_filenames,
        project_id=project_id,
    )


@router.post("/{project_id}/images/analyze", response_model=ImageManifestResponse)
async def analyze_images(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Trigger Vision AI analysis on uploaded images."""
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Book not found")

    if not project.uploaded_images:
        raise HTTPException(status_code=400, detail="No images uploaded")

    try:
        manifest = await service.analyze_images(project_id)
        return ImageManifestResponse(**manifest.to_dict())
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/images/manifest", response_model=ImageManifestResponse)
async def get_image_manifest(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Return cached image analysis manifest."""
    manifest = await service.get_image_manifest(project_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="No manifest found. Run /images/analyze first.")
    return ImageManifestResponse(**manifest.to_dict())


@router.post("/{project_id}/illustrate")
async def trigger_illustration(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Trigger illustrated output generation."""
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Book not found")
    if not project.has_images():
        raise HTTPException(status_code=400, detail="No images uploaded")

    try:
        result = await service.run_illustration_pipeline(project_id)
        return {"message": "Illustration complete", "project_id": project_id, "plan": result}
    except Exception as e:
        logger.error(f"Illustration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/illustration-plan", response_model=IllustrationPlanResponse)
async def get_illustration_plan(
    project_id: str,
    service: BookWriterV2Service = Depends(get_service),
):
    """Preview the current illustration plan."""
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Book not found")
    if not project.illustration_plan:
        raise HTTPException(status_code=404, detail="No illustration plan. Run /illustrate first.")
    return IllustrationPlanResponse(**project.illustration_plan.to_dict())


@router.put("/{project_id}/illustration-plan", response_model=IllustrationPlanResponse)
async def update_illustration_plan(
    project_id: str,
    request: IllustrationPlanUpdateRequest,
    service: BookWriterV2Service = Depends(get_service),
):
    """Manually adjust the illustration plan."""
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Book not found")
    if not project.illustration_plan:
        raise HTTPException(status_code=404, detail="No illustration plan exists")

    try:
        updated = await service.update_illustration_plan(project_id, request.placements)
        return IllustrationPlanResponse(**updated.to_dict())
    except Exception as e:
        logger.error(f"Plan update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

def _safe_plan_dict(project):
    """Safely convert illustration_plan to dict, returning None on failure."""
    plan = getattr(project, "illustration_plan", None)
    if plan is None:
        return None
    try:
        d = plan.to_dict()
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return None


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
        # Illustration (Sprint K)
        "has_images": project.has_images(),
        "uploaded_images": getattr(project, "uploaded_images", None) or [],
        "illustration_plan": _safe_plan_dict(project),
    }
    if include_blueprint and project.blueprint:
        data["blueprint"] = project.blueprint.to_dict()
    return BookProjectResponse(**data)
