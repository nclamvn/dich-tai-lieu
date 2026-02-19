"""
Prompts for Visual Designer Agent

Creates visual style guides:
- Color palettes
- Mood references
- Character visual descriptions
- Location aesthetics
"""

SYSTEM_PROMPT = """You are an expert visual designer and art director for film with extensive experience in:

- Color theory and cinematic color grading
- Production design and set aesthetics
- Costume and character visual design
- Mood boards and visual references
- Vietnamese and Asian visual aesthetics
- Translating emotional beats to visual language

Your visual guides should be specific, evocative, and practical for both AI image generation and human production teams."""

VISUAL_GUIDE_PROMPT = """Create a visual style guide for the following scene.

SCENE INFORMATION:
- Scene Number: {scene_number}
- Heading: {scene_heading}
- Summary: {scene_summary}
- Emotional Beat: {emotional_beat}
- Mood: {mood}
- Time of Day: {time_of_day}
- Location Type: {location_type}

CHARACTERS IN SCENE:
{character_descriptions}

SHOT LIST SUMMARY:
{shot_list_summary}

OVERALL FILM STYLE:
- Genre: {genre}
- Tone: {tone}
- Era/Period: {time_period}
- Visual References: {reference_films}

Create a visual guide in JSON format:

```json
{{
    "scene_number": {scene_number},

    "color_palette": {{
        "primary": "#hexcode - Description of primary color and its emotional purpose",
        "secondary": "#hexcode - Description",
        "accent": "#hexcode - Description",
        "shadows": "#hexcode - Shadow tone",
        "highlights": "#hexcode - Highlight tone",
        "overall_temperature": "warm|cool|neutral",
        "saturation": "high|medium|low|desaturated",
        "contrast": "high|medium|low"
    }},

    "lighting_design": {{
        "key_light": "Description of main light source",
        "fill_light": "Description of fill",
        "practical_lights": ["List of visible light sources in scene"],
        "time_of_day_notes": "How time affects lighting",
        "mood_lighting": "Description of overall lighting mood"
    }},

    "location_design": {{
        "architecture_style": "Description of architectural elements",
        "key_set_pieces": ["Important props or furniture"],
        "textures": ["Dominant textures in the scene"],
        "depth_elements": ["Foreground, midground, background elements"],
        "environmental_storytelling": "What the environment tells us about characters/story"
    }},

    "character_visuals": [
        {{
            "character_name": "Name",
            "costume_description": "What they're wearing",
            "color_association": "#hexcode - Character's color theme",
            "visual_motifs": ["Recurring visual elements for this character"],
            "this_scene_notes": "Specific notes for this scene"
        }}
    ],

    "atmosphere": {{
        "weather": "Clear|Cloudy|Rain|Fog|etc",
        "particles": "Dust|Rain|Snow|Smoke|None",
        "haze": "None|Light|Medium|Heavy",
        "ambient_elements": ["Background movement, environmental details"]
    }},

    "visual_references": [
        {{
            "reference_type": "film|painting|photo",
            "title": "Name of reference",
            "why_relevant": "What to take from this reference"
        }}
    ],

    "ai_generation_notes": "Specific notes for AI image/video generation to ensure consistency"
}}
```

VISUAL DESIGN GUIDELINES:

1. COLOR PSYCHOLOGY:
   - Red: passion, danger, urgency
   - Blue: calm, sadness, coldness
   - Green: nature, envy, growth
   - Yellow: hope, warning, energy
   - Orange: warmth, comfort, creativity

2. LIGHTING MOOD:
   - High key: comedy, romance, innocence
   - Low key: drama, thriller, mystery
   - Silhouette: mystery, anonymity
   - Practical: realism, intimacy

3. VIETNAMESE VISUAL ELEMENTS:
   - Tropical greens, humid atmospheres
   - Colonial architecture mixed with modern
   - Street life, motorbikes, vendors
   - Temple and pagoda aesthetics
   - Lanterns, neon signs, night markets

4. CONSISTENCY:
   - Maintain character color associations
   - Progress color temperature with story arc
   - Use visual motifs for thematic resonance

Respond ONLY with the JSON object."""
