"""
Translation Service - GPT-4o-mini Default
AI Publisher Pro

Default model: GPT-4o-mini
- Best balance of quality and cost
- $0.15/$0.60 per 1M tokens
- Supports vision for complex pages
"""

import asyncio
import hashlib
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
import os

# Import config and analyzer
from .tiered_config import (
    TieredConfig,
    TranslationMode,
    ContentType,
    MODELS,
    get_economy_config,
    get_balanced_config,
    get_quality_config,
    estimate_cost
)
from .content_analyzer import ContentAnalyzer, ContentAnalysis


@dataclass
class TranslationResult:
    """Result of a single translation"""
    original: str
    translated: str
    model_used: str
    content_type: ContentType
    tokens_used: int = 0
    cost_estimate: float = 0.0
    cached: bool = False


@dataclass
class DocumentResult:
    """Result of document translation"""
    pages: List[TranslationResult]
    total_pages: int
    elapsed_seconds: float
    total_tokens: int
    total_cost: float
    model_distribution: Dict[str, int]
    cache_hits: int


class TranslationService:
    """
    Translation service with intelligent model routing.

    Default: GPT-4o-mini for best balance

    Features:
    - Automatic content analysis
    - Smart model selection
    - Parallel processing
    - Caching
    - Cost tracking
    """

    def __init__(
        self,
        mode: TranslationMode = TranslationMode.BALANCED,
        config: Optional[TieredConfig] = None,
        api_keys: Optional[Dict[str, str]] = None
    ):
        """
        Initialize translation service.

        Args:
            mode: Translation mode (economy, balanced, quality)
            config: Custom config (uses mode default if None)
            api_keys: API keys for providers
        """
        # Set config based on mode
        if config:
            self.config = config
        else:
            mode_configs = {
                TranslationMode.ECONOMY: get_economy_config(),
                TranslationMode.BALANCED: get_balanced_config(),
                TranslationMode.QUALITY: get_quality_config(),
            }
            self.config = mode_configs[mode]

        self.mode = mode
        self.analyzer = ContentAnalyzer(self.config)

        # API keys
        self.api_keys = api_keys or {
            "openai": os.getenv("OPENAI_API_KEY"),
            "claude": os.getenv("ANTHROPIC_API_KEY"),
            "gemini": os.getenv("GOOGLE_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY"),
        }

        # Cache
        self._cache: Dict[str, str] = {}
        self._cache_hits = 0

        # Clients (lazy init)
        self._clients = {}

        # Stats
        self._total_tokens = 0
        self._total_cost = 0.0
        self._model_usage = {}

    async def _get_client(self, provider: str):
        """Get or create API client for provider"""
        if provider in self._clients:
            return self._clients[provider]

        if provider == "openai":
            from openai import AsyncOpenAI
            self._clients[provider] = AsyncOpenAI(
                api_key=self.api_keys.get("openai")
            )

        elif provider == "claude":
            import anthropic
            self._clients[provider] = anthropic.AsyncAnthropic(
                api_key=self.api_keys.get("claude")
            )

        elif provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.api_keys.get("gemini"))
            self._clients[provider] = genai

        elif provider == "deepseek":
            from openai import AsyncOpenAI
            self._clients[provider] = AsyncOpenAI(
                api_key=self.api_keys.get("deepseek"),
                base_url="https://api.deepseek.com"
            )

        return self._clients[provider]

    def _get_cache_key(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        model: str
    ) -> str:
        """Generate cache key"""
        key = f"{model}:{source_lang}:{target_lang}:{text}"
        return hashlib.md5(key.encode()).hexdigest()

    async def translate_text(
        self,
        text: str,
        source_lang: str = "Chinese",
        target_lang: str = "Vietnamese",
        context: Optional[str] = None,
        force_model: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate a single piece of text.

        Args:
            text: Text to translate
            source_lang: Source language
            target_lang: Target language
            context: Optional context for better translation
            force_model: Force specific model (bypasses auto-routing)

        Returns:
            TranslationResult
        """
        if not text or not text.strip():
            return TranslationResult(
                original=text,
                translated="",
                model_used="none",
                content_type=ContentType.PLAIN_TEXT
            )

        # Analyze content
        analysis = self.analyzer.analyze(text)

        # Determine model
        if force_model:
            model_id = force_model
            # Find provider for model
            provider = "openai"  # default
            for m in MODELS.values():
                if m.model_id == force_model:
                    provider = m.provider
                    break
        else:
            model_config = MODELS.get(
                self.config.default_model,
                MODELS["gpt-4o-mini"]
            )

            # Override based on content type if not budget mode
            if not self.config.budget_mode:
                model_name = self.config.content_routing.get(
                    analysis.content_type,
                    self.config.default_model
                )
                if model_name in MODELS:
                    model_config = MODELS[model_name]

            model_id = model_config.model_id
            provider = model_config.provider

        # Check cache
        cache_key = self._get_cache_key(text, source_lang, target_lang, model_id)
        if self.config.enable_cache and cache_key in self._cache:
            self._cache_hits += 1
            return TranslationResult(
                original=text,
                translated=self._cache[cache_key],
                model_used=model_id,
                content_type=analysis.content_type,
                cached=True
            )

        # Build system prompt
        system_prompt = f"""You are an expert translator from {source_lang} to {target_lang}.

Translation Guidelines:
- Preserve the original meaning, tone, and style
- Maintain formatting (paragraphs, lists, emphasis)
- Keep technical terms, proper nouns, formulas, and code intact
- Ensure natural, fluent output in {target_lang}
{f"Context: {context}" if context else ""}

Output ONLY the translation, no explanations or notes."""

        # Call appropriate provider
        translated = await self._call_provider(
            provider=provider,
            model_id=model_id,
            system_prompt=system_prompt,
            user_content=text,
            temperature=analysis.recommended_temperature
        )

        # Cache result
        if self.config.enable_cache:
            self._cache[cache_key] = translated

        # Track usage
        tokens = len(text.split()) + len(translated.split())
        self._total_tokens += tokens
        self._model_usage[model_id] = self._model_usage.get(model_id, 0) + 1

        # Estimate cost
        model_config = None
        for m in MODELS.values():
            if m.model_id == model_id:
                model_config = m
                break

        cost = 0.0
        if model_config:
            cost = (tokens / 1_000_000) * (model_config.input_cost + model_config.output_cost)
            self._total_cost += cost

        return TranslationResult(
            original=text,
            translated=translated,
            model_used=model_id,
            content_type=analysis.content_type,
            tokens_used=tokens,
            cost_estimate=cost
        )

    async def _call_provider(
        self,
        provider: str,
        model_id: str,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.3
    ) -> str:
        """Call the appropriate provider API"""

        client = await self._get_client(provider)

        if provider in ["openai", "deepseek"]:
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content

        elif provider == "claude":
            response = await client.messages.create(
                model=model_id,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature
            )
            return response.content[0].text

        elif provider == "gemini":
            model = client.GenerativeModel(model_id)
            prompt = f"{system_prompt}\n\n{user_content}"
            response = await model.generate_content_async(prompt)
            return response.text

        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def translate_document(
        self,
        texts: List[str],
        source_lang: str = "Chinese",
        target_lang: str = "Vietnamese",
        context: Optional[str] = None,
        on_progress: Optional[Callable[[float, int, int], None]] = None
    ) -> DocumentResult:
        """
        Translate a document (list of text chunks).

        Args:
            texts: List of text chunks
            source_lang: Source language
            target_lang: Target language
            context: Optional context
            on_progress: Progress callback (progress%, done, total)

        Returns:
            DocumentResult with all translations
        """
        start_time = time.time()
        total = len(texts)
        results = []

        # Reset stats
        self._cache_hits = 0

        # Process in batches
        batch_size = self.config.max_concurrent

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]

            # Translate batch in parallel
            tasks = [
                self.translate_text(text, source_lang, target_lang, context)
                for text in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    print(f"Error on item {i+j}: {result}")
                    # Keep original on error
                    results.append(TranslationResult(
                        original=texts[i+j],
                        translated=texts[i+j],
                        model_used="error",
                        content_type=ContentType.PLAIN_TEXT
                    ))
                else:
                    results.append(result)

            # Progress callback
            done = min(i + batch_size, total)
            if on_progress:
                progress = done / total * 100
                on_progress(progress, done, total)

        elapsed = time.time() - start_time

        return DocumentResult(
            pages=results,
            total_pages=total,
            elapsed_seconds=elapsed,
            total_tokens=self._total_tokens,
            total_cost=self._total_cost,
            model_distribution=self._model_usage.copy(),
            cache_hits=self._cache_hits
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get translation stats"""
        return {
            "mode": self.mode.value,
            "default_model": self.config.default_model,
            "total_tokens": self._total_tokens,
            "total_cost": round(self._total_cost, 4),
            "model_usage": self._model_usage,
            "cache_hits": self._cache_hits,
            "cache_size": len(self._cache)
        }

    def reset_stats(self):
        """Reset stats"""
        self._total_tokens = 0
        self._total_cost = 0.0
        self._model_usage = {}
        self._cache_hits = 0


# =========================================
# Convenience Functions
# =========================================

async def translate_quick(
    texts: List[str],
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese",
    mode: TranslationMode = TranslationMode.BALANCED
) -> List[str]:
    """
    Quick translation with default settings.

    Uses GPT-4o-mini by default (balanced mode).
    """
    service = TranslationService(mode=mode)

    result = await service.translate_document(
        texts=texts,
        source_lang=source_lang,
        target_lang=target_lang,
        on_progress=lambda p, d, t: print(f"Progress: {p:.1f}% ({d}/{t})")
    )

    print(f"\n✅ Complete!")
    print(f"   Time: {result.elapsed_seconds:.1f}s")
    print(f"   Cost: ${result.total_cost:.4f}")
    print(f"   Models: {result.model_distribution}")

    return [r.translated for r in result.pages]


# =========================================
# Example Usage
# =========================================

async def main():
    """Example usage"""

    # Sample texts (Chinese)
    texts = [
        "今天天气很好，我想去公园散步。",
        "机器学习是人工智能的一个分支，它使计算机能够从数据中学习。",
        "def calculate(x, y):\n    return x + y",
        "| 名称 | 价格 |\n|------|------|\n| 苹果 | 5元 |",
        "根据公式 $E = mc^2$，能量与质量成正比。"
    ]

    print("🚀 Translation Service - GPT-4o-mini Default")
    print("=" * 50)

    # Test with balanced mode (GPT-4o-mini)
    service = TranslationService(mode=TranslationMode.BALANCED)

    print(f"\nMode: {service.mode.value}")
    print(f"Default model: {service.config.default_model}")

    # Translate
    for i, text in enumerate(texts):
        result = await service.translate_text(
            text=text,
            source_lang="Chinese",
            target_lang="Vietnamese"
        )

        print(f"\n--- Text {i+1} ---")
        print(f"Type: {result.content_type.value}")
        print(f"Model: {result.model_used}")
        print(f"Original: {text[:50]}...")
        print(f"Translated: {result.translated[:50]}...")

    # Print stats
    stats = service.get_stats()
    print(f"\n📊 Stats:")
    print(f"   Total tokens: {stats['total_tokens']}")
    print(f"   Total cost: ${stats['total_cost']:.4f}")
    print(f"   Models used: {stats['model_usage']}")


if __name__ == "__main__":
    asyncio.run(main())
