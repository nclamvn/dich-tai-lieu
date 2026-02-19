# ═══════════════════════════════════════════════════════════════════
# FILE: api/book_writer_service.py
# PURPOSE: Service singleton — manages pipeline execution,
#          background tasks, state persistence, WebSocket events
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional, Any

from .book_writer_models import (
    BookProject, BookStatus, BookListItem, ChapterStatus,
    CreateBookRequest, ApproveOutlineRequest, RegenerateChapterRequest,
    EditChapterRequest, PipelineProgress, WSEvent, WSEventType,
    BookProjectResponse, InputMode,
)
from .book_writer_repository import BookWriterRepository

logger = logging.getLogger("book_writer.service")


class BookWriterService:
    """
    Service layer for AI Book Writer.

    Manages:
    - Project lifecycle (create, read, update, delete)
    - Pipeline execution as background tasks
    - WebSocket event broadcasting
    - Chapter-level operations (edit, regenerate)
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "data/book_writer.db", data_dir: str = "data/books"):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.repo = BookWriterRepository(db_path)
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self._running_tasks: dict[str, asyncio.Task] = {}
        self._ws_connections: dict[str, list] = {}  # book_id → [websockets]
        self._ai_service = None  # Set from main.py

    def set_ai_service(self, ai_service):
        """Set the AI service for API calls."""
        self._ai_service = ai_service

    async def resume_stalled_projects(self):
        """Resume projects that were interrupted by server restart."""
        stalled = self.repo.list_stalled_projects()
        for item in stalled:
            book_id = item.id
            status = item.status
            if book_id in self._running_tasks:
                continue  # Already running

            if status in ("analyzing", "analysis_ready", "architecting", "outlining"):
                logger.info(f"Resuming planning for {book_id} (was {status})")
                task = asyncio.create_task(self._run_planning(book_id))
                self._running_tasks[book_id] = task
            elif status in ("writing", "enriching", "editing", "compiling"):
                logger.info(f"Resuming writing for {book_id} (was {status})")
                task = asyncio.create_task(self._run_writing(book_id))
                self._running_tasks[book_id] = task

    # ─────────────────────────────────────────────────────────────
    # PROJECT CRUD
    # ─────────────────────────────────────────────────────────────

    async def create_project(self, request: CreateBookRequest) -> BookProjectResponse:
        """Create a new book project and start pipeline."""
        book_id = str(uuid.uuid4())[:12]
        now = datetime.utcnow()

        # Determine input text
        input_text = ""
        if request.ideas:
            input_text = request.ideas
        elif request.draft_content:
            input_text = request.draft_content
        elif request.draft_file_id:
            input_text = await self._load_draft_file(request.draft_file_id)

        if not input_text.strip():
            raise ValueError("No input content provided")

        project = BookProject(
            id=book_id,
            created_at=now,
            updated_at=now,
            request=request,
            status=BookStatus.CREATED,
        )

        # Save project
        self.repo.save_project(project)

        # Save input text separately (can be large)
        input_path = os.path.join(self.data_dir, book_id)
        os.makedirs(input_path, exist_ok=True)
        with open(os.path.join(input_path, "input.txt"), "w", encoding="utf-8") as f:
            f.write(input_text)

        # Start planning pipeline in background
        task = asyncio.create_task(self._run_planning(book_id))
        self._running_tasks[book_id] = task

        return self._to_response(project)

    async def get_project(self, book_id: str) -> BookProjectResponse:
        """Get project with current state."""
        project = self.repo.get_project(book_id)
        if not project:
            raise ValueError(f"Book project {book_id} not found")
        return self._to_response(project)

    async def list_projects(self, limit: int = 20, offset: int = 0) -> list[BookListItem]:
        """List all book projects."""
        return self.repo.list_projects(limit, offset)

    async def delete_project(self, book_id: str) -> bool:
        """Delete a book project and cancel running tasks."""
        if book_id in self._running_tasks:
            self._running_tasks[book_id].cancel()
            del self._running_tasks[book_id]

        # Clean up files
        import shutil
        project_dir = os.path.join(self.data_dir, book_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

        return self.repo.delete_project(book_id)

    # ─────────────────────────────────────────────────────────────
    # PIPELINE EXECUTION
    # ─────────────────────────────────────────────────────────────

    async def _run_planning(self, book_id: str):
        """Background task: Analyze → Architect → Outline."""
        from core.book_writer.pipeline import BookWriterPipeline

        try:
            project = self.repo.get_project(book_id)
            if not project:
                return

            input_text = self._load_input(book_id)
            request = project.request

            # Update status
            self._update_status(book_id, BookStatus.ANALYZING)

            pipeline = BookWriterPipeline(
                ai_service=self._ai_service,
                on_progress=lambda **kw: self._broadcast(book_id, kw),
                data_dir=self.data_dir,
            )

            # User preferences
            prefs = {}
            if request.genre:
                prefs["genre"] = request.genre.value
            if request.tone:
                prefs["tone"] = request.tone
            if request.custom_instructions:
                prefs["custom_instructions"] = request.custom_instructions
            if request.reference_style:
                prefs["reference_style"] = request.reference_style

            # Run planning pipeline
            result = await pipeline.run_full_pipeline(
                book_id=book_id,
                input_text=input_text,
                language=request.language,
                target_pages=request.target_pages,
                user_model=request.model,
                output_formats=[f.value for f in request.output_formats],
                user_preferences=prefs if prefs else None,
                save_callback=lambda data: self._save_pipeline_state(book_id, data),
            )

            # Update project with results
            project = self.repo.get_project(book_id)
            if project:
                project.analysis = result.get("analysis")
                project.blueprint = result.get("blueprint")
                project.outlines = result.get("outlines", [])
                project.status = BookStatus.OUTLINE_READY
                project.updated_at = datetime.utcnow()
                project.progress.total_tokens_in = result.get("tokens_in", 0)
                project.progress.total_tokens_out = result.get("tokens_out", 0)
                if project.blueprint:
                    bp = self._to_dict(project.blueprint)
                    project.progress.total_chapters = bp.get("total_chapters", 0)
                self.repo.save_project(project)

            self._broadcast_event(book_id, WSEventType.STATUS_CHANGE, {
                "status": "outline_ready",
                "message": "Outline ready for review!",
            })

        except asyncio.CancelledError:
            logger.info(f"Planning cancelled for {book_id}")
            self._update_status(book_id, BookStatus.PAUSED)
        except Exception as e:
            logger.error(f"Planning failed for {book_id}: {e}", exc_info=True)
            self._update_status(book_id, BookStatus.FAILED, error=str(e))

    async def approve_outline(self, book_id: str, request: ApproveOutlineRequest) -> BookProjectResponse:
        """User approves outline → start writing pipeline."""
        project = self.repo.get_project(book_id)
        if not project:
            raise ValueError(f"Book project {book_id} not found")

        if project.status != BookStatus.OUTLINE_READY:
            raise ValueError(f"Cannot approve: status is {project.status}, expected outline_ready")

        if not request.approved:
            # User wants changes — just return current state
            return self._to_response(project)

        # Apply chapter adjustments if any
        if request.chapter_adjustments and project.blueprint:
            bp = self._to_dict(project.blueprint)
            for ch_num, adjustments in request.chapter_adjustments.items():
                for ch in bp.get("chapters", []):
                    if ch.get("chapter_number") == int(ch_num):
                        ch.update(adjustments)
            project.blueprint = bp

        if request.custom_notes:
            # Store custom notes for writer context
            notes_path = os.path.join(self.data_dir, book_id, "custom_notes.txt")
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(request.custom_notes)

        project.updated_at = datetime.utcnow()
        self.repo.save_project(project)

        # Start writing pipeline in background
        task = asyncio.create_task(self._run_writing(book_id))
        self._running_tasks[book_id] = task

        return self._to_response(project)

    async def _run_writing(self, book_id: str):
        """Background task: Write → Enrich → Edit → Compile."""
        from core.book_writer.pipeline import BookWriterPipeline

        try:
            project = self.repo.get_project(book_id)
            if not project:
                return

            input_text = self._load_input(book_id)
            request = project.request

            self._update_status(book_id, BookStatus.WRITING)

            pipeline = BookWriterPipeline(
                ai_service=self._ai_service,
                on_progress=lambda **kw: self._handle_write_progress(book_id, kw),
                data_dir=self.data_dir,
            )

            blueprint = self._to_dict(project.blueprint)
            outlines = [self._to_dict(o) for o in (project.outlines or [])]
            analysis = self._to_dict(project.analysis)

            # Get existing user-edited chapters
            existing = None
            if project.chapters:
                existing = [
                    self._to_dict(ch)
                    for ch in project.chapters
                    if self._to_dict(ch).get("status") == ChapterStatus.USER_EDITED.value
                ]

            result = await pipeline.write_from_outline(
                book_id=book_id,
                blueprint=blueprint,
                outlines=outlines,
                analysis=analysis,
                input_text=input_text,
                user_model=request.model,
                output_formats=[f.value for f in request.output_formats],
                save_callback=lambda data: self._save_pipeline_state(book_id, data),
                existing_chapters=existing,
            )

            # Final update
            project = self.repo.get_project(book_id)
            if project:
                project.chapters = result.get("chapters", [])
                project.output_files = result.get("output_files", [])
                project.status = BookStatus.COMPLETE
                project.updated_at = datetime.utcnow()
                project.progress.total_words = result.get("total_words", 0)
                self.repo.save_project(project)

            self._broadcast_event(book_id, WSEventType.PIPELINE_COMPLETE, {
                "total_words": result.get("total_words", 0),
                "total_chapters": len(result.get("chapters", [])),
                "output_files": result.get("output_files", []),
            })

        except asyncio.CancelledError:
            logger.info(f"Writing cancelled for {book_id}")
            self._update_status(book_id, BookStatus.PAUSED)
        except Exception as e:
            logger.error(f"Writing failed for {book_id}: {e}", exc_info=True)
            self._update_status(book_id, BookStatus.FAILED, error=str(e))

    # ─────────────────────────────────────────────────────────────
    # CHAPTER OPERATIONS
    # ─────────────────────────────────────────────────────────────

    async def get_chapter(self, book_id: str, chapter_number: int) -> dict:
        """Get a specific chapter's content."""
        project = self.repo.get_project(book_id)
        if not project:
            raise ValueError(f"Book {book_id} not found")

        for ch in project.chapters:
            ch_data = self._to_dict(ch)
            if ch_data.get("chapter_number") == chapter_number:
                return ch_data

        raise ValueError(f"Chapter {chapter_number} not found")

    async def edit_chapter(self, book_id: str, request: EditChapterRequest) -> dict:
        """User manually edits a chapter."""
        project = self.repo.get_project(book_id)
        if not project:
            raise ValueError(f"Book {book_id} not found")

        updated = False
        for i, ch in enumerate(project.chapters):
            ch_data = self._to_dict(ch)
            if ch_data.get("chapter_number") == request.chapter_number:
                ch_data["user_edits"] = request.content
                ch_data["final_content"] = request.content
                ch_data["status"] = ChapterStatus.USER_EDITED.value
                ch_data["word_count"] = len(request.content.split())
                project.chapters[i] = ch_data
                updated = True
                break

        if not updated:
            raise ValueError(f"Chapter {request.chapter_number} not found")

        project.updated_at = datetime.utcnow()
        self.repo.save_project(project)
        return self._to_dict(project.chapters[i])

    async def regenerate_chapter(self, book_id: str, request: RegenerateChapterRequest) -> dict:
        """Regenerate a specific chapter."""
        from core.book_writer.pipeline import BookWriterPipeline

        project = self.repo.get_project(book_id)
        if not project:
            raise ValueError(f"Book {book_id} not found")

        # Find chapter and its outline
        outline = None
        for o in project.outlines:
            o_data = self._to_dict(o)
            if o_data.get("chapter_number") == request.chapter_number:
                outline = o_data
                break

        if not outline:
            raise ValueError(f"Outline for chapter {request.chapter_number} not found")

        # Build summaries from existing chapters
        summaries = []
        prev_text = ""
        for ch in project.chapters:
            ch_data = self._to_dict(ch)
            ch_num = ch_data.get("chapter_number", 0)
            if ch_num < request.chapter_number:
                summaries.append({
                    "number": ch_num,
                    "title": ch_data.get("title", ""),
                    "summary": ch_data.get("summary", ""),
                })
                if ch_num == request.chapter_number - 1:
                    prev_text = ch_data.get("final_content") or ch_data.get("content", "")

        input_text = self._load_input(book_id)
        analysis = self._to_dict(project.analysis)
        blueprint = self._to_dict(project.blueprint)

        pipeline = BookWriterPipeline(ai_service=self._ai_service, data_dir=self.data_dir)

        # Add custom instructions to outline if provided
        if request.instructions:
            outline["custom_instructions"] = request.instructions

        result = await pipeline.write_chapter(
            chapter_number=request.chapter_number,
            blueprint=blueprint,
            outline=outline,
            analysis=analysis,
            chapter_summaries=summaries,
            previous_chapter_text=prev_text,
            source_material=None,
            user_model=project.request.model,
        )

        # Update project
        for i, ch in enumerate(project.chapters):
            ch_data = self._to_dict(ch)
            if ch_data.get("chapter_number") == request.chapter_number:
                ch_data["content"] = result["content"]
                ch_data["final_content"] = result["content"]
                ch_data["word_count"] = result["word_count"]
                ch_data["status"] = ChapterStatus.WRITTEN.value
                project.chapters[i] = ch_data
                break

        project.updated_at = datetime.utcnow()
        self.repo.save_project(project)
        return result

    async def get_download_url(self, book_id: str, format: str = "docx") -> str:
        """Get download path for compiled output."""
        project = self.repo.get_project(book_id)
        if not project:
            raise ValueError(f"Book {book_id} not found")

        for f in project.output_files:
            f_data = self._to_dict(f)
            if f_data.get("format") == format:
                return f_data.get("path", "")

        raise ValueError(f"No {format} output available")

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(obj):
        """Convert Pydantic model or dict to plain dict."""
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        if hasattr(obj, 'dict'):
            return obj.dict()
        return obj

    def _load_input(self, book_id: str) -> str:
        """Load saved input text."""
        path = os.path.join(self.data_dir, book_id, "input.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    async def _load_draft_file(self, file_id: str) -> str:
        """Load draft from uploaded file (via Publisher Pro's file system)."""
        # Check common upload locations
        for dir_path in ["data/uploads", "uploads", "/tmp/uploads"]:
            path = os.path.join(dir_path, file_id)
            if os.path.exists(path):
                # Try text extraction based on extension
                if path.endswith((".txt", ".md")):
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read()
                elif path.endswith(".docx"):
                    try:
                        from docx import Document
                        doc = Document(path)
                        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
                    except Exception:
                        pass
        return ""

    def _update_status(self, book_id: str, status: BookStatus, error: str | None = None):
        """Update project status."""
        project = self.repo.get_project(book_id)
        if project:
            project.status = status
            project.updated_at = datetime.utcnow()
            project.progress.status = status
            if error:
                project.error = error
            self.repo.save_project(project)

            self._broadcast_event(book_id, WSEventType.STATUS_CHANGE, {
                "status": status.value,
                "error": error,
            })

    def _save_pipeline_state(self, book_id: str, data: dict):
        """Callback from pipeline to save intermediate state."""
        project = self.repo.get_project(book_id)
        if not project:
            return

        if "status" in data:
            project.status = BookStatus(data["status"])
            project.progress.status = project.status
        if "analysis" in data:
            project.analysis = data["analysis"]
        if "blueprint" in data:
            project.blueprint = data["blueprint"]
        if "outlines" in data:
            project.outlines = data["outlines"]
        if "chapters" in data:
            project.chapters = data["chapters"]
        if "output_files" in data:
            project.output_files = data["output_files"]
        if "total_words" in data:
            project.progress.total_words = data["total_words"]
        if "error" in data:
            project.error = data["error"]

        project.updated_at = datetime.utcnow()
        self.repo.save_project(project)

    def _handle_write_progress(self, book_id: str, kw: dict):
        """Handle progress updates from pipeline."""
        agent = kw.get("agent", "")
        chapter = kw.get("chapter", 0)
        total = kw.get("total", 0)
        message = kw.get("message", "")
        chapters_done = kw.get("chapters_done", 0)

        # Update progress in DB
        project = self.repo.get_project(book_id)
        if project:
            project.progress.current_agent = agent
            project.progress.current_chapter = chapter
            project.progress.total_chapters = total
            if agent == "writer":
                project.progress.chapters_written = chapters_done
            elif agent == "enricher":
                project.progress.chapters_enriched = chapters_done
            elif agent == "editor":
                project.progress.chapters_edited = chapters_done
            self.repo.save_project(project)

        # Broadcast to WebSocket
        self._broadcast_event(book_id, WSEventType.CHAPTER_PROGRESS, {
            "agent": agent,
            "chapter": chapter,
            "total": total,
            "message": message,
        })

    def _broadcast(self, book_id: str, data: dict):
        """Simple broadcast helper."""
        self._broadcast_event(
            book_id,
            WSEventType.CHAPTER_PROGRESS,
            data,
        )

    def _broadcast_event(self, book_id: str, event_type: WSEventType, data: dict):
        """Broadcast event to WebSocket connections."""
        connections = self._ws_connections.get(book_id, [])
        event = WSEvent(event=event_type, book_id=book_id, data=data)
        event_json = event.model_dump_json()

        for ws in connections:
            try:
                asyncio.create_task(ws.send_text(event_json))
            except Exception:
                pass

    def register_ws(self, book_id: str, ws):
        """Register WebSocket connection for a book."""
        if book_id not in self._ws_connections:
            self._ws_connections[book_id] = []
        self._ws_connections[book_id].append(ws)

    def unregister_ws(self, book_id: str, ws):
        """Unregister WebSocket connection."""
        if book_id in self._ws_connections:
            self._ws_connections[book_id] = [
                w for w in self._ws_connections[book_id] if w != ws
            ]

    def _to_response(self, project: BookProject) -> BookProjectResponse:
        """Convert internal project to API response."""
        title = None
        if project.blueprint:
            bp = self._to_dict(project.blueprint)
            title = bp.get("title")
        if not title and project.request.title:
            title = project.request.title

        total_words = 0
        chapters_out = []
        if project.chapters:
            for ch in project.chapters:
                ch_data = self._to_dict(ch)
                total_words += ch_data.get("word_count", 0)
                # Infer status if still "pending" but has content
                if ch_data.get("status", "pending") == "pending" and ch_data.get("content"):
                    if ch_data.get("edited_content") or ch_data.get("final_content"):
                        ch_data["status"] = "edited"
                    elif ch_data.get("enriched_content"):
                        ch_data["status"] = "enriched"
                    else:
                        ch_data["status"] = "written"
                chapters_out.append(ch_data)

        return BookProjectResponse(
            id=project.id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            title=title,
            status=project.status,
            input_mode=project.request.input_mode,
            progress=project.progress,
            analysis=project.analysis,
            blueprint=project.blueprint,
            outlines=project.outlines,
            chapters=chapters_out,
            chapter_count=len(chapters_out),
            total_words=total_words,
            output_files=project.output_files,
            error=project.error,
        )
