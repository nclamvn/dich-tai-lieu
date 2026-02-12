"""
Prompts for Cinematographer Agent

Designs shot lists with professional camera work:
- Shot types (wide, medium, close-up, etc.)
- Camera angles and movements
- Lens choices
- Lighting notes
"""

SYSTEM_PROMPT = """You are an expert cinematographer and director of photography with decades of experience in feature films, commercials, and international cinema. Your expertise includes:

- Shot composition and visual storytelling
- Camera movement design (dolly, crane, steadicam, handheld)
- Lens selection for emotional impact
- Lighting design and mood creation
- Shot sequencing and visual rhythm
- Vietnamese and Asian cinema aesthetics

Your shot lists should be practical, emotionally resonant, and serve the story."""

SHOT_LIST_PROMPT = """Create a detailed shot list for the following scene.

SCENE INFORMATION:
- Scene Number: {scene_number}
- Heading: {scene_heading}
- Summary: {scene_summary}
- Emotional Beat: {emotional_beat}
- Mood: {mood}
- Characters: {characters_present}

SCENE CONTENT:
{scene_content}

VISUAL STYLE GUIDE:
- Genre: {genre}
- Tone: {tone}
- Reference Films: {reference_films}

Create a shot list in JSON format:

```json
{{
    "scene_number": {scene_number},
    "visual_approach": "Brief description of overall visual approach for this scene",

    "shots": [
        {{
            "shot_number": "1A",
            "shot_type": "wide|full|medium_wide|medium|medium_close|close_up|extreme_close_up|pov|over_shoulder|two_shot|insert",
            "description": "What we see in this shot",
            "subject": "Main subject of the shot",

            "camera": {{
                "angle": "eye_level|high|low|dutch|birds_eye|worms_eye",
                "movement": "static|pan_left|pan_right|tilt_up|tilt_down|dolly_in|dolly_out|tracking|crane_up|crane_down|handheld|steadicam|zoom_in|zoom_out",
                "lens": "24mm|35mm|50mm|85mm|100mm",
                "focus": "deep|shallow|rack_focus"
            }},

            "duration_seconds": 3,

            "lighting": {{
                "type": "natural|artificial|mixed",
                "mood": "high_key|low_key|silhouette|backlit|soft|harsh",
                "direction": "front|side|back|top|bottom"
            }},

            "composition_notes": "Rule of thirds, leading lines, framing notes",
            "action_in_shot": "What happens during this shot",
            "audio_notes": "Dialogue, sound effects, or music cues",
            "transition_to_next": "cut|dissolve|fade|wipe|match_cut"
        }}
    ],

    "scene_coverage_notes": "Notes on how these shots will cut together",
    "estimated_total_duration_seconds": 60
}}
```

CINEMATOGRAPHY GUIDELINES:

1. SHOT PROGRESSION:
   - Start wide to establish location
   - Move closer as tension/intimacy increases
   - Use close-ups for emotional peaks
   - Return to wider shots for transitions

2. CAMERA MOVEMENT:
   - Static = stability, contemplation
   - Dolly/tracking = following character journey
   - Handheld = urgency, documentary feel
   - Crane = epic, emotional weight
   - Match movement to emotional beats

3. LENS CHOICES:
   - Wide (24-35mm) = environment, isolation, distortion
   - Normal (50mm) = natural, documentary
   - Telephoto (85-100mm) = intimacy, compression, voyeuristic

4. COVERAGE:
   - Ensure enough angles for editing flexibility
   - Include reaction shots
   - Plan for dialogue coverage (over-shoulders, singles)

Respond ONLY with the JSON object."""

SHOT_LIST_PROMPT_VI = """Tao bang shot list chi tiet cho canh sau.

THONG TIN CANH:
- So canh: {scene_number}
- Tieu de: {scene_heading}
- Tom tat: {scene_summary}
- Cam xuc: {emotional_beat}
- Tam trang: {mood}
- Nhan vat: {characters_present}

NOI DUNG CANH:
{scene_content}

PHONG CACH HINH ANH:
- The loai: {genre}
- Giong dieu: {tone}
- Phim tham khao: {reference_films}

Tao shot list theo dinh dang JSON:

```json
{{
    "scene_number": {scene_number},
    "visual_approach": "Mo ta ngan ve cach tiep can hinh anh cho canh nay",

    "shots": [
        {{
            "shot_number": "1A",
            "shot_type": "wide|medium|close_up|...",
            "description": "Nhung gi ta thay trong shot nay",
            "subject": "Chu the chinh",

            "camera": {{
                "angle": "eye_level|high|low|dutch",
                "movement": "static|pan|dolly|tracking|handheld",
                "lens": "35mm|50mm|85mm",
                "focus": "deep|shallow|rack_focus"
            }},

            "duration_seconds": 3,

            "lighting": {{
                "type": "natural|artificial|mixed",
                "mood": "high_key|low_key|backlit",
                "direction": "front|side|back"
            }},

            "composition_notes": "Ghi chu bo cuc",
            "action_in_shot": "Hanh dong trong shot",
            "transition_to_next": "cut|dissolve|fade"
        }}
    ],

    "scene_coverage_notes": "Ghi chu ve cach cac shot ghep noi",
    "estimated_total_duration_seconds": 60
}}
```

Chi tra loi bang JSON object."""
