"""
Prompts for Story Analyst Agent
"""

SYSTEM_PROMPT = """You are an expert story analyst and screenplay development consultant with decades of experience in Hollywood and international film industries. Your expertise includes:

- Story structure analysis (three-act, hero's journey, five-act, etc.)
- Character development and arc identification
- Theme and subtext extraction
- Genre classification
- Pacing and dramatic tension analysis
- Cultural adaptation (especially Vietnamese/Asian narratives)

Your analysis should be thorough, professional, and actionable for screenplay adaptation."""

ANALYSIS_PROMPT = """Analyze the following story/novel for screenplay adaptation.

STORY TEXT:
{source_text}

LANGUAGE: {language}

Provide a comprehensive analysis in the following JSON format:

```json
{{
    "title": "Original or suggested title",
    "logline": "One compelling sentence that captures the story's essence",
    "synopsis": "2-3 paragraph summary of the story",

    "genre": "Primary genre",
    "sub_genres": ["secondary genre 1", "secondary genre 2"],
    "tone": "Overall tone (e.g., dark, hopeful, comedic, melancholic)",
    "themes": ["theme 1", "theme 2", "theme 3"],

    "setting": "Primary setting description",
    "time_period": "When the story takes place",
    "locations": ["location 1", "location 2"],

    "structure_type": "three_act|heroes_journey|five_act|non_linear",
    "act_breakdown": {{
        "act_1": "Setup description (roughly what happens)",
        "act_2": "Confrontation description",
        "act_3": "Resolution description"
    }},

    "characters": [
        {{
            "name": "Character name",
            "description": "Brief description",
            "role": "protagonist|antagonist|supporting|minor",
            "arc": "Character's transformation journey",
            "traits": ["trait 1", "trait 2"],
            "relationships": {{
                "Other Character": "relationship type"
            }},
            "visual_description": "Physical appearance for casting/AI generation",
            "age_range": "20s, 30s, etc.",
            "gender": "male|female|non-binary|other"
        }}
    ],

    "inciting_incident": "The event that starts the main conflict",
    "midpoint": "The major turning point in the middle",
    "climax": "The peak of dramatic tension",
    "resolution": "How the story concludes",

    "key_scenes": [
        "Brief description of scene 1",
        "Brief description of scene 2"
    ],

    "estimated_runtime_minutes": 90,
    "estimated_scenes": 25,
    "estimated_pages": 90,

    "cultural_notes": ["Note 1 for cultural adaptation"],

    "adaptation_recommendations": [
        "Recommendation 1 for screenplay adaptation",
        "Recommendation 2"
    ]
}}
```

IMPORTANT GUIDELINES:
1. Be thorough but concise
2. Identify ALL named characters, even minor ones
3. For Vietnamese content, preserve cultural nuances and suggest how to convey them visually
4. Estimate realistic runtime based on story complexity
5. Key scenes should be the most dramatic/visual moments
6. Consider what will translate well to screen vs. what needs reimagining

Respond ONLY with the JSON object, no additional text."""

ANALYSIS_PROMPT_VI = """Phân tích câu chuyện/tiểu thuyết sau để chuyển thể thành kịch bản phim.

NỘI DUNG:
{source_text}

NGÔN NGỮ: Tiếng Việt

Cung cấp phân tích chi tiết theo định dạng JSON sau:

```json
{{
    "title": "Tên gốc hoặc tên đề xuất",
    "logline": "Một câu hấp dẫn tóm tắt tinh thần câu chuyện",
    "synopsis": "Tóm tắt 2-3 đoạn văn",

    "genre": "Thể loại chính",
    "sub_genres": ["thể loại phụ 1", "thể loại phụ 2"],
    "tone": "Giọng điệu tổng thể (u ám, hy vọng, hài hước, u sầu)",
    "themes": ["chủ đề 1", "chủ đề 2"],

    "setting": "Mô tả bối cảnh chính",
    "time_period": "Thời điểm câu chuyện diễn ra",
    "locations": ["địa điểm 1", "địa điểm 2"],

    "structure_type": "three_act|heroes_journey|five_act|non_linear",
    "act_breakdown": {{
        "act_1": "Mô tả phần mở đầu",
        "act_2": "Mô tả phần phát triển xung đột",
        "act_3": "Mô tả phần kết"
    }},

    "characters": [
        {{
            "name": "Tên nhân vật",
            "description": "Mô tả ngắn",
            "role": "protagonist|antagonist|supporting|minor",
            "arc": "Hành trình chuyển đổi của nhân vật",
            "traits": ["đặc điểm 1", "đặc điểm 2"],
            "relationships": {{
                "Nhân vật khác": "mối quan hệ"
            }},
            "visual_description": "Mô tả ngoại hình cho casting/AI",
            "age_range": "20s, 30s, v.v.",
            "gender": "nam|nữ|khác"
        }}
    ],

    "inciting_incident": "Sự kiện khởi đầu xung đột chính",
    "midpoint": "Điểm chuyển lớn giữa truyện",
    "climax": "Đỉnh điểm kịch tính",
    "resolution": "Cách câu chuyện kết thúc",

    "key_scenes": [
        "Mô tả ngắn cảnh quan trọng 1",
        "Mô tả ngắn cảnh quan trọng 2"
    ],

    "estimated_runtime_minutes": 90,
    "estimated_scenes": 25,
    "estimated_pages": 90,

    "cultural_notes": [
        "Ghi chú văn hóa Việt Nam cần bảo tồn"
    ],

    "adaptation_recommendations": [
        "Đề xuất cho việc chuyển thể"
    ]
}}
```

HƯỚNG DẪN QUAN TRỌNG:
1. Chi tiết nhưng súc tích
2. Nhận diện TẤT CẢ nhân vật có tên
3. Bảo tồn các yếu tố văn hóa Việt Nam và đề xuất cách thể hiện trực quan
4. Ước tính thời lượng hợp lý dựa trên độ phức tạp
5. Các cảnh quan trọng nên là những khoảnh khắc kịch tính/hình ảnh nhất

Chỉ trả lời bằng JSON object, không thêm text khác."""
