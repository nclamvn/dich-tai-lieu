"""
Prompts for Action Writer Agent

Writes cinematic action lines (scene descriptions) that paint
visual pictures while remaining economical and readable.
"""

SYSTEM_PROMPT = """You are an expert screenplay action writer with extensive experience in visual storytelling. Your expertise includes:

- Writing economical, visual scene descriptions
- Creating atmosphere and mood through sparse prose
- Describing action that can be filmed
- Using present tense, active voice
- Avoiding camera directions (leave for director)
- Writing descriptions that move the story forward
- Understanding visual storytelling for Vietnamese/Asian cinema

Your action lines should be vivid, filmable, and never exceed what the camera can capture."""

ACTION_PROMPT = """Write the action lines (scene descriptions) for the following scene.

SCENE INFORMATION:
- Scene Number: {scene_number}
- Heading: {scene_heading}
- Summary: {scene_summary}
- Characters Present: {characters_present}
- Emotional Beat: {emotional_beat}
- Mood: {mood}
- Visual Notes: {visual_notes}

DIALOGUE FOR THIS SCENE:
{dialogue_preview}

RELEVANT SOURCE TEXT:
{source_excerpt}

LANGUAGE: {language}

Write the action in JSON format:

```json
{{
    "scene_number": {scene_number},
    "action_blocks": [
        {{
            "type": "scene_opening",
            "text": "Opening description that establishes the scene",
            "placement": "before_dialogue"
        }},
        {{
            "type": "character_action",
            "text": "Description of character movement/action",
            "after_dialogue_index": 0
        }},
        {{
            "type": "transition",
            "text": "How we leave this scene",
            "placement": "scene_end"
        }}
    ],
    "action_notes": "Notes about visual approach"
}}
```

ACTION WRITING GUIDELINES:

1. VISUAL ECONOMY:
   - Write only what can be seen or heard
   - One image per sentence
   - Avoid internal thoughts (show, don't tell)
   - Maximum 3-4 lines per action block

2. PRESENT TENSE, ACTIVE VOICE:
   - "Sarah walks to the window."
   - NOT "Sarah is walking to the window."

3. ATMOSPHERE:
   - Use sensory details sparingly
   - Weather, lighting, ambient sound
   - Establish mood in opening description

4. CHARACTER INTRODUCTIONS:
   - First appearance: NAME (age, brief visual description)
   - Example: SARAH (30s, sharp eyes softened by fatigue)

5. NO CAMERA DIRECTIONS:
   - NOT "We see Sarah enter"
   - NOT "The camera pans to reveal"
   - YES "Sarah enters"

6. CAPITALIZATION:
   - CHARACTER NAMES on first appearance
   - Important SOUNDS
   - Key PROPS when introduced

7. PACING:
   - Short sentences = fast pace
   - Longer descriptions = slower, contemplative

Respond ONLY with the JSON object."""

ACTION_PROMPT_VI = """Viet phan mo ta hanh dong cho canh sau.

THONG TIN CANH:
- So canh: {scene_number}
- Tieu de: {scene_heading}
- Tom tat: {scene_summary}
- Nhan vat co mat: {characters_present}
- Cam xuc chu dao: {emotional_beat}
- Tam trang: {mood}
- Ghi chu hinh anh: {visual_notes}

LOI THOAI CUA CANH:
{dialogue_preview}

VAN BAN NGUON:
{source_excerpt}

Viet mo ta hanh dong theo dinh dang JSON:

```json
{{
    "scene_number": {scene_number},
    "action_blocks": [
        {{
            "type": "scene_opening",
            "text": "Mo ta mo dau thiet lap canh",
            "placement": "before_dialogue"
        }},
        {{
            "type": "character_action",
            "text": "Mo ta hanh dong nhan vat",
            "after_dialogue_index": 0
        }}
    ],
    "action_notes": "Ghi chu ve cach tiep can hinh anh"
}}
```

HUONG DAN:

1. KINH TE HINH ANH:
   - Chi viet nhung gi co the thay hoac nghe
   - Mot hinh anh moi cau
   - Tranh suy nghi noi tam

2. THI HIEN TAI, CHU DONG:
   - "Mai di ve phia cua so."
   - KHONG "Mai dang di ve phia cua so."

3. BAU KHONG KHI:
   - Chi tiet cam giac tiet che
   - Thoi tiet, anh sang, am thanh

4. VAN HOA VIET:
   - Mo ta boi canh Viet Nam chan thuc
   - Chi tiet kien truc, phong tuc
   - Khong khi dac trung vung mien

Chi tra loi bang JSON object."""
