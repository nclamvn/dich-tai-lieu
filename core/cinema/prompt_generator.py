"""
Cinema Prompt Generator - Screenplay to AI Video Prompts

Generates optimized prompts for various AI video generation providers
(Google Veo, Runway, Replicate, etc.)
"""

import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import (
    CinematicScene,
    ScreenplayScene,
    VideoPrompt,
    CinemaStyle,
    StyleTemplate,
)

logger = logging.getLogger(__name__)


# Default style templates as fallback
DEFAULT_STYLE_PROMPTS = {
    CinemaStyle.BLOCKBUSTER: {
        "prefix": "Cinematic Hollywood blockbuster style, epic cinematography, high production value,",
        "suffix": "8K resolution, lens flares, dramatic lighting, IMAX quality",
        "negative": "low quality, amateur, shaky camera, poor lighting",
    },
    CinemaStyle.ANIME: {
        "prefix": "High quality anime style, vibrant colors, Studio Ghibli aesthetic,",
        "suffix": "Japanese animation style, detailed backgrounds, expressive characters",
        "negative": "3D render, realistic, western cartoon, low quality",
    },
    CinemaStyle.NOIR: {
        "prefix": "Film noir style, black and white, high contrast, 1940s aesthetic,",
        "suffix": "dramatic shadows, venetian blind lighting, moody atmosphere",
        "negative": "color, bright, modern, cheerful",
    },
    CinemaStyle.DOCUMENTARY: {
        "prefix": "Documentary style, realistic, natural lighting, handheld camera feel,",
        "suffix": "authentic, journalistic, observational cinematography",
        "negative": "fantasy, surreal, artificial, staged",
    },
    CinemaStyle.FANTASY: {
        "prefix": "Epic fantasy style, magical atmosphere, Lord of the Rings aesthetic,",
        "suffix": "sweeping landscapes, mystical lighting, otherworldly beauty",
        "negative": "modern, urban, realistic, mundane",
    },
    CinemaStyle.HORROR: {
        "prefix": "Horror movie style, unsettling atmosphere, tension building,",
        "suffix": "dark shadows, eerie lighting, psychological horror",
        "negative": "bright, cheerful, comedic, safe",
    },
    CinemaStyle.SCIFI: {
        "prefix": "Science fiction style, futuristic, Blade Runner aesthetic,",
        "suffix": "neon lights, cyberpunk elements, advanced technology",
        "negative": "historical, fantasy, rural, primitive",
    },
    CinemaStyle.ROMANTIC: {
        "prefix": "Romantic drama style, warm tones, soft lighting,",
        "suffix": "golden hour lighting, intimate framing, emotional depth",
        "negative": "harsh, action, horror, dark",
    },
}


class CinemaPromptGenerator:
    """
    Generates optimized prompts for AI video generation.
    
    Supports multiple providers with provider-specific optimizations:
    - Google Veo: Detailed, descriptive prompts
    - Runway Gen-3: Shorter, more focused prompts
    - Replicate: Model-specific formatting
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize prompt generator.
        
        Args:
            templates_dir: Directory containing style template JSON files
        """
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"
        self._style_cache: Dict[str, StyleTemplate] = {}
    
    def generate_prompt(
        self,
        scene: CinematicScene,
        screenplay_scene: Optional[ScreenplayScene] = None,
        style: CinemaStyle = CinemaStyle.BLOCKBUSTER,
        style_template: Optional[StyleTemplate] = None,
        provider: str = "veo",
        duration_seconds: int = 10,
    ) -> VideoPrompt:
        """
        Generate a video prompt for a scene.
        
        Args:
            scene: CinematicScene with visual elements
            screenplay_scene: Optional screenplay scene for action lines
            style: Cinema style
            style_template: Optional detailed style template
            provider: Target AI provider ("veo", "runway", "replicate")
            duration_seconds: Target video duration
            
        Returns:
            VideoPrompt optimized for the provider
        """
        # Get style prompts
        if style_template:
            prefix = style_template.prompt_prefix
            suffix = style_template.prompt_suffix
            negative = style_template.negative_prompt
        else:
            style_prompts = DEFAULT_STYLE_PROMPTS.get(style, DEFAULT_STYLE_PROMPTS[CinemaStyle.BLOCKBUSTER])
            prefix = style_prompts["prefix"]
            suffix = style_prompts["suffix"]
            negative = style_prompts["negative"]
        
        # Generate provider-specific prompt
        if provider == "veo":
            prompt = self._generate_veo_prompt(scene, screenplay_scene, prefix, suffix)
        elif provider == "runway":
            prompt = self._generate_runway_prompt(scene, screenplay_scene, prefix, suffix)
        elif provider == "replicate":
            prompt = self._generate_replicate_prompt(scene, screenplay_scene, prefix, suffix)
        else:
            prompt = self._generate_generic_prompt(scene, screenplay_scene, prefix, suffix)
        
        return VideoPrompt(
            scene_id=scene.scene_id,
            provider=provider,
            prompt=prompt,
            negative_prompt=negative,
            duration_seconds=duration_seconds,
            aspect_ratio="16:9",
            style_preset=style.value,
        )
    
    def _generate_veo_prompt(
        self,
        scene: CinematicScene,
        screenplay_scene: Optional[ScreenplayScene],
        prefix: str,
        suffix: str,
    ) -> str:
        """Generate prompt optimized for Google Veo."""
        # Veo works well with detailed, structured prompts
        parts = [prefix]
        
        # Setting
        parts.append(f"Scene set in {scene.setting}.")
        
        # Time of day and lighting
        time_desc = {
            "day": "bright daylight",
            "night": "nighttime, artificial lights",
            "dawn": "early morning sunrise, golden hour",
            "dusk": "sunset, warm orange light",
        }
        parts.append(f"{time_desc.get(scene.time_of_day, 'natural lighting')}.")
        
        # Lighting mood
        if scene.lighting_mood:
            parts.append(f"Lighting: {scene.lighting_mood}.")
        
        # Key action (primary focus)
        if scene.key_actions:
            parts.append(f"Action: {scene.key_actions[0]}.")
        
        # Characters (if any)
        if scene.characters:
            char_desc = ", ".join([
                f"{c.get('name', 'person')} ({c.get('description', '')})"
                for c in scene.characters[:2]  # Limit to 2 characters
            ])
            parts.append(f"Characters: {char_desc}.")
        
        # Camera suggestion
        if scene.camera_suggestions:
            parts.append(f"Camera: {scene.camera_suggestions[0]}.")
        
        # Mood/atmosphere
        parts.append(f"Mood: {scene.mood} atmosphere.")
        
        parts.append(suffix)
        
        return " ".join(parts)
    
    def _generate_runway_prompt(
        self,
        scene: CinematicScene,
        screenplay_scene: Optional[ScreenplayScene],
        prefix: str,
        suffix: str,
    ) -> str:
        """Generate prompt optimized for Runway Gen-3 Alpha."""
        # Runway prefers shorter, more focused prompts
        parts = [prefix]
        
        # Core visual (setting + action)
        if scene.key_actions:
            parts.append(f"{scene.key_actions[0]} in {scene.setting}.")
        else:
            parts.append(f"Scene in {scene.setting}.")
        
        # One key visual element
        if scene.lighting_mood:
            parts.append(scene.lighting_mood + ".")
        
        # Camera (if distinctive)
        if scene.camera_suggestions:
            parts.append(scene.camera_suggestions[0] + ".")
        
        parts.append(suffix)
        
        # Runway has ~500 char limit for best results
        prompt = " ".join(parts)
        return prompt[:500]
    
    def _generate_replicate_prompt(
        self,
        scene: CinematicScene,
        screenplay_scene: Optional[ScreenplayScene],
        prefix: str,
        suffix: str,
    ) -> str:
        """Generate prompt for Replicate-hosted models."""
        # Similar to Veo but with model-specific considerations
        parts = [prefix]
        
        parts.append(f"{scene.setting}.")
        
        if scene.key_actions:
            parts.append(f"{scene.key_actions[0]}.")
        
        if scene.mood:
            parts.append(f"{scene.mood} mood.")
        
        if scene.camera_suggestions:
            parts.append(f"{scene.camera_suggestions[0]}.")
        
        parts.append(suffix)
        
        return " ".join(parts)
    
    def _generate_generic_prompt(
        self,
        scene: CinematicScene,
        screenplay_scene: Optional[ScreenplayScene],
        prefix: str,
        suffix: str,
    ) -> str:
        """Generate generic prompt for any provider."""
        parts = [
            prefix,
            scene.setting,
        ]
        
        if scene.key_actions:
            parts.append(scene.key_actions[0])
        
        parts.append(suffix)
        
        return ", ".join(parts)
    
    def generate_prompts_for_scenes(
        self,
        scenes: List[CinematicScene],
        screenplay_scenes: Optional[List[ScreenplayScene]] = None,
        style: CinemaStyle = CinemaStyle.BLOCKBUSTER,
        style_template: Optional[StyleTemplate] = None,
        provider: str = "veo",
        duration_per_scene: int = 10,
    ) -> List[VideoPrompt]:
        """
        Generate prompts for multiple scenes.
        
        Args:
            scenes: List of CinematicScene objects
            screenplay_scenes: Optional matching screenplay scenes
            style: Cinema style
            style_template: Optional style template
            provider: Target AI provider
            duration_per_scene: Duration for each video segment
            
        Returns:
            List of VideoPrompt objects
        """
        prompts = []
        screenplay_dict = {}
        
        if screenplay_scenes:
            screenplay_dict = {s.scene_id: s for s in screenplay_scenes}
        
        for scene in scenes:
            screenplay_scene = screenplay_dict.get(scene.scene_id)
            prompt = self.generate_prompt(
                scene=scene,
                screenplay_scene=screenplay_scene,
                style=style,
                style_template=style_template,
                provider=provider,
                duration_seconds=duration_per_scene,
            )
            prompts.append(prompt)
        
        logger.info(f"Generated {len(prompts)} video prompts for {provider}")
        return prompts
    
    def load_style_template(self, style: CinemaStyle) -> Optional[StyleTemplate]:
        """
        Load style template from JSON file.
        
        Args:
            style: Cinema style to load
            
        Returns:
            StyleTemplate if found, None otherwise
        """
        if style.value in self._style_cache:
            return self._style_cache[style.value]
        
        template_path = self.templates_dir / f"{style.value}.json"
        
        if template_path.exists():
            try:
                with open(template_path) as f:
                    data = json.load(f)
                template = StyleTemplate.from_dict(data)
                self._style_cache[style.value] = template
                return template
            except Exception as e:
                logger.warning(f"Failed to load template {style.value}: {e}")
        
        return None
    
    def enhance_prompt_with_continuity(
        self,
        current_prompt: VideoPrompt,
        previous_prompt: Optional[VideoPrompt] = None,
        next_scene: Optional[CinematicScene] = None,
    ) -> VideoPrompt:
        """
        Enhance prompt with continuity hints for smoother transitions.
        
        Args:
            current_prompt: The prompt to enhance
            previous_prompt: Previous scene's prompt (for continuation)
            next_scene: Next scene (for anticipation)
            
        Returns:
            Enhanced VideoPrompt with continuity elements
        """
        enhanced = current_prompt
        
        # Add transition hints
        if previous_prompt:
            enhanced.prompt = f"Continuing from previous scene. {enhanced.prompt}"
        
        return enhanced
