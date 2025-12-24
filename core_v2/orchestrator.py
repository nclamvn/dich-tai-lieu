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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

from .document_dna import DocumentDNA, extract_dna, quick_dna
from .semantic_chunker import SemanticChunker, SemanticChunk
from .publishing_profiles import PublishingProfile, PROFILES, get_profile
from .output_converter import OutputConverter, OutputFormat
from .verifier import QualityVerifier, VerificationResult
from .vision_reader import VisionReader, VisionDocument

logger = logging.getLogger(__name__)


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

TRANSLATION_PROMPT = """You are a professional translator and publisher.

DOCUMENT DNA:
{dna_context}

PUBLISHING PROFILE:
{profile_prompt}

CONTEXT:
- This is chunk {chunk_index} of {total_chunks}
- Previous content: {previous_summary}
- Next content: {next_preview}

TRANSLATION TASK:
Translate the following text from {source_lang} to {target_lang}.

Source Text:
{source_text}

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
        concurrency: int = 1,  # Reduced to avoid Anthropic rate limits (8k tokens/min)
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

    async def publish(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        profile_id: str = "essay",
        output_format: str = "docx",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        use_vision: bool = True,  # NEW: Use Claude Vision for PDF reading
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

            # Stage 2: Chunk document (55%)
            update_progress(0.55, "Chunking document")
            job.status = JobStatus.CHUNKING
            job.chunks = await self.chunker.chunk(source_text)
            logger.info(f"Document split into {len(job.chunks)} chunks")

            # Stage 3: Translate chunks (55% - 90%)
            update_progress(0.55, "Translating")
            job.status = JobStatus.TRANSLATING
            job.translated_chunks = await self._translate_chunks(
                job.chunks,
                job.dna,
                profile_id,
                source_lang,
                target_lang,
                lambda p: update_progress(0.55 + p * 0.35, f"Translating chunk {int(p * len(job.chunks))}/{len(job.chunks)}"),
            )

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
                job.dna.title or "translated_document",
                job.dna.author,
                job.job_id,
                dna=job.dna,  # Pass DNA for formula detection
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

        async def translate_with_semaphore(chunk: SemanticChunk) -> tuple[int, str]:
            """Translate single chunk with semaphore control."""
            async with self._semaphore:
                result = await self._translate_chunk(
                    chunk, dna, profile, source_lang, target_lang
                )
                completed[0] += 1
                if progress_callback:
                    progress_callback(completed[0] / total)
                return (chunk.index, result)

        # Launch all translations concurrently (semaphore limits parallelism)
        tasks = [translate_with_semaphore(chunk) for chunk in chunks]
        results_with_index = await asyncio.gather(*tasks)

        # Sort by original index to maintain order
        results_with_index.sort(key=lambda x: x[0])
        return [r[1] for r in results_with_index]

    async def _translate_chunk(
        self,
        chunk: SemanticChunk,
        dna: DocumentDNA,
        profile: PublishingProfile,
        source_lang: str,
        target_lang: str,
        max_retries: int = 3,
    ) -> str:
        """Translate a single chunk with retry logic for rate limits."""
        prompt = TRANSLATION_PROMPT.format(
            dna_context=dna.to_context_prompt(),
            profile_prompt=profile.to_prompt(),
            chunk_index=chunk.index + 1,
            total_chunks=chunk.total_chunks,
            previous_summary=chunk.previous_summary or "Start of document",
            next_preview=chunk.next_preview or "End of document",
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=chunk.content,
        )

        for attempt in range(max_retries):
            try:
                response = await self.llm_client.chat(
                    messages=[{"role": "user", "content": prompt}]
                )
                translated = response.content.strip()

                # Verify LaTeX preservation if document has formulas
                if dna.has_formulas:
                    translated = self._verify_latex_preservation(chunk.content, translated, chunk.index)

                return translated
            except Exception as e:
                error_str = str(e).lower()
                # Check for rate limit error
                if "429" in str(e) or "rate_limit" in error_str:
                    wait_time = (attempt + 1) * 15  # 15s, 30s, 45s
                    logger.warning(f"Rate limit hit for chunk {chunk.index}, waiting {wait_time}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Translation failed for chunk {chunk.index}: {e}")
                    return f"[TRANSLATION ERROR: {chunk.index}]"

        logger.error(f"Translation failed for chunk {chunk.index} after {max_retries} retries")
        return f"[TRANSLATION ERROR: {chunk.index}]"

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

        prompt = ASSEMBLY_PROMPT.format(
            dna_context=dna.to_context_prompt(),
            profile_prompt=profile.to_prompt(),
            chunks_text=chunks_text,
            target_lang=target_lang,
        )

        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}]
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


# ==================== CONVENIENCE FUNCTIONS ====================

async def translate_document(
    text: str,
    source_lang: str,
    target_lang: str,
    llm_client: Any,
    profile: str = "essay",
    output_format: str = "docx",
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
    )


def list_supported_profiles() -> List[str]:
    """List all supported publishing profiles."""
    return list(PROFILES.keys())


def list_supported_formats() -> List[str]:
    """List all supported output formats."""
    return [f.value for f in OutputFormat]
