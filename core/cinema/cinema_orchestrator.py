"""
Cinema Orchestrator - Main Book-to-Cinema Pipeline Controller

The central orchestrator that coordinates the entire book-to-cinema
conversion process with state persistence and resume capability.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from .models import (
    CinematicChunk,
    CinematicScene,
    Screenplay,
    VideoPrompt,
    RenderedVideo,
    CinemaStyle,
    StyleTemplate,
    CinemaJob,
    JobStatus,
)
from .cinema_chunker import CinemaChunker
from .scene_adapter import SceneAdapter
from .screenplay_writer import ScreenplayWriter
from .prompt_generator import CinemaPromptGenerator
from .video_renderer import VideoRenderer
from .video_assembler import VideoAssembler

logger = logging.getLogger(__name__)


class CinemaOrchestrator:
    """
    Main orchestrator for Book-to-Cinema conversion.
    
    Pipeline stages:
    1. CHUNKING: Split text into scene-sized segments
    2. ADAPTING: Extract cinematic elements from text
    3. WRITING_SCREENPLAY: Generate screenplay format
    4. GENERATING_PROMPTS: Create AI video prompts
    5. RENDERING: Generate videos via AI
    6. ASSEMBLING: Combine into final movie
    
    Features:
    - State persistence after each stage
    - Resume from any stage
    - Progress tracking callbacks
    - Multi-provider video rendering
    - Automatic retry on failures
    
    Environment Variables:
    - CINEMA_DEFAULT_PROVIDER: "veo" or "replicate" (default: "veo")
    - CINEMA_MIN_VIDEO_DURATION: seconds per scene (default: 30)
    - CINEMA_MAX_CONCURRENT_RENDERS: parallel renders (default: 3)
    - CINEMA_OUTPUT_DIR: output directory (default: "outputs/cinema")
    - CINEMA_DEFAULT_STYLE: default style (default: "blockbuster")
    """
    
    def __init__(
        self,
        llm_client: Any,
        video_provider: Optional[str] = None,
        output_dir: Optional[Path] = None,
        state_dir: Optional[Path] = None,
        language: str = "vi",
    ):
        """
        Initialize CinemaOrchestrator.
        
        Args:
            llm_client: AI client for text processing (Gemini, Claude, etc.)
            video_provider: Primary video AI provider ("veo", "replicate")
                           Defaults to CINEMA_DEFAULT_PROVIDER env var
            output_dir: Directory for output files
                       Defaults to CINEMA_OUTPUT_DIR env var
            state_dir: Directory for job state persistence
            language: Output language ("vi" or "en")
        """
        self.llm_client = llm_client
        self.language = language
        
        # Read from environment with fallbacks
        self.video_provider = video_provider or os.getenv("CINEMA_DEFAULT_PROVIDER", "veo")
        self.MIN_VIDEO_DURATION = int(os.getenv("CINEMA_MIN_VIDEO_DURATION", "30"))
        self.max_concurrent_renders = int(os.getenv("CINEMA_MAX_CONCURRENT_RENDERS", "3"))
        default_style_name = os.getenv("CINEMA_DEFAULT_STYLE", "blockbuster")
        
        # Try to get default style from env
        try:
            self.default_style = CinemaStyle(default_style_name)
        except ValueError:
            self.default_style = CinemaStyle.BLOCKBUSTER
        
        # Directories (from env or args)
        default_output = os.getenv("CINEMA_OUTPUT_DIR", "outputs/cinema")
        self.output_dir = output_dir or Path(default_output)
        self.state_dir = state_dir or self.output_dir / ".state"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.chunker = CinemaChunker(llm_client)
        self.scene_adapter = SceneAdapter(llm_client, language)
        self.screenplay_writer = ScreenplayWriter(llm_client, language)
        self.prompt_generator = CinemaPromptGenerator(
            templates_dir=Path(__file__).parent / "templates"
        )
        self.video_renderer = VideoRenderer(
            primary_provider=self.video_provider,
            output_dir=self.output_dir / "videos",
            max_concurrent=self.max_concurrent_renders,
        )
        self.video_assembler = VideoAssembler(
            output_dir=self.output_dir / "movies"
        )
    
    async def adapt_book(
        self,
        source: str,  # File path or text content
        title: str,
        author: str = "Unknown",
        style: CinemaStyle = CinemaStyle.BLOCKBUSTER,
        style_template: Optional[StyleTemplate] = None,
        progress_callback: Optional[Callable[[float, str, str], None]] = None,
        resume_job_id: Optional[str] = None,
    ) -> CinemaJob:
        """
        Main entry point: Convert a book into a cinematic video.
        
        Args:
            source: File path or raw text content
            title: Movie title
            author: Original author name
            style: Cinema style template
            style_template: Optional custom style template
            progress_callback: Called with (progress, stage, message)
            resume_job_id: Resume a previous job from saved state
            
        Returns:
            CinemaJob with all results and final video path
        """
        # Resume existing job or create new one
        if resume_job_id:
            job = self._load_job_state(resume_job_id)
            if not job:
                raise ValueError(f"Job {resume_job_id} not found")
            logger.info(f"Resuming job {job.job_id} from stage: {job.status.value}")
        else:
            job = CinemaJob(
                job_id=str(uuid.uuid4())[:8],
                source_path=Path(source) if len(source) < 500 else Path("inline_text"),
                output_dir=self.output_dir / f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                style=style,
                video_provider=self.video_provider,
                target_segment_duration=self.MIN_VIDEO_DURATION,
            )
            job.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load text content
        if len(source) < 500 and Path(source).exists():
            text = self._load_text_from_file(Path(source))
        else:
            text = source
        
        # Load style template if not provided
        if not style_template:
            style_template = self.prompt_generator.load_style_template(style)
        
        def update_progress(progress: float, stage: str, message: str = ""):
            job.progress = progress
            job.current_stage = stage
            if progress_callback:
                progress_callback(progress, stage, message)
        
        try:
            # Stage 1: Chunking (0-10%)
            if job.status.value in ["pending", "chunking"]:
                update_progress(0.01, "chunking", "Đang chia văn bản thành phân cảnh...")
                job.status = JobStatus.CHUNKING
                
                job.chunks = await self.chunker.chunk_for_cinema(text)
                logger.info(f"Created {len(job.chunks)} chunks")
                
                self._save_job_state(job)
                update_progress(0.10, "chunking", f"Đã chia thành {len(job.chunks)} phân cảnh")
            
            # Stage 2: Scene Adaptation (10-30%)
            if job.status.value in ["chunking", "adapting"]:
                update_progress(0.11, "adapting", "Đang phân tích và trích xuất yếu tố điện ảnh...")
                job.status = JobStatus.ADAPTING
                
                job.scenes = await self.scene_adapter.adapt_chunks(
                    chunks=job.chunks,
                    style=style,
                    style_template=style_template,
                    progress_callback=lambda i, t: update_progress(
                        0.10 + (i / t) * 0.20,
                        "adapting",
                        f"Đang xử lý phân cảnh {i}/{t}"
                    ),
                )
                
                self._save_job_state(job)
                update_progress(0.30, "adapting", f"Đã tạo {len(job.scenes)} scene điện ảnh")
            
            # Stage 3: Screenplay Writing (30-50%)
            if job.status.value in ["adapting", "writing_screenplay"]:
                update_progress(0.31, "writing_screenplay", "Đang viết kịch bản điện ảnh...")
                job.status = JobStatus.WRITING_SCREENPLAY
                
                job.screenplay = await self.screenplay_writer.write_screenplay(
                    scenes=job.scenes,
                    title=title,
                    author=author,
                    style=style,
                    style_template=style_template,
                    progress_callback=lambda i, t: update_progress(
                        0.30 + (i / t) * 0.20,
                        "writing_screenplay",
                        f"Đang viết scene {i}/{t}"
                    ),
                )
                
                # Save screenplay to file
                screenplay_path = job.output_dir / f"{title}_screenplay.txt"
                screenplay_path.write_text(job.screenplay.to_text(), encoding="utf-8")
                
                # Also save Fountain format
                fountain_path = job.output_dir / f"{title}_screenplay.fountain"
                fountain_path.write_text(
                    self.screenplay_writer.export_to_fountain(job.screenplay),
                    encoding="utf-8"
                )
                
                self._save_job_state(job)
                update_progress(0.50, "writing_screenplay", "Đã hoàn thành kịch bản")
            
            # Stage 4: Prompt Generation (50-55%)
            if job.status.value in ["writing_screenplay", "generating_prompts"]:
                update_progress(0.51, "generating_prompts", "Đang tạo prompts cho AI video...")
                job.status = JobStatus.GENERATING_PROMPTS
                
                screenplay_scenes = job.screenplay.scenes if job.screenplay else None
                
                job.prompts = self.prompt_generator.generate_prompts_for_scenes(
                    scenes=job.scenes,
                    screenplay_scenes=screenplay_scenes,
                    style=style,
                    style_template=style_template,
                    provider=self.video_provider,
                    duration_per_scene=self.MIN_VIDEO_DURATION,
                )
                
                # Save prompts to file
                prompts_path = job.output_dir / "video_prompts.json"
                prompts_data = [p.to_dict() for p in job.prompts]
                prompts_path.write_text(json.dumps(prompts_data, indent=2, ensure_ascii=False))
                
                self._save_job_state(job)
                update_progress(0.55, "generating_prompts", f"Đã tạo {len(job.prompts)} prompts")
            
            # Stage 5: Video Rendering (55-90%)
            if job.status.value in ["generating_prompts", "rendering"]:
                update_progress(0.56, "rendering", "Đang render video với AI...")
                job.status = JobStatus.RENDERING
                
                job.videos = await self.video_renderer.render_scenes(
                    prompts=job.prompts,
                    scenes=job.scenes,
                    progress_callback=lambda i, t: update_progress(
                        0.55 + (i / t) * 0.35,
                        "rendering",
                        f"Đang render video {i}/{t}"
                    ),
                )
                
                self._save_job_state(job)
                successful = sum(1 for v in job.videos if v.success)
                update_progress(0.90, "rendering", f"Đã render {successful}/{len(job.videos)} video")
            
            # Stage 6: Assembly (90-100%)
            if job.status.value in ["rendering", "assembling"]:
                update_progress(0.91, "assembling", "Đang ghép video thành phim hoàn chỉnh...")
                job.status = JobStatus.ASSEMBLING
                
                # Check if FFmpeg is available
                if self.video_assembler.is_available():
                    transition = style_template.default_transitions if style_template else "crossfade"
                    
                    job.final_video_path = await self.video_assembler.assemble(
                        videos=job.videos,
                        output_name=f"{title}_{job.job_id}",
                        transition=transition,
                    )
                else:
                    # FFmpeg not available - just use first video as "final"
                    logger.warning("FFmpeg not available, skipping video assembly")
                    successful_videos = [v for v in job.videos if v.success]
                    if successful_videos:
                        job.final_video_path = successful_videos[0].video_path
                    else:
                        job.final_video_path = None
                
                self._save_job_state(job)
                update_progress(0.98, "assembling", "Đang hoàn thiện...")
            
            # Complete
            job.status = JobStatus.COMPLETE
            job.completed_at = datetime.now()
            self._save_job_state(job)
            
            update_progress(1.0, "complete", f"Hoàn thành! Video: {job.final_video_path}")
            logger.info(f"Job {job.job_id} completed: {job.final_video_path}")
            
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            self._save_job_state(job)
            raise
        
        return job
    
    def _load_text_from_file(self, file_path: Path) -> str:
        """Load text from various file formats."""
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt":
            return file_path.read_text(encoding="utf-8")
        
        elif suffix == ".pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                return text
            except ImportError:
                raise RuntimeError("PyMuPDF (fitz) required for PDF files")
        
        elif suffix == ".docx":
            try:
                from docx import Document
                doc = Document(file_path)
                return "\n\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                raise RuntimeError("python-docx required for DOCX files")
        
        elif suffix == ".epub":
            try:
                import ebooklib
                from ebooklib import epub
                from bs4 import BeautifulSoup
                
                book = epub.read_epub(file_path)
                text = ""
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        soup = BeautifulSoup(item.get_content(), "html.parser")
                        text += soup.get_text() + "\n\n"
                return text
            except ImportError:
                raise RuntimeError("ebooklib and beautifulsoup4 required for EPUB files")
        
        else:
            # Try as plain text
            return file_path.read_text(encoding="utf-8")
    
    def _save_job_state(self, job: CinemaJob) -> None:
        """Save job state for resume capability."""
        state_path = self.state_dir / f"{job.job_id}.json"
        
        state = {
            "job_id": job.job_id,
            "source_path": str(job.source_path),
            "output_dir": str(job.output_dir),
            "style": job.style.value,
            "video_provider": job.video_provider,
            "status": job.status.value,
            "progress": job.progress,
            "current_stage": job.current_stage,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            # Serialized results
            "chunks_count": len(job.chunks),
            "scenes_count": len(job.scenes),
            "prompts_count": len(job.prompts),
            "videos_count": len(job.videos),
            "final_video_path": str(job.final_video_path) if job.final_video_path else None,
            # Detailed data for resume
            "chunks": [{"id": c.chunk_id, "text": c.text[:500]} for c in job.chunks],
            "scenes": [s.to_dict() for s in job.scenes],
            "prompts": [p.to_dict() for p in job.prompts],
            "videos": [
                {
                    "scene_id": v.scene_id,
                    "path": str(v.video_path) if v.video_path else None,
                    "success": v.success,
                    "error": v.error_message,
                }
                for v in job.videos
            ],
        }
        
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        logger.debug(f"Saved job state: {state_path}")
    
    def _load_job_state(self, job_id: str) -> Optional[CinemaJob]:
        """Load job state for resume."""
        state_path = self.state_dir / f"{job_id}.json"
        
        if not state_path.exists():
            return None
        
        try:
            state = json.loads(state_path.read_text())
            
            job = CinemaJob(
                job_id=state["job_id"],
                source_path=Path(state["source_path"]),
                output_dir=Path(state["output_dir"]),
                style=CinemaStyle(state["style"]),
                video_provider=state["video_provider"],
                status=JobStatus(state["status"]),
                progress=state["progress"],
                current_stage=state["current_stage"],
                error=state.get("error"),
                created_at=datetime.fromisoformat(state["created_at"]),
            )
            
            if state.get("completed_at"):
                job.completed_at = datetime.fromisoformat(state["completed_at"])
            
            if state.get("final_video_path"):
                job.final_video_path = Path(state["final_video_path"])
            
            # Restore chunks
            job.chunks = [
                CinematicChunk(
                    chunk_id=c["id"],
                    text=c["text"],
                )
                for c in state.get("chunks", [])
            ]
            
            # Note: Full scene/prompt/video restoration would require
            # re-loading from detailed saved data or re-processing
            
            logger.info(f"Loaded job state: {job_id}, status: {job.status.value}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to load job state {job_id}: {e}")
            return None
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all saved jobs."""
        jobs = []
        for state_file in self.state_dir.glob("*.json"):
            try:
                state = json.loads(state_file.read_text())
                jobs.append({
                    "job_id": state["job_id"],
                    "status": state["status"],
                    "progress": state["progress"],
                    "created_at": state["created_at"],
                    "style": state["style"],
                })
            except Exception:
                continue
        
        return sorted(jobs, key=lambda j: j["created_at"], reverse=True)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed job information."""
        state_path = self.state_dir / f"{job_id}.json"
        if state_path.exists():
            return json.loads(state_path.read_text())
        return None
    
    async def retry_failed_videos(self, job_id: str) -> CinemaJob:
        """Retry rendering for failed video segments."""
        job = self._load_job_state(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Find failed videos
        failed_prompts = [
            p for p, v in zip(job.prompts, job.videos)
            if not v.success
        ]
        
        if not failed_prompts:
            logger.info("No failed videos to retry")
            return job
        
        logger.info(f"Retrying {len(failed_prompts)} failed videos")
        
        # Re-render failed segments
        new_videos = await self.video_renderer.render_scenes(
            prompts=failed_prompts,
            scenes=[s for s in job.scenes if s.scene_id in [p.scene_id for p in failed_prompts]],
        )
        
        # Update job with new results
        video_dict = {v.scene_id: v for v in job.videos}
        for new_video in new_videos:
            video_dict[new_video.scene_id] = new_video
        
        job.videos = list(video_dict.values())
        self._save_job_state(job)
        
        return job
