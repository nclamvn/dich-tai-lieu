"""
Base Translation Engine Abstract Class
All translation engines must inherit from this class
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class EngineStatus(Enum):
    """Engine availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    LOADING = "loading"
    ERROR = "error"


@dataclass
class TranslationResult:
    """Result of a translation operation"""
    translated_text: str
    source_lang: str
    target_lang: str
    engine: str
    success: bool = True
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class TranslationEngine(ABC):
    """
    Abstract base class for all translation engines.

    All engines must implement:
    - name property
    - supported_languages property
    - translate() method
    - is_available() method
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name"""
        pass

    @property
    @abstractmethod
    def engine_id(self) -> str:
        """Unique engine identifier"""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """List of supported ISO 639-1 language codes"""
        pass

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        **kwargs
    ) -> TranslationResult:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate
            source_lang: Source language code (ISO 639-1)
            target_lang: Target language code (ISO 639-1)
            **kwargs: Additional engine-specific options

        Returns:
            TranslationResult with translated text or error
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if engine is ready to use.

        Returns:
            True if engine can accept translation requests
        """
        pass

    def supports_language(self, lang_code: str) -> bool:
        """Check if a language is supported"""
        return lang_code.lower() in [l.lower() for l in self.supported_languages]

    def get_status(self) -> EngineStatus:
        """Get current engine status"""
        if self.is_available():
            return EngineStatus.AVAILABLE
        return EngineStatus.UNAVAILABLE

    def get_info(self) -> dict:
        """Get engine information for API/UI"""
        return {
            "id": self.engine_id,
            "name": self.name,
            "available": self.is_available(),
            "status": self.get_status().value,
            "languages_count": len(self.supported_languages),
        }
