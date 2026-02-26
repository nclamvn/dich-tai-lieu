"""
Prompts for Dialogue Writer Agent

Converts prose narrative into cinematic dialogue with proper
character voice, subtext, and parentheticals.
"""

SYSTEM_PROMPT = """You are an expert screenplay dialogue writer with decades of experience in Hollywood and international cinema. Your expertise includes:

- Converting prose and narrative into natural, cinematic dialogue
- Creating distinct character voices that remain consistent
- Writing subtext - what characters mean vs. what they say
- Adding parentheticals for acting direction
- Balancing exposition with natural conversation
- Writing dialogue that advances plot and reveals character
- Understanding Vietnamese and Asian dialogue conventions

Your dialogue should feel natural, reveal character, and be speakable by actors."""

DIALOGUE_PROMPT = """Write the dialogue for the following scene based on the source material.

SCENE INFORMATION:
- Scene Number: {scene_number}
- Heading: {scene_heading}
- Summary: {scene_summary}
- Characters Present: {characters_present}
- Emotional Beat: {emotional_beat}
- Purpose: {scene_purpose}

CHARACTERS IN THIS SCENE:
{character_profiles}

RELEVANT SOURCE TEXT:
{source_excerpt}

LANGUAGE: {language}

Write the dialogue in JSON format:

```json
{{
    "scene_number": {scene_number},
    "dialogue_blocks": [
        {{
            "character": "CHARACTER NAME",
            "parenthetical": "(optional acting direction)",
            "dialogue": "The spoken line",
            "subtext_note": "What the character really means (for writer's reference)"
        }}
    ],
    "dialogue_notes": "Notes about the overall dialogue approach for this scene"
}}
```

DIALOGUE GUIDELINES:

1. VOLUME AND DENSITY:
   - Write 10-25 dialogue blocks per scene depending on scene duration
   - Each dialogue exchange should advance the story or reveal character — no filler
   - Include character reaction beats: (beat), (pause), physical actions between exchanges

2. CHARACTER VOICE:
   - Each character should sound distinct based on their profile
   - Consider age, education, background, personality
   - Maintain consistency with previous scenes

3. SOURCE FIDELITY (for literary adaptations):
   - Preserve the original author's dialogue and voice wherever the source text provides it
   - Adapt prose narration into spoken dialogue, but keep existing dialogue intact
   - Capture the rhythm and vocabulary of the source material

4. SUBTEXT:
   - Characters rarely say exactly what they mean
   - Use implication, deflection, avoidance
   - Let silence speak when appropriate

5. PARENTHETICALS:
   - Use for essential acting direction and reaction beats
   - Common: (beat), (quietly), (to NAME), (continuing), (under his breath)
   - Include physical actions: (picks up the glass), (turns away), (standing)

6. NATURAL SPEECH:
   - Use contractions
   - Allow interruptions with "--"
   - Include false starts, hesitations when appropriate
   - Avoid on-the-nose dialogue

7. EXPOSITION:
   - Hide exposition in conflict
   - Never have characters tell each other what they both know
   - Use questions to reveal information naturally

8. VIETNAMESE DIALOGUE (if applicable):
   - Use appropriate honorifics (anh, chi, em, ong, ba)
   - Consider generational speech patterns
   - Include cultural expressions naturally

Respond ONLY with the JSON object."""

DIALOGUE_PROMPT_VI = """Viet loi thoai cho canh sau dua tren tai lieu nguon.

THONG TIN CANH:
- So canh: {scene_number}
- Tieu de: {scene_heading}
- Tom tat: {scene_summary}
- Nhan vat co mat: {characters_present}
- Cam xuc chu dao: {emotional_beat}
- Muc dich: {scene_purpose}

NHAN VAT TRONG CANH:
{character_profiles}

VAN BAN NGUON LIEN QUAN:
{source_excerpt}

Viet loi thoai theo dinh dang JSON:

```json
{{
    "scene_number": {scene_number},
    "dialogue_blocks": [
        {{
            "character": "TEN NHAN VAT",
            "parenthetical": "(huong dan dien xuat tuy chon)",
            "dialogue": "Cau thoai",
            "subtext_note": "Y nghia thuc su cua nhan vat"
        }}
    ],
    "dialogue_notes": "Ghi chu ve cach tiep can loi thoai cho canh nay"
}}
```

HƯỚNG DẪN LỜI THOẠI:

1. SỐ LƯỢNG VÀ MẬT ĐỘ:
   - Viết 10-25 khối thoại mỗi cảnh tùy thời lượng
   - Mỗi câu thoại phải đẩy câu chuyện hoặc bộc lộ nhân vật — không có thoại thừa
   - Bao gồm phản ứng nhân vật: (nhịp), (dừng lại), hành động thể chất giữa các trao đổi

2. GIỌNG NHÂN VẬT:
   - Mỗi nhân vật phải có giọng riêng biệt
   - Sử dụng đại từ xưng hô phù hợp (anh/chị/em/ông/bà/con/cháu)
   - Phản ánh tuổi tác, học vấn, xuất thân

3. TRUNG THÀNH VỚI NGUỒN (cho chuyển thể văn học):
   - Giữ nguyên lời thoại và giọng văn gốc của tác giả khi văn bản nguồn cung cấp
   - Chuyển thể lời kể thành lời thoại, nhưng giữ nguyên thoại sẵn có
   - Nắm bắt nhịp điệu và từ vựng của tác phẩm gốc

4. NGÔN NGỮ TỰ NHIÊN:
   - Sử dụng từ ngữ đời thường
   - Cho phép ngắt lời với "--"
   - Bao gồm ngập ngừng, do dự khi cần

5. VĂN HÓA VIỆT:
   - Thể hiện lễ nghi, tôn ti trật tự
   - Sử dụng thành ngữ, tục ngữ tự nhiên
   - Phản ánh mối quan hệ qua cách xưng hô

Chỉ trả lời bằng JSON object."""
