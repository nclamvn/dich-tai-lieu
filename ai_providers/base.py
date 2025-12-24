"""
Base AI Provider - Abstract Interface
AI Publisher Pro - Multi-Provider Support
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum


class AIProviderType(Enum):
    """Supported AI Providers"""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"


@dataclass
class AIMessage:
    """Unified message format across providers"""
    role: str  # "user", "assistant", "system"
    content: str
    images: Optional[List[bytes]] = None  # For vision models


@dataclass
class AIResponse:
    """Unified response format"""
    content: str
    model: str
    provider: AIProviderType
    usage: Optional[Dict[str, int]] = None  # tokens used
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


@dataclass 
class AIConfig:
    """Provider configuration"""
    api_key: str
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    base_url: Optional[str] = None  # For custom endpoints


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers.
    All providers must implement these methods.
    """
    
    def __init__(self, config: AIConfig):
        self.config = config
        self._client = None
    
    @property
    @abstractmethod
    def provider_type(self) -> AIProviderType:
        """Return the provider type"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """Return list of supported models"""
        pass
    
    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Whether this provider supports vision/image input"""
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client connection"""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        Generate a completion from the AI model.
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Provider-specific parameters
            
        Returns:
            AIResponse with the generated content
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream a completion from the AI model.
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Provider-specific parameters
            
        Yields:
            String chunks of the response
        """
        pass
    
    @abstractmethod
    async def analyze_document(
        self,
        content: str,
        images: Optional[List[bytes]] = None,
        task: str = "analyze"
    ) -> AIResponse:
        """
        Analyze a document (text and/or images).
        
        Args:
            content: Text content to analyze
            images: Optional list of images (for vision models)
            task: Type of analysis to perform
            
        Returns:
            AIResponse with analysis results
        """
        pass
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
        terminology: Optional[Dict[str, str]] = None
    ) -> AIResponse:
        """
        Translate text between languages.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context for better translation
            terminology: Optional glossary of terms
            
        Returns:
            AIResponse with translated text
        """
        pass
    
    async def health_check(self) -> bool:
        """Check if the provider is available"""
        try:
            response = await self.complete(
                messages=[AIMessage(role="user", content="Hi")],
                max_tokens=5
            )
            return response.content is not None
        except Exception:
            return False
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.config.model}>"
