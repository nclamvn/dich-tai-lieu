"""
Unified LLM Client with Auto-Fallback
AI Publisher Pro

Features:
- Auto-fallback: If one provider fails, automatically switches to another
- Billing detection: Detects credit/billing errors
- Pre-validation: Tests API before starting jobs
- Vision support: Converts between Anthropic and OpenAI vision formats
- Unified interface: Works with all pipelines
"""

import os
import logging
import asyncio
import time
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    NO_CREDIT = "no_credit"
    INVALID_KEY = "invalid_key"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ProviderHealth:
    """Health status of a provider"""
    provider: str
    status: ProviderStatus
    error: Optional[str] = None
    model: Optional[str] = None


@dataclass
class UsageStats:
    """Token and time usage statistics"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    provider: str = ""
    model: str = ""

    # Cost per 1M tokens (input/output) - approximate rates
    COST_RATES = {
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "claude-sonnet-4-20250514": (3.00, 15.00),
        "claude-3.5-sonnet": (3.00, 15.00),
        "deepseek-chat": (0.14, 0.28),
    }

    @property
    def cost_usd(self) -> float:
        """Estimate cost in USD"""
        rates = self.COST_RATES.get(self.model, (1.0, 3.0))
        input_cost = (self.input_tokens / 1_000_000) * rates[0]
        output_cost = (self.output_tokens / 1_000_000) * rates[1]
        return round(input_cost + output_cost, 6)

    def to_dict(self) -> Dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "cost_usd": self.cost_usd,
            "provider": self.provider,
            "model": self.model,
        }


@dataclass
class CumulativeStats:
    """Cumulative statistics across multiple API calls"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_elapsed_seconds: float = 0.0
    total_calls: int = 0
    calls_by_provider: Dict[str, int] = field(default_factory=dict)

    def add(self, stats: UsageStats):
        """Add stats from a single call"""
        self.total_input_tokens += stats.input_tokens
        self.total_output_tokens += stats.output_tokens
        self.total_tokens += stats.total_tokens
        self.total_elapsed_seconds += stats.elapsed_seconds
        self.total_calls += 1
        self.calls_by_provider[stats.provider] = self.calls_by_provider.get(stats.provider, 0) + 1

    def estimate_cost(self, model: str = "gpt-4o-mini") -> float:
        """Estimate total cost"""
        rates = UsageStats.COST_RATES.get(model, (1.0, 3.0))
        input_cost = (self.total_input_tokens / 1_000_000) * rates[0]
        output_cost = (self.total_output_tokens / 1_000_000) * rates[1]
        return round(input_cost + output_cost, 4)

    def to_dict(self) -> Dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_elapsed_seconds": round(self.total_elapsed_seconds, 2),
            "total_calls": self.total_calls,
            "calls_by_provider": self.calls_by_provider,
            "estimated_cost_usd": self.estimate_cost(),
        }


class AllProvidersUnavailableError(Exception):
    """Raised when all providers are unavailable"""
    def __init__(self, statuses: Dict[str, ProviderHealth]):
        self.statuses = statuses
        messages = []
        for name, health in statuses.items():
            messages.append(f"{name}: {health.status.value}" + (f" - {health.error}" if health.error else ""))
        super().__init__(
            "All AI providers are unavailable!\n" +
            "\n".join(messages) +
            "\n\nPlease check your API keys and billing status."
        )


class UnifiedLLMClient:
    """
    Unified LLM Client with automatic fallback between providers.

    Usage:
        client = UnifiedLLMClient()

        # Auto-selects best available provider
        response = await client.chat([{"role": "user", "content": "Hello"}])

        # Check provider status
        status = await client.get_provider_status()
    """

    # Billing/credit error patterns
    BILLING_ERROR_PATTERNS = [
        "credit balance is too low",
        "insufficient_quota",
        "billing",
        "exceeded your current quota",
        "account is not active",
        "payment required",
        "insufficient funds",
        "billing_hard_limit_reached",
    ]

    RATE_LIMIT_PATTERNS = [
        "rate_limit",
        "rate limit",
        "too many requests",
        "429",
    ]

    INVALID_KEY_PATTERNS = [
        "invalid api key",
        "invalid_api_key",
        "authentication",
        "unauthorized",
        "api key not found",
        "incorrect api key",
    ]

    # Provider priority order (will try in this order)
    PROVIDER_ORDER = ["openai", "anthropic", "deepseek"]

    # Provider configurations
    PROVIDER_CONFIG = {
        "openai": {
            "env_key": "OPENAI_API_KEY",
            "text_model": "gpt-4o-mini",
            "vision_model": "gpt-4o",
        },
        "anthropic": {
            "env_key": "ANTHROPIC_API_KEY",
            "text_model": "claude-sonnet-4-20250514",
            "vision_model": "claude-sonnet-4-20250514",
        },
        "deepseek": {
            "env_key": "DEEPSEEK_API_KEY",
            "text_model": "deepseek-chat",
            "vision_model": None,  # DeepSeek doesn't support vision
        },
    }

    def __init__(self, preferred_provider: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the unified client.

        Args:
            preferred_provider: Preferred provider to try first (optional)
            api_key: User-provided API key (overrides environment variable)
        """
        self.preferred_provider = preferred_provider
        self._user_api_key = api_key  # User-provided key
        self._clients: Dict[str, Any] = {}
        self._provider_status: Dict[str, ProviderHealth] = {}
        self._current_provider: Optional[str] = None
        self._validated = False
        self._failed_providers: set = set()
        # Usage tracking
        self._cumulative_stats = CumulativeStats()
        self._job_start_time: Optional[float] = None

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider. User-provided key takes priority."""
        # If user provided an API key, use it for the preferred provider
        if self._user_api_key and provider == self.preferred_provider:
            return self._user_api_key

        # Otherwise, fall back to environment variable
        config = self.PROVIDER_CONFIG.get(provider)
        if not config:
            return None
        return os.environ.get(config["env_key"])

    def _classify_error(self, error: Exception) -> ProviderStatus:
        """Classify an error into a status type."""
        error_str = str(error).lower()

        if any(p in error_str for p in self.BILLING_ERROR_PATTERNS):
            return ProviderStatus.NO_CREDIT
        if any(p in error_str for p in self.RATE_LIMIT_PATTERNS):
            return ProviderStatus.RATE_LIMITED
        if any(p in error_str for p in self.INVALID_KEY_PATTERNS):
            return ProviderStatus.INVALID_KEY
        return ProviderStatus.ERROR

    def _is_retryable_error(self, status: ProviderStatus) -> bool:
        """Check if we should try another provider for this error."""
        return status in (
            ProviderStatus.NO_CREDIT,
            ProviderStatus.INVALID_KEY,
            ProviderStatus.ERROR,
        )

    async def _get_client(self, provider: str):
        """Get or create async client for a provider."""
        if provider in self._clients:
            return self._clients[provider]

        api_key = self._get_api_key(provider)
        if not api_key:
            raise ValueError(f"API key not configured for {provider}")

        if provider == "openai":
            from openai import AsyncOpenAI
            self._clients[provider] = AsyncOpenAI(api_key=api_key)
        elif provider == "anthropic":
            from anthropic import AsyncAnthropic
            self._clients[provider] = AsyncAnthropic(api_key=api_key)
        elif provider == "deepseek":
            from openai import AsyncOpenAI
            self._clients[provider] = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        return self._clients[provider]

    async def validate_provider(self, provider: str) -> ProviderHealth:
        """
        Test if a provider is available and working.

        Returns:
            ProviderHealth with status and any error message
        """
        # Check if API key is configured
        api_key = self._get_api_key(provider)
        if not api_key:
            return ProviderHealth(
                provider=provider,
                status=ProviderStatus.NOT_CONFIGURED,
                error="API key not set"
            )

        config = self.PROVIDER_CONFIG[provider]

        try:
            client = await self._get_client(provider)

            if provider == "anthropic":
                response = await client.messages.create(
                    model=config["text_model"],
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}]
                )
                return ProviderHealth(
                    provider=provider,
                    status=ProviderStatus.AVAILABLE,
                    model=config["text_model"]
                )
            else:  # openai or deepseek
                response = await client.chat.completions.create(
                    model=config["text_model"],
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=10
                )
                return ProviderHealth(
                    provider=provider,
                    status=ProviderStatus.AVAILABLE,
                    model=config["text_model"]
                )

        except Exception as e:
            status = self._classify_error(e)
            return ProviderHealth(
                provider=provider,
                status=status,
                error=str(e)[:200]
            )

    async def validate_all_providers(self) -> Dict[str, ProviderHealth]:
        """
        Validate all configured providers.

        Returns:
            Dict mapping provider names to their health status
        """
        results = {}
        for provider in self.PROVIDER_ORDER:
            results[provider] = await self.validate_provider(provider)
            self._provider_status[provider] = results[provider]
        return results

    async def auto_select_provider(self) -> str:
        """
        Automatically select the best available provider.

        Returns:
            Name of the selected provider

        Raises:
            AllProvidersUnavailableError if no providers are available
        """
        logger.info("Auto-selecting LLM provider...")

        # If preferred provider is set and available, use it
        if self.preferred_provider:
            health = await self.validate_provider(self.preferred_provider)
            if health.status == ProviderStatus.AVAILABLE:
                logger.info(f"  Using preferred provider: {self.preferred_provider}")
                self._current_provider = self.preferred_provider
                self._validated = True
                return self.preferred_provider

        # Try providers in order
        for provider in self.PROVIDER_ORDER:
            if provider in self._failed_providers:
                continue

            logger.info(f"  Testing {provider}...")
            health = await self.validate_provider(provider)
            self._provider_status[provider] = health

            if health.status == ProviderStatus.AVAILABLE:
                logger.info(f"  ✅ {provider} is available (model: {health.model})")
                self._current_provider = provider
                self._validated = True
                return provider
            else:
                logger.warning(f"  ❌ {provider}: {health.status.value} - {health.error}")
                if self._is_retryable_error(health.status):
                    self._failed_providers.add(provider)

        # No providers available
        raise AllProvidersUnavailableError(self._provider_status)

    def _convert_vision_to_openai(self, content: List[Dict]) -> List[Dict]:
        """Convert Anthropic vision format to OpenAI format."""
        converted = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "image":
                source = item.get("source", {})
                if source.get("type") == "base64":
                    media_type = source.get("media_type", "image/png")
                    data = source.get("data", "")
                    converted.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{data}"}
                    })
                else:
                    converted.append(item)
            else:
                converted.append(item)
        return converted

    def _convert_vision_to_anthropic(self, content: List[Dict]) -> List[Dict]:
        """Convert OpenAI vision format to Anthropic format."""
        converted = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    # Parse data URL
                    parts = url.split(",", 1)
                    if len(parts) == 2:
                        media_part = parts[0]  # data:image/png;base64
                        data = parts[1]
                        media_type = media_part.split(":")[1].split(";")[0]
                        converted.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": data
                            }
                        })
                    else:
                        converted.append(item)
                else:
                    converted.append(item)
            else:
                converted.append(item)
        return converted

    def _has_vision_content(self, messages: List[Dict]) -> bool:
        """Check if messages contain vision content."""
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") in ("image", "image_url"):
                        return True
        return False

    async def chat(
        self,
        messages: List[Dict],
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        """
        Send a chat request with automatic fallback.

        Args:
            messages: List of message dicts (OpenAI or Anthropic format)
            max_tokens: Maximum tokens in response
            response_format: Optional response format (OpenAI only)

        Returns:
            Response object with .content attribute
        """
        # Auto-validate on first call
        if not self._validated:
            await self.auto_select_provider()

        has_vision = self._has_vision_content(messages)
        providers_tried = []
        last_error = None

        while True:
            providers_tried.append(self._current_provider)

            try:
                return await self._call_provider(
                    messages, max_tokens, response_format, has_vision, **kwargs
                )
            except Exception as e:
                last_error = e
                status = self._classify_error(e)

                logger.error(f"❌ {self._current_provider} failed: {status.value} - {str(e)[:200]}")

                if self._is_retryable_error(status):
                    self._failed_providers.add(self._current_provider)

                    # Find next available provider
                    next_provider = None
                    for p in self.PROVIDER_ORDER:
                        if p not in self._failed_providers:
                            # For vision, skip providers that don't support it
                            if has_vision and not self.PROVIDER_CONFIG[p].get("vision_model"):
                                continue
                            next_provider = p
                            break

                    if next_provider:
                        logger.warning(f"🔄 Switching from {self._current_provider} to {next_provider}")
                        self._current_provider = next_provider
                        continue
                    else:
                        # No more providers
                        raise AllProvidersUnavailableError(self._provider_status)
                else:
                    # Non-retryable error (rate limit, etc.)
                    raise

    async def _call_provider(
        self,
        messages: List[Dict],
        max_tokens: int,
        response_format: Optional[Dict],
        has_vision: bool,
        **kwargs
    ) -> Any:
        """Make actual API call to current provider."""
        provider = self._current_provider
        config = self.PROVIDER_CONFIG[provider]
        client = await self._get_client(provider)

        # Response wrapper with usage stats
        class Response:
            def __init__(self, content, usage: Optional[UsageStats] = None):
                self.content = content
                self.usage = usage

        # Track time
        start_time = time.time()

        if provider == "anthropic":
            # Convert to Anthropic format
            system_msg = None
            user_msgs = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    new_msg = {"role": msg["role"]}
                    content = msg.get("content")
                    if isinstance(content, list):
                        new_msg["content"] = self._convert_vision_to_anthropic(content)
                    else:
                        new_msg["content"] = content
                    user_msgs.append(new_msg)

            model = config["vision_model"] if has_vision else config["text_model"]
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_msg or "You are a helpful assistant.",
                messages=user_msgs,
            )

            # Extract usage from Anthropic response
            elapsed = time.time() - start_time
            usage = UsageStats(
                input_tokens=response.usage.input_tokens if hasattr(response, 'usage') else 0,
                output_tokens=response.usage.output_tokens if hasattr(response, 'usage') else 0,
                total_tokens=(response.usage.input_tokens + response.usage.output_tokens) if hasattr(response, 'usage') else 0,
                elapsed_seconds=elapsed,
                provider=provider,
                model=model,
            )
            self._cumulative_stats.add(usage)

            return Response(response.content[0].text, usage)

        else:  # openai or deepseek
            # Convert messages to OpenAI format
            converted_messages = []
            for msg in messages:
                new_msg = {"role": msg["role"]}
                content = msg.get("content")
                if isinstance(content, list):
                    new_msg["content"] = self._convert_vision_to_openai(content)
                else:
                    new_msg["content"] = content
                converted_messages.append(new_msg)

            # Select model
            if has_vision:
                if not config.get("vision_model"):
                    raise ValueError(f"{provider} does not support vision")
                model = config["vision_model"]
            else:
                model = config["text_model"]

            call_kwargs = {
                "model": model,
                "messages": converted_messages,
                "max_tokens": max_tokens,
            }
            if response_format and not has_vision:
                call_kwargs["response_format"] = response_format

            response = await client.chat.completions.create(**call_kwargs)

            # Extract usage from OpenAI response
            elapsed = time.time() - start_time
            usage = UsageStats(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                elapsed_seconds=elapsed,
                provider=provider,
                model=model,
            )
            self._cumulative_stats.add(usage)

            return Response(response.choices[0].message.content, usage)

    def get_current_provider(self) -> Optional[str]:
        """Get the currently active provider."""
        return self._current_provider

    def get_failed_providers(self) -> List[str]:
        """Get list of providers that have failed."""
        return list(self._failed_providers)

    def get_usage_stats(self) -> CumulativeStats:
        """Get cumulative usage statistics."""
        return self._cumulative_stats

    def get_usage_dict(self) -> Dict:
        """Get usage statistics as a dictionary."""
        return self._cumulative_stats.to_dict()

    def reset_usage_stats(self):
        """Reset usage statistics (call at job start)."""
        self._cumulative_stats = CumulativeStats()
        self._job_start_time = time.time()

    def start_job_timer(self):
        """Start job timer."""
        self._job_start_time = time.time()

    def get_job_elapsed_time(self) -> float:
        """Get elapsed time since job start."""
        if self._job_start_time is None:
            return 0.0
        return time.time() - self._job_start_time

    async def get_status_summary(self) -> Dict:
        """
        Get a summary of all provider statuses.

        Returns:
            Dict with provider statuses and recommendations
        """
        statuses = await self.validate_all_providers()

        available = [p for p, h in statuses.items() if h.status == ProviderStatus.AVAILABLE]
        no_credit = [p for p, h in statuses.items() if h.status == ProviderStatus.NO_CREDIT]

        result = {
            "current_provider": self._current_provider,
            "available_providers": available,
            "unavailable_providers": {
                p: {"status": h.status.value, "error": h.error}
                for p, h in statuses.items() if h.status != ProviderStatus.AVAILABLE
            },
        }

        if not available:
            result["recommendation"] = "⚠️ CRITICAL: No AI providers available! Check API keys and billing."
        elif len(available) == 1:
            result["recommendation"] = f"⚠️ Only {available[0]} is available. Add backup API keys."
        else:
            result["recommendation"] = f"✅ {len(available)} providers available. Auto-fallback enabled."

        if no_credit:
            result["billing_issues"] = no_credit

        return result


# Singleton instance for app-wide usage
_global_client: Optional[UnifiedLLMClient] = None


def get_unified_client() -> UnifiedLLMClient:
    """Get the global unified LLM client instance."""
    global _global_client
    if _global_client is None:
        _global_client = UnifiedLLMClient()
    return _global_client


async def validate_providers_before_job() -> Tuple[bool, str, Dict]:
    """
    Validate providers before starting a job.

    Returns:
        (success, message, status_dict)
    """
    client = get_unified_client()

    try:
        await client.auto_select_provider()
        status = await client.get_status_summary()
        return True, f"Using provider: {client.get_current_provider()}", status
    except AllProvidersUnavailableError as e:
        return False, str(e), {"error": str(e), "statuses": {
            p: {"status": h.status.value, "error": h.error}
            for p, h in e.statuses.items()
        }}
