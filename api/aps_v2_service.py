"""
APS V2 Service

Service layer connecting API to core_v2 UniversalPublisher.
"""

import asyncio
import logging
import uuid
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

from api.services.eqs import ExtractionQualityScorer
from api.services.extraction_feedback import (
    ExtractionFeedbackLoop,
    ExtractionStrategy as EQSStrategy,
    FeedbackAction,
)
from api.services.provider_stats import ProviderStatsTracker, CallRecord
from api.services.provider_router import ProviderRouter, RoutingMode
from api.services.consistency_checker import ConsistencyChecker
from api.services.layout_analyzer import LayoutAnalyzer
from api.services.epub_renderer import EpubRenderer, is_available as epub_available

from .job_repository import get_job_repository, JobRepository

from core_v2 import (
    UniversalPublisher,
    PublishingJob,
    DocumentDNA,
    PROFILES,
    SemanticChunk,
)
from core_v2.publishing_profiles import get_profile, list_profiles
from core_v2.orchestrator import JobStatus as CoreJobStatus

from .aps_v2_models import (
    JobStatusV2,
    JobResponseV2,
    DocumentDNAResponse,
    PublishingProfileResponse,
    UsageStatsResponse,
)

# Import unified client for auto-fallback
from ai_providers.unified_client import (
    UnifiedLLMClient,
    get_unified_client,
    validate_providers_before_job,
    AllProvidersUnavailableError,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class LLMClientAdapter:
    """
    Adapter that delegates to UnifiedLLMClient for auto-fallback support.

    core_v2 expects an llm_client with async chat() method.
    This adapter provides that interface while using the unified
    fallback logic from ai_providers.unified_client.
    """

    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self._unified_client = UnifiedLLMClient(preferred_provider=provider, api_key=api_key)

    async def chat(self, messages: List[Dict], response_format: Optional[Dict] = None, max_tokens: int = 8192) -> Any:
        """
        Send chat request to LLM with automatic fallback.
        Delegates to UnifiedLLMClient which handles all fallback logic.
        """
        try:
            return await self._unified_client.chat(
                messages=messages,
                max_tokens=max_tokens,
                response_format=response_format
            )
        except AllProvidersUnavailableError as e:
            # Re-raise with clear message
            raise RuntimeError(str(e))

    async def validate_provider(self, provider: str) -> tuple:
        """Test if a provider's API key is valid."""
        health = await self._unified_client.validate_provider(provider)
        if health.status == ProviderStatus.AVAILABLE:
            return True, ""
        return False, f"{health.status.value}: {health.error}"

    async def auto_select_provider(self) -> str:
        """Automatically select the best available provider."""
        return await self._unified_client.auto_select_provider()

    def get_current_provider(self) -> str:
        """Get the currently active provider."""
        return self._unified_client.get_current_provider() or "none"

    def get_failed_providers(self) -> list:
        """Get list of providers that have failed."""
        return self._unified_client.get_failed_providers()

    async def get_status(self) -> Dict:
        """Get detailed status of all providers."""
        return await self._unified_client.get_status_summary()

    def get_usage_stats(self) -> Dict:
        """Get usage statistics."""
        return self._unified_client.get_usage_dict()

    def reset_usage_stats(self):
        """Reset usage statistics (call at job start)."""
        self._unified_client.reset_usage_stats()

    # Keep property for backward compatibility
    @property
    def provider(self) -> str:
        return self._unified_client.get_current_provider() or "openai"

    @property
    def PROVIDER_ORDER(self) -> List[str]:
        return self._unified_client.PROVIDER_ORDER


class APSV2Service:
    """
    APS V2 Service

    Manages publishing jobs using the Claude-Native pipeline.
    """

    def __init__(
        self,
        output_dir: str = "outputs/v2",
        upload_dir: str = "uploads/v2",
        provider: str = "openai",
        base_dir: str = None,
    ):
        # Base directory for resolving relative paths
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent

        self.output_dir = Path(output_dir)
        self.upload_dir = Path(upload_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        self.provider = provider

        # Job storage - now backed by SQLite
        self._jobs: Dict[str, Dict] = {}
        self._job_tasks: Dict[str, asyncio.Task] = {}
        self._last_db_update: Dict[str, float] = {}  # Throttle DB writes
        self._db_update_interval = 2.0  # Min seconds between DB updates per job

        # Database repository
        self._repo: JobRepository = get_job_repository()

        # Load existing jobs from database
        self._load_jobs_from_db()

        # LLM client
        self._llm_client: Optional[LLMClientAdapter] = None
        self._publisher: Optional[UniversalPublisher] = None

        # EQS — Extraction Quality Scoring (Sprint 9)
        self._eqs_scorer = ExtractionQualityScorer()
        self._eqs_feedback = ExtractionFeedbackLoop(
            min_score=0.7, max_retries=3, scorer=self._eqs_scorer,
        )
        self._last_eqs_report: Optional[Dict] = None  # per-extraction metadata

        # QAPR — Quality-Aware Provider Routing (Sprint 10)
        self._provider_stats = ProviderStatsTracker(
            persist_path=str(self.base_dir / "data" / "provider_stats.json"),
        )
        self._provider_router = ProviderRouter(
            stats_tracker=self._provider_stats,
            mode=RoutingMode.BALANCED,
        )
        self._last_routing_decision: Optional[Dict] = None

        # Consistency Checker (Sprint 11)
        self._consistency_checker = ConsistencyChecker()

        # Layout Analyzer (Sprint 12)
        self._layout_analyzer = LayoutAnalyzer()

        logger.info(f"APSV2Service initialized: output={self.output_dir}, jobs loaded: {len(self._jobs)}")

    def _load_jobs_from_db(self):
        """Load jobs from database on startup."""
        try:
            all_jobs = self._repo.get_all_jobs(limit=100)
            for job in all_jobs:
                self._jobs[job["job_id"]] = job
                logger.debug(f"Loaded job from DB: {job['job_id']} ({job['status']})")

            logger.info(f"Loaded {len(all_jobs)} jobs from database")
        except Exception as e:
            logger.error(f"Failed to load jobs from database: {e}")

    def _ensure_publisher(self):
        """Ensure publisher is initialized."""
        if self._publisher is None:
            self._llm_client = LLMClientAdapter(self.provider)
            self._publisher = UniversalPublisher(
                llm_client=self._llm_client,
                output_dir=self.output_dir,
                concurrency=5,  # Parallel translation for faster processing
            )

    # ==================== JOB MANAGEMENT ====================

    async def create_job(
        self,
        source_file: str,
        content: str,
        source_language: str,
        target_language: str,
        profile_id: str,
        output_formats: List[str],
        use_vision: bool = True,  # NEW: Use Claude Vision for PDF reading
        api_key: Optional[str] = None,  # User-provided API key
        docx_template: str = "auto",  # DOCX template (ebook/academic/business/auto)
        pdf_template: str = "auto",  # PDF template (ebook/academic/business/auto)
        provider: Optional[str] = None,  # AI provider: 'openai', 'anthropic'
        model: Optional[str] = None,  # Model name (e.g., 'gpt-4o', 'claude-sonnet-4-20250514')
    ) -> Dict:
        """Create and start a new publishing job."""

        self._ensure_publisher()

        # Generate job ID
        job_id = str(uuid.uuid4())[:8]

        # Save content to file for resume capability
        content_path = self.upload_dir / f"{job_id}_content.txt"
        content_path.write_text(content, encoding='utf-8')

        # Create job record
        job_record = {
            "job_id": job_id,
            "source_file": source_file,
            "source_language": source_language,
            "target_language": target_language,
            "profile_id": profile_id,
            "output_formats": output_formats,
            "use_vision": use_vision,
            "docx_template": docx_template,  # DOCX template (ebook/academic/business/auto)
            "pdf_template": pdf_template,  # PDF template (ebook/academic/business/auto)
            "provider": provider,  # AI provider selection
            "model": model,  # Model name
            "status": JobStatusV2.PENDING,
            "progress": 0.0,
            "current_stage": "",
            "error": None,
            "dna": None,
            "chunks": [],
            "translated_chunks": [],
            "output_paths": {},
            "verification": None,
            "content_path": str(content_path),  # For resume
            "created_at": datetime.now(),
            "completed_at": None,
            # Usage tracking
            "usage_stats": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_elapsed_seconds": 0.0,
                "total_calls": 0,
                "estimated_cost_usd": 0.0,
                "calls_by_provider": {},
            },
            "job_start_time": time.time(),
            # NOTE: api_key intentionally NOT stored in job record (security)
            "eqs": self._last_eqs_report,  # EQS extraction quality (Sprint 9)
        }

        # Save to database FIRST
        self._repo.save(job_record)
        self._jobs[job_id] = job_record

        # Start processing in background with Vision mode
        task = asyncio.create_task(self._process_job(
            job_id, content, use_vision=use_vision, api_key=api_key,
            docx_template=docx_template, pdf_template=pdf_template,
            provider=provider, model=model
        ))
        self._job_tasks[job_id] = task

        logger.info(f"[{job_id}] Job created: {source_file} ({profile_id}) vision={use_vision} provider={provider} model={model}")

        return job_record

    async def _process_job(self, job_id: str, content: str, use_vision: bool = True, api_key: Optional[str] = None, docx_template: str = "auto", pdf_template: str = "auto", provider: Optional[str] = None, model: Optional[str] = None):
        """Process job in background."""
        job = self._jobs.get(job_id)
        if not job:
            return

        # Determine provider to use
        use_provider = provider or self.provider
        if model:
            # Auto-detect provider from model name
            if 'claude' in model.lower():
                use_provider = 'anthropic'
            elif 'gpt' in model.lower():
                use_provider = 'openai'

        # QAPR: data-driven provider routing when no explicit provider given
        routing_decision = None
        if not provider and not model:
            try:
                lang_pair = f"{job.get('source_language', '*')}→{job.get('target_language', '*')}"
                doc_type = job.get("profile_id", "general")
                routing_decision = self._provider_router.select(
                    language_pair=lang_pair,
                    document_type=doc_type,
                )
                use_provider = routing_decision.provider
                self._last_routing_decision = routing_decision.to_dict()
                logger.info(
                    f"[{job_id}] QAPR selected provider={use_provider} "
                    f"(score={routing_decision.score:.3f}, mode={routing_decision.mode.value})"
                )
            except Exception as exc:
                logger.warning(f"[{job_id}] QAPR routing failed, using default: {exc}")
                self._last_routing_decision = None

        # If user provided API key or specific provider, create a temporary client/publisher for this job
        publisher = self._publisher
        llm_client = self._llm_client
        if api_key or provider:
            logger.info(f"[{job_id}] Using provider={use_provider}, model={model or 'default'}")
            llm_client = LLMClientAdapter(use_provider, api_key=api_key)
            publisher = UniversalPublisher(
                llm_client=llm_client,
                output_dir=self.output_dir,
                concurrency=5,
            )

        # Reset usage stats at job start
        if llm_client:
            llm_client.reset_usage_stats()

        try:
            def progress_callback(progress: float, stage: str):
                job["progress"] = progress * 100  # Convert to percentage
                job["current_stage"] = stage
                job["status"] = "running"
                logger.debug(f"[{job_id}] {progress*100:.1f}% - {stage}")

                # Sync usage stats from LLM client
                if llm_client:
                    job["usage_stats"] = llm_client.get_usage_stats()

                # Throttled DB update (every 2 seconds max)
                now = time.time()
                last_update = self._last_db_update.get(job_id, 0)
                if now - last_update >= self._db_update_interval:
                    self._repo.update_progress(job_id, job["progress"], stage)
                    self._last_db_update[job_id] = now

                    # Broadcast progress via WebSocket
                    try:
                        from api.deps import manager
                        loop = asyncio.get_event_loop()
                        loop.call_soon_threadsafe(
                            asyncio.ensure_future,
                            manager.broadcast({
                                "event": "job_progress",
                                "job_id": job_id,
                                "progress": job["progress"],
                                "stage": stage,
                                "status": "running",
                            })
                        )
                    except Exception:
                        pass  # WebSocket broadcast is best-effort

            # Run the publisher pipeline (first format for main processing)
            first_format = job["output_formats"][0] if job["output_formats"] else "docx"
            # Use source filename (without extension) as title fallback
            source_file = job.get("source_file", "")
            title_fallback = source_file.rsplit(".", 1)[0] if source_file else ""
            result = await publisher.publish(
                source_text=content,
                source_lang=job["source_language"],
                target_lang=job["target_language"],
                profile_id=job["profile_id"],
                output_format=first_format,
                progress_callback=progress_callback,
                use_vision=use_vision,  # NEW: Pass Vision mode flag
                docx_template=docx_template,  # Professional DOCX template
                pdf_template=pdf_template,  # Professional PDF template
                title_fallback=title_fallback,
            )

            # Update job with results
            job["status"] = JobStatusV2.COMPLETE if result.status == CoreJobStatus.COMPLETE else JobStatusV2.FAILED
            job["progress"] = 100.0
            job["current_stage"] = "Complete"
            job["completed_at"] = datetime.now()

            # Final sync of usage stats
            if llm_client:
                job["usage_stats"] = llm_client.get_usage_stats()

            if result.dna:
                job["dna"] = result.dna

            if result.chunks:
                job["chunks"] = result.chunks

            # Handle first output format
            if result.output_path:
                job["output_paths"][first_format] = str(result.output_path)

            # Generate additional output formats if requested
            if len(job["output_formats"]) > 1 and result.assembled_content:
                from core_v2.output_converter import OutputConverter, OutputFormat
                converter = OutputConverter()

                # Check if document has formulas
                has_formulas = False
                if result.dna:
                    has_formulas = result.dna.has_formulas
                if not has_formulas:
                    formula_patterns = ['$', '\\begin{equation}', '\\frac', '\\sum', '\\int']
                    has_formulas = any(p in result.assembled_content for p in formula_patterns)

                for fmt in job["output_formats"][1:]:
                    try:
                        # Sprint 13: Use LayoutDNA-aware EPUB renderer
                        if fmt == "epub" and epub_available() and job.get("layout_dna"):
                            from api.services.layout_dna import LayoutDNA
                            base_name = f"{job_id}_translated"
                            output_path = self.output_dir / f"{base_name}.epub"
                            dna = LayoutDNA.from_dict(job["layout_dna"])
                            epub_renderer = EpubRenderer()
                            epub_renderer.render(
                                layout_dna=dna,
                                output_path=str(output_path),
                                title=result.dna.title if result.dna else "Document",
                                author=result.dna.author if result.dna else "",
                                language=job.get("target_language", "en"),
                            )
                            job["output_paths"]["epub"] = str(output_path)
                            logger.info(f"[{job_id}] EPUB created via LayoutDNA renderer")
                            continue

                        format_enum = OutputFormat(fmt)
                        base_name = f"{job_id}_translated"
                        output_path = self.output_dir / f"{base_name}.{fmt}"
                        success = await converter.convert(
                            content=result.assembled_content,
                            output_format=format_enum,
                            output_path=output_path,
                            title=result.dna.title if result.dna else "Document",
                            author=result.dna.author if result.dna else "",
                            has_formulas=has_formulas,
                        )
                        if success:
                            job["output_paths"][fmt] = str(output_path)
                            logger.info(f"[{job_id}] Additional format created: {fmt}")
                    except Exception as e:
                        logger.warning(f"[{job_id}] Failed to create {fmt}: {e}")

            if result.verification:
                job["verification"] = result.verification

            # Consistency check (Sprint 11) — read-only analysis, non-blocking
            try:
                if (result.chunks and result.translated_chunks
                        and len(result.translated_chunks) >= 2):
                    source_texts = [
                        c.content if hasattr(c, 'content') else str(c)
                        for c in result.chunks
                    ]
                    consistency_report = self._consistency_checker.check(
                        source_chunks=source_texts,
                        translated_chunks=result.translated_chunks,
                        source_language=job.get("source_language", "en"),
                        target_language=job.get("target_language", "vi"),
                    )
                    job["consistency"] = consistency_report.to_dict()
                    logger.info(
                        f"[{job_id}] Consistency: score={consistency_report.score:.3f} "
                        f"issues={consistency_report.issues_found} "
                        f"passed={consistency_report.passed}"
                    )
            except Exception as exc:
                logger.warning(f"[{job_id}] Consistency check failed: {exc}")

            # Layout DNA analysis (Sprint 12) — read-only, non-blocking
            try:
                source_text = result.full_content if hasattr(result, 'full_content') else None
                if not source_text and result.chunks:
                    source_text = "\n\n".join(
                        c.content if hasattr(c, 'content') else str(c)
                        for c in result.chunks
                    )
                if source_text and len(source_text) > 50:
                    layout_dna = self._layout_analyzer.analyze(source_text)
                    job["layout_dna"] = layout_dna.to_dict()
                    logger.info(f"[{job_id}] {layout_dna.summary()}")
            except Exception as exc:
                logger.warning(f"[{job_id}] Layout DNA analysis failed: {exc}")

            if result.error:
                job["error"] = result.error
                job["status"] = JobStatusV2.FAILED
                self._repo.mark_failed(job_id, result.error)
            else:
                # Save completion to database
                self._repo.mark_complete(job_id, job["output_paths"])

            # QAPR: record call outcome for future routing decisions
            try:
                job_elapsed = (time.time() - job.get("job_start_time", time.time())) * 1000
                usage = job.get("usage_stats", {})
                eqs_score = 0.0
                if self._last_eqs_report:
                    eqs_score = self._last_eqs_report.get("eqs_score", 0.0)
                lang_pair = f"{job.get('source_language', '*')}→{job.get('target_language', '*')}"
                doc_type = job.get("profile_id", "general")

                self._provider_stats.record(CallRecord(
                    provider=use_provider,
                    language_pair=lang_pair,
                    document_type=doc_type,
                    success=result.error is None,
                    latency_ms=job_elapsed,
                    quality_score=eqs_score,
                    cost_usd=usage.get("estimated_cost_usd", 0.0),
                    input_tokens=usage.get("total_input_tokens", 0),
                    output_tokens=usage.get("total_output_tokens", 0),
                ))

                # Save routing metadata to job
                job["qapr"] = self._last_routing_decision
            except Exception as exc:
                logger.warning(f"[{job_id}] QAPR recording failed: {exc}")

            logger.info(f"[{job_id}] Job completed: {job['status']}")

        except asyncio.CancelledError:
            job["status"] = JobStatusV2.CANCELLED
            job["error"] = "Job cancelled"
            self._repo.mark_failed(job_id, "Job cancelled by user")
            logger.info(f"[{job_id}] Job cancelled")
        except Exception as e:
            job["status"] = JobStatusV2.FAILED
            job["error"] = str(e)
            self._repo.mark_failed(job_id, str(e))
            logger.error(f"[{job_id}] Job failed: {e}")

            # QAPR: record failure
            try:
                lang_pair = f"{job.get('source_language', '*')}→{job.get('target_language', '*')}"
                doc_type = job.get("profile_id", "general")
                self._provider_stats.record(CallRecord(
                    provider=use_provider,
                    language_pair=lang_pair,
                    document_type=doc_type,
                    success=False,
                    latency_ms=0,
                ))
            except Exception:
                pass

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job by ID (memory first, then database)."""
        # Check memory first
        job = self._jobs.get(job_id)
        if job:
            return job

        # Try database
        job = self._repo.get(job_id)
        if job:
            self._jobs[job_id] = job  # Cache it
            return job

        return None

    async def resume_pending_jobs(self):
        """Resume any pending/running jobs after server restart."""
        pending_jobs = self._repo.get_pending_jobs()
        resumed = 0

        for job in pending_jobs:
            job_id = job["job_id"]

            # Skip if already running
            if job_id in self._job_tasks and not self._job_tasks[job_id].done():
                continue

            # Check if content file exists
            content_path = job.get("content_path")
            if not content_path or not Path(content_path).exists():
                logger.warning(f"[{job_id}] Cannot resume: content file missing")
                self._repo.mark_failed(job_id, "Content file missing after restart")
                continue

            # Ensure publisher is initialized
            self._ensure_publisher()

            # Read content
            content = Path(content_path).read_text(encoding='utf-8')

            # Restart job
            self._jobs[job_id] = job
            task = asyncio.create_task(
                self._process_job(
                    job_id, content,
                    use_vision=job.get("use_vision", True),
                    docx_template=job.get("docx_template", "auto"),
                    pdf_template=job.get("pdf_template", "auto")
                )
            )
            self._job_tasks[job_id] = task
            resumed += 1
            logger.info(f"[{job_id}] Resumed pending job from {job['progress']:.1f}%")

        if resumed > 0:
            logger.info(f"Resumed {resumed} pending jobs")

        return resumed

    def get_job_response(self, job: Dict) -> JobResponseV2:
        """Convert internal job to API response."""

        # Convert DNA if available
        dna_response = None
        if job.get("dna"):
            dna = job["dna"]
            if isinstance(dna, DocumentDNA):
                dna_response = DocumentDNAResponse(
                    document_id=dna.document_id,
                    title=dna.title,
                    author=dna.author,
                    language=dna.language,
                    genre=dna.genre,
                    sub_genre=dna.sub_genre,
                    tone=dna.tone,
                    voice=dna.voice,
                    reading_level=dna.reading_level,
                    has_chapters=dna.has_chapters,
                    has_sections=dna.has_sections,
                    has_footnotes=dna.has_footnotes,
                    has_citations=dna.has_citations,
                    has_formulas=dna.has_formulas,
                    has_code=dna.has_code,
                    has_tables=dna.has_tables,
                    characters=dna.characters,
                    locations=dna.locations,
                    key_terms=dna.key_terms,
                    proper_nouns=dna.proper_nouns,
                    word_count=dna.word_count,
                )

        # Get quality info from verification
        quality_score = None
        quality_level = None
        if job.get("verification"):
            v = job["verification"]
            quality_score = v.score if hasattr(v, "score") else None
            quality_level = v.overall_quality.value if hasattr(v, "overall_quality") else None

        # Get usage stats
        usage_stats_response = None
        if job.get("usage_stats"):
            stats = job["usage_stats"]
            usage_stats_response = UsageStatsResponse(
                total_input_tokens=stats.get("total_input_tokens", 0),
                total_output_tokens=stats.get("total_output_tokens", 0),
                total_tokens=stats.get("total_tokens", 0),
                total_elapsed_seconds=stats.get("total_elapsed_seconds", 0.0),
                total_calls=stats.get("total_calls", 0),
                estimated_cost_usd=stats.get("estimated_cost_usd", 0.0),
                calls_by_provider=stats.get("calls_by_provider", {}),
            )

        # Calculate elapsed time
        job_start = job.get("job_start_time", 0)
        elapsed = time.time() - job_start if job_start else 0.0

        return JobResponseV2(
            job_id=job["job_id"],
            status=job["status"],
            progress=job["progress"],
            current_stage=job["current_stage"],
            error=job.get("error"),
            source_file=job["source_file"],
            source_language=job["source_language"],
            target_language=job["target_language"],
            profile_id=job["profile_id"],
            output_formats=job["output_formats"],
            dna=dna_response,
            chunks_count=len(job.get("chunks", [])),
            output_paths=job.get("output_paths", {}),
            quality_score=quality_score,
            quality_level=quality_level,
            usage_stats=usage_stats_response,
            elapsed_time_seconds=round(elapsed, 1),
            created_at=job["created_at"],
            completed_at=job.get("completed_at"),
        )

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        job = self._jobs.get(job_id)
        if not job:
            return False

        task = self._job_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            job["status"] = JobStatusV2.CANCELLED
            job["error"] = "Cancelled by user"
            return True

        return False

    # ==================== FILE HANDLING ====================

    async def save_upload(self, filename: str, content: bytes) -> Path:
        """Save uploaded file."""
        safe_name = Path(filename).name  # Sanitize
        file_path = self.upload_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"
        file_path.write_bytes(content)
        return file_path

    async def read_upload(
        self,
        file_path: Path,
        use_vision: bool = True,
        source_lang: str = None
    ) -> str:
        """
        Read uploaded file content.

        For PDFs:
        - use_vision=True: Uses Smart Extraction Router (auto-detect strategy)
        - use_vision=False: Forces fast PyMuPDF extraction
        - source_lang='ja': Uses PaddleOCR for Japanese scanned docs (FREE)

        Smart Extraction analyzes the PDF and chooses:
        - FAST_TEXT for text-only (novels, articles) → FREE, 0.1s/page
        - HYBRID for mixed content → Text + Vision for complex pages
        - OCR for scanned docs with known language → FREE (PaddleOCR)
        - FULL_VISION for scanned/complex → Full Vision API
        """
        suffix = file_path.suffix.lower()

        if suffix == '.txt':
            return file_path.read_text(encoding='utf-8')

        elif suffix == '.md':
            return file_path.read_text(encoding='utf-8')

        elif suffix == '.docx':
            try:
                from docx import Document
                doc = Document(str(file_path))
                paragraphs = [p.text for p in doc.paragraphs]
                return '\n\n'.join(paragraphs)
            except ImportError:
                raise RuntimeError("python-docx required for .docx files")

        elif suffix == '.pdf':
            return await self._smart_extract_pdf(file_path, use_vision, source_lang)

        else:
            # Try reading as text
            return file_path.read_text(encoding='utf-8', errors='ignore')

    def _eqs_score_text(
        self, text: str, total_pages: int, strategy: str, source_lang: str = None
    ) -> None:
        """Score extracted text quality and store result. Never raises."""
        try:
            report = self._eqs_scorer.score(
                text=text,
                total_pages=total_pages,
                expected_language=source_lang,
            )
            self._last_eqs_report = {
                "eqs_score": round(report.overall_score, 4),
                "eqs_grade": report.grade,
                "eqs_strategy_used": strategy,
                "eqs_recommendation": report.recommendation,
                "eqs_passed": report.passed,
            }
            logger.info(
                "EQS: strategy=%s score=%.3f grade=%s recommendation=%s",
                strategy, report.overall_score, report.grade, report.recommendation,
            )
        except Exception as exc:
            logger.warning("EQS scoring failed (non-blocking): %s", exc)
            self._last_eqs_report = None

    async def _smart_extract_pdf(
        self,
        file_path: Path,
        use_vision: bool = True,
        source_lang: str = None
    ) -> str:
        """
        Smart PDF extraction with automatic strategy selection.

        Analyzes PDF and routes to optimal extraction:
        - FAST_TEXT: Novel, articles (text-only) → PyMuPDF, FREE
        - HYBRID: Text + some tables/images → PyMuPDF + selective Vision
        - OCR: Scanned docs with known language → PaddleOCR, FREE
        - FULL_VISION: Scanned, complex layouts → Full Vision API

        After extraction, runs EQS quality scoring and auto-retries
        with the next fallback strategy if score < 0.7.

        Args:
            file_path: Path to PDF file
            use_vision: Enable Vision API fallback
            source_lang: Source language for OCR routing ('ja', 'zh', 'ko', etc.)
        """
        self._last_eqs_report = None

        try:
            from core.smart_extraction import (
                SmartExtractionRouter,
                ExtractionStrategy,
                analyze_document,
                smart_extract,
            )

            # First, analyze the document
            analysis = analyze_document(str(file_path))

            logger.info(f"📊 Document Analysis:")
            logger.info(f"   Pages: {analysis.total_pages}")
            logger.info(f"   Text coverage: {analysis.text_coverage:.0%}")
            logger.info(f"   Scanned pages: {analysis.scanned_pages}")
            logger.info(f"   Strategy: {analysis.strategy.value}")
            logger.info(f"   Reason: {analysis.strategy_reason}")
            if source_lang:
                logger.info(f"   Source language: {source_lang}")

            # If use_vision=False, force FAST_TEXT
            if not use_vision:
                logger.info(f"   Vision disabled, forcing FAST_TEXT")
                analysis.strategy = ExtractionStrategy.FAST_TEXT

            # === Extraction with EQS feedback loop (Sprint 9) ===
            async def _try_extract(strategy: ExtractionStrategy):
                """Extract text using a specific strategy. Returns (text, pages)."""
                if strategy == ExtractionStrategy.FAST_TEXT:
                    from core.smart_extraction import fast_extract
                    result = await fast_extract(str(file_path))
                    logger.info(f"   ⚡ Fast extracted {result.total_pages} pages in {result.extraction_time:.1f}s")
                    return result.full_content, result.total_pages

                elif strategy == ExtractionStrategy.HYBRID:
                    from core.smart_extraction import fast_extract
                    result = await fast_extract(str(file_path))
                    logger.info(f"   📖 Hybrid extraction (fast for most pages)")
                    logger.info(f"   Complex pages that could use Vision: {len(analysis.complex_page_numbers)}")
                    return result.full_content, result.total_pages

                elif strategy == ExtractionStrategy.FULL_VISION:
                    ocr_supported = {'ja', 'zh', 'zh-Hans', 'zh-Hant', 'ko', 'en', 'fr', 'de', 'es', 'vi'}
                    if source_lang and source_lang in ocr_supported and analysis.scanned_pages > 0:
                        logger.info(f"   🔤 Using PaddleOCR for {source_lang} scanned document (FREE)")
                        result = await smart_extract(
                            str(file_path),
                            source_lang=source_lang,
                            use_vision=False
                        )
                        logger.info(f"   ✅ OCR extracted {result.total_pages} pages")
                        logger.info(f"   📊 OCR confidence: {result.ocr_confidence:.1%}")
                        return result.content, result.total_pages
                    else:
                        # Vision path: return file path for orchestrator
                        logger.info(f"   🔍 Document requires Vision API (scanned/complex)")
                        return None, analysis.total_pages  # None signals "pass to orchestrator"

                else:  # OCR strategy
                    logger.info(f"   🔤 Using PaddleOCR extraction")
                    result = await smart_extract(
                        str(file_path),
                        source_lang=source_lang or 'en',
                        use_vision=False
                    )
                    logger.info(f"   ✅ OCR extracted {result.total_pages} pages")
                    logger.info(f"   📊 OCR confidence: {result.ocr_confidence:.1%}")
                    return result.content, result.total_pages

            # Map core ExtractionStrategy to EQS strategy names
            _STRATEGY_TO_EQS = {
                ExtractionStrategy.FAST_TEXT: EQSStrategy.TEXT,
                ExtractionStrategy.HYBRID: EQSStrategy.TEXT,  # hybrid uses text extraction
                ExtractionStrategy.FULL_VISION: EQSStrategy.VISION,
                ExtractionStrategy.OCR: EQSStrategy.OCR,
            }
            # Reverse: EQS strategy → core strategy for retry
            _EQS_TO_STRATEGY = {
                EQSStrategy.TEXT: ExtractionStrategy.FAST_TEXT,
                EQSStrategy.OCR: ExtractionStrategy.OCR,
                EQSStrategy.VISION: ExtractionStrategy.FULL_VISION,
            }

            # --- First extraction attempt ---
            text, total_pages = await _try_extract(analysis.strategy)

            if text is None:
                # FULL_VISION pass-through — can't score, return file path
                logger.info(f"   💰 Estimated savings: ${analysis.estimated_cost_vision:.2f}")
                return str(file_path)

            # --- EQS scoring + feedback loop ---
            try:
                eqs_strategy = _STRATEGY_TO_EQS.get(analysis.strategy, EQSStrategy.TEXT)
                fb = self._eqs_feedback.evaluate(
                    text=text,
                    strategy=eqs_strategy,
                    total_pages=total_pages,
                    expected_language=source_lang,
                    iteration=1,
                )
                logger.info(
                    "EQS: strategy=%s score=%.3f grade=%s action=%s",
                    eqs_strategy.value, fb.eqs_report.overall_score,
                    fb.eqs_report.grade, fb.action.value,
                )

                # Retry if score below threshold and there's a next strategy
                if fb.action == FeedbackAction.RETRY and fb.next_strategy:
                    retry_core = _EQS_TO_STRATEGY.get(fb.next_strategy)
                    if retry_core and retry_core != analysis.strategy:
                        logger.info(
                            "EQS retry: %s → %s (score %.3f < %.1f)",
                            getattr(analysis.strategy, 'value', analysis.strategy),
                            getattr(retry_core, 'value', retry_core),
                            fb.eqs_report.overall_score, self._eqs_feedback.min_score,
                        )
                        try:
                            retry_text, retry_pages = await _try_extract(retry_core)
                            if retry_text is not None:
                                fb2 = self._eqs_feedback.evaluate(
                                    text=retry_text,
                                    strategy=fb.next_strategy,
                                    total_pages=retry_pages,
                                    expected_language=source_lang,
                                    iteration=2,
                                )
                                logger.info(
                                    "EQS retry result: score=%.3f grade=%s",
                                    fb2.eqs_report.overall_score, fb2.eqs_report.grade,
                                )
                                # Use retry text if it scored better
                                if fb2.eqs_report.overall_score > fb.eqs_report.overall_score:
                                    text = retry_text
                                    fb = fb2
                                    logger.info("EQS: using retry result (better score)")
                                else:
                                    logger.info("EQS: keeping original (retry not better)")
                        except Exception as retry_exc:
                            logger.warning("EQS retry extraction failed: %s", retry_exc)

                # Store final EQS metadata
                self._last_eqs_report = {
                    "eqs_score": round(fb.eqs_report.overall_score, 4),
                    "eqs_grade": fb.eqs_report.grade,
                    "eqs_strategy_used": fb.strategy_used.value,
                    "eqs_recommendation": fb.eqs_report.recommendation,
                    "eqs_passed": fb.eqs_report.passed,
                    "eqs_retried": fb.iteration > 1,
                    "eqs_attempts": fb.iteration,
                }
            except Exception as eqs_exc:
                logger.warning("EQS scoring failed (non-blocking): %s", eqs_exc)
                self._last_eqs_report = None

            return text

        except ImportError as e:
            logger.warning(f"Smart extraction not available: {e}, using legacy")
            if use_vision:
                return str(file_path)
            else:
                return await self._extract_pdf_text_legacy(file_path)
        except Exception as e:
            logger.error(f"Smart extraction failed: {e}, falling back")
            if use_vision:
                return str(file_path)
            else:
                return await self._extract_pdf_text_legacy(file_path)

    async def _extract_pdf_text_legacy(self, file_path: Path) -> str:
        """Legacy PDF text extraction (not recommended)."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            try:
                import pdfplumber
                with pdfplumber.open(str(file_path)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                    return text
            except ImportError:
                raise RuntimeError("PyMuPDF or pdfplumber required for .pdf files")

    def get_output_path(self, job_id: str, format_type: str) -> Optional[Path]:
        """Get output file path."""
        job = self._jobs.get(job_id)
        if not job or not job.get("output_paths"):
            return None

        path_str = job["output_paths"].get(format_type)
        if path_str:
            path = Path(path_str)
            # Handle relative paths - resolve from project root
            if not path.is_absolute():
                path = self.base_dir / path
            if path.exists():
                return path

        return None

    # ==================== PROFILES ====================

    def get_profiles(self) -> List[PublishingProfileResponse]:
        """Get all publishing profiles."""
        profiles = []
        for profile_id in list_profiles():
            profile = get_profile(profile_id)
            if profile:
                profiles.append(PublishingProfileResponse(
                    id=profile.id,
                    name=profile.name,
                    description=profile.description,
                    output_format=profile.output_format,
                    style_guide=profile.style_guide,
                    special_instructions=profile.special_instructions,
                ))
        return profiles

    def get_profile_by_id(self, profile_id: str) -> Optional[PublishingProfileResponse]:
        """Get specific profile."""
        profile = get_profile(profile_id)
        if not profile:
            return None

        return PublishingProfileResponse(
            id=profile.id,
            name=profile.name,
            description=profile.description,
            output_format=profile.output_format,
            style_guide=profile.style_guide,
            special_instructions=profile.special_instructions,
        )

    # ==================== CACHE MANAGEMENT ====================

    def clear_cache(self) -> int:
        """
        Clear all cached jobs.

        Returns number of jobs cleared.
        """
        count = len(self._jobs)

        # Cancel running tasks
        for job_id, task in list(self._job_tasks.items()):
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled task for job {job_id}")

        # Delete from database
        for job_id in list(self._jobs.keys()):
            self._repo.delete(job_id)

        # Clear storage
        self._jobs.clear()
        self._job_tasks.clear()
        self._last_db_update.clear()

        # Clear output files
        if self.output_dir.exists():
            for item in self.output_dir.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to delete {item}: {e}")

        # Clear upload files
        if self.upload_dir.exists():
            for item in self.upload_dir.iterdir():
                try:
                    item.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to delete {item}: {e}")

        logger.info(f"Cache cleared: {count} jobs removed")
        return count

    def clear_job(self, job_id: str) -> bool:
        """Clear specific job from cache and database."""
        # Cancel task if running
        if job_id in self._job_tasks:
            task = self._job_tasks[job_id]
            if not task.done():
                task.cancel()
            del self._job_tasks[job_id]

        # Remove from database
        deleted = self._repo.delete(job_id)

        # Remove from memory
        if job_id in self._jobs:
            del self._jobs[job_id]

        if job_id in self._last_db_update:
            del self._last_db_update[job_id]

        if deleted:
            logger.info(f"Job {job_id} cleared from cache and database")
            return True

        return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        running = 0
        completed = 0
        failed = 0

        for job in self._jobs.values():
            status = job.get("status")
            if status:
                status_val = status.value if hasattr(status, 'value') else str(status)
                if status_val == "complete":
                    completed += 1
                elif status_val == "failed":
                    failed += 1
                elif status_val not in ["complete", "failed", "cancelled"]:
                    running += 1

        return {
            "total_jobs": len(self._jobs),
            "running_jobs": running,
            "completed_jobs": completed,
            "failed_jobs": failed,
            "output_dir": str(self.output_dir),
            "upload_dir": str(self.upload_dir),
        }

    # ==================== JOB CLEANUP ====================

    MAX_MEMORY_JOBS = 200  # Max jobs kept in memory
    JOB_TTL_HOURS = 72  # Jobs older than this are evicted from memory

    def cleanup_old_jobs(self) -> int:
        """
        Evict completed/failed jobs older than TTL from memory.
        Jobs remain in the database for historical queries.
        Returns number of jobs evicted.
        """
        now = time.time()
        ttl_seconds = self.JOB_TTL_HOURS * 3600
        evicted = 0

        for job_id in list(self._jobs.keys()):
            job = self._jobs[job_id]
            status = job.get("status")
            status_val = status.value if hasattr(status, "value") else str(status)

            # Only evict completed/failed/cancelled jobs
            if status_val not in ("complete", "failed", "cancelled"):
                continue

            job_start = job.get("job_start_time", 0)
            if job_start and (now - job_start) > ttl_seconds:
                del self._jobs[job_id]
                self._job_tasks.pop(job_id, None)
                self._last_db_update.pop(job_id, None)
                evicted += 1

        # If still over capacity, evict oldest completed jobs
        if len(self._jobs) > self.MAX_MEMORY_JOBS:
            completed_jobs = [
                (jid, j.get("job_start_time", 0))
                for jid, j in self._jobs.items()
                if (j.get("status", "").value if hasattr(j.get("status", ""), "value") else str(j.get("status", "")))
                in ("complete", "failed", "cancelled")
            ]
            completed_jobs.sort(key=lambda x: x[1])  # oldest first
            excess = len(self._jobs) - self.MAX_MEMORY_JOBS
            for jid, _ in completed_jobs[:excess]:
                del self._jobs[jid]
                self._job_tasks.pop(jid, None)
                self._last_db_update.pop(jid, None)
                evicted += 1

        if evicted > 0:
            logger.info(f"Job cleanup: evicted {evicted} old jobs from memory (remaining: {len(self._jobs)})")

        return evicted

    # ==================== HEALTH ====================

    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "dependencies": {
                "pandoc": shutil.which("pandoc") is not None,
                "pdflatex": shutil.which("pdflatex") is not None,
                "anthropic": True,  # Will init on first use
            }
        }


# ==================== SINGLETON ====================

_service: Optional[APSV2Service] = None


def get_v2_service() -> APSV2Service:
    """Get or create service singleton."""
    global _service
    if _service is None:
        _service = APSV2Service()
    return _service
