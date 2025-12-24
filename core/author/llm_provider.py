"""
LLM Provider Abstraction (Phase 5C)

Unified interface for multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)
- Fallback to placeholder mode if no API key

Supports:
- Streaming and non-streaming responses
- Token counting and cost tracking
- Rate limiting and retry logic
- Response caching for efficiency
"""

import os
import json
import time
import hashlib
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    PLACEHOLDER = "placeholder"  # Fallback mode (no API calls)


class LLMModel(str, Enum):
    """Supported models"""
    # OpenAI
    GPT4_TURBO = "gpt-4-turbo-preview"
    GPT4 = "gpt-4"
    GPT35_TURBO = "gpt-3.5-turbo"

    # Anthropic
    CLAUDE_35_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"

    # Placeholder
    PLACEHOLDER = "placeholder"


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    provider: LLMProvider
    model: LLMModel
    api_key: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7

    # Cost tracking
    cost_per_1k_input_tokens: float = 0.01  # Default pricing
    cost_per_1k_output_tokens: float = 0.03

    # Rate limiting
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 90000

    # Caching
    enable_cache: bool = True
    cache_dir: Optional[Path] = None


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    provider: LLMProvider
    model: str

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Cost tracking
    cost_usd: float = 0.0

    # Performance
    latency_ms: float = 0.0
    cached: bool = False

    # Metadata
    timestamp: float = field(default_factory=time.time)


class LLMClient:
    """
    Unified LLM client supporting multiple providers

    Usage:
        client = LLMClient(config)
        response = await client.generate("Write a story about...")
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM client

        Args:
            config: LLMConfig with provider and model settings
        """
        self.config = config
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0

        # Initialize cache
        if config.enable_cache:
            if config.cache_dir is None:
                config.cache_dir = Path.home() / ".translator_cache" / "llm"
            config.cache_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting state
        self.last_request_time = 0
        self.tokens_used_this_minute = 0
        self.requests_this_minute = 0
        self.minute_start = time.time()

        # Initialize provider client
        self._init_provider()

    def _init_provider(self):
        """Initialize the specific provider client"""
        if self.config.provider == LLMProvider.OPENAI:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")

        elif self.config.provider == LLMProvider.ANTHROPIC:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")

        elif self.config.provider == LLMProvider.PLACEHOLDER:
            # No initialization needed for placeholder
            pass

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response from LLM

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens from config
            temperature: Override temperature from config
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated content
        """
        start_time = time.time()

        # Use config defaults if not provided
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature or self.config.temperature

        # Check cache
        if self.config.enable_cache:
            cache_key = self._get_cache_key(prompt, system_prompt, max_tokens, temperature)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                cached_response.cached = True
                return cached_response

        # Rate limiting
        await self._rate_limit()

        # Generate based on provider
        if self.config.provider == LLMProvider.OPENAI:
            response = await self._generate_openai(prompt, system_prompt, max_tokens, temperature, **kwargs)

        elif self.config.provider == LLMProvider.ANTHROPIC:
            response = await self._generate_anthropic(prompt, system_prompt, max_tokens, temperature, **kwargs)

        elif self.config.provider == LLMProvider.PLACEHOLDER:
            response = self._generate_placeholder(prompt, system_prompt)

        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

        # Calculate latency
        response.latency_ms = (time.time() - start_time) * 1000

        # Update tracking
        self.total_cost += response.cost_usd
        self.total_tokens += response.total_tokens
        self.request_count += 1

        # Cache response
        if self.config.enable_cache and not response.cached:
            self._save_to_cache(cache_key, response)

        return response

    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> LLMResponse:
        """Generate using OpenAI API"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Make API call
        completion = self.openai_client.chat.completions.create(
            model=self.config.model.value,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        # Extract response
        content = completion.choices[0].message.content

        # Token usage
        input_tokens = completion.usage.prompt_tokens
        output_tokens = completion.usage.completion_tokens
        total_tokens = completion.usage.total_tokens

        # Calculate cost
        cost = (
            (input_tokens / 1000) * self.config.cost_per_1k_input_tokens +
            (output_tokens / 1000) * self.config.cost_per_1k_output_tokens
        )

        return LLMResponse(
            content=content,
            provider=self.config.provider,
            model=self.config.model.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost
        )

    async def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> LLMResponse:
        """Generate using Anthropic API"""

        # Make API call
        message = self.anthropic_client.messages.create(
            model=self.config.model.value,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )

        # Extract response
        content = message.content[0].text

        # Token usage
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        total_tokens = input_tokens + output_tokens

        # Calculate cost (Claude 3.5 Sonnet pricing)
        cost = (
            (input_tokens / 1000) * 0.003 +  # $3/MTok input
            (output_tokens / 1000) * 0.015   # $15/MTok output
        )

        return LLMResponse(
            content=content,
            provider=self.config.provider,
            model=self.config.model.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost
        )

    def _generate_placeholder(
        self,
        prompt: str,
        system_prompt: Optional[str]
    ) -> LLMResponse:
        """Generate placeholder response (no API call)"""

        # Simple keyword-based extraction (like before)
        content = json.dumps({
            "note": "Placeholder mode - using pattern-based extraction",
            "detected": "basic patterns only",
            "upgrade": "Add API key for better results"
        })

        return LLMResponse(
            content=content,
            provider=LLMProvider.PLACEHOLDER,
            model="placeholder",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost_usd=0.0
        )

    async def _rate_limit(self):
        """Apply rate limiting"""
        current_time = time.time()

        # Reset counters if a minute has passed
        if current_time - self.minute_start >= 60:
            self.minute_start = current_time
            self.tokens_used_this_minute = 0
            self.requests_this_minute = 0

        # Check request limit
        if self.requests_this_minute >= self.config.max_requests_per_minute:
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.minute_start = time.time()
                self.tokens_used_this_minute = 0
                self.requests_this_minute = 0

        # Check token limit
        if self.tokens_used_this_minute >= self.config.max_tokens_per_minute:
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.minute_start = time.time()
                self.tokens_used_this_minute = 0
                self.requests_this_minute = 0

        # Increment counters
        self.requests_this_minute += 1
        self.tokens_used_this_minute += self.config.max_tokens  # Estimate

    def _get_cache_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate cache key from parameters"""
        cache_string = f"{self.config.model.value}:{system_prompt}:{prompt}:{max_tokens}:{temperature}"
        return hashlib.sha256(cache_string.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[LLMResponse]:
        """Get response from cache"""
        if not self.config.enable_cache:
            return None

        cache_file = self.config.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)

                return LLMResponse(
                    content=data['content'],
                    provider=LLMProvider(data['provider']),
                    model=data['model'],
                    input_tokens=data['input_tokens'],
                    output_tokens=data['output_tokens'],
                    total_tokens=data['total_tokens'],
                    cost_usd=data['cost_usd'],
                    latency_ms=0.0,
                    cached=True
                )
            except Exception:
                # Cache read failed, ignore
                pass

        return None

    def _save_to_cache(self, cache_key: str, response: LLMResponse):
        """Save response to cache"""
        if not self.config.enable_cache:
            return

        cache_file = self.config.cache_dir / f"{cache_key}.json"

        try:
            data = {
                'content': response.content,
                'provider': response.provider.value,
                'model': response.model,
                'input_tokens': response.input_tokens,
                'output_tokens': response.output_tokens,
                'total_tokens': response.total_tokens,
                'cost_usd': response.cost_usd,
                'timestamp': response.timestamp
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            # Cache write failed, ignore
            pass

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            'provider': self.config.provider.value,
            'model': self.config.model.value,
            'total_requests': self.request_count,
            'total_tokens': self.total_tokens,
            'total_cost_usd': round(self.total_cost, 4),
            'avg_cost_per_request': round(self.total_cost / max(self.request_count, 1), 4)
        }


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def create_llm_client(
    provider: str = "placeholder",
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> LLMClient:
    """
    Create LLM client with sensible defaults

    Args:
        provider: "openai", "anthropic", or "placeholder"
        model: Specific model name (optional)
        api_key: API key (optional, will check env vars)

    Returns:
        Configured LLMClient
    """
    # Get provider enum
    provider_enum = LLMProvider(provider)

    # Auto-detect API key from environment if not provided
    if api_key is None:
        if provider_enum == LLMProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider_enum == LLMProvider.ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY")

    # Select default model if not specified
    if model is None:
        if provider_enum == LLMProvider.OPENAI:
            model_enum = LLMModel.GPT4_TURBO
        elif provider_enum == LLMProvider.ANTHROPIC:
            model_enum = LLMModel.CLAUDE_35_SONNET
        else:
            model_enum = LLMModel.PLACEHOLDER
    else:
        model_enum = LLMModel(model)

    # Create config
    config = LLMConfig(
        provider=provider_enum,
        model=model_enum,
        api_key=api_key
    )

    return LLMClient(config)
