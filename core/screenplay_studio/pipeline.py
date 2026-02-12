"""
Screenplay Studio Pipeline Orchestrator

Coordinates the multi-agent screenplay generation pipeline.

Phases:
1. Analysis - Story structure, characters, themes
2. Screenplay - Dialogue + Action writing, formatting
3. Pre-Visualization - Shot lists, storyboards
4. Video Rendering - AI video generation
"""

import logging
from typing import Optional, List, Dict, Any

from .models import (
    ScreenplayProject, StoryAnalysis, Screenplay, Scene,
    DialogueBlock, ActionBlock, Language,
    ShotList, VideoPrompt, VideoClip, VideoProvider,
)
from .agents.story_analyst import StoryAnalystAgent
from .agents.scene_architect import SceneArchitectAgent
from .agents.dialogue_writer import DialogueWriterAgent
from .agents.action_writer import ActionWriterAgent
from .agents.vietnamese_adapter import VietnameseAdapterAgent
from .agents.screenplay_formatter import ScreenplayFormatterAgent
from .agents.cinematographer import CinematographerAgent
from .agents.visual_designer import VisualDesignerAgent
from .agents.storyboarder import StoryboarderAgent
from .agents.prompt_engineer import PromptEngineerAgent
from .agents.video_renderer import VideoRendererAgent
from .agents.video_editor import VideoEditorAgent
from .agents.base_agent import AgentResult

logger = logging.getLogger(__name__)


class ScreenplayPipeline:
    """Main orchestrator for screenplay generation"""

    def __init__(self):
        # Phase 1 agents
        self.story_analyst = StoryAnalystAgent()
        self.scene_architect = SceneArchitectAgent()

        # Phase 2 agents
        self.dialogue_writer = DialogueWriterAgent()
        self.action_writer = ActionWriterAgent()
        self.vietnamese_adapter = VietnameseAdapterAgent()
        self.screenplay_formatter = ScreenplayFormatterAgent()

        # Phase 3 agents
        self.cinematographer = CinematographerAgent()
        self.visual_designer = VisualDesignerAgent()
        self.storyboarder = StoryboarderAgent()

        # Phase 4 agents
        self.prompt_engineer = PromptEngineerAgent()
        self.video_renderer = VideoRendererAgent()
        self.video_editor = VideoEditorAgent()

    # =========================================================================
    # PHASE 1: ANALYSIS
    # =========================================================================

    async def analyze(self, project: ScreenplayProject) -> AgentResult:
        """
        Run Phase 1: Story Analysis

        Returns AgentResult with StoryAnalysis
        """
        logger.info(f"Starting analysis for project: {project.id}")

        result = await self.story_analyst.execute({
            "source_text": project.source_text,
            "language": project.language.value,
            "title": project.title,
        })

        return result

    async def create_scene_breakdown(
        self,
        project: ScreenplayProject,
        target_runtime: Optional[int] = None,
    ) -> AgentResult:
        """
        Run Phase 1b: Scene Breakdown

        Requires story_analysis to be completed first.
        Returns AgentResult with list of Scenes.
        """
        if not project.story_analysis:
            return AgentResult(
                success=False,
                data=None,
                error="Story analysis must be completed first"
            )

        logger.info(f"Creating scene breakdown for project: {project.id}")

        result = await self.scene_architect.execute({
            "story_analysis": project.story_analysis,
            "target_runtime": target_runtime or project.story_analysis.estimated_runtime_minutes,
        })

        return result

    async def run_phase_1(self, project: ScreenplayProject) -> AgentResult:
        """
        Run complete Phase 1: Analysis + Scene Breakdown
        """
        # Step 1: Story Analysis
        analysis_result = await self.analyze(project)

        if not analysis_result.success:
            return analysis_result

        project.story_analysis = analysis_result.data

        # Step 2: Scene Breakdown
        breakdown_result = await self.create_scene_breakdown(project)

        if not breakdown_result.success:
            return breakdown_result

        # Combine results
        total_tokens = analysis_result.tokens_used + breakdown_result.tokens_used
        total_cost = analysis_result.cost_usd + breakdown_result.cost_usd

        return AgentResult(
            success=True,
            data={
                "story_analysis": analysis_result.data,
                "scene_breakdown": breakdown_result.data,
            },
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )

    # =========================================================================
    # PHASE 2: SCREENPLAY WRITING
    # =========================================================================

    async def write_scene_dialogue(
        self,
        scene: Scene,
        characters: List,
        source_excerpt: str,
        language: Language,
    ) -> AgentResult:
        """Write dialogue for a single scene"""
        return await self.dialogue_writer.execute({
            "scene": scene,
            "characters": characters,
            "source_excerpt": source_excerpt,
            "language": language,
        })

    async def write_scene_action(
        self,
        scene: Scene,
        dialogue_blocks: List[DialogueBlock],
        source_excerpt: str,
        language: Language,
    ) -> AgentResult:
        """Write action for a single scene"""
        return await self.action_writer.execute({
            "scene": scene,
            "dialogue_blocks": dialogue_blocks,
            "source_excerpt": source_excerpt,
            "language": language,
        })

    async def adapt_for_vietnamese(
        self,
        scene: Scene,
        characters: List,
        scene_content: str,
        setting: str = "",
        time_period: str = "contemporary",
        region: str = "south",
    ) -> AgentResult:
        """Adapt scene for Vietnamese culture"""
        return await self.vietnamese_adapter.execute({
            "scene": scene,
            "characters": characters,
            "scene_content": scene_content,
            "setting": setting,
            "time_period": time_period,
            "region": region,
        })

    async def write_scene(
        self,
        scene: Scene,
        project: ScreenplayProject,
        source_excerpt: str = "",
    ) -> AgentResult:
        """
        Write complete scene (dialogue + action).

        Returns Scene with elements populated.
        """
        logger.info(f"Writing scene {scene.scene_number}")

        characters = project.story_analysis.characters if project.story_analysis else []
        language = project.language

        # Step 1: Write dialogue
        dialogue_result = await self.write_scene_dialogue(
            scene=scene,
            characters=characters,
            source_excerpt=source_excerpt,
            language=language,
        )

        if not dialogue_result.success:
            return dialogue_result

        dialogue_blocks = dialogue_result.data.get("dialogue_blocks", [])

        # Step 2: Write action
        action_result = await self.write_scene_action(
            scene=scene,
            dialogue_blocks=dialogue_blocks,
            source_excerpt=source_excerpt,
            language=language,
        )

        if not action_result.success:
            return action_result

        action_blocks = action_result.data.get("action_blocks", [])

        # Step 3: Vietnamese adaptation (if needed)
        if language == Language.VIETNAMESE:
            scene_content = self._build_scene_content(dialogue_blocks, action_blocks)

            adapt_result = await self.adapt_for_vietnamese(
                scene=scene,
                characters=characters,
                scene_content=scene_content,
                setting=project.story_analysis.setting if project.story_analysis else "",
            )

            if adapt_result.success and adapt_result.data:
                dialogue_blocks, action_blocks = self._apply_adaptations(
                    dialogue_blocks,
                    action_blocks,
                    adapt_result.data,
                )

        # Step 4: Assemble scene
        completed_scene = self.screenplay_formatter.assemble_scene(
            scene=scene,
            dialogue_blocks=dialogue_blocks,
            action_blocks=action_blocks,
        )

        total_tokens = dialogue_result.tokens_used + action_result.tokens_used
        total_cost = dialogue_result.cost_usd + action_result.cost_usd

        return AgentResult(
            success=True,
            data=completed_scene,
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )

    async def run_phase_2(
        self,
        project: ScreenplayProject,
        scenes: List[Scene],
        progress_callback=None,
    ) -> AgentResult:
        """
        Run complete Phase 2: Write all scenes.

        Args:
            project: Project with story_analysis
            scenes: Scene blueprints from Phase 1
            progress_callback: Optional callback(scene_num, total, scene)

        Returns:
            AgentResult with complete Screenplay
        """
        logger.info(f"Starting Phase 2 for project: {project.id}")

        if not project.story_analysis:
            return AgentResult(
                success=False,
                data=None,
                error="Story analysis required before writing"
            )

        total_tokens = 0
        total_cost = 0.0
        completed_scenes = []

        # Extract source excerpts for each scene
        source_text = project.source_text
        excerpt_length = len(source_text) // len(scenes) if scenes else 1000

        for i, scene in enumerate(scenes):
            start = i * excerpt_length
            end = start + excerpt_length + 500  # Overlap
            source_excerpt = source_text[start:min(end, len(source_text))]

            result = await self.write_scene(
                scene=scene,
                project=project,
                source_excerpt=source_excerpt,
            )

            if not result.success:
                logger.error(f"Failed to write scene {scene.scene_number}: {result.error}")
                continue

            completed_scenes.append(result.data)
            total_tokens += result.tokens_used
            total_cost += result.cost_usd

            if progress_callback:
                progress_callback(i + 1, len(scenes), result.data)

        # Assemble screenplay
        format_result = await self.screenplay_formatter.execute({
            "title": project.title,
            "author": "AI Publisher Pro",
            "language": project.language,
            "story_analysis": project.story_analysis,
            "scenes": completed_scenes,
        })

        if not format_result.success:
            return format_result

        return AgentResult(
            success=True,
            data=format_result.data,
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )

    def _build_scene_content(
        self,
        dialogue_blocks: List[DialogueBlock],
        action_blocks: List[Dict],
    ) -> str:
        """Build scene content string for adaptation"""
        lines = []

        for action in action_blocks:
            if action.get("type") == "scene_opening":
                lines.append(action.get("text", ""))

        for dialogue in dialogue_blocks:
            lines.append(f"{dialogue.character}: {dialogue.dialogue}")

        return "\n".join(lines)

    def _apply_adaptations(
        self,
        dialogue_blocks: List[DialogueBlock],
        action_blocks: List[Dict],
        adaptations: Dict,
    ) -> tuple:
        """Apply Vietnamese adaptations to dialogue and action"""
        adapted_dialogues = []
        for dialogue in dialogue_blocks:
            adapted = dialogue
            for adapt in adaptations.get("dialogue_adaptations", []):
                if adapt.get("original_character") == dialogue.character:
                    adapted = DialogueBlock(
                        character=dialogue.character,
                        dialogue=adapt.get("adapted_dialogue", dialogue.dialogue),
                        parenthetical=dialogue.parenthetical,
                    )
                    break
            adapted_dialogues.append(adapted)

        adapted_actions = action_blocks.copy()
        for adapt in adaptations.get("action_adaptations", []):
            for i, action in enumerate(adapted_actions):
                if action.get("text") == adapt.get("original"):
                    adapted_actions[i]["text"] = adapt.get("adapted", action["text"])

        return adapted_dialogues, adapted_actions

    # =========================================================================
    # PHASE 3: PRE-VISUALIZATION
    # =========================================================================

    async def create_shot_list(
        self,
        scene: Scene,
        project: ScreenplayProject,
    ) -> AgentResult:
        """Create shot list for a scene"""
        return await self.cinematographer.execute({
            "scene": scene,
            "genre": project.story_analysis.genre if project.story_analysis else "Drama",
            "tone": project.story_analysis.tone if project.story_analysis else "neutral",
            "reference_films": [],
            "language": project.language,
        })

    async def create_visual_guide(
        self,
        scene: Scene,
        shot_list: ShotList,
        project: ScreenplayProject,
    ) -> AgentResult:
        """Create visual style guide for a scene"""
        return await self.visual_designer.execute({
            "scene": scene,
            "shot_list": shot_list,
            "characters": project.story_analysis.characters if project.story_analysis else [],
            "genre": project.story_analysis.genre if project.story_analysis else "Drama",
            "tone": project.story_analysis.tone if project.story_analysis else "neutral",
            "time_period": project.story_analysis.time_period if project.story_analysis else "contemporary",
            "reference_films": [],
            "language": project.language,
        })

    async def generate_storyboard(
        self,
        scene: Scene,
        shot_list: ShotList,
        visual_guide: Dict,
        output_dir: str,
    ) -> AgentResult:
        """Generate storyboard images for a scene"""
        return await self.storyboarder.execute({
            "scene": scene,
            "shot_list": shot_list,
            "visual_guide": visual_guide,
            "output_dir": output_dir,
        })

    async def run_phase_3(
        self,
        project: ScreenplayProject,
        output_dir: str = "outputs/storyboard",
        progress_callback=None,
    ) -> AgentResult:
        """
        Run complete Phase 3: Pre-Visualization for all scenes.

        Creates shot lists, visual guides, and storyboard images.
        """
        logger.info(f"Starting Phase 3 for project: {project.id}")

        if not project.screenplay:
            return AgentResult(
                success=False,
                data=None,
                error="Screenplay required before pre-visualization"
            )

        total_tokens = 0
        total_cost = 0.0
        all_shot_lists = []
        all_images = []

        for i, scene in enumerate(project.screenplay.scenes):
            if progress_callback:
                progress_callback("scene", i + 1, f"Pre-viz scene {i + 1}")

            # Step 1: Create shot list
            shot_result = await self.create_shot_list(scene, project)
            if not shot_result.success:
                logger.warning(f"Shot list failed for scene {scene.scene_number}")
                continue

            shot_list = shot_result.data
            all_shot_lists.append(shot_list)
            total_tokens += shot_result.tokens_used
            total_cost += shot_result.cost_usd

            # Step 2: Create visual guide
            visual_result = await self.create_visual_guide(scene, shot_list, project)
            if not visual_result.success:
                logger.warning(f"Visual guide failed for scene {scene.scene_number}")
                visual_guide = {}
            else:
                visual_guide = visual_result.data
                total_tokens += visual_result.tokens_used
                total_cost += visual_result.cost_usd

            # Step 3: Generate storyboard images
            storyboard_result = await self.generate_storyboard(
                scene=scene,
                shot_list=shot_list,
                visual_guide=visual_guide,
                output_dir=output_dir,
            )

            if storyboard_result.success:
                all_images.extend(storyboard_result.data.get("images", []))
                total_cost += storyboard_result.cost_usd

            # Update scene with shot list
            scene.shot_list = shot_list

        return AgentResult(
            success=True,
            data={
                "shot_lists": all_shot_lists,
                "images": all_images,
                "total_images": len(all_images),
            },
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )

    # =========================================================================
    # PHASE 4: VIDEO RENDERING
    # =========================================================================

    async def create_video_prompts(
        self,
        shot_list: ShotList,
        visual_guide: Dict,
        characters: List,
        provider: VideoProvider,
    ) -> AgentResult:
        """Create video prompts for a shot list"""
        return await self.prompt_engineer.execute({
            "shot_list": shot_list,
            "visual_guide": visual_guide,
            "characters": characters,
            "provider": provider,
        })

    async def render_videos(
        self,
        prompts: List[VideoPrompt],
        output_dir: str,
        provider: VideoProvider,
    ) -> AgentResult:
        """Render videos from prompts"""
        return await self.video_renderer.execute({
            "prompts": prompts,
            "output_dir": output_dir,
            "provider": provider,
            "max_concurrent": 3,
        })

    async def stitch_videos(
        self,
        clips: List[VideoClip],
        output_path: str,
        transition: str = "cut",
    ) -> AgentResult:
        """Stitch video clips into sequence"""
        return await self.video_editor.execute({
            "clips": clips,
            "output_path": output_path,
            "transition": transition,
        })

    async def run_phase_4(
        self,
        project: ScreenplayProject,
        provider: VideoProvider = VideoProvider.RUNWAY,
        output_dir: str = "outputs/video",
        progress_callback=None,
    ) -> AgentResult:
        """
        Run complete Phase 4: Video Rendering for all scenes.

        Creates video prompts, generates videos, and stitches them together.
        """
        logger.info(f"Starting Phase 4 for project: {project.id}")

        if not project.screenplay:
            return AgentResult(
                success=False,
                data=None,
                error="Screenplay required before video rendering"
            )

        total_cost = 0.0
        all_clips = []

        characters = project.story_analysis.characters if project.story_analysis else []

        for i, scene in enumerate(project.screenplay.scenes):
            if progress_callback:
                progress_callback("scene", i + 1, f"Rendering scene {i + 1}")

            shot_list = scene.shot_list
            if not shot_list:
                logger.warning(f"No shot list for scene {scene.scene_number}")
                continue

            visual_guide = {}  # Would be stored from Phase 3

            # Step 1: Create video prompts
            prompt_result = await self.create_video_prompts(
                shot_list=shot_list,
                visual_guide=visual_guide,
                characters=characters,
                provider=provider,
            )

            if not prompt_result.success:
                logger.warning(f"Prompt creation failed for scene {scene.scene_number}")
                continue

            prompts = prompt_result.data
            total_cost += prompt_result.cost_usd

            # Step 2: Render videos
            scene_output_dir = f"{output_dir}/scene_{scene.scene_number:03d}"
            render_result = await self.render_videos(
                prompts=prompts,
                output_dir=scene_output_dir,
                provider=provider,
            )

            if render_result.success:
                clips = render_result.data.get("clips", [])
                all_clips.extend(clips)
                total_cost += render_result.cost_usd

                scene.video_clips = [c.file_path for c in clips]

        # Step 3: Stitch all clips
        if all_clips:
            final_output = f"{output_dir}/final_{project.id}.mp4"
            stitch_result = await self.stitch_videos(
                clips=all_clips,
                output_path=final_output,
                transition="dissolve",
            )

            if stitch_result.success:
                project.output_files["video_final"] = final_output

        return AgentResult(
            success=True,
            data={
                "clips": all_clips,
                "total_clips": len(all_clips),
                "final_video": project.output_files.get("video_final"),
            },
            tokens_used=0,
            cost_usd=total_cost,
        )

    # =========================================================================
    # FULL PIPELINE
    # =========================================================================

    async def run_full_screenplay_generation(
        self,
        project: ScreenplayProject,
        progress_callback=None,
    ) -> AgentResult:
        """
        Run complete screenplay generation (Phase 1 + 2).

        This is the main entry point for FREE tier.
        """
        logger.info(f"Starting full screenplay generation for: {project.id}")

        # Phase 1: Analysis
        if progress_callback:
            progress_callback("phase", 1, "Starting analysis...")

        phase1_result = await self.run_phase_1(project)

        if not phase1_result.success:
            return phase1_result

        project.story_analysis = phase1_result.data["story_analysis"]
        scenes = phase1_result.data["scene_breakdown"]["scenes"]

        # Phase 2: Writing
        if progress_callback:
            progress_callback("phase", 2, "Writing screenplay...")

        def scene_progress(num, total, scene):
            if progress_callback:
                progress_callback("scene", num, f"Scene {num}/{total}")

        phase2_result = await self.run_phase_2(
            project=project,
            scenes=scenes,
            progress_callback=scene_progress,
        )

        if not phase2_result.success:
            return phase2_result

        total_tokens = phase1_result.tokens_used + phase2_result.tokens_used
        total_cost = phase1_result.cost_usd + phase2_result.cost_usd

        return AgentResult(
            success=True,
            data={
                "story_analysis": project.story_analysis,
                "screenplay": phase2_result.data,
            },
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )
