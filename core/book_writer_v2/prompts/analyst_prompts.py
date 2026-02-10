"""
Analyst Agent Prompts
"""

ANALYST_SYSTEM_PROMPT = """You are an expert book analyst and publishing consultant.
Your role is to analyze book topics and create comprehensive analysis documents.

You understand:
- Target audience profiling
- Competitive landscape analysis
- Content structure recommendations
- Tone and style guidelines

Always output structured JSON that can be parsed programmatically."""

ANALYST_PROMPT = """Analyze this book project and provide a comprehensive analysis.

BOOK PROJECT:
- Title: {title}
- Description: {description}
- Target Pages: {target_pages}
- Genre: {genre}
- Target Audience: {audience}

Provide your analysis in this JSON format:

```json
{{
    "topic_summary": "2-3 sentence summary of what this book is about",
    "target_audience": "Primary target audience description",
    "audience_profile": {{
        "demographics": "Age, profession, education level",
        "knowledge_level": "Beginner/Intermediate/Advanced",
        "pain_points": ["What problems they face"],
        "goals": ["What they want to achieve"]
    }},
    "key_themes": [
        "Theme 1",
        "Theme 2",
        "Theme 3",
        "Theme 4",
        "Theme 5"
    ],
    "key_messages": [
        "Core message 1",
        "Core message 2",
        "Core message 3"
    ],
    "unique_value": "What makes this book unique and valuable",
    "competitive_landscape": [
        {{"title": "Competing Book 1", "gap": "What this book does differently"}},
        {{"title": "Competing Book 2", "gap": "What this book does differently"}}
    ],
    "recommended_structure": {{
        "num_parts": 3,
        "chapters_per_part": 4,
        "suggested_parts": [
            "Part 1: Foundations",
            "Part 2: Core Concepts",
            "Part 3: Applications"
        ]
    }},
    "tone_and_style": "Recommended writing style (e.g., 'Academic but accessible, using real-world examples')",
    "content_warnings": ["Any sensitive topics to handle carefully"],
    "research_notes": "Suggested research areas or sources"
}}
```

Be thorough and specific. This analysis will guide the entire book creation process."""
