"""
Video Renderer - Multi-Provider Video Generation Orchestration

Orchestrates video generation across multiple AI providers with
fallback, retry logic, and progress tracking.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from .models import (
    CinematicScene,
    VideoPrompt,
    RenderedVideo,
    CinemaStyle,
)

from core.cinema_providers import VideoProvider, VideoGenerationResult
from core.cinema_providers.google_veo import GoogleVeoProvider
from core.cinema_providers.replicate_provider import ReplicateProvider
from core.cinema_providers.mock_provider import MockVideoProvider

logger = logging.getLogger(__name__)


class VideoRenderer:
    """
    Multi-provider video rendering orchestrator.
    
    Features:
    - Multiple provider support (Veo, Replicate, Mock)
    - Automatic fallback on failure
    - Retry logic with exponential backoff
    - Progress tracking
    - Concurrent rendering with rate limiting
    - Mock mode for testing without real APIs
    
    Environment Variables:
    - CINEMA_DEMO_MODE: Set to "true" for mock/demo mode
    """
    
    def __init__(
        self,
        primary_provider: str = "replicate",
        fallback_providers: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        max_concurrent: int = 3,
        max_retries: int = 3,
        demo_mode: Optional[bool] = None,
    ):
        """
        Initialize VideoRenderer.
        
        Args:
            primary_provider: Main provider to use ("veo", "replicate", "mock")
            fallback_providers: Backup providers if primary fails
            output_dir: Directory for rendered videos
            max_concurrent: Maximum concurrent render jobs
            max_retries: Maximum retries per scene
            demo_mode: Force mock provider (overrides primary_provider)
        """
        # Check for demo mode from env or argument
        self.demo_mode = demo_mode
        if self.demo_mode is None:
            self.demo_mode = os.getenv("CINEMA_DEMO_MODE", "false").lower() == "true"
        
        # In demo mode, always use mock provider
        if self.demo_mode:
            self.primary_provider = "mock"
            self.fallback_providers = []
            logger.info("VideoRenderer running in DEMO MODE (mock provider)")
        else:
            self.primary_provider = primary_provider
            self.fallback_providers = fallback_providers or []
        
        self.output_dir = output_dir or Path("outputs/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        
        # Initialize semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Provider instances (lazy loaded)
        self._providers: Dict[str, VideoProvider] = {}
    
    def _get_provider(self, name: str) -> Optional[VideoProvider]:
        """Get or create a provider instance."""
        if name not in self._providers:
            if name == "veo":
                provider = GoogleVeoProvider(output_dir=self.output_dir)
            elif name == "replicate":
                provider = ReplicateProvider(output_dir=self.output_dir)
            elif name == "mock":
                provider = MockVideoProvider(output_dir=self.output_dir)
            else:
                logger.warning(f"Unknown provider: {name}")
                return None
            
            if provider.is_available():
                self._providers[name] = provider
            else:
                logger.warning(f"Provider {name} is not available")
                return None
        
        return self._providers.get(name)
    
    async def render_scene(
        self,
        prompt: VideoPrompt,
        scene: Optional[CinematicScene] = None,
    ) -> RenderedVideo:
        """
        Render a single scene to video.
        
        Args:
            prompt: VideoPrompt with generation details
            scene: Optional CinematicScene for metadata
            
        Returns:
            RenderedVideo with result or error
        """
        start_time = time.time()
        
        # Try primary provider first
        providers_to_try = [self.primary_provider] + self.fallback_providers
        
        for provider_name in providers_to_try:
            provider = self._get_provider(provider_name)
            if not provider:
                continue
            
            for attempt in range(self.max_retries):
                try:
                    async with self._semaphore:
                        result = await provider.generate(
                            prompt=prompt.prompt,
                            duration_seconds=prompt.duration_seconds,
                            aspect_ratio=prompt.aspect_ratio,
                            negative_prompt=prompt.negative_prompt,
                            **prompt.provider_params,
                        )
                    
                    if result.success:
                        generation_time = time.time() - start_time
                        
                        return RenderedVideo(
                            scene_id=prompt.scene_id,
                            video_path=result.video_path,
                            duration_seconds=result.duration_seconds,
                            provider=provider_name,
                            prompt_used=prompt.prompt,
                            generation_time_seconds=generation_time,
                            success=True,
                            metadata=result.metadata,
                        )
                    else:
                        logger.warning(
                            f"Render failed with {provider_name} (attempt {attempt + 1}): "
                            f"{result.error_message}"
                        )
                        
                except Exception as e:
                    logger.error(f"Render exception with {provider_name}: {e}")
                    
                # Exponential backoff before retry
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
        
        # All providers failed
        return RenderedVideo(
            scene_id=prompt.scene_id,
            video_path=Path(""),
            success=False,
            error_message="All providers failed to render video",
        )
    
    async def render_scenes(
        self,
        prompts: List[VideoPrompt],
        scenes: Optional[List[CinematicScene]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[RenderedVideo]:
        """
        Render multiple scenes with concurrency control.
        
        Args:
            prompts: List of VideoPrompt objects
            scenes: Optional matching CinematicScene objects
            progress_callback: Called with (completed, total) after each render
            
        Returns:
            List of RenderedVideo objects
        """
        total = len(prompts)
        completed = [0]  # Use list for mutable reference in closure
        
        scenes_dict = {}
        if scenes:
            scenes_dict = {s.scene_id: s for s in scenes}
        
        async def render_with_progress(prompt: VideoPrompt) -> RenderedVideo:
            scene = scenes_dict.get(prompt.scene_id)
            result = await self.render_scene(prompt, scene)
            
            completed[0] += 1
            if progress_callback:
                progress_callback(completed[0], total)
            
            return result
        
        # Render all scenes (semaphore controls concurrency)
        tasks = [render_with_progress(p) for p in prompts]
        results = await asyncio.gather(*tasks)
        
        # Sort by scene order
        scene_order = {p.scene_id: i for i, p in enumerate(prompts)}
        results = sorted(results, key=lambda r: scene_order.get(r.scene_id, 0))
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Rendered {successful}/{total} scenes successfully")
        
        return results
    
    def get_available_providers(self) -> List[str]:
        """List available video providers."""
        available = []
        for name in ["veo", "replicate"]:
            provider = self._get_provider(name)
            if provider and provider.is_available():
                available.append(name)
        return available
    
    async def estimate_cost(
        self,
        prompts: List[VideoPrompt],
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate cost for rendering all prompts.
        
        Returns dict with:
        - total_duration: Total video seconds
        - estimated_cost: Estimated USD cost
        - provider: Provider used for estimate
        """
        provider = provider or self.primary_provider
        
        total_duration = sum(p.duration_seconds for p in prompts)
        
        # Rough cost estimates per second
        cost_per_second = {
            "veo": 0.05,  # $0.05/second estimate
            "replicate": 0.02,  # ~$0.02/second estimate
        }
        
        rate = cost_per_second.get(provider, 0.03)
        estimated_cost = total_duration * rate
        
        return {
            "total_scenes": len(prompts),
            "total_duration_seconds": total_duration,
            "estimated_cost_usd": round(estimated_cost, 2),
            "provider": provider,
        }
