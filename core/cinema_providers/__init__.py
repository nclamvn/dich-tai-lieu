"""
Video AI Providers - Abstract Interface and Implementations

Provides a unified interface for multiple video generation AI services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class VideoGenerationResult:
    """Result from a video generation request."""
    success: bool
    video_path: Optional[Path] = None
    video_url: Optional[str] = None
    duration_seconds: float = 0.0
    generation_time_seconds: float = 0.0
    cost_usd: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class VideoProvider(ABC):
    """Abstract base class for video generation providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass
    
    @property
    @abstractmethod
    def max_duration_seconds(self) -> int:
        """Maximum video duration supported."""
        pass
    
    @property
    @abstractmethod
    def supported_aspect_ratios(self) -> List[str]:
        """List of supported aspect ratios."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration_seconds: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        output_path: Optional[Path] = None,
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Generate a video from a text prompt.
        
        Args:
            prompt: Text prompt describing the video
            duration_seconds: Desired video length
            aspect_ratio: Video aspect ratio
            negative_prompt: What to avoid in generation
            output_path: Where to save the video
            **kwargs: Provider-specific parameters
            
        Returns:
            VideoGenerationResult with video path or error
        """
        pass
    
    @abstractmethod
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of an async generation job."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass
