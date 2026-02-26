"""
Prompts for Action Writer Agent

Writes cinematic action lines (scene descriptions) that paint
visual pictures while remaining economical and readable.
"""

SYSTEM_PROMPT = """You are an expert screenplay action writer for shooting scripts with extensive experience in visual storytelling and production. Your expertise includes:

- Writing detailed, visual scene descriptions for production use
- Creating atmosphere and mood through vivid, sensory prose
- Including camera directions when they ARE the story beat
- Describing character blocking — physical positioning and movement through space
- Writing transitions between scenes (CUT TO, DISSOLVE TO, SMASH CUT TO)
- Noting production-relevant details: key PROPS, lighting mood, essential SFX
- Using present tense, active voice
- Understanding visual storytelling for Vietnamese/Asian cinema

Your action lines should be vivid, filmable, and detailed enough for a director on set."""

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
            "text": "Opening description that establishes the scene — setting, atmosphere, lighting",
            "placement": "before_dialogue"
        }},
        {{
            "type": "character_action",
            "text": "Description of character movement, blocking, physical positioning",
            "after_dialogue_index": 0
        }},
        {{
            "type": "camera_direction",
            "text": "CLOSE ON the letter in her hand — the ink still wet.",
            "after_dialogue_index": 3
        }},
        {{
            "type": "character_action",
            "text": "Another action beat between dialogue exchanges",
            "after_dialogue_index": 5
        }},
        {{
            "type": "transition",
            "text": "CUT TO:",
            "placement": "scene_end"
        }}
    ],
    "action_notes": "Notes about visual approach"
}}
```

ACTION WRITING GUIDELINES:

1. DETAIL AND DENSITY:
   - Write 4-8 action blocks per scene, each 2-5 lines
   - Paint a complete visual picture — this is a shooting script, not a spec
   - Include character blocking: where characters stand, sit, move through space

2. PRESENT TENSE, ACTIVE VOICE:
   - "Sarah walks to the window."
   - NOT "Sarah is walking to the window."

3. ATMOSPHERE AND PRODUCTION NOTES:
   - Describe lighting mood: "Harsh fluorescent light bleaches the room."
   - Note essential ambient SOUND: "The distant HUM of cicadas fills the silence."
   - Weather and environment when relevant to the scene

4. CAMERA DIRECTIONS (use sparingly — only when the shot IS the story beat):
   - CLOSE ON — for critical details the audience must see
   - WIDE SHOT — for establishing geography or isolation
   - INSERT — for a prop, document, or object
   - POV — when we see through a character's eyes
   - ANGLE ON — to shift focus within a scene

5. TRANSITIONS (at end of every scene):
   - CUT TO: — standard scene change
   - DISSOLVE TO: — passage of time or thematic link
   - SMASH CUT TO: — abrupt contrast for shock
   - MATCH CUT: — visual or thematic continuity between scenes

6. CHARACTER INTRODUCTIONS:
   - First appearance: NAME (age, brief visual description)
   - Example: SARAH (30s, sharp eyes softened by fatigue)

7. CAPITALIZATION:
   - CHARACTER NAMES on first appearance
   - Important SOUNDS
   - Key PROPS when introduced (a REVOLVER, a LETTER, a PHOTOGRAPH)

8. PACING:
   - Short sentences = fast pace
   - Longer descriptions = slower, contemplative

Respond ONLY with the JSON object."""

ACTION_PROMPT_VI = """Viết phần mô tả hành động (shooting script) cho cảnh sau.

THÔNG TIN CẢNH:
- Số cảnh: {scene_number}
- Tiêu đề: {scene_heading}
- Tóm tắt: {scene_summary}
- Nhân vật có mặt: {characters_present}
- Cảm xúc chủ đạo: {emotional_beat}
- Tâm trạng: {mood}
- Ghi chú hình ảnh: {visual_notes}

LỜI THOẠI CỦA CẢNH:
{dialogue_preview}

VĂN BẢN NGUỒN:
{source_excerpt}

Viết mô tả hành động theo định dạng JSON:

```json
{{
    "scene_number": {scene_number},
    "action_blocks": [
        {{
            "type": "scene_opening",
            "text": "Mô tả mở đầu thiết lập cảnh — bối cảnh, ánh sáng, không khí",
            "placement": "before_dialogue"
        }},
        {{
            "type": "character_action",
            "text": "Mô tả hành động, vị trí, di chuyển của nhân vật",
            "after_dialogue_index": 0
        }},
        {{
            "type": "camera_direction",
            "text": "CẬN CẢNH bức thư trong tay — mực vẫn còn ướt.",
            "after_dialogue_index": 3
        }},
        {{
            "type": "transition",
            "text": "CUT TO:",
            "placement": "scene_end"
        }}
    ],
    "action_notes": "Ghi chú về cách tiếp cận hình ảnh"
}}
```

HƯỚNG DẪN:

1. CHI TIẾT VÀ MẬT ĐỘ:
   - Viết 4-8 khối hành động mỗi cảnh, mỗi khối 2-5 dòng
   - Đây là kịch bản quay (shooting script), cần chi tiết đầy đủ
   - Mô tả vị trí nhân vật: đứng đâu, ngồi đâu, di chuyển thế nào

2. THÌ HIỆN TẠI, CHỦ ĐỘNG:
   - "Mai đi về phía cửa sổ."
   - KHÔNG "Mai đang đi về phía cửa sổ."

3. BẦU KHÔNG KHÍ VÀ SẢN XUẤT:
   - Mô tả ánh sáng: "Ánh đèn huỳnh quang tái nhợt phủ căn phòng."
   - ÂM THANH môi trường: "Tiếng VE KÊU rền rĩ trong im lặng."
   - ĐẠO CỤ quan trọng viết HOA

4. HƯỚNG MÁY QUAY (chỉ khi cần thiết cho câu chuyện):
   - CẬN CẢNH — chi tiết quan trọng
   - TOÀN CẢNH — thiết lập không gian
   - INSERT — đạo cụ, tài liệu
   - GÓC NHÌN — nhìn qua mắt nhân vật

5. CHUYỂN CẢNH (cuối mỗi cảnh):
   - CUT TO: — chuyển cảnh thông thường
   - DISSOLVE TO: — chuyển thời gian
   - SMASH CUT TO: — tương phản đột ngột

6. VĂN HÓA VIỆT:
   - Mô tả bối cảnh Việt Nam chân thực
   - Chi tiết kiến trúc, phong tục
   - Không khí đặc trưng vùng miền

Chỉ trả lời bằng JSON object."""
