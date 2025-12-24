"""
AI Providers Package
AI Publisher Pro - Multi-Provider Support

Supports:
- Anthropic Claude (claude-sonnet-4, claude-3.5-sonnet, etc.)
- OpenAI GPT (gpt-4o, gpt-4-turbo, etc.)
- Google Gemini (gemini-2.0-flash, gemini-1.5-pro, etc.)
- DeepSeek (deepseek-chat, deepseek-reasoner)

Usage:
    from ai_providers import create_provider_manager, AIProviderType
    
    # Create manager with default provider
    manager = create_provider_manager("claude")
    
    # Translate text
    response = await manager.translate(
        text="Hello, world!",
        source_lang="en",
        target_lang="vi"
    )
    print(response.content)
    
    # Switch to different provider
    manager.set_provider(AIProviderType.OPENAI)
    
    # Or use specific provider for one call
    response = await manager.translate(
        text="Hello!",
        source_lang="en", 
        target_lang="vi",
        provider=AIProviderType.GEMINI
    )
"""

from .base import (
    BaseAIProvider,
    AIProviderType,
    AIMessage,
    AIResponse,
    AIConfig
)

from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider

from .manager import (
    AIProviderManager,
    ProviderInfo,
    PROVIDER_REGISTRY,
    PROVIDER_INFO,
    create_provider_manager
)

from .unified_client import (
    UnifiedLLMClient,
    get_unified_client,
    validate_providers_before_job,
    AllProvidersUnavailableError,
    ProviderStatus,
    ProviderHealth,
    UsageStats,
    CumulativeStats,
)

__all__ = [
    # Base classes
    "BaseAIProvider",
    "AIProviderType",
    "AIMessage",
    "AIResponse",
    "AIConfig",

    # Providers
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "DeepSeekProvider",

    # Manager
    "AIProviderManager",
    "ProviderInfo",
    "PROVIDER_REGISTRY",
    "PROVIDER_INFO",
    "create_provider_manager",

    # Unified Client (with auto-fallback)
    "UnifiedLLMClient",
    "get_unified_client",
    "validate_providers_before_job",
    "AllProvidersUnavailableError",
    "ProviderStatus",
    "ProviderHealth",
    "UsageStats",
    "CumulativeStats",
]

__version__ = "1.0.0"
