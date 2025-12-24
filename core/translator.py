#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core Translation Engine for AI Translator Pro.

This module provides the main translation functionality, including:
- Single chunk translation with LLM providers (OpenAI, Anthropic)
- Parallel translation for multiple chunks
- Translation Memory (TM) integration for reuse
- Multi-level caching (chunk cache, legacy cache)
- Glossary integration for terminology consistency
- Quality validation with automatic retry

Usage:
    from core.translator import TranslatorEngine
    from core.chunker import TranslationChunk

    engine = TranslatorEngine(
        provider="openai",
        model="gpt-4",
        api_key="sk-...",
        source_lang="en",
        target_lang="vi"
    )

    async with httpx.AsyncClient() as client:
        result = await engine.translate_chunk(client, chunk)

Classes:
    TranslatorEngine: Main translation engine with multi-provider support.

Dependencies:
    - httpx: Async HTTP client for API calls
    - TranslationMemory: For translation reuse
    - QualityValidator: For translation validation
    - GlossaryManager: For terminology management
"""

import asyncio
from typing import Optional, List, Any
from collections.abc import Callable
import httpx

from .chunker import TranslationChunk
from .validator import TranslationResult, QualityValidator
from .glossary import GlossaryManager
from .cache import TranslationCache
from .parallel import ParallelProcessor, BatchProcessor, ProcessingStats
from .translation_memory import TranslationMemory, TMSegment
from .language import LanguagePair, get_language_pair, get_language_name, LanguageValidator

from config.logging_config import get_logger
logger = get_logger(__name__)



class TranslatorEngine:
    """
    Main translation engine with multi-provider LLM support.

    Provides high-quality translation using OpenAI or Anthropic APIs with:
    - Translation Memory for reuse of previous translations
    - Multi-level caching (chunk cache + legacy cache)
    - Glossary integration for terminology consistency
    - Quality validation with automatic retry on low scores
    - Language-agnostic prompt building

    Attributes:
        provider: LLM provider name ('openai' or 'anthropic').
        model: Model identifier (e.g., 'gpt-4', 'claude-3-opus').
        api_key: API key for the provider.
        source_lang: Source language code (ISO 639-1).
        target_lang: Target language code (ISO 639-1).
        glossary_mgr: Optional glossary manager for terminology.
        cache: Legacy translation cache.
        chunk_cache: Phase 5.1 chunk-level cache.
        validator: Quality validator instance.
        tm: Translation Memory instance.
        tm_exact_matches: Count of exact TM matches used.
        tm_fuzzy_matches: Count of fuzzy TM matches used.

    Example:
        >>> engine = TranslatorEngine(
        ...     provider="openai",
        ...     model="gpt-4",
        ...     api_key="sk-xxx",
        ...     source_lang="en",
        ...     target_lang="vi"
        ... )
        >>> async with httpx.AsyncClient() as client:
        ...     result = await engine.translate_chunk(client, chunk)
        >>> print(result.translated)
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        source_lang: str = "en",
        target_lang: str = "vi",
        glossary_mgr: Optional[GlossaryManager] = None,
        cache: Optional[TranslationCache] = None,
        validator: Optional[QualityValidator] = None,
        tm: Optional[TranslationMemory] = None,
        tm_fuzzy_threshold: float = 0.85,
        max_retries: int = 5,
        retry_delay: int = 3,
        chunk_cache=None,
        mode: str = "simple",
        domain: Optional[str] = None
    ):
        """
        Initialize TranslatorEngine.

        Args:
            provider: LLM provider ('openai' or 'anthropic').
            model: Model name/ID to use for translation.
            api_key: API key for the provider.
            source_lang: Source language code (default: 'en').
            target_lang: Target language code (default: 'vi').
            glossary_mgr: Optional GlossaryManager for terminology.
            cache: Optional legacy TranslationCache.
            validator: Optional QualityValidator (creates default if None).
            tm: Optional TranslationMemory for reuse.
            tm_fuzzy_threshold: Minimum similarity for fuzzy TM matches (0-1).
            max_retries: Maximum retry attempts on failure.
            retry_delay: Delay in seconds between retries.
            chunk_cache: Optional ChunkCache for persistent caching.
            mode: Pipeline mode for cache key differentiation.
            domain: Domain for cache key (e.g., 'stem', 'book').

        Raises:
            ValueError: If provider is not supported.
        """
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key

        # Language configuration
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.language_pair = get_language_pair(source_lang, target_lang)

        self.glossary_mgr = glossary_mgr
        self.cache = cache
        self.validator = validator or QualityValidator()
        self.tm = tm
        self.tm_fuzzy_threshold = tm_fuzzy_threshold
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Phase 5.1: Chunk cache configuration
        self.chunk_cache = chunk_cache
        self.mode = mode
        self.domain = domain

        # TM statistics
        self.tm_exact_matches = 0
        self.tm_fuzzy_matches = 0
        self.tm_no_matches = 0

    def build_prompt(self, chunk: TranslationChunk) -> str:
        """
        Build translation prompt for LLM with context and glossary.

        Creates a comprehensive prompt that includes:
        - Translation instructions with quality requirements
        - Glossary terms for terminology consistency
        - Context from surrounding chunks (if available)
        - The source text to translate

        Args:
            chunk: TranslationChunk with text and optional context.

        Returns:
            Formatted prompt string ready for LLM API call.

        Note:
            The prompt is language-agnostic and adapts based on
            source_lang and target_lang configuration.
        """
        source_name = get_language_name(self.source_lang)
        target_name = get_language_name(self.target_lang)

        prompt_parts = [
            f"You are an expert translator with 20 years of experience.",
            f"Translate the following text from {source_name} to {target_name}.",
            "",
            "IMPORTANT REQUIREMENTS:",
            "1. Translate ALL content, do not omit anything",
            "2. Preserve meaning and tone",
            "3. Natural, fluent style - not machine translation",
            "4. Preserve formatting (line breaks, bullet points, etc.)",
            "5. Proper nouns: transcribe or keep original as appropriate",
            ""
        ]

        # Add glossary nếu có
        if self.glossary_mgr:
            glossary_section = self.glossary_mgr.build_prompt_section()
            if glossary_section:
                prompt_parts.append(glossary_section)
                prompt_parts.append("")

        # FIX-004: Add context với chỉ dẫn rõ ràng KHÔNG DỊCH
        if chunk.context_before or chunk.context_after:
            prompt_parts.append("=" * 50)
            prompt_parts.append("CONTEXT (DO NOT TRANSLATE - for reference only):")
            prompt_parts.append("Use this context to maintain consistency in terminology and tone.")
            prompt_parts.append("DO NOT include this context in your translation output.")
            prompt_parts.append("-" * 50)
            if chunk.context_before:
                prompt_parts.append(f"[Previous paragraph]: ...{chunk.context_before}")
            if chunk.context_after:
                prompt_parts.append(f"[Next paragraph]: {chunk.context_after}...")
            prompt_parts.append("=" * 50)
            prompt_parts.append("")

        prompt_parts.extend([
            f"TEXT TO TRANSLATE ({source_name}):",
            "---START---",
            chunk.text,
            "---END---",
            "",
            f"IMPORTANT: Translate ONLY the text between ---START--- and ---END---.",
            f"Output the {target_name} translation only. No explanations, no context."
        ])

        return "\n".join(prompt_parts)

    async def translate_chunk(
        self,
        client: httpx.AsyncClient,
        chunk: TranslationChunk
    ) -> TranslationResult:
        """
        Translate a single chunk with caching, TM lookup, and validation.

        Translation flow:
        1. Check Translation Memory for exact/fuzzy matches
        2. Check chunk cache for cached translation
        3. Check legacy cache
        4. If not cached, call LLM API with retry logic
        5. Validate translation quality
        6. Cache successful translations (quality >= 0.7)
        7. Save to Translation Memory

        Args:
            client: httpx.AsyncClient for API calls.
            chunk: TranslationChunk containing text to translate.

        Returns:
            TranslationResult with translated text, quality score, and metadata.

        Raises:
            ValueError: If provider is not supported.

        Note:
            Low quality translations (score < 0.5) trigger automatic retry.
            Failed translations return fallback text with quality_score=0.
        """
        # 1. Check Translation Memory first (exact match)
        if self.tm:
            exact_match = self.tm.get_exact_match(
                chunk.text,
                self.source_lang,
                self.target_lang
            )
            if exact_match:
                self.tm_exact_matches += 1
                # FIX-002: Copy overlap_char_count
                overlap_count = getattr(chunk, 'overlap_char_count', 0)
                result = TranslationResult(
                    chunk_id=chunk.id,
                    source=chunk.text,
                    translated=exact_match.segment.target,
                    quality_score=exact_match.segment.quality_score,
                    overlap_char_count=overlap_count
                )
                result.warnings.append(f"✓ TM exact match (100%)")
                return result

            # Check fuzzy matches
            fuzzy_matches = self.tm.get_fuzzy_matches(
                chunk.text,
                self.source_lang,
                self.target_lang,
                threshold=self.tm_fuzzy_threshold,
                max_results=1
            )
            if fuzzy_matches and fuzzy_matches[0].similarity >= self.tm_fuzzy_threshold:
                self.tm_fuzzy_matches += 1
                match = fuzzy_matches[0]
                # FIX-002: Copy overlap_char_count
                overlap_count = getattr(chunk, 'overlap_char_count', 0)
                result = TranslationResult(
                    chunk_id=chunk.id,
                    source=chunk.text,
                    translated=match.segment.target,
                    quality_score=match.segment.quality_score * match.similarity,
                    overlap_char_count=overlap_count
                )
                result.warnings.append(f"✓ TM fuzzy match ({match.similarity:.1%})")
                return result

            self.tm_no_matches += 1

        # 2. Phase 5.1: Check new chunk cache (hash-based, persistent)
        if self.chunk_cache:
            from .cache.chunk_cache import compute_chunk_key
            cache_key = compute_chunk_key(
                source_text=chunk.text,
                source_lang=self.source_lang,
                target_lang=self.target_lang,
                mode=self.mode,
                domain=self.domain
            )
            cached_translation = self.chunk_cache.get(cache_key)
            if cached_translation:
                # FIX-002: Copy overlap_char_count
                overlap_count = getattr(chunk, 'overlap_char_count', 0)
                return TranslationResult(
                    chunk_id=chunk.id,
                    source=chunk.text,
                    translated=cached_translation,
                    quality_score=1.0,  # Cached results assumed high quality
                    overlap_char_count=overlap_count
                )

        # Fallback to legacy cache
        if self.cache:
            cached = self.cache.get(chunk.text, self.model)
            if cached:
                # FIX-002: Copy overlap_char_count
                overlap_count = getattr(chunk, 'overlap_char_count', 0)
                return TranslationResult(
                    chunk_id=chunk.id,
                    source=chunk.text,
                    translated=cached,
                    quality_score=1.0,
                    overlap_char_count=overlap_count
                )

        prompt = self.build_prompt(chunk)

        for attempt in range(1, self.max_retries + 1):
            try:
                # Call API
                if self.provider == "openai":
                    translated = await self._call_openai(client, prompt, chunk.text)
                elif self.provider == "anthropic":
                    translated = await self._call_anthropic(client, prompt, chunk.text)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")

                if not translated.strip():
                    raise ValueError("Empty translation")

                # Validate
                # FIX-002: Copy overlap_char_count từ chunk sang result
                overlap_count = getattr(chunk, 'overlap_char_count', 0)
                result = TranslationResult(
                    chunk_id=chunk.id,
                    source=chunk.text,
                    translated=translated,
                    overlap_char_count=overlap_count
                )

                domain = self.glossary_mgr.domain if self.glossary_mgr else 'default'
                validation = self.validator.validate(
                    chunk.text, translated, self.glossary_mgr,
                    domain=domain,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang
                )
                result.quality_score = validation.quality_score
                result.warnings = validation.warnings

                # Retry if quality too low
                if result.quality_score < 0.5 and attempt < self.max_retries:
                    logger.warning(f" Chunk {chunk.id}: Low quality {result.quality_score:.2f}, retrying...")
                    await asyncio.sleep(self.retry_delay)
                    continue

                # Phase 5.1: Cache successful translation in new chunk cache
                if self.chunk_cache and result.quality_score >= 0.7:
                    from .cache.chunk_cache import compute_chunk_key
                    cache_key = compute_chunk_key(
                        source_text=chunk.text,
                        source_lang=self.source_lang,
                        target_lang=self.target_lang,
                        mode=self.mode,
                        domain=self.domain
                    )
                    self.chunk_cache.set(
                        key=cache_key,
                        value=translated,
                        source_lang=self.source_lang,
                        target_lang=self.target_lang,
                        mode=self.mode
                    )

                # Legacy cache (fallback)
                if self.cache and result.quality_score >= 0.7:
                    self.cache.set(chunk.text, translated, self.model, result.quality_score)

                # Save to Translation Memory
                if self.tm and result.quality_score >= 0.7:
                    tm_segment = TMSegment(
                        source=chunk.text,
                        target=translated,
                        source_lang=self.source_lang,
                        target_lang=self.target_lang,
                        domain=domain,
                        quality_score=result.quality_score,
                        context_before=chunk.context_before,
                        context_after=chunk.context_after,
                        created_by=f"{self.provider}/{self.model}"
                    )
                    self.tm.add_segment(tm_segment)

                return result

            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    # Return với fallback
                    # FIX-002: Copy overlap_char_count
                    overlap_count = getattr(chunk, 'overlap_char_count', 0)
                    return TranslationResult(
                        chunk_id=chunk.id,
                        source=chunk.text,
                        translated=f"[TRANSLATION FAILED: {str(e)}]\n{chunk.text}",
                        quality_score=0.0,
                        warnings=[f"Translation failed after {self.max_retries} attempts: {str(e)}"],
                        overlap_char_count=overlap_count
                    )

    async def translate_parallel(
        self,
        chunks: List[TranslationChunk],
        max_concurrency: int = 10,
        show_progress: bool = True,
        progress_callback: Optional[Callable] = None,
        cancellation_token: Optional[Any] = None
    ) -> tuple[List[TranslationResult], ProcessingStats]:
        """
        Translate multiple chunks in parallel with concurrency control.

        Uses ParallelProcessor to handle concurrent API calls with rate
        limiting, retries, and progress tracking. Optimal for medium-sized
        documents (10-100 chunks).

        Args:
            chunks: List of TranslationChunks to translate.
            max_concurrency: Maximum concurrent API calls (default: 10).
                Higher values speed up processing but may hit rate limits.
            show_progress: Display progress bar in terminal.
            progress_callback: Optional callback function with signature
                ``callback(completed: int, total: int, quality_score: float)``.
            cancellation_token: Optional token to cancel processing.
                Set ``token.cancelled = True`` to stop.

        Returns:
            Tuple of (results, stats) where:
                - results: List[TranslationResult] in same order as input
                - stats: ProcessingStats with timing and cache metrics

        Example:
            >>> results, stats = await engine.translate_parallel(
            ...     chunks, max_concurrency=5
            ... )
            >>> print(f"Completed {stats.completed}/{stats.total}")
        """
        processor = ParallelProcessor(
            max_concurrency=max_concurrency,
            max_retries=self.max_retries,
            timeout=120.0,
            show_progress=show_progress,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token
        )

        # Use self.translate_chunk as the processing function
        results, stats = await processor.process_all(
            chunks,
            self.translate_chunk
        )

        # Update cache stats if available
        if self.cache:
            stats.cache_hits = self.cache.hits
            stats.cache_misses = self.cache.misses

        return results, stats

    async def translate_in_batches(
        self,
        chunks: List[TranslationChunk],
        batch_size: int = 20,
        max_concurrency: int = 5
    ) -> tuple[List[TranslationResult], ProcessingStats]:
        """
        Translate chunks in sequential batches for large documents.

        Processes chunks in batches to manage memory and provide natural
        checkpoints. Better for large documents (100+ chunks) where
        full parallel processing could overwhelm resources.

        Args:
            chunks: List of TranslationChunks to translate.
            batch_size: Number of chunks per batch (default: 20).
                Larger batches = faster but more memory.
            max_concurrency: Concurrent calls within each batch (default: 5).
                Lower than translate_parallel to avoid rate limits.

        Returns:
            Tuple of (results, stats) where:
                - results: List[TranslationResult] in same order as input
                - stats: ProcessingStats with combined metrics from all batches

        Example:
            >>> # For a 500-chunk document
            >>> results, stats = await engine.translate_in_batches(
            ...     chunks, batch_size=25, max_concurrency=5
            ... )
            >>> # Processes 20 batches of 25 chunks each
        """
        batch_processor = BatchProcessor(
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )

        results, stats = await batch_processor.process_in_batches(
            chunks,
            self.translate_chunk
        )

        # Update cache stats
        if self.cache:
            stats.cache_hits = self.cache.hits
            stats.cache_misses = self.cache.misses

        return results, stats

    async def _call_openai(self, client: httpx.AsyncClient, prompt: str, text: str) -> str:
        """
        Call OpenAI Chat Completions API.

        Makes an async HTTP request to OpenAI's API with configured model
        and parameters optimized for translation (low temperature, high top_p).

        Args:
            client: httpx.AsyncClient for making the request.
            prompt: System prompt with translation instructions.
            text: Source text to translate (sent as user message).

        Returns:
            Translated text from the API response.

        Raises:
            httpx.HTTPStatusError: On API errors (rate limit, auth, etc.).
            Exception: On network or parsing errors.

        Note:
            Uses temperature=0.3 and top_p=0.9 for consistent,
            high-quality translations. Timeout is 120 seconds.
        """
        logger.info(f" Calling OpenAI API: model={self.model}, text_length={len(text)} chars")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        }

        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            data = response.json()
            result = data["choices"][0]["message"]["content"].strip()
            logger.info(f" OpenAI API success: returned {len(result)} chars")
            return result

        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail += f": {error_body.get('error', {}).get('message', str(error_body))}"
            except:
                error_detail += f": {e.response.text[:200]}"
            logger.error(f" OpenAI API error: {error_detail}")
            raise
        except Exception as e:
            logger.error(f" OpenAI API exception: {type(e).__name__}: {str(e)}")
            raise

    async def _call_anthropic(self, client: httpx.AsyncClient, prompt: str, text: str) -> str:
        """
        Call Anthropic Messages API.

        Makes an async HTTP request to Anthropic's Claude API with configured
        model and parameters optimized for translation tasks.

        Args:
            client: httpx.AsyncClient for making the request.
            prompt: System prompt with translation instructions.
            text: Source text to translate (sent as user message).

        Returns:
            Translated text from the API response.

        Raises:
            httpx.HTTPStatusError: On API errors (rate limit, auth, etc.).
            Exception: On network or parsing errors.

        Note:
            Uses anthropic-version 2023-06-01 and max_tokens=4096.
            Timeout is 180 seconds (longer for Claude's thorough responses).
        """
        logger.info(f" Calling Anthropic API: model={self.model}, text_length={len(text)} chars")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.3,
            "system": prompt,
            "messages": [{"role": "user", "content": text}]
        }

        try:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=180
            )
            response.raise_for_status()

            data = response.json()
            content = []
            for part in data.get("content", []):
                if part.get("type") == "text":
                    content.append(part.get("text", ""))

            result = "\n".join(content).strip()
            logger.info(f" Anthropic API success: returned {len(result)} chars")
            return result

        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail += f": {error_body.get('error', {}).get('message', str(error_body))}"
            except:
                error_detail += f": {e.response.text[:200]}"
            logger.error(f" Anthropic API error: {error_detail}")
            raise
        except Exception as e:
            logger.error(f" Anthropic API exception: {type(e).__name__}: {str(e)}")
            raise
