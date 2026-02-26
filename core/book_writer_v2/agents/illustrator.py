"""
Illustrator Agent (Sprint K)

Matches analyzed images to book content, decides layouts,
generates captions, and produces the IllustrationPlan.
"""

import asyncio
import json
import re
import uuid
from typing import Dict, List, Optional, Tuple

from .base import BaseAgent, AgentContext
from ..illustration_models import (
    BookGenre,
    ChapterIndex,
    GalleryGroup,
    IllustrationPlan,
    ImageAnalysis,
    ImageManifest,
    ImagePlacement,
    ImageSize,
    LayoutConfig,
    LayoutMode,
    MatchCandidate,
)
from ..models import BookProject
from ..prompts.illustrator_prompts import MATCH_PROMPT, CAPTION_PROMPT


class IllustratorAgent(BaseAgent[Dict, IllustrationPlan]):
    """
    Agent K2: Illustrator

    Takes analyzed images + book content and produces an
    IllustrationPlan: which images go where, with what layout.
    """

    @property
    def name(self) -> str:
        return "Illustrator"

    @property
    def description(self) -> str:
        return "Match images to chapters, decide layout, generate captions"

    async def execute(
        self, input_data: Dict, context: AgentContext
    ) -> IllustrationPlan:
        project: BookProject = input_data["project"]
        manifest: ImageManifest = input_data["manifest"]

        if not project.blueprint or not manifest.images:
            return IllustrationPlan()

        blueprint = project.blueprint
        layout_config = LayoutConfig.for_genre(manifest.detected_genre)

        context.report_progress("Building chapter index...", 5)
        chapter_indices = self._build_chapter_index(blueprint)

        context.report_progress("Matching images to content...", 15)
        candidates = await self._match_all_images(
            manifest.images, chapter_indices, manifest.detected_genre
        )

        context.report_progress("Deciding layouts...", 50)
        placements = self._assign_placements(
            candidates, manifest, layout_config
        )

        context.report_progress("Generating captions...", 65)
        placements = await self._generate_all_captions(
            placements, manifest, blueprint, manifest.detected_genre
        )

        context.report_progress("Balancing distribution...", 80)
        placements = self._balance_distribution(placements, layout_config)

        context.report_progress("Identifying galleries...", 90)
        galleries = self._identify_galleries(
            placements, manifest, layout_config
        )

        # Find unmatched images
        placed_ids = {p.image_id for p in placements}
        unmatched = [
            img.image_id for img in manifest.images
            if img.image_id not in placed_ids
        ]

        context.report_progress("Illustration plan complete", 100)

        return IllustrationPlan(
            placements=placements,
            galleries=galleries,
            unmatched_image_ids=unmatched,
        )

    def _build_chapter_index(self, blueprint) -> List[ChapterIndex]:
        """Extract topics, entities, keywords, time periods per chapter."""
        indices = []
        chapter_num = 0
        for part in blueprint.parts:
            for chapter in part.chapters:
                chapter_num += 1
                keywords = []
                topics = [chapter.title]
                entities = []
                time_periods = []
                paragraph_count = 0
                section_data = []

                for sec_idx, section in enumerate(chapter.sections):
                    topics.append(section.title)
                    sec_keywords = []

                    if section.content:
                        words = section.content.lower().split()
                        paragraph_count += max(1, section.content.count("\n\n") + 1)

                        # Frequency-based keyword extraction
                        word_freq: Dict[str, int] = {}
                        for w in words:
                            w = w.strip(".,;:!?\"'()[]{}").lower()
                            if len(w) > 4:
                                word_freq[w] = word_freq.get(w, 0) + 1
                        sec_keywords = [w for w, c in word_freq.items() if c >= 3]
                        keywords.extend(sec_keywords)

                        # Extract capitalized multi-word entities (proper nouns)
                        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', section.content)
                        entities.extend(caps[:10])

                        # Extract year-like time periods
                        years = re.findall(r'\b(?:1[0-9]{3}|20[0-2][0-9])\b', section.content)
                        time_periods.extend(years)

                    section_data.append({
                        "index": sec_idx,
                        "title": section.title,
                        "keywords": sec_keywords[:10],
                    })

                # Build summary from chapter intro/summary if available
                summary = ""
                if hasattr(chapter, "summary") and chapter.summary:
                    summary = chapter.summary
                elif hasattr(chapter, "introduction") and chapter.introduction:
                    summary = chapter.introduction[:300]

                indices.append(ChapterIndex(
                    chapter_id=chapter.id,
                    chapter_number=chapter_num,
                    title=chapter.title,
                    summary=summary,
                    topics=topics,
                    entities=list(set(entities))[:20],
                    keywords=list(set(keywords))[:30],
                    time_periods=list(set(time_periods))[:10],
                    paragraph_count=paragraph_count,
                    sections=section_data,
                ))
        return indices

    async def _match_all_images(
        self,
        images: List[ImageAnalysis],
        chapters: List[ChapterIndex],
        genre: BookGenre,
    ) -> List[MatchCandidate]:
        """Match each image to best-fitting chapters."""
        all_candidates = []
        semaphore = asyncio.Semaphore(5)

        async def match_one(img: ImageAnalysis, ch: ChapterIndex):
            async with semaphore:
                return await self._match_image_to_content(img, ch)

        tasks = []
        for img in images:
            for ch in chapters:
                tasks.append((img.image_id, ch.chapter_number - 1, match_one(img, ch)))

        for image_id, ch_idx, coro in tasks:
            try:
                candidate = await coro
                if candidate:
                    all_candidates.append(candidate)
            except Exception as e:
                self.logger.warning(f"Match failed for {image_id}: {e}")

        return all_candidates

    async def _match_image_to_content(
        self, image: ImageAnalysis, chapter: ChapterIndex
    ) -> Optional[MatchCandidate]:
        """Score how well an image matches a chapter."""
        # Keyword overlap
        img_keywords = set(k.lower() for k in image.keywords)
        ch_keywords = set(k.lower() for k in chapter.keywords + chapter.topics)

        # Also check entity overlap and time period alignment
        if image.era_or_context and chapter.time_periods:
            era_words = set(image.era_or_context.lower().split())
            period_words = set(w.lower() for w in chapter.time_periods)
            if era_words & period_words:
                img_keywords.add("_era_match_")
                ch_keywords.add("_era_match_")

        if not img_keywords or not ch_keywords:
            overlap = 0.0
        else:
            common = img_keywords & ch_keywords
            overlap = len(common) / max(len(img_keywords), 1)

        # AI judgment for non-trivial overlap
        ai_relevance = 0.0
        if overlap > 0.05 or not chapter.keywords:
            try:
                prompt = MATCH_PROMPT.format(
                    image_subject=image.subject,
                    image_description=image.description,
                    image_keywords=", ".join(image.keywords[:10]),
                    image_category=image.category.value,
                    chapter_title=chapter.title,
                    chapter_topics=", ".join(chapter.topics[:5]),
                    chapter_keywords=", ".join(chapter.keywords[:10]),
                )
                response = await self.call_ai(prompt, max_tokens=256)
                data = self._parse_json(response)
                ai_relevance = float(data.get("relevance", 0.0))
            except Exception:
                ai_relevance = overlap * 0.5

        candidate = MatchCandidate(
            image_id=image.image_id,
            chapter_index=chapter.chapter_number - 1,
            keyword_overlap=overlap,
            ai_relevance=ai_relevance,
        )
        candidate.compute_combined()
        return candidate

    def _assign_placements(
        self,
        candidates: List[MatchCandidate],
        manifest: ImageManifest,
        config: LayoutConfig,
    ) -> List[ImagePlacement]:
        """Assign images to chapters based on best matches."""
        # Sort by score descending
        candidates.sort(key=lambda c: c.combined_score, reverse=True)

        placed_image_ids = set()
        chapter_counts: Dict[int, int] = {}
        placements = []
        prev_layout = None

        for candidate in candidates:
            if candidate.image_id in placed_image_ids:
                continue
            if candidate.combined_score < config.min_relevance_score:
                continue

            ch_count = chapter_counts.get(candidate.chapter_index, 0)
            if ch_count >= config.max_images_per_chapter:
                continue

            image = manifest.get_image(candidate.image_id)
            if not image:
                continue

            layout = self._decide_layout(
                image, config, ch_count, manifest.detected_genre, prev_layout
            )
            size = self._decide_size(image, layout)

            # Generate alt text from image analysis
            alt_text = self._generate_alt_text(image)

            placements.append(ImagePlacement(
                image_id=candidate.image_id,
                chapter_index=candidate.chapter_index,
                section_index=min(ch_count, 3),
                layout_mode=layout,
                size=size,
                relevance_score=candidate.combined_score,
                alt_text=alt_text,
            ))

            placed_image_ids.add(candidate.image_id)
            chapter_counts[candidate.chapter_index] = ch_count + 1
            prev_layout = layout

        return placements

    def _decide_layout(
        self,
        image: ImageAnalysis,
        config: LayoutConfig,
        position: int,
        genre: BookGenre = BookGenre.NON_FICTION,
        prev_layout: Optional[LayoutMode] = None,
    ) -> LayoutMode:
        """Genre-aware rules engine for layout mode."""
        from ..illustration_models import ImageCategory

        # HARD RULE: low quality never gets FULL_PAGE
        if image.quality_score < 0.5:
            if position == 0:
                return LayoutMode.FLOAT_TOP
            if image.suggested_size == ImageSize.SMALL:
                return LayoutMode.MARGIN
            return LayoutMode.INLINE

        # HARD RULE: avoid 2 FULL_PAGE in a row
        avoid_full_page = prev_layout == LayoutMode.FULL_PAGE

        # Genre-specific layout preferences
        if genre in (BookGenre.PHOTOGRAPHY, BookGenre.TRAVEL):
            # Photography/travel books: prefer large images
            if (
                image.is_high_quality
                and image.is_landscape
                and position == 0
                and not avoid_full_page
            ):
                return LayoutMode.FULL_PAGE
            if position == 0:
                return LayoutMode.FLOAT_TOP
            return LayoutMode.INLINE

        if genre == BookGenre.CHILDREN:
            # Children's books: full page for artwork, inline for others
            if (
                image.category in (ImageCategory.ART, ImageCategory.ILLUSTRATION)
                and image.is_high_quality
                and not avoid_full_page
            ):
                return LayoutMode.FULL_PAGE
            return LayoutMode.INLINE

        if genre == BookGenre.TECHNICAL:
            # Technical: strict inline, diagrams/charts always inline
            if image.category in (
                ImageCategory.DIAGRAM, ImageCategory.CHART,
                ImageCategory.INFOGRAPHIC, ImageCategory.SCREENSHOT
            ):
                return LayoutMode.INLINE
            if position == 0:
                return LayoutMode.FLOAT_TOP
            return LayoutMode.INLINE

        if genre == BookGenre.COOKBOOK:
            # Cookbook: food photos get full page, diagrams inline
            if (
                image.is_high_quality
                and image.category == ImageCategory.PHOTO
                and position == 0
                and not avoid_full_page
            ):
                return LayoutMode.FULL_PAGE
            return LayoutMode.INLINE

        # Default / NON_FICTION / FICTION / MEMOIR / ACADEMIC
        if (
            config.prefer_full_page_for_high_quality
            and image.is_high_quality
            and image.is_landscape
            and position == 0
            and not avoid_full_page
        ):
            return LayoutMode.FULL_PAGE

        if position == 0:
            return LayoutMode.FLOAT_TOP

        if image.suggested_size == ImageSize.SMALL:
            return LayoutMode.MARGIN

        return image.suggested_layout

    def _decide_size(self, image: ImageAnalysis, layout: LayoutMode) -> ImageSize:
        """Decide image size based on layout."""
        if layout == LayoutMode.FULL_PAGE:
            return ImageSize.FULL
        if layout == LayoutMode.MARGIN:
            return ImageSize.SMALL
        if layout == LayoutMode.FLOAT_TOP:
            return ImageSize.LARGE
        return image.suggested_size

    @staticmethod
    def _generate_alt_text(image: ImageAnalysis) -> str:
        """Generate accessibility alt text from image analysis."""
        parts = []
        if image.category and image.category.value != "other":
            parts.append(image.category.value.title())
        subject = image.subject or (image.description[:120] if image.description else "")
        if subject:
            if image.era_or_context:
                subject = f"{subject} ({image.era_or_context})"
            parts.append(subject)
        elif image.era_or_context:
            parts.append(image.era_or_context)
        return ": ".join(parts) if parts else "Image"

    async def _generate_all_captions(
        self,
        placements: List[ImagePlacement],
        manifest: ImageManifest,
        blueprint,
        genre: BookGenre,
    ) -> List[ImagePlacement]:
        """Generate contextual captions for all placements."""
        chapters = blueprint.all_chapters
        semaphore = asyncio.Semaphore(5)

        # Sort by chapter then section for figure numbering
        placements_sorted = sorted(
            placements, key=lambda p: (p.chapter_index, p.section_index)
        )
        figure_counter: Dict[int, int] = {}

        async def caption_one(placement: ImagePlacement, fig_num: int):
            async with semaphore:
                image = manifest.get_image(placement.image_id)
                if not image:
                    return

                ch_idx = placement.chapter_index
                chapter_title = chapters[ch_idx].title if ch_idx < len(chapters) else ""
                sec_idx = placement.section_index
                sections = chapters[ch_idx].sections if ch_idx < len(chapters) else []
                section_title = sections[sec_idx].title if sec_idx < len(sections) else ""

                caption = await self._generate_caption(
                    image, chapter_title, section_title, genre
                )

                # Add figure number for technical/academic genres
                if genre in (BookGenre.TECHNICAL, BookGenre.ACADEMIC):
                    placement.caption = f"Figure {ch_idx + 1}.{fig_num}: {caption}"
                else:
                    placement.caption = caption

        tasks = []
        for p in placements_sorted:
            ch = p.chapter_index
            figure_counter[ch] = figure_counter.get(ch, 0) + 1
            tasks.append(caption_one(p, figure_counter[ch]))

        await asyncio.gather(*tasks)
        return placements

    async def _generate_caption(
        self,
        image: ImageAnalysis,
        chapter_title: str,
        section_title: str,
        genre: BookGenre,
    ) -> str:
        """Generate a single contextual caption."""
        try:
            prompt = CAPTION_PROMPT.format(
                genre=genre.value,
                image_description=image.description,
                chapter_title=chapter_title,
                section_title=section_title,
            )
            response = await self.call_ai(prompt, max_tokens=128)
            caption = response.strip().strip('"').strip("'")
            return caption
        except Exception:
            return image.subject or image.description[:80]

    def _balance_distribution(
        self,
        placements: List[ImagePlacement],
        config: LayoutConfig,
    ) -> List[ImagePlacement]:
        """Redistribute images if some chapters are overloaded."""
        chapter_counts: Dict[int, int] = {}
        for p in placements:
            chapter_counts[p.chapter_index] = chapter_counts.get(p.chapter_index, 0) + 1

        if not chapter_counts:
            return placements

        max_count = max(chapter_counts.values())
        if max_count <= config.max_images_per_chapter:
            return placements

        # Trim excess from overloaded chapters (keep highest relevance)
        result = []
        chapter_kept: Dict[int, int] = {}
        placements_sorted = sorted(placements, key=lambda p: p.relevance_score, reverse=True)

        for p in placements_sorted:
            kept = chapter_kept.get(p.chapter_index, 0)
            if kept < config.max_images_per_chapter:
                result.append(p)
                chapter_kept[p.chapter_index] = kept + 1

        return result

    def _identify_galleries(
        self,
        placements: List[ImagePlacement],
        manifest: ImageManifest,
        config: LayoutConfig,
    ) -> List[GalleryGroup]:
        """Group related images in the same chapter into galleries."""
        if not config.enable_galleries:
            return []

        galleries = []
        chapter_placements: Dict[int, List[ImagePlacement]] = {}
        for p in placements:
            chapter_placements.setdefault(p.chapter_index, []).append(p)

        for ch_idx, ch_placements in chapter_placements.items():
            if len(ch_placements) < 3:
                continue

            # Group by similar category
            category_groups: Dict[str, List[str]] = {}
            for p in ch_placements:
                img = manifest.get_image(p.image_id)
                if img:
                    cat = img.category.value
                    category_groups.setdefault(cat, []).append(p.image_id)

            for cat, ids in category_groups.items():
                if len(ids) >= 2:
                    galleries.append(GalleryGroup(
                        group_id=str(uuid.uuid4())[:8],
                        image_ids=ids,
                        title=f"{cat.title()} gallery",
                        chapter_index=ch_idx,
                    ))
                    # Mark these placements as gallery layout
                    for p in ch_placements:
                        if p.image_id in ids:
                            p.layout_mode = LayoutMode.GALLERY

        return galleries

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
            return {}
