"""
Book Writer v2.0 Service Layer

Handles business logic between API and pipeline.
"""

import asyncio
import logging
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.book_writer_v2 import (
    BookWriterPipeline,
    BookWriterConfig,
    BookProject,
    BookStatus,
)
from core.book_writer_v2.ai_adapter import AIClientAdapter, MockAIClient
from core.book_writer_v2.progress import progress_tracker


logger = logging.getLogger("BookWriterV2.Service")


class BookWriterV2Service:
    """
    Service layer for Book Writer v2.0.

    Manages project lifecycle, AI client integration,
    progress tracking, and file-based persistence.
    """

    def __init__(self, ai_client: Any = None, db_path: str = "data/books_v2"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)

        if ai_client:
            self.ai_client = AIClientAdapter(ai_client)
        else:
            logger.warning("No AI client provided, using mock client")
            self.ai_client = MockAIClient()

        self._active_projects: Dict[str, BookProject] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def create_book(
        self,
        title: str,
        description: str,
        target_pages: int = 100,
        genre: str = "non-fiction",
        audience: str = "",
        subtitle: str = "",
        author_name: str = "AI Publisher Pro",
        language: str = "en",
        output_formats: List[str] = None,
        words_per_page: int = 300,
        sections_per_chapter: int = 4,
    ) -> BookProject:
        """Create a new book project and start generation in background."""
        config = BookWriterConfig(
            words_per_page=words_per_page,
            default_sections_per_chapter=sections_per_chapter,
        )

        pipeline = BookWriterPipeline(
            config=config,
            ai_client=self.ai_client,
            progress_callback=self._progress_callback,
        )

        project = BookProject(
            user_request=f"{title}: {description}",
            user_description=description,
            status=BookStatus.CREATED,
        )

        self._active_projects[project.id] = project

        task = asyncio.create_task(
            self._run_pipeline(
                pipeline=pipeline,
                project=project,
                title=title,
                description=description,
                target_pages=target_pages,
                genre=genre,
                audience=audience,
                subtitle=subtitle,
            )
        )
        self._running_tasks[project.id] = task

        await self._save_project(project)
        return project

    async def _run_pipeline(
        self,
        pipeline: BookWriterPipeline,
        project: "BookProject",
        **kwargs,
    ):
        """Run pipeline in background task."""
        project_id = project.id
        try:
            result = await pipeline.create_book(project=project, **kwargs)
            self._active_projects[project_id] = result
            await self._save_project(result)

        except Exception as e:
            logger.error(f"Pipeline error for {project_id}: {e}")
            if project_id in self._active_projects:
                proj = self._active_projects[project_id]
                proj.status = BookStatus.FAILED
                proj.add_error(str(e), "Pipeline", recoverable=False)
                await self._save_project(proj)

        finally:
            self._running_tasks.pop(project_id, None)

    def _progress_callback(self, project_id: str, message: str, percentage: float):
        """Handle progress updates from pipeline."""
        project = self._active_projects.get(project_id)
        agent = project.current_agent if project else ""

        # Fire-and-forget progress update
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                progress_tracker.update(
                    project_id=project_id,
                    agent=agent,
                    message=message,
                    percentage=percentage,
                )
            )
        except RuntimeError:
            pass

    async def get_project(self, project_id: str) -> Optional[BookProject]:
        """Get project by ID (cache first, then disk)."""
        if project_id in self._active_projects:
            return self._active_projects[project_id]
        return await self._load_project(project_id)

    async def list_projects(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> tuple:
        """List book projects with pagination. Returns (projects, total)."""
        projects = []

        # From disk
        if os.path.exists(self.db_path):
            files = [f for f in os.listdir(self.db_path) if f.endswith(".json")]
            files.sort(
                key=lambda f: os.path.getmtime(os.path.join(self.db_path, f)),
                reverse=True,
            )
            for filename in files:
                pid = filename.replace(".json", "")
                project = await self._load_project(pid)
                if project:
                    if status and project.status.value != status:
                        continue
                    projects.append(project)

        # Include active projects not yet on disk
        seen_ids = {p.id for p in projects}
        for pid, project in self._active_projects.items():
            if pid not in seen_ids:
                if status and project.status.value != status:
                    continue
                projects.insert(0, project)

        total = len(projects)
        start = (page - 1) * page_size
        return projects[start:start + page_size], total

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project (cancel if running)."""
        self._active_projects.pop(project_id, None)

        if project_id in self._running_tasks:
            self._running_tasks[project_id].cancel()
            self._running_tasks.pop(project_id, None)

        filepath = os.path.join(self.db_path, f"{project_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    async def get_structure_preview(self, target_pages: int) -> dict:
        """Preview book structure without creating a project."""
        config = BookWriterConfig()
        structure = config.calculate_structure(target_pages)
        est_sections = structure["total_sections"]
        structure["estimated_time_minutes"] = max(5, (est_sections * 30) // 60)
        return structure

    async def get_book_content(self, project_id: str) -> Optional[dict]:
        """Get full book content formatted for reading."""
        project = await self.get_project(project_id)
        if not project or not project.blueprint:
            return None

        bp = project.blueprint
        content = {
            "title": bp.title,
            "subtitle": bp.subtitle,
            "author": bp.author,
            "parts": [],
            "word_count": bp.actual_words,
            "page_count": bp.actual_pages,
        }

        for part in bp.parts:
            part_data = {
                "number": part.number,
                "title": part.title,
                "introduction": part.introduction,
                "chapters": [],
            }
            for chapter in part.chapters:
                ch_data = {
                    "number": chapter.number,
                    "title": chapter.title,
                    "introduction": chapter.introduction,
                    "sections": [],
                    "summary": chapter.summary,
                    "key_takeaways": chapter.key_takeaways,
                }
                for section in chapter.sections:
                    ch_data["sections"].append({
                        "number": section.number,
                        "title": section.title,
                        "content": section.content,
                        "word_count": section.word_count.actual,
                    })
                part_data["chapters"].append(ch_data)
            content["parts"].append(part_data)

        return content

    async def get_download_path(self, project_id: str, fmt: str = "docx") -> Optional[str]:
        """Get file path for a given output format."""
        project = await self.get_project(project_id)
        if not project or not project.output_files:
            return None
        return project.output_files.get(fmt)

    async def pause_project(self, project_id: str) -> bool:
        """Pause a running project."""
        if project_id in self._running_tasks:
            self._running_tasks[project_id].cancel()
            self._running_tasks.pop(project_id, None)
            if project_id in self._active_projects:
                self._active_projects[project_id].status = BookStatus.PAUSED
                await self._save_project(self._active_projects[project_id])
            return True
        return False

    # === Illustration (Sprint K) ===

    async def save_project(self, project: BookProject):
        """Public save method for route handlers."""
        await self._save_project(project)
        self._active_projects[project.id] = project

    async def analyze_images(self, project_id: str):
        """Run VisionAnalyzer on project images."""
        from core.book_writer_v2.agents.vision_analyzer import VisionAnalyzerAgent
        from core.book_writer_v2.agents.base import AgentContext

        project = await self.get_project(project_id)
        if not project or not project.uploaded_images:
            return None

        config = BookWriterConfig()
        agent = VisionAnalyzerAgent(config, self.ai_client)
        context = AgentContext(project_id=project_id, config=config)

        manifest = await agent.execute(
            {"image_paths": project.uploaded_images}, context
        )

        # Cache manifest to disk
        manifest_path = os.path.join(self.db_path, f"{project_id}_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        return manifest

    async def get_image_manifest(self, project_id: str):
        """Load cached image manifest."""
        from core.book_writer_v2.illustration_models import (
            ImageManifest, ImageAnalysis, ImageCategory, LayoutMode,
            ImageSize, BookGenre,
        )

        manifest_path = os.path.join(self.db_path, f"{project_id}_manifest.json")
        if not os.path.exists(manifest_path):
            return None

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        images = []
        for img_data in data.get("images", []):
            images.append(ImageAnalysis(
                image_id=img_data["image_id"],
                filename=img_data["filename"],
                filepath=img_data.get("filepath", ""),
                subject=img_data.get("subject", ""),
                description=img_data.get("description", ""),
                keywords=img_data.get("keywords", []),
                category=ImageCategory(img_data.get("category", "other")),
                width=img_data.get("width", 0),
                height=img_data.get("height", 0),
                file_size_bytes=img_data.get("file_size_bytes", 0),
                media_type=img_data.get("media_type", "image/jpeg"),
                quality_score=img_data.get("quality_score", 0.5),
                suggested_layout=LayoutMode(img_data.get("suggested_layout", "inline")),
                suggested_size=ImageSize(img_data.get("suggested_size", "medium")),
            ))

        return ImageManifest(
            images=images,
            detected_genre=BookGenre(data.get("detected_genre", "non_fiction")),
            total_images=len(images),
        )

    async def run_illustration_pipeline(self, project_id: str) -> dict:
        """Run the full illustration pipeline: analyze → match → plan."""
        from core.book_writer_v2.agents.illustrator import IllustratorAgent
        from core.book_writer_v2.agents.base import AgentContext

        project = await self.get_project(project_id)
        if not project:
            raise ValueError("Project not found")

        # Get or create manifest
        manifest = await self.get_image_manifest(project_id)
        if not manifest:
            manifest = await self.analyze_images(project_id)

        if not manifest or not manifest.images:
            raise ValueError("No images to illustrate with")

        config = BookWriterConfig()
        agent = IllustratorAgent(config, self.ai_client)
        context = AgentContext(project_id=project_id, config=config)

        plan = await agent.execute(
            {"project": project, "manifest": manifest}, context
        )

        project.illustration_plan = plan
        project.status = BookStatus.COMPLETED
        await self._save_project(project)
        self._active_projects[project_id] = project

        return plan.to_dict()

    async def update_illustration_plan(self, project_id: str, placements_data):
        """Update illustration plan with manual adjustments."""
        from core.book_writer_v2.illustration_models import (
            ImagePlacement, LayoutMode, ImageSize,
        )

        project = await self.get_project(project_id)
        if not project or not project.illustration_plan:
            raise ValueError("No illustration plan to update")

        if placements_data:
            new_placements = []
            for p in placements_data:
                new_placements.append(ImagePlacement(
                    image_id=p["image_id"],
                    chapter_index=p["chapter_index"],
                    section_index=p.get("section_index", 0),
                    paragraph_index=p.get("paragraph_index", 0),
                    layout_mode=LayoutMode(p.get("layout_mode", "inline")),
                    size=ImageSize(p.get("size", "medium")),
                    caption=p.get("caption", ""),
                    relevance_score=p.get("relevance_score", 0.5),
                ))
            project.illustration_plan.placements = new_placements

        await self._save_project(project)
        self._active_projects[project_id] = project
        return project.illustration_plan

    # === Persistence ===

    async def _save_project(self, project: BookProject):
        filepath = os.path.join(self.db_path, f"{project.id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(project.to_json())

    async def _load_project(self, project_id: str) -> Optional[BookProject]:
        filepath = os.path.join(self.db_path, f"{project_id}.json")
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            project = BookProject(
                id=data.get("id"),
                user_request=data.get("user_request", ""),
                user_description=data.get("user_description", ""),
                status=BookStatus(data.get("status", "created")),
                current_agent=data.get("current_agent", ""),
                current_task=data.get("current_task", ""),
                sections_completed=data.get("sections_completed", 0),
                sections_total=data.get("sections_total", 0),
                expansion_rounds=data.get("expansion_rounds", 0),
                output_files=data.get("output_files", {}),
                errors=data.get("errors", []),
                uploaded_images=data.get("uploaded_images", []),
            )

            # Restore illustration plan if present
            if data.get("illustration_plan"):
                try:
                    from core.book_writer_v2.illustration_models import IllustrationPlan
                    project.illustration_plan = IllustrationPlan.from_dict(
                        data["illustration_plan"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to restore illustration plan: {e}")

            if data.get("created_at"):
                project.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("updated_at"):
                project.updated_at = datetime.fromisoformat(data["updated_at"])
            if data.get("completed_at"):
                project.completed_at = datetime.fromisoformat(data["completed_at"])

            return project

        except Exception as e:
            logger.error(f"Failed to load project {project_id}: {e}")
            return None


# Singleton
_service: Optional[BookWriterV2Service] = None


def get_book_writer_v2_service(ai_client: Any = None) -> BookWriterV2Service:
    """Get or create the global service instance."""
    global _service
    if _service is None:
        _service = BookWriterV2Service(ai_client=ai_client)
    return _service
