"""
Mock Video Provider - For Testing Without Real APIs

Provides simulated video generation for development and testing.
Generates placeholder videos or just simulates the API calls.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from . import VideoProvider, VideoGenerationResult

logger = logging.getLogger(__name__)


class MockVideoProvider(VideoProvider):
    """
    Mock video provider for testing and demo purposes.
    
    Features:
    - Simulates API delays
    - Creates placeholder video files (or just metadata)
    - Configurable success/failure rates for testing
    - No API keys required
    
    Environment Variables:
    - CINEMA_MOCK_DELAY: Simulated delay in seconds (default: 2)
    - CINEMA_MOCK_SUCCESS_RATE: Success rate 0.0-1.0 (default: 1.0)
    """
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        simulated_delay: float = 2.0,
        success_rate: float = 1.0,
        create_placeholder_files: bool = False,
    ):
        """
        Initialize mock provider.
        
        Args:
            output_dir: Directory for mock output files
            simulated_delay: Seconds to wait (simulating API call)
            success_rate: Probability of success (0.0 to 1.0)
            create_placeholder_files: Create actual placeholder files
        """
        self.output_dir = output_dir or Path("outputs/videos/mock")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Read from env or use provided values
        self.simulated_delay = float(os.getenv("CINEMA_MOCK_DELAY", str(simulated_delay)))
        self.success_rate = float(os.getenv("CINEMA_MOCK_SUCCESS_RATE", str(success_rate)))
        self.create_placeholder_files = create_placeholder_files
        
        self._call_count = 0
    
    @property
    def name(self) -> str:
        return "mock"
    
    @property
    def max_duration_seconds(self) -> int:
        return 60  # Mock supports any duration
    
    @property
    def supported_aspect_ratios(self) -> List[str]:
        return ["16:9", "9:16", "1:1", "4:3", "21:9"]
    
    def is_available(self) -> bool:
        """Mock is always available."""
        return True
    
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
        Simulate video generation.
        
        Args:
            prompt: Text prompt (logged for testing)
            duration_seconds: Target duration
            aspect_ratio: Video aspect ratio
            negative_prompt: What to avoid
            output_path: Where to "save" video
            **kwargs: Additional parameters
            
        Returns:
            VideoGenerationResult with simulated results
        """
        start_time = time.time()
        self._call_count += 1
        
        logger.info(f"[MOCK] Generating video #{self._call_count}: {prompt[:50]}...")
        
        # Simulate API delay
        await asyncio.sleep(self.simulated_delay)
        
        # Simulate failure based on success rate
        import random
        if random.random() > self.success_rate:
            return VideoGenerationResult(
                success=False,
                error_message="Simulated API failure (mock mode)",
                metadata={"mock": True, "call_count": self._call_count},
            )
        
        # Generate output path
        if output_path is None:
            output_path = self.output_dir / f"mock_video_{self._call_count}_{int(time.time())}.mp4"
        
        # Create placeholder file if requested
        if self.create_placeholder_files:
            # Create a minimal valid MP4 placeholder (just metadata)
            self._create_placeholder_video(output_path, duration_seconds)
        else:
            # Just touch the file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"MOCK VIDEO: {prompt[:100]}\nDuration: {duration_seconds}s\n")
        
        generation_time = time.time() - start_time
        
        logger.info(f"[MOCK] Video generated in {generation_time:.1f}s: {output_path}")
        
        return VideoGenerationResult(
            success=True,
            video_path=output_path,
            video_url=f"mock://videos/{output_path.name}",
            duration_seconds=duration_seconds,
            generation_time_seconds=generation_time,
            cost_usd=0.0,  # Free in mock mode
            metadata={
                "mock": True,
                "call_count": self._call_count,
                "prompt": prompt[:100],
                "aspect_ratio": aspect_ratio,
            }
        )
    
    def _create_placeholder_video(self, path: Path, duration: int):
        """Create a placeholder file (not a real video)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        # Just create a text file as placeholder
        content = f"""MOCK VIDEO PLACEHOLDER
Duration: {duration} seconds
Created: {time.strftime('%Y-%m-%d %H:%M:%S')}
Note: This is a placeholder for testing. In production, this would be a real video.
"""
        path.write_text(content)
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Mock status check - always complete."""
        return {
            "status": "complete",
            "job_id": job_id,
            "mock": True,
        }
    
    def get_call_count(self) -> int:
        """Get number of generate calls made."""
        return self._call_count
    
    def reset_call_count(self):
        """Reset call counter."""
        self._call_count = 0
