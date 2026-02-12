"""
Prompts for Scene Architect Agent
"""

SYSTEM_PROMPT = """You are an expert screenplay scene architect with extensive experience in film structure and visual storytelling. Your expertise includes:

- Breaking down narratives into cinematic scenes
- Understanding scene transitions and flow
- Allocating screen time effectively
- Creating compelling scene descriptions
- Understanding INT/EXT, DAY/NIGHT conventions
- Balancing dialogue scenes with action sequences

Your scene breakdowns should be professional, visual, and ready for screenplay writing."""

SCENE_BREAKDOWN_PROMPT = """Based on the following story analysis, create a detailed scene breakdown for screenplay adaptation.

STORY ANALYSIS:
{story_analysis_json}

LANGUAGE: {language}
TARGET RUNTIME: {target_runtime} minutes (approximately {target_pages} pages)

Create a comprehensive scene breakdown in the following JSON format:

```json
{{
    "total_scenes": 25,
    "total_estimated_pages": 25,
    "total_estimated_runtime_minutes": 25,

    "sequences": [
        {{
            "sequence_number": 1,
            "name": "Opening / Setup",
            "description": "Brief description of this sequence",
            "scenes": [1, 2, 3, 4]
        }}
    ],

    "scenes": [
        {{
            "scene_number": 1,
            "heading": {{
                "int_ext": "INT",
                "location": "APARTMENT - LIVING ROOM",
                "time": "DAY"
            }},
            "summary": "2-3 sentence description of what happens in this scene",
            "purpose": "What this scene accomplishes in the story (setup, conflict, revelation, etc.)",
            "characters_present": ["Character 1", "Character 2"],
            "emotional_beat": "The emotional tone/journey of this scene",
            "estimated_duration_seconds": 120,
            "page_count": 2.0,
            "visual_notes": "Key visual elements, atmosphere, or specific imagery",
            "mood": "tense|romantic|comedic|melancholic|hopeful|etc",
            "key_dialogue_hint": "Brief hint of important dialogue if any",
            "transition_from_previous": "How we get to this scene from the previous one"
        }}
    ]
}}
```

IMPORTANT GUIDELINES:

1. SCENE PACING:
   - Opening scenes: Establish world, characters, mood
   - Act 1 scenes: Setup, introduce conflict
   - Act 2a scenes: Rising action, complications
   - Midpoint scene: Major turning point (should be impactful)
   - Act 2b scenes: Escalating stakes
   - Act 3 scenes: Climax, resolution

2. SCENE VARIETY:
   - Mix dialogue-heavy and action-heavy scenes
   - Vary INT/EXT and DAY/NIGHT
   - Include establishing shots where needed
   - Consider visual contrast between scenes

3. TIMING:
   - Dialogue scenes: ~1-2 pages (1-2 minutes)
   - Action scenes: ~2-3 pages (2-3 minutes)
   - Climax: Can be longer
   - Total should roughly match target runtime

4. VIETNAMESE CONTENT:
   - Use appropriate location names
   - Consider Vietnamese cultural settings
   - Include cultural rituals/customs as visual opportunities

5. CINEMATIC CONSIDERATIONS:
   - Think about what will look good on screen
   - Note any VFX or special requirements
   - Consider practical filming locations

Respond ONLY with the JSON object, no additional text."""

SCENE_BREAKDOWN_PROMPT_VI = """Dựa trên phân tích câu chuyện sau, tạo bảng phân cảnh chi tiết cho kịch bản phim.

PHÂN TÍCH CÂU CHUYỆN:
{story_analysis_json}

NGÔN NGỮ: Tiếng Việt
THỜI LƯỢNG MỤC TIÊU: {target_runtime} phút (khoảng {target_pages} trang)

Tạo bảng phân cảnh theo định dạng JSON sau:

```json
{{
    "total_scenes": 25,
    "total_estimated_pages": 25,
    "total_estimated_runtime_minutes": 25,

    "sequences": [
        {{
            "sequence_number": 1,
            "name": "Mở đầu / Thiết lập",
            "description": "Mô tả ngắn về chuỗi cảnh này",
            "scenes": [1, 2, 3, 4]
        }}
    ],

    "scenes": [
        {{
            "scene_number": 1,
            "heading": {{
                "int_ext": "NỘI",
                "location": "CĂN HỘ - PHÒNG KHÁCH",
                "time": "NGÀY"
            }},
            "summary": "Mô tả 2-3 câu về những gì xảy ra trong cảnh này",
            "purpose": "Mục đích của cảnh trong câu chuyện",
            "characters_present": ["Nhân vật 1", "Nhân vật 2"],
            "emotional_beat": "Cảm xúc chủ đạo của cảnh",
            "estimated_duration_seconds": 120,
            "page_count": 2.0,
            "visual_notes": "Yếu tố hình ảnh quan trọng, bầu không khí",
            "mood": "căng thẳng|lãng mạn|hài hước|u buồn|hy vọng|etc",
            "key_dialogue_hint": "Gợi ý đối thoại quan trọng nếu có",
            "transition_from_previous": "Cách chuyển cảnh từ cảnh trước"
        }}
    ]
}}
```

LƯU Ý QUAN TRỌNG:

1. NHỊP CẢNH: Cân bằng giữa cảnh đối thoại và cảnh hành động
2. ĐA DẠNG: Xen kẽ NỘI/NGOẠI, NGÀY/ĐÊM
3. THỜI LƯỢNG: Tổng cộng phải khớp với mục tiêu
4. VĂN HÓA VIỆT: Bảo tồn yếu tố văn hóa, địa điểm Việt Nam
5. ĐIỆN ẢNH: Nghĩ về hình ảnh đẹp trên màn ảnh

Chỉ trả lời bằng JSON object."""
