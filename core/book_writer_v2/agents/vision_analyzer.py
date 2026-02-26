"""
Vision Analyzer Agent (Sprint K)

Analyzes uploaded images using Vision AI + PIL for dimensions.
Produces an ImageManifest with per-image analysis.
"""

import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from .base import BaseAgent, AgentContext
from ..illustration_models import (
    ImageAnalysis,
    ImageCategory,
    ImageManifest,
    ImageSize,
    LayoutMode,
    BookGenre,
)
from ..prompts.vision_analyzer_prompts import (
    VISION_SYSTEM_PROMPT,
    VISION_ANALYSIS_PROMPT,
    GENRE_DETECTION_PROMPT,
)


class VisionAnalyzerAgent(BaseAgent[Dict, ImageManifest]):
    """
    Agent K1: Vision Analyzer

    Analyzes uploaded images via PIL (dimensions) + Vision AI (content).
    Produces an ImageManifest describing all images.
    """

    @property
    def name(self) -> str:
        return "VisionAnalyzer"

    @property
    def description(self) -> str:
        return "Analyze uploaded images for content, quality, and placement"

    async def execute(
        self, input_data: Dict, context: AgentContext
    ) -> ImageManifest:
        image_paths: List[str] = input_data.get("image_paths", [])
        if not image_paths:
            return ImageManifest()

        context.report_progress(f"Analyzing {len(image_paths)} images...", 0)

        # Parallel analysis with concurrency limit
        semaphore = asyncio.Semaphore(5)
        analyses: List[ImageAnalysis] = []

        async def analyze_with_limit(path: str, idx: int) -> Optional[ImageAnalysis]:
            async with semaphore:
                try:
                    result = await self.analyze_single(path)
                    pct = ((idx + 1) / len(image_paths)) * 80
                    context.report_progress(
                        f"Analyzed {idx + 1}/{len(image_paths)}: {result.subject}",
                        pct,
                    )
                    return result
                except Exception as e:
                    self.logger.error(f"Failed to analyze {path}: {e}")
                    return None

        tasks = [
            analyze_with_limit(p, i) for i, p in enumerate(image_paths)
        ]
        results = await asyncio.gather(*tasks)
        analyses = [r for r in results if r is not None]

        # Detect genre from collection
        genre = await self._detect_genre(analyses)

        context.report_progress("Image analysis complete", 100)

        manifest = ImageManifest(
            images=analyses,
            detected_genre=genre,
            total_images=len(analyses),
        )
        return manifest

    async def analyze_single(self, filepath: str) -> ImageAnalysis:
        """Analyze a single image: PIL dimensions + Vision AI content."""
        path = Path(filepath)
        image_id = str(uuid.uuid4())[:12]

        # Get dimensions and media type via PIL
        width, height, media_type = self._get_image_info(path)
        file_size = path.stat().st_size
        fmt = path.suffix.lstrip(".").lower() or "jpg"

        # Read image bytes for Vision API
        image_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")

        # Call Vision AI
        ai_result = await self._call_vision_ai(image_b64, media_type)

        # Map strings to enums
        category = self._parse_category(ai_result.get("category", "other"))

        # Compute quality score — blend AI opinion with resolution heuristic
        ai_quality = float(ai_result.get("quality_score", 0.5))
        resolution_quality = self._score_resolution(width, height)
        quality_score = round(ai_quality * 0.6 + resolution_quality * 0.4, 2)

        # Determine layout + size based on content + dimensions + quality
        suggested_layout, suggested_size = self._suggest_layout(
            category, width, height, quality_score,
            ai_result.get("suggested_layout", "inline"),
            ai_result.get("suggested_size", "medium"),
        )

        return ImageAnalysis(
            image_id=image_id,
            filename=path.name,
            filepath=str(path),
            subject=ai_result.get("subject", ""),
            description=ai_result.get("description", ""),
            keywords=ai_result.get("keywords", []),
            category=category,
            dominant_colors=ai_result.get("dominant_colors", []),
            era_or_context=ai_result.get("era_or_context"),
            mood=ai_result.get("mood"),
            text_in_image=ai_result.get("text_in_image"),
            width=width,
            height=height,
            file_size_bytes=file_size,
            media_type=media_type,
            format=fmt,
            quality_score=quality_score,
            suggested_layout=suggested_layout,
            suggested_size=suggested_size,
            min_display_width_px=self._min_display_width(width),
        )

    def _get_image_info(self, path: Path) -> tuple:
        """Get image dimensions and media type via PIL."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                width, height = img.size
                fmt = img.format or "JPEG"
                media_map = {
                    "JPEG": "image/jpeg",
                    "PNG": "image/png",
                    "GIF": "image/gif",
                    "WEBP": "image/webp",
                    "TIFF": "image/tiff",
                    "BMP": "image/bmp",
                }
                media_type = media_map.get(fmt.upper(), "image/jpeg")
                return width, height, media_type
        except Exception as e:
            self.logger.warning(f"PIL failed for {path}: {e}")
            return 0, 0, "image/jpeg"

    async def _call_vision_ai(self, image_b64: str, media_type: str) -> dict:
        """Call Vision AI to analyze image content."""
        try:
            response = await self.ai.generate_with_vision(
                prompt=VISION_ANALYSIS_PROMPT,
                image_base64=image_b64,
                media_type=media_type,
                system=VISION_SYSTEM_PROMPT,
            )
            return self._parse_json(response)
        except Exception as e:
            self.logger.warning(f"Vision AI failed, using defaults: {e}")
            return {
                "subject": "Unknown",
                "description": "Image could not be analyzed",
                "keywords": [],
                "category": "other",
                "quality_score": 0.5,
                "suggested_layout": "inline",
                "suggested_size": "medium",
            }

    async def _detect_genre(self, analyses: List[ImageAnalysis]) -> BookGenre:
        """Detect book genre from image collection."""
        if not analyses:
            return BookGenre.NON_FICTION

        descriptions = "\n".join(
            f"- {a.subject}: {a.description} (category: {a.category.value})"
            for a in analyses[:20]
        )

        try:
            prompt = GENRE_DETECTION_PROMPT.format(descriptions=descriptions)
            response = await self.call_ai(prompt)
            data = self._parse_json(response)
            genre_str = data.get("genre", "non_fiction")
            return self._parse_genre(genre_str)
        except Exception:
            return BookGenre.NON_FICTION

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from AI response."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse JSON: {text[:200]}")
            return {}

    @staticmethod
    def _parse_category(val: str) -> ImageCategory:
        try:
            return ImageCategory(val.lower())
        except ValueError:
            return ImageCategory.OTHER

    @staticmethod
    def _parse_layout(val: str) -> LayoutMode:
        try:
            return LayoutMode(val.lower())
        except ValueError:
            return LayoutMode.INLINE

    @staticmethod
    def _parse_size(val: str) -> ImageSize:
        try:
            return ImageSize(val.lower())
        except ValueError:
            return ImageSize.MEDIUM

    @staticmethod
    def _parse_genre(val: str) -> BookGenre:
        try:
            return BookGenre(val.lower())
        except ValueError:
            return BookGenre.NON_FICTION

    @staticmethod
    def _score_resolution(width: int, height: int) -> float:
        """Score image quality based on resolution (0.0–1.0)."""
        if width == 0 or height == 0:
            return 0.0
        longest = max(width, height)
        if longest >= 2000:
            return 1.0
        elif longest >= 1500:
            return 0.85
        elif longest >= 1000:
            return 0.7
        elif longest >= 600:
            return 0.5
        else:
            return 0.3

    @staticmethod
    def _suggest_layout(
        category: ImageCategory,
        width: int,
        height: int,
        quality_score: float,
        ai_layout: str,
        ai_size: str,
    ) -> tuple:
        """Determine layout mode and size from content + dimensions + quality.

        Returns (LayoutMode, ImageSize).
        """
        aspect = width / height if height > 0 else 1.0
        is_landscape = aspect > 1.2
        is_portrait = aspect < 0.8

        # Start with AI suggestion
        try:
            layout = LayoutMode(ai_layout.lower())
        except ValueError:
            layout = LayoutMode.INLINE
        try:
            size = ImageSize(ai_size.lower())
        except ValueError:
            size = ImageSize.MEDIUM

        # Rule overrides based on content type and quality

        # Diagrams/charts/infographics → inline, medium-large (readability)
        if category in (ImageCategory.DIAGRAM, ImageCategory.CHART, ImageCategory.INFOGRAPHIC):
            layout = LayoutMode.INLINE
            size = ImageSize.LARGE if max(width, height) >= 1000 else ImageSize.MEDIUM

        # Maps → inline large for detail
        elif category == ImageCategory.MAP:
            layout = LayoutMode.INLINE
            size = ImageSize.LARGE

        # Screenshots → inline medium
        elif category == ImageCategory.SCREENSHOT:
            layout = LayoutMode.INLINE
            size = ImageSize.MEDIUM

        # High-quality landscape photos/art → full page candidate
        elif category in (ImageCategory.PHOTO, ImageCategory.ART, ImageCategory.ILLUSTRATION):
            if quality_score >= 0.8 and is_landscape and max(width, height) >= 1500:
                layout = LayoutMode.FULL_PAGE
                size = ImageSize.FULL
            elif quality_score >= 0.7:
                layout = LayoutMode.FLOAT_TOP if is_landscape else LayoutMode.INLINE
                size = ImageSize.LARGE

        # Low quality → never full page, cap at medium
        if quality_score < 0.4:
            if layout == LayoutMode.FULL_PAGE:
                layout = LayoutMode.INLINE
            if size in (ImageSize.FULL, ImageSize.LARGE):
                size = ImageSize.MEDIUM

        # Very small images → margin placement
        if max(width, height) < 300:
            layout = LayoutMode.MARGIN
            size = ImageSize.SMALL

        return layout, size

    @staticmethod
    def _min_display_width(width: int) -> int:
        """Compute minimum display width to maintain image clarity."""
        if width == 0:
            return 200
        if width >= 1500:
            return 600
        elif width >= 1000:
            return 500
        elif width >= 600:
            return 400
        elif width >= 300:
            return 250
        else:
            return max(width, 100)
