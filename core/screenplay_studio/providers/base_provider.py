"""
Base Provider Classes

Abstract base classes for image and video providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result from image/video generation"""
    success: bool
    file_path: Optional[str] = None
    url: Optional[str] = None
    duration_seconds: float = 0
    cost_usd: float = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseImageProvider(ABC):
    """Abstract base class for image generation providers"""

    name: str = "BaseImageProvider"
    cost_per_image: float = 0.0
    max_resolution: str = "1024x1024"
    supported_styles: List[str] = []

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.logger = logging.getLogger(f"provider.{self.name}")

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        style: str = "cinematic",
        aspect_ratio: str = "16:9",
        quality: str = "standard",
    ) -> GenerationResult:
        """Generate an image from prompt"""
        pass

    @abstractmethod
    async def check_status(self, generation_id: str) -> GenerationResult:
        """Check generation status"""
        pass

    def estimate_cost(self, count: int = 1) -> float:
        """Estimate cost for generating images"""
        return count * self.cost_per_image


class BaseVideoProvider(ABC):
    """Abstract base class for video generation providers"""

    name: str = "BaseVideoProvider"
    cost_per_second: float = 0.0
    max_duration_seconds: int = 5
    supported_resolutions: List[str] = ["1280x720"]
    supported_aspect_ratios: List[str] = ["16:9"]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.logger = logging.getLogger(f"provider.{self.name}")

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        duration_seconds: int = 5,
        aspect_ratio: str = "16:9",
        style: str = "cinematic",
        camera_motion: str = "static",
        quality: str = "standard",
    ) -> GenerationResult:
        """Generate a video from prompt"""
        pass

    @abstractmethod
    async def check_status(self, generation_id: str) -> GenerationResult:
        """Check generation status"""
        pass

    @abstractmethod
    async def download_video(
        self,
        generation_id: str,
        output_path: str,
    ) -> GenerationResult:
        """Download completed video"""
        pass

    def estimate_cost(self, duration_seconds: int) -> float:
        """Estimate cost for generating video"""
        return duration_seconds * self.cost_per_second
