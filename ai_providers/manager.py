"""
AI Provider Manager
AI Publisher Pro - Multi-Provider Support

Manages multiple AI providers and allows easy switching.
"""

import os
from typing import Optional, Dict, List, Type
from dataclasses import dataclass

from .base import BaseAIProvider, AIProviderType, AIConfig, AIResponse, AIMessage
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider


@dataclass
class ProviderInfo:
    """Information about an AI provider"""
    type: AIProviderType
    name: str
    description: str
    supports_vision: bool
    supports_streaming: bool
    models: Dict[str, str]
    default_model: str
    env_key: str  # Environment variable name for API key


# Registry of all available providers
PROVIDER_REGISTRY: Dict[AIProviderType, Type[BaseAIProvider]] = {
    AIProviderType.CLAUDE: ClaudeProvider,
    AIProviderType.OPENAI: OpenAIProvider,
    AIProviderType.GEMINI: GeminiProvider,
    AIProviderType.DEEPSEEK: DeepSeekProvider,
}

# Provider information
PROVIDER_INFO: Dict[AIProviderType, ProviderInfo] = {
    AIProviderType.CLAUDE: ProviderInfo(
        type=AIProviderType.CLAUDE,
        name="Anthropic Claude",
        description="Claude AI - Best for nuanced, thoughtful translation",
        supports_vision=True,
        supports_streaming=True,
        models=ClaudeProvider.MODELS,
        default_model=ClaudeProvider.DEFAULT_MODEL,
        env_key="ANTHROPIC_API_KEY"
    ),
    AIProviderType.OPENAI: ProviderInfo(
        type=AIProviderType.OPENAI,
        name="OpenAI GPT",
        description="GPT-4o - Versatile, multimodal AI",
        supports_vision=True,
        supports_streaming=True,
        models=OpenAIProvider.MODELS,
        default_model=OpenAIProvider.DEFAULT_MODEL,
        env_key="OPENAI_API_KEY"
    ),
    AIProviderType.GEMINI: ProviderInfo(
        type=AIProviderType.GEMINI,
        name="Google Gemini",
        description="Gemini - Fast, multimodal AI from Google",
        supports_vision=True,
        supports_streaming=True,
        models=GeminiProvider.MODELS,
        default_model=GeminiProvider.DEFAULT_MODEL,
        env_key="GOOGLE_API_KEY"
    ),
    AIProviderType.DEEPSEEK: ProviderInfo(
        type=AIProviderType.DEEPSEEK,
        name="DeepSeek",
        description="DeepSeek V3 - Cost-effective, strong multilingual",
        supports_vision=False,
        supports_streaming=True,
        models=DeepSeekProvider.MODELS,
        default_model=DeepSeekProvider.DEFAULT_MODEL,
        env_key="DEEPSEEK_API_KEY"
    ),
}


class AIProviderManager:
    """
    Manages multiple AI providers and handles switching between them.
    
    Usage:
        manager = AIProviderManager()
        
        # Use default provider (Claude)
        response = await manager.translate(text, "en", "vi")
        
        # Switch provider
        manager.set_provider(AIProviderType.OPENAI)
        response = await manager.translate(text, "en", "vi")
        
        # Use specific provider for one call
        response = await manager.translate(
            text, "en", "vi", 
            provider=AIProviderType.GEMINI
        )
    """
    
    def __init__(
        self,
        default_provider: AIProviderType = AIProviderType.CLAUDE,
        api_keys: Optional[Dict[AIProviderType, str]] = None
    ):
        """
        Initialize the provider manager.
        
        Args:
            default_provider: Default AI provider to use
            api_keys: Optional dict of API keys for each provider.
                     If not provided, will use environment variables.
        """
        self._default_provider = default_provider
        self._current_provider = default_provider
        self._api_keys = api_keys or {}
        self._providers: Dict[AIProviderType, BaseAIProvider] = {}
        self._initialized: Dict[AIProviderType, bool] = {}
    
    def _get_api_key(self, provider_type: AIProviderType) -> str:
        """Get API key for a provider from dict or environment"""
        if provider_type in self._api_keys:
            return self._api_keys[provider_type]
        
        info = PROVIDER_INFO[provider_type]
        key = os.environ.get(info.env_key)
        
        if not key:
            raise ValueError(
                f"API key not found for {info.name}. "
                f"Set {info.env_key} environment variable or pass api_keys dict."
            )
        
        return key
    
    def _create_provider(
        self,
        provider_type: AIProviderType,
        model: Optional[str] = None
    ) -> BaseAIProvider:
        """Create a provider instance"""
        info = PROVIDER_INFO[provider_type]
        provider_class = PROVIDER_REGISTRY[provider_type]
        
        config = AIConfig(
            api_key=self._get_api_key(provider_type),
            model=model or info.default_model
        )
        
        return provider_class(config)
    
    async def get_provider(
        self,
        provider_type: Optional[AIProviderType] = None,
        model: Optional[str] = None
    ) -> BaseAIProvider:
        """
        Get a provider instance, initializing if needed.
        
        Args:
            provider_type: Provider to get (uses current if None)
            model: Specific model to use
        """
        ptype = provider_type or self._current_provider
        
        # Create new if model differs or not cached
        cache_key = f"{ptype.value}:{model or 'default'}"
        
        if cache_key not in self._providers:
            self._providers[cache_key] = self._create_provider(ptype, model)
        
        provider = self._providers[cache_key]
        
        if cache_key not in self._initialized:
            await provider.initialize()
            self._initialized[cache_key] = True
        
        return provider
    
    def set_provider(self, provider_type: AIProviderType) -> None:
        """Set the current default provider"""
        if provider_type not in PROVIDER_REGISTRY:
            raise ValueError(f"Unknown provider: {provider_type}")
        self._current_provider = provider_type
    
    @property
    def current_provider(self) -> AIProviderType:
        """Get current provider type"""
        return self._current_provider
    
    @staticmethod
    def list_providers() -> List[ProviderInfo]:
        """List all available providers"""
        return list(PROVIDER_INFO.values())
    
    @staticmethod
    def get_provider_info(provider_type: AIProviderType) -> ProviderInfo:
        """Get information about a specific provider"""
        return PROVIDER_INFO[provider_type]
    
    def get_available_providers(self) -> List[ProviderInfo]:
        """Get list of providers that have API keys configured"""
        available = []
        for ptype, info in PROVIDER_INFO.items():
            try:
                self._get_api_key(ptype)
                available.append(info)
            except ValueError:
                pass
        return available
    
    # ========== Convenience methods ==========
    
    async def complete(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        provider: Optional[AIProviderType] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate completion using specified or current provider"""
        p = await self.get_provider(provider, model)
        return await p.complete(messages, system_prompt, **kwargs)
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
        terminology: Optional[Dict[str, str]] = None,
        provider: Optional[AIProviderType] = None,
        model: Optional[str] = None
    ) -> AIResponse:
        """Translate text using specified or current provider"""
        p = await self.get_provider(provider, model)
        return await p.translate(text, source_lang, target_lang, context, terminology)
    
    async def analyze_document(
        self,
        content: str,
        images: Optional[List[bytes]] = None,
        task: str = "analyze",
        provider: Optional[AIProviderType] = None,
        model: Optional[str] = None
    ) -> AIResponse:
        """Analyze document using specified or current provider"""
        p = await self.get_provider(provider, model)
        
        # If images provided but provider doesn't support vision, warn
        if images and not p.supports_vision:
            print(f"Warning: {p.provider_type.value} doesn't support vision. Images ignored.")
        
        return await p.analyze_document(content, images, task)
    
    async def health_check(
        self,
        provider: Optional[AIProviderType] = None
    ) -> Dict[str, bool]:
        """
        Check health of providers.
        
        Args:
            provider: Specific provider to check, or all available if None
        """
        results = {}
        
        if provider:
            providers_to_check = [provider]
        else:
            providers_to_check = [p.type for p in self.get_available_providers()]
        
        for ptype in providers_to_check:
            try:
                p = await self.get_provider(ptype)
                results[ptype.value] = await p.health_check()
            except Exception as e:
                results[ptype.value] = False
                print(f"Health check failed for {ptype.value}: {e}")
        
        return results


# ========== Factory function ==========

def create_provider_manager(
    default_provider: str = "claude",
    api_keys: Optional[Dict[str, str]] = None
) -> AIProviderManager:
    """
    Factory function to create a provider manager.
    
    Args:
        default_provider: Name of default provider ("claude", "openai", "gemini", "deepseek")
        api_keys: Optional dict with provider names as keys and API keys as values
        
    Returns:
        Configured AIProviderManager instance
    """
    # Convert string to enum
    provider_map = {
        "claude": AIProviderType.CLAUDE,
        "openai": AIProviderType.OPENAI,
        "gpt": AIProviderType.OPENAI,
        "chatgpt": AIProviderType.OPENAI,
        "gemini": AIProviderType.GEMINI,
        "google": AIProviderType.GEMINI,
        "deepseek": AIProviderType.DEEPSEEK,
    }
    
    default_type = provider_map.get(default_provider.lower())
    if not default_type:
        raise ValueError(f"Unknown provider: {default_provider}")
    
    # Convert api_keys dict if provided
    typed_keys = None
    if api_keys:
        typed_keys = {}
        for name, key in api_keys.items():
            ptype = provider_map.get(name.lower())
            if ptype:
                typed_keys[ptype] = key
    
    return AIProviderManager(default_provider=default_type, api_keys=typed_keys)
