"""
Cost Calculator for Screenplay Studio

Estimates costs for different tiers and providers.
"""

from typing import Dict, Optional
from .models import ProjectTier, VideoProvider


class CostCalculator:
    """Calculate estimated costs for screenplay projects"""

    # Cost per image (DALL-E 3)
    IMAGE_COST_USD = 0.04

    # Cost per second of video by provider
    VIDEO_COST_PER_SEC = {
        VideoProvider.PIKA: 0.02,
        VideoProvider.RUNWAY: 0.05,
        VideoProvider.VEO: 0.08,
    }

    # Average shot duration in seconds
    AVG_SHOT_DURATION = 5

    # Average shots per scene
    AVG_SHOTS_PER_SCENE = 4

    @classmethod
    def estimate_project_cost(
        cls,
        tier: ProjectTier,
        estimated_scenes: int,
        video_provider: Optional[VideoProvider] = None,
        takes_per_shot: int = 1,
    ) -> Dict[str, float]:
        """
        Estimate total project cost.

        Args:
            tier: Project tier
            estimated_scenes: Number of scenes
            video_provider: AI video provider (for PRO/DIRECTOR tiers)
            takes_per_shot: Number of video takes per shot (DIRECTOR tier)

        Returns:
            Dict with cost breakdown
        """
        costs = {
            "screenplay": 0,  # Free (uses existing API quota)
            "storyboard": 0,
            "video": 0,
            "total": 0,
        }

        # FREE tier: No additional costs
        if tier == ProjectTier.FREE:
            return costs

        # STANDARD tier: Add storyboard images
        if tier in [ProjectTier.STANDARD, ProjectTier.PRO, ProjectTier.DIRECTOR]:
            # 1 image per scene
            images_per_scene = 1
            if tier == ProjectTier.DIRECTOR:
                images_per_scene = 3  # Multiple angles

            costs["storyboard"] = estimated_scenes * images_per_scene * cls.IMAGE_COST_USD

        # PRO/DIRECTOR tier: Add video generation
        if tier in [ProjectTier.PRO, ProjectTier.DIRECTOR]:
            if video_provider:
                cost_per_sec = cls.VIDEO_COST_PER_SEC.get(video_provider, 0.05)

                total_shots = estimated_scenes * cls.AVG_SHOTS_PER_SCENE
                total_seconds = total_shots * cls.AVG_SHOT_DURATION * takes_per_shot

                costs["video"] = total_seconds * cost_per_sec

        costs["total"] = sum([
            costs["screenplay"],
            costs["storyboard"],
            costs["video"],
        ])

        return costs

    @classmethod
    def estimate_scene_video_cost(
        cls,
        shots: int,
        provider: VideoProvider,
        avg_duration: int = 5,
        takes: int = 1,
    ) -> float:
        """Estimate video cost for a single scene"""
        cost_per_sec = cls.VIDEO_COST_PER_SEC.get(provider, 0.05)
        return shots * avg_duration * takes * cost_per_sec

    @classmethod
    def get_tier_features(cls, tier: ProjectTier) -> Dict[str, bool]:
        """Get features available for each tier"""
        features = {
            "screenplay": True,
            "shot_list": True,
            "storyboard_images": False,
            "video_generation": False,
            "multi_take": False,
            "video_editing": False,
            "music_suggestions": False,
        }

        if tier in [ProjectTier.STANDARD, ProjectTier.PRO, ProjectTier.DIRECTOR]:
            features["storyboard_images"] = True

        if tier in [ProjectTier.PRO, ProjectTier.DIRECTOR]:
            features["video_generation"] = True

        if tier == ProjectTier.DIRECTOR:
            features["multi_take"] = True
            features["video_editing"] = True
            features["music_suggestions"] = True

        return features
