"""
Replicate Provider - Replicate-hosted Video Models

Integration with Replicate for various video generation models:
- minimax/video-01
- tencent/hunyuan-video
- stability-ai/stable-video-diffusion
"""

import asyncio
import logging
import os
import time
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List

from . import VideoProvider, VideoGenerationResult

logger = logging.getLogger(__name__)


class ReplicateProvider(VideoProvider):
    """
    Replicate video generation provider.
    
    Supports multiple video models hosted on Replicate:
    - minimax/video-01: High quality video generation
    - tencent/hunyuan-video: Chinese model, good for various styles
    - stability-ai/stable-video-diffusion: Image-to-video
    
    Environment variables:
    - REPLICATE_API_TOKEN: Your Replicate API token
    """
    
    AVAILABLE_MODELS = {
        "minimax": "minimax/video-01",
        "hunyuan": "tencent/hunyuan-video",
        "svd": "stability-ai/stable-video-diffusion",
        "zeroscope": "anotherjesse/zeroscope-v2-xl",
    }
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        default_model: str = "minimax",
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize Replicate provider.
        
        Args:
            api_token: Replicate API token
            default_model: Default model to use
            output_dir: Directory to save generated videos
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        self.default_model = default_model
        self.output_dir = output_dir or Path("outputs/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._base_url = "https://api.replicate.com/v1"
    
    @property
    def name(self) -> str:
        return "replicate"
    
    @property
    def max_duration_seconds(self) -> int:
        return 6  # Most Replicate video models support ~4-6 seconds
    
    @property
    def supported_aspect_ratios(self) -> List[str]:
        return ["16:9", "9:16", "1:1", "4:3", "3:4"]
    
    def is_available(self) -> bool:
        """Check if Replicate is properly configured."""
        return bool(self.api_token)
    
    async def generate(
        self,
        prompt: str,
        duration_seconds: int = 5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        output_path: Optional[Path] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Generate video using Replicate.
        
        Args:
            prompt: Text prompt for video generation
            duration_seconds: Target duration
            aspect_ratio: Video aspect ratio
            negative_prompt: What to avoid
            output_path: Where to save video
            model: Specific model to use (optional)
            **kwargs: Model-specific parameters
            
        Returns:
            VideoGenerationResult with generated video
        """
        start_time = time.time()
        
        if not self.is_available():
            return VideoGenerationResult(
                success=False,
                error_message="Replicate API token not configured. Set REPLICATE_API_TOKEN.",
            )
        
        model_name = model or self.default_model
        model_version = self.AVAILABLE_MODELS.get(model_name, model_name)
        
        try:
            # Use replicate library if available
            try:
                import replicate
                
                logger.info(f"Generating video with {model_version}: {prompt[:50]}...")
                
                # Run prediction
                output = await asyncio.to_thread(
                    replicate.run,
                    model_version,
                    input={
                        "prompt": prompt,
                        "negative_prompt": negative_prompt or "",
                        "aspect_ratio": aspect_ratio,
                        **kwargs,
                    }
                )
                
                # Download video
                if output_path is None:
                    output_path = self.output_dir / f"replicate_{int(time.time())}.mp4"
                
                video_url = output[0] if isinstance(output, list) else output
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(video_url)
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                
                generation_time = time.time() - start_time
                
                logger.info(f"Replicate video generated in {generation_time:.1f}s: {output_path}")
                
                return VideoGenerationResult(
                    success=True,
                    video_path=output_path,
                    video_url=video_url,
                    duration_seconds=duration_seconds,
                    generation_time_seconds=generation_time,
                    metadata={
                        "model": model_version,
                        "prompt": prompt[:100],
                    }
                )
                
            except ImportError:
                # Fallback to direct API call
                return await self._generate_via_api(
                    prompt=prompt,
                    model_version=model_version,
                    duration_seconds=duration_seconds,
                    aspect_ratio=aspect_ratio,
                    negative_prompt=negative_prompt,
                    output_path=output_path,
                    **kwargs,
                )
                
        except Exception as e:
            logger.error(f"Replicate generation failed: {e}")
            return VideoGenerationResult(
                success=False,
                error_message=str(e),
            )
    
    async def _generate_via_api(
        self,
        prompt: str,
        model_version: str,
        duration_seconds: int,
        aspect_ratio: str,
        negative_prompt: Optional[str],
        output_path: Optional[Path],
        **kwargs,
    ) -> VideoGenerationResult:
        """Generate via direct API call."""
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            # Create prediction
            response = await client.post(
                f"{self._base_url}/predictions",
                headers={
                    "Authorization": f"Token {self.api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "version": model_version,
                    "input": {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt or "",
                        "aspect_ratio": aspect_ratio,
                        **kwargs,
                    }
                }
            )
            
            if response.status_code != 201:
                return VideoGenerationResult(
                    success=False,
                    error_message=f"API error: {response.text}",
                )
            
            prediction = response.json()
            prediction_id = prediction["id"]
            
            # Poll for completion
            while True:
                status_response = await client.get(
                    f"{self._base_url}/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {self.api_token}"},
                )
                status = status_response.json()
                
                if status["status"] == "succeeded":
                    output = status["output"]
                    video_url = output[0] if isinstance(output, list) else output
                    
                    # Download video
                    if output_path is None:
                        output_path = self.output_dir / f"replicate_{int(time.time())}.mp4"
                    
                    video_response = await client.get(video_url)
                    with open(output_path, "wb") as f:
                        f.write(video_response.content)
                    
                    return VideoGenerationResult(
                        success=True,
                        video_path=output_path,
                        video_url=video_url,
                        duration_seconds=duration_seconds,
                        generation_time_seconds=time.time() - start_time,
                    )
                
                elif status["status"] == "failed":
                    return VideoGenerationResult(
                        success=False,
                        error_message=status.get("error", "Generation failed"),
                    )
                
                await asyncio.sleep(2)  # Poll every 2 seconds
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check prediction status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url}/predictions/{job_id}",
                headers={"Authorization": f"Token {self.api_token}"},
            )
            return response.json()
    
    def list_models(self) -> Dict[str, str]:
        """List available video models."""
        return self.AVAILABLE_MODELS.copy()
