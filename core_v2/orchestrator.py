"""
Universal Publisher Orchestrator

The main orchestrator that ties everything together.
Claude handles content; we handle context and orchestration.

Pipeline:
    Input → DNA Extraction → Semantic Chunking → Translation → Assembly → Conversion → Output
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

from .document_dna import DocumentDNA, extract_dna, quick_dna
from .semantic_chunker import SemanticChunker, SemanticChunk
from .publishing_profiles import PublishingProfile, PROFILES, get_profile, BASE_RENDERING_SKILL
from .output_converter import OutputConverter, OutputFormat
from .verifier import QualityVerifier, VerificationResult
from .vision_reader import VisionReader, VisionDocument
from .reliability import ChunkTranslationError, backoff_delay, is_transient_error
from .term_ledger import TermLedger, extract_terms, load_glossary_ledger
from .context_builder import build_chunk_contexts
from core_v2.aio_utils import run_blocking

# Optional wiring — degrade gracefully if config/cache modules are unavailable.
try:
    from config.settings import settings as _settings
except Exception:  # pragma: no cover
    _settings = None

try:
    from core.cache.chunk_cache import ChunkCache, compute_chunk_key
except Exception:  # pragma: no cover
    ChunkCache = None
    compute_chunk_key = None

logger = logging.getLogger(__name__)


def _cfg(name: str, default):
    """Read a setting with a safe fallback when settings are unavailable."""
    return getattr(_settings, name, default) if _settings is not None else default


class JobStatus(Enum):
    """Publishing job status."""
    PENDING = "pending"
    VISION_READING = "vision_reading"  # NEW: Claude Vision reading PDF
    EXTRACTING_DNA = "extracting_dna"
    CHUNKING = "chunking"
    TRANSLATING = "translating"
    ASSEMBLING = "assembling"
    CONVERTING = "converting"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PublishingJob:
    """A publishing/translation job."""

    job_id: str
    source_text: str
    source_lang: str
    target_lang: str
    profile_id: str

    # Status
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    current_stage: str = ""
    error: Optional[str] = None

    # Results
    dna: Optional[DocumentDNA] = None
    chunks: List[SemanticChunk] = field(default_factory=list)
    translated_chunks: List[str] = field(default_factory=list)
    assembled_content: str = ""
    output_path: Optional[Path] = None
    verification: Optional[VerificationResult] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "error": self.error,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "profile_id": self.profile_id,
            "chunk_count": len(self.chunks),
            "translated_count": len(self.translated_chunks),
        }


# ==================== TRANSLATION PROMPTS ====================

# The translation prompt is split into a STATIC system block (role + math
# rules + profile + document DNA — constant across every chunk of a document)
# and a DYNAMIC user block (per-chunk context + source text). This lets the
# static prefix be cached (Anthropic prompt caching / OpenAI automatic caching),
# cutting input tokens 30-50% on multi-chunk documents, and keeps per-chunk
# messages small.
TRANSLATION_SYSTEM = """You are a professional translator and publisher.

DOCUMENT DNA:
{dna_context}

PUBLISHING PROFILE:
{profile_prompt}

{glossary}

CRITICAL REQUIREMENTS FOR MATHEMATICAL CONTENT:

1. **PRESERVE ALL LaTeX MATH NOTATION EXACTLY AS-IS:**
   - Keep `$...$` (inline math) delimiters unchanged
   - Keep `$$...$$` (display math) delimiters unchanged
   - Keep `\\[...\\]` and `\\(...\\)` delimiters unchanged
   - Keep ALL LaTeX commands inside math mode: \\sum, \\frac, \\int, \\nabla, \\mathbb, etc.
   - Keep ALL subscripts and superscripts: x_{{i}}, x^{{2}}, etc.
   - Keep ALL Greek letters: \\alpha, \\beta, \\gamma, etc.

2. **ONLY TRANSLATE SURROUNDING TEXT, NEVER FORMULA CONTENT:**

   CORRECT Example:
   Input:  "The formula $\\sum_{{j=1}}^n f(j)$ shows..."
   Output: "Công thức $\\sum_{{j=1}}^n f(j)$ cho thấy..."

   WRONG Example:
   Input:  "The formula $\\sum_{{j=1}}^n f(j)$ shows..."
   Output: "Công thức tổng j=1 đến n f(j) cho thấy..."  ← WRONG! Lost LaTeX!

3. **PRESERVE EQUATION ENVIRONMENTS:**
   - Keep \\begin{{equation}}, \\end{{equation}}
   - Keep \\begin{{align}}, \\end{{align}}
   - Keep \\begin{{theorem}}, \\end{{theorem}}

OTHER REQUIREMENTS:
1. Follow the publishing profile's style guide exactly
2. Maintain consistency with the document DNA
3. Preserve all formatting and special elements
4. Keep proper nouns as specified in the DNA
5. Use consistent terminology throughout

OUTPUT:
Provide ONLY the translated text. Preserve ALL LaTeX math notation exactly as in the original.
Do not add explanations or meta-commentary.
"""

# Dynamic, per-chunk portion (kept small so the cached system prefix dominates).
TRANSLATION_USER = """CONTEXT:
- This is chunk {chunk_index} of {total_chunks}
- Previous content: {previous_summary}
- Next content: {next_preview}

TRANSLATION TASK:
Translate the following text from {source_lang} to {target_lang}.

Source Text:
{source_text}"""

# Back-compat: a single combined prompt (system + user) for any caller/test
# that still expects the original one-shot template.
TRANSLATION_PROMPT = TRANSLATION_SYSTEM + "\n\n" + TRANSLATION_USER

ASSEMBLY_PROMPT = """You are a professional editor preparing a translated document for publication.

IMPORTANT: The chunks below are ALREADY TRANSLATED to {target_lang}.
DO NOT translate or change the language. Preserve the existing translation.
Your task is ONLY to:
1. Combine the chunks smoothly
2. Fix any transition issues between chunks
3. Ensure consistent formatting
4. **PRESERVE ALL LaTeX MATH NOTATION EXACTLY**

DOCUMENT DNA:
{dna_context}

PUBLISHING PROFILE:
{profile_prompt}

{rendering_skill}

TRANSLATED CHUNKS (in {target_lang}):
{chunks_text}

CRITICAL: Preserve ALL LaTeX math notation:
- Keep all $...$ and $$...$$ delimiters
- Keep all \\sum, \\frac, \\int, etc.
- Keep all subscripts/superscripts: x_{{i}}, x^{{2}}
- Do NOT convert LaTeX to plain text

OUTPUT:
Provide the assembled document in {target_lang}, ready for final formatting.
Keep all content in {target_lang}. Do NOT translate anything.
Preserve ALL mathematical notation exactly as provided.
"""

# ==================== JAPANESE-SPECIFIC TRANSLATION ADDITIONS ====================

JAPANESE_TRANSLATION_ADDITIONS = """
JAPANESE → VIETNAMESE SPECIFIC REQUIREMENTS:

1. **HONORIFICS (敬称)** - Translate with appropriate Vietnamese equivalents:
   - 先生 (sensei) → Thầy/Cô (teacher) hoặc Bác sĩ (doctor, based on context)
   - さん (san) → Anh/Chị/Ông/Bà (based on gender/age context)
   - 様 (sama) → Ngài/Quý ông/Quý bà
   - 君 (kun), ちゃん (chan) → có thể giữ nguyên hoặc bỏ qua tùy ngữ cảnh

2. **SENTENCE ENDINGS (文末表現)** - Preserve register/formality:
   - です/ます (polite form) → giữ văn phong lịch sự trong tiếng Việt
   - だ/である (plain/academic) → văn phong học thuật/trang trọng
   - だろう/でしょう → "có lẽ", "chắc là", "chắc hẳn"

3. **COUNTING WORDS (助数詞)** - Use appropriate Vietnamese counters:
   - 一人、二人 → một người, hai người
   - 一冊、二冊 → một quyển, hai quyển
   - 一枚、二枚 → một tờ/tấm, hai tờ/tấm
   - 一本、二本 → một cây/chai, hai cây/chai

4. **ONOMATOPOEIA (擬音語・擬態語)** - Translate with Vietnamese equivalents:
   - ドキドキ → tim đập thình thịch
   - ワクワク → háo hức, hồi hộp
   - キラキラ → lấp lánh
   - ニコニコ → tươi cười
   - サラサラ → mượt mà, trơn tru

5. **JAPANESE PARTICLES** - Understand context:
   - は (topic marker) affects sentence emphasis
   - が (subject marker) indicates new/important information
   - を, に, で, から, まで, へ, より → translate based on context

6. **PRESERVE SPECIAL ELEMENTS**:
   - Japanese names: Keep original + romanization if helpful (田中 - Tanaka)
   - Technical terms: Original Japanese + Vietnamese translation
   - Ruby text (furigana): Preserve if present
   - Japanese punctuation: 。→ . and 、→ ,

7. **ACADEMIC/NOVEL STYLE**:
   - For academic papers: Use formal Vietnamese (học thuật)
   - For novels/light novels: Natural, flowing Vietnamese dialogue
"""

JAPANESE_TO_ENGLISH_ADDITIONS = """
JAPANESE → ENGLISH SPECIFIC REQUIREMENTS:

1. **HONORIFICS**: Keep or translate based on context:
   - 先生 (sensei) → "Professor", "Doctor", "Teacher", or keep as "Sensei"
   - さん (san) → "Mr./Ms." or omit in casual context
   - 様 (sama) → "Lord/Lady" (formal) or "Dear" (letters)

2. **SENTENCE STRUCTURE**: Japanese is SOV, English is SVO
   - Restructure sentences for natural English flow
   - Don't translate word-by-word

3. **PASSIVE VOICE**: Japanese uses passive more frequently
   - Convert to active voice where natural in English

4. **ONOMATOPOEIA**: Translate or adapt:
   - ドキドキ → "heart pounding", "nervous"
   - ワクワク → "excited", "thrilled"

5. **CULTURAL CONTEXT**: Add brief explanations for:
   - Japanese-specific concepts (tatami, hanami, etc.)
   - Cultural references that Western readers may not understand
"""


def _extract_pdf_text_sync(pdf_path: Path) -> str:
    """Synchronous legacy PDF text extraction.

    Blocking (fitz/pdfplumber) work extracted from _extract_pdf_text_legacy so
    it can be run off the event loop via run_blocking.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        logger.info(f"Legacy PDF extraction: {len(text)} chars")
        return text
    except ImportError:
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except ImportError:
            raise RuntimeError("PyMuPDF or pdfplumber required for PDF extraction")


class UniversalPublisher:
    """
    The main orchestrator for Claude-native publishing.

    This class coordinates:
    1. DNA extraction (understanding the document)
    2. Semantic chunking (intelligent splitting)
    3. Translation (with full context)
    4. Assembly (combining chunks)
    5. Conversion (to final format)
    6. Verification (quality check)
    """

    def __init__(
        self,
        llm_client: Any,
        output_dir: Path = Path("output"),
        enable_verification: bool = True,
        concurrency: int = int(os.environ.get("PUBLISHER_CONCURRENCY", "3")),
    ):
        """
        Args:
            llm_client: LLM client with async chat method
            output_dir: Directory for output files
            enable_verification: Whether to verify output quality
            concurrency: Max concurrent translation requests
        """
        self.llm_client = llm_client
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.enable_verification = enable_verification
        self.concurrency = concurrency

        # Initialize components
        self.chunker = SemanticChunker(llm_client)
        self.converter = OutputConverter()
        self.verifier = QualityVerifier(llm_client) if enable_verification else None

        # NEW: Vision reader for PDF/images
        self.vision_reader = VisionReader(llm_client)

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(concurrency)

        # --- Translation quality / cost knobs (env-overridable via settings) ---
        self.translation_temperature: float = float(_cfg("translation_temperature", 0.3))
        self.prompt_cache_enabled: bool = bool(_cfg("translation_prompt_cache_enabled", True))
        self.prompt_version: str = str(_cfg("translation_prompt_version", "v2"))
        self.max_retries: int = int(_cfg("translation_max_retries", 4))
        self.backoff_base: float = float(_cfg("translation_backoff_base", 2.0))
        self.backoff_cap: float = float(_cfg("translation_backoff_cap", 60.0))

        # --- Terminology ledger (auto-glossary + explicit glossaries) ---
        # Built once per job in publish() and injected into the cached system
        # prompt so proper nouns / key terms stay consistent across chunks.
        self.auto_glossary_enabled = bool(_cfg("translation_auto_glossary_enabled", True))
        self.glossary_max_terms = int(_cfg("translation_glossary_max_terms", 80))
        self.glossary_ids = [
            s.strip() for s in str(_cfg("translation_glossary_ids", "")).split(",") if s.strip()
        ]
        self._active_ledger = None  # set per-job in publish()

        # Cache signature: same (provider, model, temperature, prompt version)
        # => same cache key. Changing any of them invalidates reuse, which
        # prevents serving a translation produced under a different config.
        self._provider_sig = str(_cfg("provider", ""))
        self._model_sig = str(_cfg("model", ""))

        # --- Chunk cache (persistent translation memoization) ---
        self.chunk_cache = None
        cache_on = bool(_cfg("chunk_cache_enabled", True)) and bool(_cfg("cache_enabled", True))
        if cache_on and ChunkCache is not None and compute_chunk_key is not None:
            try:
                self.chunk_cache = ChunkCache()  # defaults to settings.cache_dir/chunks.db
                logger.info("ChunkCache enabled for core_v2 translation path")
            except Exception as e:  # pragma: no cover - cache is best-effort
                logger.warning(f"ChunkCache unavailable, continuing without cache: {e}")

        # --- Translation Memory gateway (read/hints path — reuse approved
        # translations as prompt hints). Built once per publisher and guarded:
        # an empty/unavailable/disabled TM makes lookups a zero-cost no-op, and
        # any construction failure degrades to no TM reuse (translation proceeds).
        self.tm_gateway = None
        if bool(_cfg("tm_reuse_enabled", True)) and bool(_cfg("tm_enabled", True)):
            try:
                from .tm_gateway import TMGateway
                self.tm_gateway = TMGateway(
                    enabled=True,
                    threshold=float(_cfg("tm_fuzzy_threshold", 0.85)),
                    max_hints=int(_cfg("tm_max_hints", 5)),
                )
            except Exception as e:
                logger.warning(f"TM gateway unavailable, continuing without TM reuse: {e}")
                self.tm_gateway = None

    def _chunk_cache_key(self, source_text: str, source_lang: str,
                         target_lang: str, profile_id: str,
                         ledger_fingerprint: str = "noterms") -> Optional[str]:
        """Build a collision-safe cache key including model/temp/profile/version.

        ``ledger_fingerprint`` folds the active terminology ledger into the key
        (via the existing ``glossary_name`` discriminator) so a chunk retranslated
        under a different glossary can't serve a stale cached translation. The
        default ``"noterms"`` reproduces the pre-ledger key for a chunk with no
        terminology, keeping cache behavior identical when no ledger is active.
        """
        if compute_chunk_key is None:
            return None
        return compute_chunk_key(
            source_text=source_text,
            source_lang=source_lang or "auto",
            target_lang=target_lang or "vi",
            mode=profile_id or "essay",
            model=f"{self._provider_sig}:{self._model_sig}",
            profile_id=profile_id or "essay",
            temperature=str(self.translation_temperature),
            prompt_version=self.prompt_version,
            glossary_name=ledger_fingerprint or "noterms",
        )

    async def publish(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        profile_id: str = "essay",
        output_format: str = "docx",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        use_vision: bool = True,  # NEW: Use Claude Vision for PDF reading
        docx_template: str = "auto",  # NEW: DOCX template (ebook/academic/business/auto)
        pdf_template: str = "auto",  # NEW: PDF template (ebook/academic/business/auto)
        title_fallback: str = "",  # Fallback title (e.g. source filename without extension)
    ) -> PublishingJob:
        """
        Main publishing pipeline.

        Args:
            source_text: Document text to translate (or PDF file path for Vision mode)
            source_lang: Source language code (or "auto")
            target_lang: Target language code
            profile_id: Publishing profile to use
            output_format: Desired output format
            progress_callback: Optional callback for progress updates
            use_vision: Use Claude Vision for PDF reading (recommended)
            docx_template: DOCX template ('ebook', 'academic', 'business', 'auto')
            pdf_template: PDF template ('ebook', 'academic', 'business', 'auto')

        Returns:
            PublishingJob with results
        """
        import uuid

        # Create job
        job = PublishingJob(
            job_id=str(uuid.uuid4())[:8],
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
            profile_id=profile_id,
        )

        def update_progress(progress: float, stage: str):
            job.progress = progress
            job.current_stage = stage
            if progress_callback:
                progress_callback(progress, stage)

        try:
            # Check if source_text is a PDF file path and use Vision
            content_path = Path(source_text) if len(source_text) < 500 else None

            if content_path and content_path.exists() and content_path.suffix.lower() == '.pdf':
                if use_vision:
                    # Stage 0: Vision Reading (0-50%) - Major portion for large PDFs
                    logger.info(f"[{job.job_id}] Using Claude Vision for PDF reading (profile: {profile_id})")
                    update_progress(0.01, "Claude Vision reading PDF...")
                    job.status = JobStatus.VISION_READING

                    source_text = await self._read_with_vision(
                        content_path,
                        lambda p, s: update_progress(p * 0.50, s),  # Vision = 0-50%
                        profile_id=profile_id,  # Pass profile for optimized reading
                    )
                    job.source_text = source_text
                    logger.info(f"[{job.job_id}] Vision read complete: {len(source_text)} chars")
                else:
                    # Fallback to traditional extraction
                    source_text = await self._extract_pdf_text_legacy(content_path)
                    job.source_text = source_text

            # Stage 1: Extract DNA (52%)
            update_progress(0.52, "Extracting document DNA")
            job.status = JobStatus.EXTRACTING_DNA
            job.dna = await self._extract_dna(source_text, source_lang)
            logger.info(f"DNA extracted: genre={job.dna.genre}, {job.dna.word_count} words")

            # Resolve the source language now (needed by the terminology ledger
            # below and reused for translation): fall back to DNA-detected
            # language when the caller requested 'auto'.
            actual_source_lang = job.dna.language if source_lang == "auto" and job.dna.language else source_lang

            # Build the terminology ledger ONCE per job (REQ-02/04/06): explicit
            # glossary terms (if any) + optional auto-extracted terms, merged with
            # glossary winning on conflicts. Never fails the job — any error
            # degrades to an empty ledger and translation proceeds unchanged.
            ledger = TermLedger()
            try:
                ledger.merge(load_glossary_ledger(self.glossary_ids, sample_text=source_text[:6000]))
                if self.auto_glossary_enabled:
                    ledger.merge(await extract_terms(
                        source_text, self.llm_client, actual_source_lang, target_lang, max_terms=40
                    ))
            except Exception as e:
                logger.warning(f"terminology ledger build failed, continuing without: {e}")
            self._active_ledger = ledger
            logger.info(f"Terminology ledger: {len(ledger)} terms")

            # Stage 2: Chunk document (55%)
            update_progress(0.55, "Chunking document")
            job.status = JobStatus.CHUNKING
            job.chunks = await self.chunker.chunk(source_text)
            logger.info(f"Document split into {len(job.chunks)} chunks")

            # Optional LLM summary pre-pass (gated OFF by default): enrich the
            # deterministic rolling context with a one-sentence summary per chunk.
            # Disabled => no extra LLM calls; the chunker's deterministic context
            # stands. Any failure keeps the deterministic context unchanged.
            if bool(_cfg("translation_context_summary_enabled", False)) and len(job.chunks) > 1:
                try:
                    summaries = await self._summarize_chunks(job.chunks)
                    contexts = build_chunk_contexts([c.content for c in job.chunks], summaries=summaries,
                                                    window=int(_cfg("translation_context_window", 3)))
                    for c, (preceding, following) in zip(job.chunks, contexts):
                        c.previous_summary = preceding or None
                        c.next_preview = following or None
                    logger.info(f"[{job.job_id}] Context enriched with {sum(1 for s in summaries if s)} chunk summaries")
                except Exception as e:
                    logger.warning(f"context summary pre-pass failed, keeping deterministic context: {e}")

            # Stage 3: Translate chunks (55% - 90%)
            update_progress(0.55, "Translating")
            job.status = JobStatus.TRANSLATING
            # actual_source_lang resolved above (DNA-detected when 'auto').
            logger.info(f"Translation: {actual_source_lang} → {target_lang} (requested: {source_lang}, detected: {job.dna.language})")
            job.translated_chunks = await self._translate_chunks(
                job.chunks,
                job.dna,
                profile_id,
                actual_source_lang,
                target_lang,
                lambda p: update_progress(0.55 + p * 0.35, f"Translating chunk {int(p * len(job.chunks))}/{len(job.chunks)}"),
            )

            # Stage 3.5: Bounded repair pass — re-translate only the chunks the
            # deterministic quality gate flags as suspect (empty / truncated /
            # wrong-language / dropped-formula), adopting a retry only when it is
            # strictly better. Gated by config; degrades to a no-op on any issue.
            if bool(_cfg("translation_repair_enabled", True)):
                update_progress(0.90, "Checking & repairing translation")
                job.translated_chunks, repaired = await self._repair_suspect_chunks(
                    job.chunks, job.translated_chunks, job.dna, profile_id, actual_source_lang, target_lang)
                if repaired:
                    logger.info(f"[{job.job_id}] Repaired {repaired} suspect chunk(s)")

            # Stage 4: Assemble (92%)
            update_progress(0.92, "Assembling document")
            job.status = JobStatus.ASSEMBLING
            job.assembled_content = await self._assemble(
                job.translated_chunks,
                job.dna,
                profile_id,
                target_lang,
            )

            # Stage 5: Convert to output format (95%)
            update_progress(0.95, f"Converting to {output_format}")
            job.status = JobStatus.CONVERTING
            job.output_path = await self._convert(
                job.assembled_content,
                output_format,
                job.dna.title or title_fallback or "translated_document",
                job.dna.author,
                job.job_id,
                dna=job.dna,  # Pass DNA for formula detection
                docx_template=docx_template,  # Professional DOCX template
                pdf_template=pdf_template,  # Professional PDF template
                profile_id=profile_id,  # For profile-based template selection
                target_lang=target_lang,  # For i18n in renderers
            )

            # Stage 6: Verify (98%)
            if self.enable_verification and self.verifier:
                update_progress(0.98, "Verifying quality")
                job.status = JobStatus.VERIFYING
                source_texts = [c.content for c in job.chunks]
                job.verification = await self.verifier.verify(
                    source_texts,
                    job.translated_chunks,
                    source_lang,
                    target_lang,
                    profile_id,
                )
                logger.info(f"Verification: {job.verification.overall_quality.value} ({job.verification.score:.2f})")

            # Complete
            update_progress(1.0, "Complete")
            job.status = JobStatus.COMPLETE
            job.completed_at = datetime.now()

        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)

        return job

    async def _summarize_chunks(self, chunks) -> list:
        """One-sentence summary per chunk (parallel, guarded). Empty string on any failure."""
        async def _one(ch):
            async with self._semaphore:
                try:
                    prompt = ("Summarize the following text in ONE short sentence, "
                              "in its original language. Text:\n" + ch.content[:3000])
                    resp = await self.llm_client.chat(messages=[{"role": "user", "content": prompt}], temperature=0.0)
                    return (getattr(resp, "content", "") or "").strip()
                except Exception:
                    return ""
        return list(await asyncio.gather(*[_one(c) for c in chunks]))

    async def _extract_dna(self, text: str, source_lang: str) -> DocumentDNA:
        """Extract document DNA."""
        try:
            dna = await extract_dna(text, self.llm_client)
            if source_lang != "auto":
                dna.language = source_lang
            return dna
        except Exception as e:
            logger.warning(f"DNA extraction failed, using quick_dna: {e}")
            return quick_dna(text)

    async def _translate_chunks(
        self,
        chunks: List[SemanticChunk],
        dna: DocumentDNA,
        profile_id: str,
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> List[str]:
        """Translate chunks with controlled concurrency."""
        profile = get_profile(profile_id) or PROFILES.get("essay")

        # Track progress
        completed = [0]  # Use list to allow modification in nested function
        total = len(chunks)

        # The terminology ledger is built once per job in publish(); thread it
        # through so every chunk shares the same (cached) glossary block.
        active_ledger = getattr(self, "_active_ledger", None)

        async def translate_with_semaphore(chunk: SemanticChunk) -> tuple[int, str]:
            """Translate single chunk with semaphore control."""
            async with self._semaphore:
                result = await self._translate_chunk(
                    chunk, dna, profile, source_lang, target_lang,
                    profile_id=profile_id, ledger=active_ledger,
                )
                completed[0] += 1
                if progress_callback:
                    progress_callback(completed[0] / total)
                return (chunk.index, result)

        # Launch all translations concurrently (semaphore limits parallelism).
        # return_exceptions=True so one failing chunk doesn't orphan the rest;
        # we then fail the whole job loudly rather than shipping a partial doc.
        tasks = [translate_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            first = errors[0]
            logger.error(
                f"Translation aborted: {len(errors)}/{total} chunk(s) failed; "
                f"first error: {first}"
            )
            raise first

        # Sort by original index to maintain order
        results_with_index = list(results)
        results_with_index.sort(key=lambda x: x[0])
        translated = [r[1] for r in results_with_index]

        # Log translation language quality summary
        correct_lang = sum(
            1 for t in translated
            if self._detect_language(t) in (target_lang, "unknown")
        )
        logger.info(
            f"Translation quality: {correct_lang}/{total} chunks in target language '{target_lang}'"
        )
        if correct_lang < total:
            wrong = [
                i for i, t in enumerate(translated)
                if self._detect_language(t) not in (target_lang, "unknown")
            ]
            logger.warning(f"Chunks still in source language: {wrong}")

        return translated

    @staticmethod
    def _detect_language(text: str) -> str:
        """Quick language detection based on character analysis.

        Returns 'vi', 'zh', 'ja', 'en', or 'unknown'.
        """
        if not text or len(text) < 20:
            return "unknown"

        sample = text[:3000]
        alpha_count = sum(1 for c in sample if c.isalpha())
        if alpha_count == 0:
            return "unknown"

        # Vietnamese diacritical characters (unique to Vietnamese)
        vi_diacriticals = set(
            'àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệ'
            'ìíỉĩịòóỏõọôốồổỗộơớờởỡợ'
            'ùúủũụưứừửữựỳýỷỹỵđ'
        )
        vi_diacriticals |= {c.upper() for c in vi_diacriticals}

        vi_count = sum(1 for c in sample if c in vi_diacriticals)

        # CJK characters (Chinese/Japanese)
        cjk_count = sum(
            1 for c in sample
            if '\u4e00' <= c <= '\u9fff'       # CJK Unified
            or '\u3040' <= c <= '\u309f'        # Hiragana
            or '\u30a0' <= c <= '\u30ff'        # Katakana
        )

        vi_ratio = vi_count / alpha_count
        cjk_ratio = cjk_count / max(len(sample), 1)

        if cjk_ratio > 0.1:
            # Distinguish Chinese vs Japanese by kana presence
            kana_count = sum(1 for c in sample if '\u3040' <= c <= '\u30ff')
            return "ja" if kana_count > 5 else "zh"
        if vi_ratio > 0.02:
            return "vi"
        return "en"

    async def _translate_chunk(
        self,
        chunk: SemanticChunk,
        dna: DocumentDNA,
        profile: PublishingProfile,
        source_lang: str,
        target_lang: str,
        profile_id: str = "essay",
        max_retries: Optional[int] = None,
        ledger=None,
        force_refresh: bool = False,
    ) -> str:
        """Translate a single chunk.

        Improvements over the original:
        - Static (cacheable) system prompt + small dynamic user prompt.
        - Low, configurable temperature for faithful, low-variance output.
        - Persistent chunk cache (keyed by model/temperature/profile/version).
        - Exponential backoff + jitter on transient errors, and a raised
          ``ChunkTranslationError`` on permanent failure — so the job fails
          loudly instead of silently shipping a ``[TRANSLATION ERROR]`` hole.
        """
        max_retries = self.max_retries if max_retries is None else max_retries

        # Resolve the active terminology ledger (explicit arg wins; otherwise the
        # per-job ledger built in publish()). An empty or absent ledger is falsy,
        # so glossary_block == "" and the fingerprint stays "noterms" — i.e. the
        # exact pre-ledger behavior: same system prompt, same cache key.
        ledger = ledger if ledger is not None else getattr(self, "_active_ledger", None)
        glossary_block = ledger.to_prompt_block(getattr(self, "glossary_max_terms", 80)) if ledger else ""
        ledger_fp = ledger.fingerprint() if ledger else "noterms"

        # 1) Cache lookup (best-effort — must never break translation).
        # A forced refresh (repair pass) skips the GET so we always re-translate,
        # but still computes cache_key below only when a store could happen.
        cache_key: Optional[str] = None
        if self.chunk_cache is not None and not force_refresh:
            try:
                cache_key = self._chunk_cache_key(
                    chunk.content, source_lang, target_lang, profile_id,
                    ledger_fingerprint=ledger_fp,
                )
                if cache_key:
                    # Off-loop: ChunkCache is sync sqlite (thread-local conns + WAL),
                    # so run it in a worker thread to keep the event loop free.
                    cached = await run_blocking(self.chunk_cache.get, cache_key)
                    if cached is not None:
                        logger.debug(f"[Chunk {chunk.index}] cache hit")
                        return cached
            except Exception as e:  # pragma: no cover
                logger.debug(f"[Chunk {chunk.index}] cache lookup skipped: {e}")
                cache_key = None

        # 2) Build system (static/cacheable) + user (dynamic) prompts
        system_prompt = TRANSLATION_SYSTEM.format(
            dna_context=dna.to_context_prompt(),
            profile_prompt=profile.to_prompt(),
            glossary=glossary_block,
        )
        if source_lang == 'ja':
            if target_lang == 'vi':
                system_prompt += "\n\n" + JAPANESE_TRANSLATION_ADDITIONS
            elif target_lang == 'en':
                system_prompt += "\n\n" + JAPANESE_TO_ENGLISH_ADDITIONS

        user_prompt = TRANSLATION_USER.format(
            chunk_index=chunk.index + 1,
            total_chunks=chunk.total_chunks,
            previous_summary=chunk.previous_summary or "Start of document",
            next_preview=chunk.next_preview or "End of document",
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=chunk.content,
        )

        # Prepend approved Translation-Memory hints to the DYNAMIC user message
        # (never the cached system prefix / template, so no KeyError and no cache
        # thrash). TM state is deliberately NOT in the chunk-cache key, so a cache
        # HIT legitimately returns above before hints are ever computed. Guarded via
        # getattr so publishers built without __init__ (tests) are unaffected; an
        # inactive/None gateway yields "" and leaves user_prompt byte-for-byte
        # identical to the prior prompt.
        gw = getattr(self, "tm_gateway", None)
        if gw is not None:
            try:
                _hints = gw.lookup_hints(chunk.content, source_lang, target_lang)
                _tm_block = gw.render_hints_block(_hints)
                if _tm_block:
                    user_prompt = _tm_block + "\n\n" + user_prompt
            except Exception:
                pass

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                response = await self.llm_client.chat(
                    messages=messages,
                    temperature=self.translation_temperature,
                    cache_system=self.prompt_cache_enabled,
                )
                translated = response.content.strip()
                truncated = bool(getattr(response, "truncated", False))

                # Verify LaTeX preservation if document has formulas
                if dna.has_formulas:
                    translated = self._verify_latex_preservation(chunk.content, translated, chunk.index)

                # Language check + strengthened retry (REUSING the full system
                # prompt so terminology/formula guidance is preserved).
                detected = self._detect_language(translated)
                if detected != "unknown" and detected != target_lang:
                    logger.warning(
                        f"[Chunk {chunk.index}] Language mismatch: expected '{target_lang}', "
                        f"detected '{detected}'. Retrying with stronger instruction."
                    )
                    strong_user = (
                        user_prompt
                        + f"\n\nCRITICAL: Your output MUST be entirely in {target_lang}. "
                        f"Do NOT include any {source_lang} text and do NOT echo the original."
                    )
                    retry_response = await self.llm_client.chat(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": strong_user},
                        ],
                        temperature=self.translation_temperature,
                        cache_system=self.prompt_cache_enabled,
                    )
                    retranslated = retry_response.content.strip()
                    truncated = bool(getattr(retry_response, "truncated", False))
                    detected2 = self._detect_language(retranslated)
                    if detected2 not in (target_lang, "unknown"):
                        logger.error(
                            f"[Chunk {chunk.index}] Still '{detected2}' after retry; using it anyway."
                        )
                    translated = retranslated
                    detected = detected2

                # 3) Store in cache — only cache "good" results (right language,
                # not truncated) so we never memoize a corrupted chunk.
                lang_ok = detected in (target_lang, "unknown")
                if self.chunk_cache is not None and cache_key and lang_ok and not truncated and not force_refresh:
                    try:
                        await run_blocking(
                            self.chunk_cache.set,
                            cache_key, translated, source_lang, target_lang, mode=profile_id,
                        )
                    except Exception as e:  # pragma: no cover
                        logger.debug(f"[Chunk {chunk.index}] cache store skipped: {e}")

                return translated

            except ChunkTranslationError:
                raise
            except Exception as e:
                last_error = e
                if is_transient_error(e) and attempt < max_retries - 1:
                    delay = backoff_delay(attempt, self.backoff_base, self.backoff_cap)
                    logger.warning(
                        f"[Chunk {chunk.index}] transient error "
                        f"(attempt {attempt + 1}/{max_retries}): {str(e)[:160]} — "
                        f"retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                # Permanent error, or retries exhausted: fail loudly.
                logger.error(f"[Chunk {chunk.index}] translation failed permanently: {e}")
                raise ChunkTranslationError(chunk.index, str(e)[:200]) from e

        raise ChunkTranslationError(chunk.index, f"exhausted {max_retries} retries: {last_error}")

    async def _repair_suspect_chunks(
        self,
        chunks,
        translated,
        dna,
        profile_id,
        source_lang,
        target_lang,
    ) -> tuple[list, int]:
        """Bounded, best-effort repair pass over suspect translated chunks.

        Runs the deterministic quality gate over every (source, translation)
        pair; for each flagged chunk it re-translates ONCE with the cache GET
        bypassed (``force_refresh=True``) and adopts the new translation only if
        it has *strictly* fewer issues. Clean chunks are never touched. Returns
        the (possibly repaired) translation list and the number of chunks
        replaced. Never raises — a hard translation failure keeps the original.

        When ``translation_semantic_verify_enabled`` is set, an OPTIONAL LLM
        faithfulness pass additionally checks the deterministically-clean chunks
        (capped by ``translation_semantic_verify_max``, run under the semaphore)
        and folds any chunk it judges unfaithful (>= major) into the SAME bounded
        repair loop as a one-issue ``["semantic"]`` suspect — so a chunk is
        deterministic-suspect OR semantic-suspect, never both. Disabled (the
        default) => none of the semantic code runs and this method behaves
        byte-for-byte like the deterministic-only pass.
        """
        from .quality_gate import check_chunk

        profile = get_profile(profile_id) or PROFILES.get("essay")
        max_repairs = int(_cfg("translation_repair_max_chunks", 20))
        semantic_enabled = bool(_cfg("translation_semantic_verify_enabled", False))
        semantic_max = int(_cfg("translation_semantic_verify_max", 30))

        # Identify suspect chunks deterministically (no LLM calls). Also record
        # the deterministically-clean indices so an optional semantic pass can
        # scrutinize only those.
        suspects: list[tuple[int, list]] = []
        clean: list[int] = []
        for i, (src, tr) in enumerate(zip(chunks, translated)):
            issues = check_chunk(
                src.content, tr, target_lang,
                detected_lang=self._detect_language(tr),
                has_formulas=dna.has_formulas,
            )
            if issues:
                suspects.append((i, issues))
            else:
                clean.append(i)

        # Optional semantic faithfulness pass (opt-in, bounded, under the
        # semaphore). Only deterministically-clean chunks are checked; any judged
        # unfaithful (>= major) joins the repair loop as a ["semantic"] suspect.
        if semantic_enabled and clean:
            from .semantic_verifier import verify_chunk, is_unfaithful

            to_check = clean[:semantic_max]

            async def _sem(i):
                async with self._semaphore:
                    v = await verify_chunk(
                        chunks[i].content, translated[i],
                        source_lang, target_lang, self.llm_client,
                    )
                    return (i, is_unfaithful(v, min_severity="major"))

            for i, bad in await asyncio.gather(*[_sem(i) for i in to_check]):
                if bad:
                    suspects.append((i, ["semantic"]))

        if not suspects:
            return (translated, 0)

        # Stable order after merging deterministic + semantic suspects (the
        # deterministic pass already yields ascending indices, so with semantic
        # disabled this sort is a no-op and the result is unchanged).
        suspects.sort(key=lambda x: x[0])

        to_repair = suspects[:max_repairs]
        if len(suspects) > max_repairs:
            logger.warning(
                f"{len(suspects)} suspect chunk(s) found; repairing only the first "
                f"{max_repairs} (translation_repair_max_chunks)."
            )

        async def _repair_one(i, orig_issues):
            async with self._semaphore:
                try:
                    new = await self._translate_chunk(
                        chunks[i], dna, profile, source_lang, target_lang,
                        profile_id=profile_id, force_refresh=True,
                    )
                except ChunkTranslationError:
                    return (i, None)  # keep original on hard failure
                new_issues = check_chunk(
                    chunks[i].content, new, target_lang,
                    detected_lang=self._detect_language(new),
                    has_formulas=dna.has_formulas,
                )
                # For a semantic suspect, re-verify the repair so a faithful+clean
                # re-translation falls to 0 issues (adopted) while a still-unfaithful
                # one stays at 1 (rejected), unifying with the deterministic count.
                if semantic_enabled and "semantic" in orig_issues:
                    from .semantic_verifier import verify_chunk, is_unfaithful
                    v = await verify_chunk(
                        chunks[i].content, new, source_lang, target_lang, self.llm_client,
                    )
                    if is_unfaithful(v, min_severity="major"):
                        new_issues = new_issues + ["semantic"]
                # Adopt only when the repair is strictly better (fewer issues).
                if len(new_issues) < len(orig_issues):
                    return (i, new)
                return (i, None)

        results = await asyncio.gather(*[_repair_one(i, iss) for (i, iss) in to_repair])

        repaired = list(translated)
        count = 0
        for (i, new) in results:
            if new is not None:
                repaired[i] = new
                count += 1
                # Best-effort: overwrite the cache with the good repair so a later
                # run serves the improved translation instead of the bad one.
                if self.chunk_cache is not None:
                    try:
                        fp = self._active_ledger.fingerprint() if getattr(self, "_active_ledger", None) else "noterms"
                        key = self._chunk_cache_key(
                            chunks[i].content, source_lang, target_lang, profile_id,
                            ledger_fingerprint=fp,
                        )
                        if key:
                            await run_blocking(
                                self.chunk_cache.set,
                                key, new, source_lang, target_lang, mode=profile_id,
                            )
                    except Exception:
                        pass

        return (repaired, count)

    def _verify_latex_preservation(self, original: str, translated: str, chunk_index: int) -> str:
        """
        Verify and log LaTeX math preservation.

        Checks that $...$ delimiters and LaTeX commands are preserved.
        """
        import re

        # Extract math from original and translated
        original_math = re.findall(r'\$[^$]+\$|\$\$[^$]+\$\$', original)
        translated_math = re.findall(r'\$[^$]+\$|\$\$[^$]+\$\$', translated)

        # Log comparison
        if len(original_math) != len(translated_math):
            logger.warning(
                f"[Chunk {chunk_index}] Math count mismatch: "
                f"original={len(original_math)}, translated={len(translated_math)}"
            )

        # Check for common LaTeX commands
        latex_commands = ['\\sum', '\\frac', '\\int', '\\nabla', '\\partial',
                          '\\mathbb', '\\mathcal', '\\begin', '\\end', '\\alpha',
                          '\\beta', '\\gamma', '\\delta', '\\epsilon', '\\theta']

        missing_commands = []
        for cmd in latex_commands:
            orig_count = original.count(cmd)
            trans_count = translated.count(cmd)
            if orig_count > 0 and trans_count < orig_count:
                missing_commands.append(f"{cmd}: {orig_count}→{trans_count}")

        if missing_commands:
            logger.warning(f"[Chunk {chunk_index}] LaTeX commands reduced: {', '.join(missing_commands)}")

        return translated

    async def _assemble(
        self,
        translated_chunks: List[str],
        dna: DocumentDNA,
        profile_id: str,
        target_lang: str = "vi",
    ) -> str:
        """Assemble translated chunks into final document."""
        # Calculate total content size
        total_chars = sum(len(chunk) for chunk in translated_chunks)

        # For small documents (≤3 chunks) or large documents (>15000 chars),
        # just join directly. Claude assembly would truncate large documents.
        if len(translated_chunks) <= 3 or total_chars > 15000:
            logger.info(f"Simple join: {len(translated_chunks)} chunks, {total_chars:,} chars")
            return "\n\n".join(translated_chunks)

        # For medium documents, let Claude do light editing
        profile = get_profile(profile_id) or PROFILES.get("essay")

        # Join chunks with markers
        chunks_text = "\n\n---\n\n".join(translated_chunks)

        # Build rendering skill from base + profile-specific instructions
        rendering_skill = BASE_RENDERING_SKILL
        if profile.rendering_instructions:
            rendering_skill += "\n" + profile.rendering_instructions

        prompt = ASSEMBLY_PROMPT.format(
            dna_context=dna.to_context_prompt(),
            profile_prompt=profile.to_prompt(),
            rendering_skill=rendering_skill,
            chunks_text=chunks_text,
            target_lang=target_lang,
        )

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.translation_temperature,
            )
            assembled = response.content.strip()

            # Verify assembly didn't lose too much content
            if len(assembled) < total_chars * 0.7:
                logger.warning(f"Assembly lost content ({len(assembled)} vs {total_chars}), using simple join")
                return "\n\n".join(translated_chunks)

            return assembled
        except Exception as e:
            logger.warning(f"Assembly with Claude failed, using simple join: {e}")
            return "\n\n".join(translated_chunks)

    async def _convert(
        self,
        content: str,
        output_format: str,
        title: str,
        author: str,
        job_id: str,
        dna: Optional[DocumentDNA] = None,
        docx_template: str = "auto",
        pdf_template: str = "auto",
        profile_id: str = "essay",
        target_lang: str = "vi",
    ) -> Path:
        """Convert to final output format."""
        format_enum = OutputFormat(output_format.lower())
        filename = f"{job_id}_{title[:30].replace(' ', '_')}.{output_format}"
        output_path = self.output_dir / filename

        # Check if content has formulas (from DNA or content inspection)
        has_formulas = False
        if dna:
            has_formulas = dna.has_formulas

        # Also check content for LaTeX patterns
        if not has_formulas:
            formula_patterns = ['$', '\\begin{equation}', '\\frac', '\\sum', '\\int']
            has_formulas = any(p in content for p in formula_patterns)

        if has_formulas:
            logger.info(f"Document has formulas - using LaTeX-aware conversion")

        # Resolve template from profile first, then DNA-based heuristic
        profile = get_profile(profile_id)

        def _resolve_template(requested: str) -> str:
            """Resolve 'auto' template using profile, then DNA fallback."""
            if requested != "auto":
                return requested
            # Try profile-based template first
            if profile and profile.template_name != "auto":
                logger.info(f"Template from profile '{profile_id}': {profile.template_name}")
                return profile.template_name
            # Fallback to DNA-based heuristic
            if dna:
                genre = (dna.genre or "").lower()
                if any(kw in genre for kw in ["academic", "research", "paper", "thesis", "technical"]):
                    return "academic"
                elif any(kw in genre for kw in ["business", "report", "memo", "corporate"]):
                    return "business"
            return "ebook"

        language = target_lang

        # Use professional DOCX rendering if template specified and format is docx
        if format_enum == OutputFormat.DOCX and docx_template:
            try:
                template = _resolve_template(docx_template)
                logger.info(f"DOCX template: {template}")

                result_path = await self.converter.convert_markdown_to_docx_professional(
                    markdown_content=content,
                    output_path=output_path,
                    template=template,
                    title=title,
                    author=author or "Unknown",
                    language=language,
                )
                logger.info(f"Professional DOCX created: {result_path}")
                return result_path
            except Exception as e:
                logger.warning(f"Professional DOCX failed, falling back to pandoc: {e}")
                # Fall through to standard conversion

        # Use professional PDF rendering if template specified and format is pdf
        if format_enum == OutputFormat.PDF and pdf_template:
            try:
                template = _resolve_template(pdf_template)
                logger.info(f"PDF template: {template}")

                result_path = await self.converter.convert_markdown_to_pdf_professional(
                    markdown_content=content,
                    output_path=output_path,
                    template=template,
                    title=title,
                    author=author or "Unknown",
                    language=language,
                )
                logger.info(f"Professional PDF created: {result_path}")
                return result_path
            except Exception as e:
                logger.warning(f"Professional PDF failed, falling back to pandoc: {e}")
                # Fall through to standard conversion

        success = await self.converter.convert(
            content=content,
            output_format=format_enum,
            output_path=output_path,
            title=title,
            author=author,
            has_formulas=has_formulas,
        )

        if not success:
            # Fallback to markdown
            fallback_path = self.output_dir / f"{job_id}_{title[:30]}.md"
            fallback_path.write_text(content, encoding='utf-8')
            return fallback_path

        return output_path

    # ==================== VISION METHODS ====================

    async def _read_with_vision(
        self,
        pdf_path: Path,
        progress_callback: Optional[Callable] = None,
        profile_id: str = "academic_paper",
    ) -> str:
        """
        Read PDF using Claude Vision with document-type optimization.

        TRUE Claude-native: Claude sees the document, not text extraction.

        Args:
            pdf_path: Path to PDF file
            progress_callback: Called with (progress, stage)
            profile_id: Publishing profile for optimized reading

        Returns:
            Markdown+LaTeX content from Vision reading
        """
        def vision_progress(current, total):
            if progress_callback:
                progress = current / total
                progress_callback(progress, f"Vision reading page {current}/{total}")

        # Route to specialized reader based on profile
        novel_profiles = ['novel', 'fiction', 'literature', 'poetry']
        business_profiles = ['business_report', 'financial', 'legal', 'contract']

        if profile_id in novel_profiles:
            logger.info(f"Using NOVEL reading mode for profile: {profile_id}")
            vision_doc = await self.vision_reader.read_pdf_novel(
                pdf_path,
                dpi=150,
                progress_callback=vision_progress,
            )
        elif profile_id in business_profiles:
            logger.info(f"Using BUSINESS reading mode (enhanced tables) for profile: {profile_id}")
            vision_doc = await self.vision_reader.read_pdf_business(
                pdf_path,
                dpi=200,  # Higher DPI for tables
                progress_callback=vision_progress,
            )
        else:
            # Default academic/technical mode
            logger.info(f"Using default academic reading mode for profile: {profile_id}")
            vision_doc = await self.vision_reader.read_pdf(
                pdf_path,
                dpi=150,
                progress_callback=vision_progress,
            )

        # Assemble if multi-page
        if len(vision_doc.pages) > 1:
            logger.info(f"Assembling {len(vision_doc.pages)} pages from Vision")
            content = await self.vision_reader.assemble_document(vision_doc)
        else:
            content = vision_doc.full_content

        # Store table info for later use
        has_tables = any(p.has_tables for p in vision_doc.pages)

        logger.info(
            f"Vision read complete: {len(content)} chars, "
            f"{vision_doc.total_pages} pages, has_formulas={vision_doc.has_formulas}, "
            f"has_tables={has_tables}"
        )

        return content

    async def _extract_pdf_text_legacy(self, pdf_path: Path) -> str:
        """
        Legacy PDF text extraction (not recommended).

        Use Vision mode instead for better formula preservation.
        """
        return await run_blocking(_extract_pdf_text_sync, pdf_path)


# ==================== CONVENIENCE FUNCTIONS ====================

async def translate_document(
    text: str,
    source_lang: str,
    target_lang: str,
    llm_client: Any,
    profile: str = "essay",
    output_format: str = "docx",
    docx_template: str = "auto",
) -> PublishingJob:
    """
    Convenience function for quick translation.

    Args:
        text: Document text
        source_lang: Source language (or "auto")
        target_lang: Target language
        llm_client: LLM client
        profile: Publishing profile ID
        output_format: Output format
        docx_template: DOCX template ('ebook', 'academic', 'business', 'auto')

    Returns:
        PublishingJob with results
    """
    publisher = UniversalPublisher(llm_client)
    return await publisher.publish(
        source_text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        profile_id=profile,
        output_format=output_format,
        docx_template=docx_template,
    )


def list_supported_profiles() -> List[str]:
    """List all supported publishing profiles."""
    return list(PROFILES.keys())


def list_supported_formats() -> List[str]:
    """List all supported output formats."""
    return [f.value for f in OutputFormat]
