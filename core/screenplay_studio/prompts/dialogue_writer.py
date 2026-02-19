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

1. CHARACTER VOICE:
   - Each character should sound distinct based on their profile
   - Consider age, education, background, personality
   - Maintain consistency with previous scenes

2. SUBTEXT:
   - Characters rarely say exactly what they mean
   - Use implication, deflection, avoidance
   - Let silence speak when appropriate

3. PARENTHETICALS:
   - Use sparingly, only when necessary
   - Common: (beat), (quietly), (to NAME), (continuing)
   - Avoid over-directing actors

4. NATURAL SPEECH:
   - Use contractions
   - Allow interruptions with "--"
   - Include false starts, hesitations when appropriate
   - Avoid on-the-nose dialogue

5. EXPOSITION:
   - Hide exposition in conflict
   - Never have characters tell each other what they both know
   - Use questions to reveal information naturally

6. VIETNAMESE DIALOGUE (if applicable):
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

HUONG DAN LOI THOAI:

1. GIONG NHAN VAT:
   - Moi nhan vat phai co giong rieng biet
   - Su dung dai tu xung ho phu hop (anh/chi/em/ong/ba/con/chau)
   - Phan anh tuoi tac, hoc van, xuat than

2. NGON NGU TU NHIEN:
   - Su dung tu ngu doi thuong
   - Cho phep ngat loi voi "--"
   - Bao gom ngap ngung, do du khi can

3. VAN HOA VIET:
   - The hien le nghi, ton ti trat tu
   - Su dung thanh ngu, tuc ngu tu nhien
   - Phan anh moi quan he qua cach xung ho

Chi tra loi bang JSON object."""
