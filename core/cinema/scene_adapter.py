"""
Scene Adapter - Text to Cinematic Scene Conversion

Transforms raw text chunks into structured cinematic scenes using AI.
Extracts setting, characters, actions, dialogue, and visual elements.
"""

import json
import logging
import uuid
from typing import List, Optional, Any, Dict

from .models import CinematicChunk, CinematicScene, CinemaStyle, StyleTemplate

logger = logging.getLogger(__name__)


# AI Prompt Templates
SCENE_EXTRACTION_PROMPT = """Bạn là chuyên gia phân tích văn học và điện ảnh.

Phân tích đoạn văn sau và trích xuất các yếu tố điện ảnh để chuyển thể thành phân cảnh phim.

📝 VĂN BẢN:
{text}

🎬 PHONG CÁCH MỤC TIÊU: {style}

YÊU CẦU PHÂN TÍCH:

1. **SETTING** (Bối cảnh):
   - Địa điểm cụ thể (indoor/outdoor)
   - Thời gian trong ngày
   - Mô tả chi tiết không gian

2. **CHARACTERS** (Nhân vật):
   - Tên và vai trò
   - Mô tả ngoại hình
   - Trạng thái cảm xúc

3. **KEY_ACTIONS** (Hành động chính):
   - Liệt kê 3-5 hành động quan trọng
   - Theo thứ tự thời gian

4. **DIALOGUE** (Hội thoại):
   - Trích xuất hội thoại quan trọng
   - Ghi chú cách nói (thì thầm, la hét, v.v.)

5. **MOOD** (Không khí):
   - Cảm xúc chủ đạo
   - Arc cảm xúc (tăng/giảm tension)

6. **VISUAL_SUGGESTIONS** (Gợi ý hình ảnh):
   - Góc quay đề xuất
   - Phong cách ánh sáng
   - Bảng màu (3-5 hex colors)

7. **ESTIMATED_DURATION** (Thời lượng ước tính):
   - Số giây phù hợp cho cảnh này (10-60s)

Trả về JSON theo format sau:
```json
{{
  "setting": "mô tả bối cảnh",
  "time_of_day": "day/night/dawn/dusk",
  "location_type": "interior/exterior",
  "characters": [
    {{"name": "Tên", "description": "mô tả", "emotion": "cảm xúc"}}
  ],
  "key_actions": ["hành động 1", "hành động 2"],
  "dialogue": [
    {{"character": "Tên", "line": "Lời thoại", "direction": "cách nói"}}
  ],
  "mood": "tense/romantic/action/peaceful/dark/mysterious",
  "emotional_arc": "mô tả arc cảm xúc",
  "camera_suggestions": ["wide shot", "close-up", "tracking"],
  "lighting_mood": "mô tả ánh sáng",
  "color_palette": ["#hexcode1", "#hexcode2"],
  "estimated_duration": 30
}}
```
"""

SCENE_EXTRACTION_PROMPT_EN = """You are an expert in literary and cinematic analysis.

Analyze the following text and extract cinematic elements for film adaptation.

📝 TEXT:
{text}

🎬 TARGET STYLE: {style}

ANALYSIS REQUIREMENTS:

1. **SETTING**: Location, time of day, detailed visual description
2. **CHARACTERS**: Names, appearances, emotional states
3. **KEY_ACTIONS**: 3-5 main actions in chronological order
4. **DIALOGUE**: Important dialogue with delivery notes
5. **MOOD**: Primary emotion, emotional arc
6. **VISUAL_SUGGESTIONS**: Camera angles, lighting, color palette
7. **ESTIMATED_DURATION**: Appropriate length in seconds (10-60s)

Return JSON format:
```json
{{
  "setting": "description",
  "time_of_day": "day/night/dawn/dusk",
  "location_type": "interior/exterior",
  "characters": [{{"name": "", "description": "", "emotion": ""}}],
  "key_actions": [],
  "dialogue": [{{"character": "", "line": "", "direction": ""}}],
  "mood": "tense/romantic/action/peaceful/dark/mysterious",
  "emotional_arc": "",
  "camera_suggestions": [],
  "lighting_mood": "",
  "color_palette": [],
  "estimated_duration": 30
}}
```
"""


class SceneAdapter:
    """
    Transforms text chunks into structured cinematic scenes.
    
    Uses AI to analyze text and extract visual, character, and mood
    information needed for screenplay and video generation.
    """
    
    def __init__(self, llm_client: Any, language: str = "vi"):
        """
        Initialize SceneAdapter.
        
        Args:
            llm_client: AI client for scene extraction
            language: Output language ("vi" or "en")
        """
        self.llm_client = llm_client
        self.language = language
        self.prompt_template = (
            SCENE_EXTRACTION_PROMPT if language == "vi" 
            else SCENE_EXTRACTION_PROMPT_EN
        )
    
    async def adapt_chunk(
        self, 
        chunk: CinematicChunk, 
        style: CinemaStyle = CinemaStyle.BLOCKBUSTER,
        style_template: Optional[StyleTemplate] = None,
    ) -> CinematicScene:
        """
        Convert a text chunk into a cinematic scene.
        
        Args:
            chunk: Text chunk to adapt
            style: Cinema style for adaptation
            style_template: Optional detailed style template
            
        Returns:
            CinematicScene with extracted elements
        """
        style_name = style_template.name if style_template else style.value
        
        prompt = self.prompt_template.format(
            text=chunk.text,
            style=style_name,
        )
        
        try:
            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON from response
            scene_data = self._parse_scene_json(response.content)
            
            # Create CinematicScene
            scene = CinematicScene(
                scene_id=f"adapted_{chunk.chunk_id}",
                chunk_id=chunk.chunk_id,
                original_text=chunk.text,
                setting=scene_data.get("setting", ""),
                time_of_day=scene_data.get("time_of_day", "day"),
                location_type=scene_data.get("location_type", "interior"),
                characters=scene_data.get("characters", []),
                key_actions=scene_data.get("key_actions", []),
                dialogue=scene_data.get("dialogue", []),
                mood=scene_data.get("mood", "neutral"),
                emotional_arc=scene_data.get("emotional_arc", ""),
                camera_suggestions=scene_data.get("camera_suggestions", []),
                lighting_mood=scene_data.get("lighting_mood", ""),
                color_palette=scene_data.get("color_palette", []),
                estimated_duration=scene_data.get("estimated_duration", 30),
            )
            
            logger.info(f"Adapted chunk {chunk.chunk_id} -> scene with {len(scene.characters)} characters, mood: {scene.mood}")
            return scene
            
        except Exception as e:
            logger.error(f"Scene adaptation failed for chunk {chunk.chunk_id}: {e}")
            # Return minimal scene on error
            return CinematicScene(
                scene_id=f"adapted_{chunk.chunk_id}",
                chunk_id=chunk.chunk_id,
                original_text=chunk.text,
                setting="Unknown setting",
                mood="neutral",
                estimated_duration=30,
            )
    
    async def adapt_chunks(
        self,
        chunks: List[CinematicChunk],
        style: CinemaStyle = CinemaStyle.BLOCKBUSTER,
        style_template: Optional[StyleTemplate] = None,
        progress_callback: Optional[callable] = None,
    ) -> List[CinematicScene]:
        """
        Convert multiple chunks into scenes.
        
        Args:
            chunks: List of text chunks
            style: Cinema style
            style_template: Optional style template
            progress_callback: Called with (current, total) after each chunk
            
        Returns:
            List of CinematicScene objects
        """
        scenes = []
        total = len(chunks)
        
        for i, chunk in enumerate(chunks):
            scene = await self.adapt_chunk(chunk, style, style_template)
            scenes.append(scene)
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        logger.info(f"Adapted {len(scenes)} chunks into cinematic scenes")
        return scenes
    
    def _parse_scene_json(self, response_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from AI response."""
        # Try to find JSON in response
        json_match = None
        
        # Look for ```json block
        import re
        json_block = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if json_block:
            json_match = json_block.group(1)
        else:
            # Try to find raw JSON object
            json_obj = re.search(r'\{[\s\S]*\}', response_text)
            if json_obj:
                json_match = json_obj.group(0)
        
        if json_match:
            try:
                return json.loads(json_match)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed: {e}")
        
        # Return empty dict if parsing fails
        return {}
    
    def enhance_scene_with_style(
        self, 
        scene: CinematicScene, 
        style_template: StyleTemplate
    ) -> CinematicScene:
        """
        Enhance a scene with style-specific suggestions.
        
        Args:
            scene: Base scene
            style_template: Style template to apply
            
        Returns:
            Enhanced scene with style elements
        """
        # Add style-specific camera movements
        if not scene.camera_suggestions:
            scene.camera_suggestions = style_template.default_shots[:3]
        
        # Add style-specific lighting if not set
        if not scene.lighting_mood:
            scene.lighting_mood = style_template.lighting_style
        
        # Enhance color palette
        if not scene.color_palette:
            # Default palettes by mood
            mood_palettes = {
                "dark": ["#1a1a2e", "#16213e", "#0f3460"],
                "romantic": ["#ff6b6b", "#feca57", "#ff9ff3"],
                "action": ["#e74c3c", "#f39c12", "#2c3e50"],
                "peaceful": ["#55efc4", "#81ecec", "#74b9ff"],
                "mysterious": ["#2d3436", "#636e72", "#b2bec3"],
            }
            scene.color_palette = mood_palettes.get(scene.mood, ["#34495e", "#2c3e50", "#1a1a2e"])
        
        return scene
