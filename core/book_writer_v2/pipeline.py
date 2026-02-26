"""
Book Writer v2.0 Pipeline

Main orchestrator that coordinates all agents.
"""

import logging
import os
from typing import Optional, Callable, Any
from datetime import datetime

from .config import BookWriterConfig
from .models import BookProject, BookStatus
from .exceptions import BookWriterError
from .agents import (
    AnalystAgent, ArchitectAgent, OutlinerAgent,
    WriterAgent, ExpanderAgent, EnricherAgent,
    EditorAgent, QualityGateAgent, PublisherAgent,
)
from .agents.base import AgentContext
from .agents.illustrator import IllustratorAgent

_PIPELINE_PHASES = ["analysis", "outline", "writing", "expansion", "editing", "enriching", "quality", "publishing"]


class BookWriterPipeline:
    """
    Main pipeline orchestrator for Book Writer v2.0.

    Coordinates the 9-agent pipeline to produce books
    that meet exact page count targets.

    Usage:
        pipeline = BookWriterPipeline(config, ai_client)
        project = await pipeline.create_book(
            title="My Book",
            description="A book about...",
            target_pages=300
        )
    """

    def __init__(
        self,
        config: BookWriterConfig,
        ai_client: Any,
        progress_callback: Optional[Callable[[str, str, float], None]] = None,
    ):
        self.config = config
        self.ai = ai_client
        self.progress_callback = progress_callback
        self.logger = logging.getLogger("BookWriter.Pipeline")

        # Checkpointing
        self._checkpoint_mgr = None
        if config.enable_auto_save:
            try:
                from core.cache.checkpoint_manager import CheckpointManager
                self._checkpoint_mgr = CheckpointManager()
            except Exception as e:
                self.logger.warning(f"Checkpoint manager unavailable: {e}")

        # Initialize agents
        self.analyst = AnalystAgent(config, ai_client)
        self.architect = ArchitectAgent(config, ai_client)
        self.outliner = OutlinerAgent(config, ai_client)
        self.writer = WriterAgent(config, ai_client)
        self.expander = ExpanderAgent(config, ai_client)
        self.enricher = EnricherAgent(config, ai_client)
        self.editor = EditorAgent(config, ai_client)
        self.quality_gate = QualityGateAgent(config, ai_client)
        self.publisher = PublisherAgent(config, ai_client)
        self.illustrator = IllustratorAgent(config, ai_client)

    def _save_checkpoint(self, project: BookProject, phase: str, completed_phases: list[str]):
        """Save pipeline checkpoint after a major phase completes."""
        if self._checkpoint_mgr is None:
            return
        try:
            self._checkpoint_mgr.save_checkpoint(
                job_id=project.id,
                input_file=project.user_request,
                output_file=self.config.output_dir,
                total_chunks=len(_PIPELINE_PHASES),
                completed_chunk_ids=completed_phases,
                results_data={"phase": phase, "status": project.status.value},
                job_metadata={"current_agent": project.current_agent},
            )
        except Exception as e:
            self.logger.warning(f"Checkpoint save failed at {phase}: {e}")

    def _delete_checkpoint(self, project_id: str):
        """Remove checkpoint on successful completion."""
        if self._checkpoint_mgr is None:
            return
        try:
            self._checkpoint_mgr.delete_checkpoint(project_id)
        except Exception as e:
            self.logger.warning(f"Checkpoint delete failed: {e}")

    async def create_book(
        self,
        title: str,
        description: str,
        target_pages: int = 300,
        genre: str = "non-fiction",
        audience: str = "",
        subtitle: str = "",
        project: Optional["BookProject"] = None,
    ) -> BookProject:
        """
        Create a complete book.

        This is the main entry point. It orchestrates all 9 agents
        to produce a book meeting the exact page count target.
        """
        if project is None:
            project = BookProject(
                user_request=f"{title}: {description}",
                user_description=description,
            )

        self.logger.info(f"Starting book project: {project.id}")
        self._report_progress(project.id, "Starting book creation...", 0)
        completed_phases: list[str] = []

        try:
            context = AgentContext(
                project_id=project.id,
                config=self.config,
                progress_callback=lambda msg, pct: self._report_progress(
                    project.id, msg, pct
                ),
            )

            # === PHASE 1: PLANNING ===

            # Agent 1: Analyst
            project.status = BookStatus.ANALYZING
            project.current_agent = "Analyst"
            self._report_progress(project.id, "Analyzing book topic...", 5)

            analysis = await self.analyst.execute({
                "title": title,
                "description": description,
                "target_pages": target_pages,
                "genre": genre,
                "audience": audience,
            }, context)

            project.analysis = analysis
            completed_phases.append("analysis")
            self._save_checkpoint(project, "analysis", completed_phases)

            # Agent 2: Architect
            project.status = BookStatus.ARCHITECTING
            project.current_agent = "Architect"
            self._report_progress(project.id, "Designing book structure...", 10)

            blueprint = await self.architect.execute({
                "title": title,
                "subtitle": subtitle,
                "target_pages": target_pages,
                "analysis": analysis,
                "genre": genre,
            }, context)

            project.blueprint = blueprint
            project.sections_total = blueprint.total_sections

            # Agent 3: Outliner
            project.status = BookStatus.OUTLINING
            project.current_agent = "Outliner"
            self._report_progress(project.id, "Creating detailed outlines...", 15)

            blueprint = await self.outliner.execute(blueprint, context)
            completed_phases.append("outline")
            self._save_checkpoint(project, "outline", completed_phases)

            # === PHASE 2: WRITING ===

            # Agent 4: Writer
            project.status = BookStatus.WRITING
            project.current_agent = "Writer"
            self._report_progress(project.id, "Writing content...", 25)

            blueprint = await self.writer.execute(blueprint, context)
            project.update_progress()
            completed_phases.append("writing")
            self._save_checkpoint(project, "writing", completed_phases)

            # Agent 5: Expander (may run multiple rounds)
            project.status = BookStatus.EXPANDING
            project.current_agent = "Expander"

            for round_num in range(self.config.max_total_expansion_rounds):
                sections_needing_expansion = blueprint.get_sections_needing_expansion()

                if not sections_needing_expansion:
                    break

                self._report_progress(
                    project.id,
                    f"Expansion round {round_num + 1}: {len(sections_needing_expansion)} sections",
                    45 + (round_num * 5)
                )

                blueprint = await self.expander.execute(blueprint, context)
                project.expansion_rounds += 1
                project.update_progress()

            completed_phases.append("expansion")
            self._save_checkpoint(project, "expansion", completed_phases)

            # === PHASE 3: ENHANCEMENT ===

            # Agent 6: Enricher
            project.status = BookStatus.ENRICHING
            project.current_agent = "Enricher"
            self._report_progress(project.id, "Enriching content...", 65)

            blueprint = await self.enricher.execute(blueprint, context)

            # Agent 7: Editor
            project.status = BookStatus.EDITING
            project.current_agent = "Editor"
            self._report_progress(project.id, "Editing and polishing...", 75)

            blueprint = await self.editor.execute(blueprint, context)
            project.update_progress()
            completed_phases.extend(["enriching", "editing"])
            self._save_checkpoint(project, "editing", completed_phases)

            # === PHASE 4: QUALITY GATE ===

            project.status = BookStatus.QUALITY_CHECK
            project.current_agent = "QualityGate"
            self._report_progress(project.id, "Running quality checks...", 85)

            quality_result = await self.quality_gate.execute(blueprint, context)
            project.quality_checks.append(quality_result)

            if not quality_result.passed:
                self.logger.warning(f"Quality check failed: {quality_result.issues}")

                if any("word count" in issue.lower() for issue in quality_result.issues):
                    self._report_progress(project.id, "Additional expansion needed...", 87)
                    blueprint = await self.expander.execute(blueprint, context)
                    project.expansion_rounds += 1

                    quality_result = await self.quality_gate.execute(blueprint, context)
                    project.quality_checks.append(quality_result)

            # === PHASE 4b: ILLUSTRATION (optional) ===

            if project.has_images():
                project.status = BookStatus.ILLUSTRATING
                project.current_agent = "Illustrator"
                self._report_progress(project.id, "Planning illustrations...", 88)

                # Load manifest if available
                manifest = None
                try:
                    import json as _json
                    manifest_path = f"data/books_v2/{project.id}_manifest.json"
                    if os.path.exists(manifest_path):
                        from .illustration_models import (
                            ImageManifest, ImageAnalysis, ImageCategory,
                            LayoutMode, ImageSize, BookGenre,
                        )
                        with open(manifest_path) as _f:
                            mdata = _json.load(_f)
                        images = []
                        for img_data in mdata.get("images", []):
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
                                quality_score=img_data.get("quality_score", 0.5),
                                suggested_layout=LayoutMode(img_data.get("suggested_layout", "inline")),
                                suggested_size=ImageSize(img_data.get("suggested_size", "medium")),
                            ))
                        manifest = ImageManifest(
                            images=images,
                            detected_genre=BookGenre(mdata.get("detected_genre", "non_fiction")),
                            total_images=len(images),
                        )
                except Exception as e:
                    self.logger.warning(f"Failed to load manifest: {e}")

                if manifest and manifest.images:
                    illus_plan = await self.illustrator.execute(
                        {"project": project, "manifest": manifest}, context
                    )
                    project.illustration_plan = illus_plan

            # === PHASE 5: PUBLISHING ===

            project.status = BookStatus.PUBLISHING
            project.current_agent = "Publisher"
            self._report_progress(project.id, "Generating output files...", 90)

            output_files = await self.publisher.execute(project, context)
            project.output_files = output_files

            # === COMPLETE ===

            project.status = BookStatus.COMPLETED
            project.current_agent = ""
            project.completed_at = datetime.now()
            project.update_progress()

            self._report_progress(project.id, "Book creation complete!", 100)
            self._delete_checkpoint(project.id)

            self.logger.info(
                f"Book completed: {project.id} | "
                f"Pages: {blueprint.actual_pages}/{blueprint.target_pages} | "
                f"Words: {blueprint.actual_words:,}/{blueprint.target_words:,} | "
                f"Completion: {blueprint.completion:.1f}%"
            )

            return project

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            project.status = BookStatus.FAILED
            project.add_error(str(e), project.current_agent, recoverable=False)
            # Keep checkpoint on failure so the job can be resumed later
            self._save_checkpoint(project, "failed", completed_phases)
            raise BookWriterError(f"Book creation failed: {e}")

    def _report_progress(self, project_id: str, message: str, percentage: float):
        """Report progress via callback"""
        if self.progress_callback:
            try:
                self.progress_callback(project_id, message, percentage)
            except Exception as e:
                self.logger.warning(f"Progress callback error: {e}")
