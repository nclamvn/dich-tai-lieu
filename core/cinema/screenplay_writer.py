"""
Screenplay Writer - Scene to Screenplay Conversion

Converts CinematicScene objects into properly formatted screenplays
following industry-standard screenplay format.
"""

import json
import logging
import re
from typing import List, Optional, Any

from .models import (
    CinematicScene, 
    ScreenplayScene, 
    Screenplay, 
    CinemaStyle,
    StyleTemplate,
)

logger = logging.getLogger(__name__)


SCREENPLAY_PROMPT = """Bạn là biên kịch điện ảnh chuyên nghiệp với kinh nghiệm viết kịch bản theo tiêu chuẩn Hollywood.

🎬 PHONG CÁCH: {style_name}
{style_description}

📍 DỮ LIỆU PHÂN CẢNH:
- Bối cảnh: {setting}
- Thời gian: {time_of_day}
- Nhân vật: {characters}
- Hành động: {actions}
- Hội thoại: {dialogue}
- Không khí: {mood}
- Gợi ý camera: {camera}

📝 VĂN BẢN GỐC:
{original_text}

VIẾT KỊCH BẢN THEO FORMAT CHUẨN:

1. SCENE HEADING (Tiêu đề cảnh):
   INT./EXT. ĐỊA ĐIỂM - THỜI GIAN

2. ACTION LINES (Mô tả hành động):
   - Viết ở thì hiện tại
   - Chỉ mô tả những gì THẤY và NGHE được
   - Tối đa 4 dòng liên tiếp

3. CHARACTER CUE (Tên nhân vật):
   - Viết HOA, căn giữa
   
4. PARENTHETICAL (Chỉ dẫn diễn xuất):
   - Trong ngoặc đơn, ngay dưới tên nhân vật
   
5. DIALOGUE (Lời thoại):
   - Dưới tên nhân vật, căn giữa

Trả về JSON:
```json
{{
  "int_ext": "INT" hoặc "EXT",
  "location": "Tên địa điểm",
  "time": "DAY/NIGHT/CONTINUOUS",
  "action_lines": ["Dòng hành động 1", "Dòng hành động 2"],
  "dialogue_blocks": [
    {{
      "character": "TÊN NHÂN VẬT",
      "parenthetical": "(chỉ dẫn)",
      "line": "Lời thoại"
    }}
  ],
  "opening_transition": null hoặc "FADE IN:",
  "closing_transition": null hoặc "CUT TO:"
}}
```
"""

SCREENPLAY_PROMPT_EN = """You are a professional screenwriter with Hollywood industry experience.

🎬 STYLE: {style_name}
{style_description}

📍 SCENE DATA:
- Setting: {setting}
- Time: {time_of_day}
- Characters: {characters}
- Actions: {actions}
- Dialogue: {dialogue}
- Mood: {mood}
- Camera suggestions: {camera}

📝 ORIGINAL TEXT:
{original_text}

WRITE SCREENPLAY IN STANDARD FORMAT:

1. SCENE HEADING: INT./EXT. LOCATION - TIME
2. ACTION LINES: Present tense, visual descriptions only
3. CHARACTER CUE: UPPERCASE, centered
4. PARENTHETICAL: Acting directions in parentheses
5. DIALOGUE: Below character name

Return JSON:
```json
{{
  "int_ext": "INT" or "EXT",
  "location": "Location name",
  "time": "DAY/NIGHT/CONTINUOUS",
  "action_lines": ["Action line 1", "Action line 2"],
  "dialogue_blocks": [
    {{
      "character": "CHARACTER NAME",
      "parenthetical": "(direction)",
      "line": "Dialogue"
    }}
  ],
  "opening_transition": null or "FADE IN:",
  "closing_transition": null or "CUT TO:"
}}
```
"""


class ScreenplayWriter:
    """
    Converts cinematic scenes into professionally formatted screenplays.
    
    Uses AI to generate screenplay content following industry standards.
    """
    
    def __init__(self, llm_client: Any, language: str = "vi"):
        """
        Initialize ScreenplayWriter.
        
        Args:
            llm_client: AI client for screenplay generation
            language: Output language ("vi" or "en")
        """
        self.llm_client = llm_client
        self.language = language
        self.prompt_template = (
            SCREENPLAY_PROMPT if language == "vi" 
            else SCREENPLAY_PROMPT_EN
        )
    
    async def write_scene(
        self,
        scene: CinematicScene,
        scene_number: int,
        style: CinemaStyle = CinemaStyle.BLOCKBUSTER,
        style_template: Optional[StyleTemplate] = None,
    ) -> ScreenplayScene:
        """
        Write a screenplay scene from cinematic scene data.
        
        Args:
            scene: CinematicScene with extracted elements
            scene_number: Scene number in screenplay
            style: Cinema style
            style_template: Optional style template
            
        Returns:
            ScreenplayScene in proper format
        """
        style_name = style_template.name if style_template else style.value
        style_description = style_template.description if style_template else ""
        
        # Format scene data for prompt
        characters_str = ", ".join([
            f"{c.get('name', 'Unknown')} ({c.get('emotion', '')})" 
            for c in scene.characters
        ]) if scene.characters else "Không rõ"
        
        actions_str = "\n".join(f"- {a}" for a in scene.key_actions) if scene.key_actions else "Không có"
        
        dialogue_str = "\n".join([
            f"- {d.get('character', 'Unknown')}: \"{d.get('line', '')}\" ({d.get('direction', '')})"
            for d in scene.dialogue
        ]) if scene.dialogue else "Không có"
        
        camera_str = ", ".join(scene.camera_suggestions) if scene.camera_suggestions else "Tiêu chuẩn"
        
        prompt = self.prompt_template.format(
            style_name=style_name,
            style_description=style_description,
            setting=scene.setting,
            time_of_day=scene.time_of_day,
            characters=characters_str,
            actions=actions_str,
            dialogue=dialogue_str,
            mood=scene.mood,
            camera=camera_str,
            original_text=scene.original_text[:2000],  # Limit text length
        )
        
        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            screenplay_data = self._parse_screenplay_json(response.content)
            
            # Create ScreenplayScene
            screenplay_scene = ScreenplayScene(
                scene_number=scene_number,
                scene_id=scene.scene_id,
                int_ext=screenplay_data.get("int_ext", "INT"),
                location=screenplay_data.get("location", scene.setting),
                time=screenplay_data.get("time", scene.time_of_day.upper()),
                action_lines=screenplay_data.get("action_lines", []),
                dialogue_blocks=screenplay_data.get("dialogue_blocks", []),
                opening_transition=screenplay_data.get("opening_transition"),
                closing_transition=screenplay_data.get("closing_transition"),
            )
            
            logger.info(f"Wrote screenplay scene {scene_number} for {scene.scene_id}")
            return screenplay_scene
            
        except Exception as e:
            logger.error(f"Screenplay writing failed for scene {scene.scene_id}: {e}")
            # Return minimal screenplay scene
            return ScreenplayScene(
                scene_number=scene_number,
                scene_id=scene.scene_id,
                int_ext="INT" if scene.location_type == "interior" else "EXT",
                location=scene.setting or "UNKNOWN LOCATION",
                time=scene.time_of_day.upper() if scene.time_of_day else "DAY",
                action_lines=[scene.original_text[:200] + "..."],
            )
    
    async def write_screenplay(
        self,
        scenes: List[CinematicScene],
        title: str,
        author: str,
        style: CinemaStyle = CinemaStyle.BLOCKBUSTER,
        style_template: Optional[StyleTemplate] = None,
        progress_callback: Optional[callable] = None,
    ) -> Screenplay:
        """
        Write complete screenplay from multiple scenes.
        
        Args:
            scenes: List of CinematicScene objects
            title: Screenplay title
            author: Author name
            style: Cinema style
            style_template: Optional style template
            progress_callback: Called with (current, total)
            
        Returns:
            Complete Screenplay object
        """
        screenplay_scenes = []
        total = len(scenes)
        
        for i, scene in enumerate(scenes):
            screenplay_scene = await self.write_scene(
                scene=scene,
                scene_number=i + 1,
                style=style,
                style_template=style_template,
            )
            screenplay_scenes.append(screenplay_scene)
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        # Add opening fade in to first scene
        if screenplay_scenes:
            screenplay_scenes[0].opening_transition = "FADE IN:"
            screenplay_scenes[-1].closing_transition = "FADE OUT."
        
        # Calculate estimated runtime
        total_duration = sum(s.estimated_duration for s in scenes)
        runtime_minutes = total_duration // 60
        
        screenplay = Screenplay(
            title=title,
            author=author,
            scenes=screenplay_scenes,
            genre=self._detect_genre(scenes),
            style=style,
            estimated_runtime_minutes=runtime_minutes,
        )
        
        logger.info(f"Created screenplay '{title}' with {len(screenplay_scenes)} scenes, ~{runtime_minutes} min")
        return screenplay
    
    def _parse_screenplay_json(self, response_text: str) -> dict:
        """Extract and parse JSON from AI response."""
        # Look for ```json block
        json_block = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if json_block:
            try:
                return json.loads(json_block.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find raw JSON
        json_obj = re.search(r'\{[\s\S]*\}', response_text)
        if json_obj:
            try:
                return json.loads(json_obj.group(0))
            except json.JSONDecodeError:
                pass
        
        return {}
    
    def _detect_genre(self, scenes: List[CinematicScene]) -> str:
        """Detect genre from scene moods."""
        mood_counts = {}
        for scene in scenes:
            mood = scene.mood
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        if not mood_counts:
            return "Drama"
        
        dominant_mood = max(mood_counts, key=mood_counts.get)
        
        mood_to_genre = {
            "action": "Action",
            "romantic": "Romance",
            "dark": "Thriller",
            "mysterious": "Mystery",
            "peaceful": "Drama",
            "tense": "Thriller",
            "horror": "Horror",
        }
        
        return mood_to_genre.get(dominant_mood, "Drama")
    
    def export_to_text(self, screenplay: Screenplay) -> str:
        """Export screenplay to standard text format."""
        return screenplay.to_text()
    
    def export_to_fountain(self, screenplay: Screenplay) -> str:
        """Export screenplay to Fountain format (industry standard)."""
        lines = []
        
        # Title page
        lines.append(f"Title: {screenplay.title}")
        lines.append(f"Author: {screenplay.author}")
        lines.append("")
        lines.append("===")
        lines.append("")
        
        for scene in screenplay.scenes:
            # Scene heading (starts with INT or EXT)
            heading = f"{scene.int_ext}. {scene.location.upper()} - {scene.time.upper()}"
            lines.append(heading)
            lines.append("")
            
            # Action lines
            for action in scene.action_lines:
                lines.append(action)
                lines.append("")
            
            # Dialogue
            for block in scene.dialogue_blocks:
                # Character name (UPPERCASE, preceded by empty line)
                lines.append(f"@{block['character'].upper()}")
                if block.get('parenthetical'):
                    lines.append(f"({block['parenthetical'].strip('()')})")
                lines.append(block['line'])
                lines.append("")
            
            # Transition
            if scene.closing_transition:
                lines.append(f"> {scene.closing_transition}")
                lines.append("")
        
        return "\n".join(lines)
