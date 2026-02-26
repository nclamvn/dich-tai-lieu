"""
Vision Analyzer Prompts (Sprint K)
"""

VISION_SYSTEM_PROMPT = """You are an expert image analyst for a book publishing system.
Analyze images to determine their subject, content, quality, and best placement in a book.
Return structured JSON only — no commentary."""

VISION_ANALYSIS_PROMPT = """Analyze this image for use in an illustrated book.

Return a JSON object with these fields:
{{
    "subject": "Brief subject (3-8 words). Be specific — e.g., 'Battle of Dien Bien Phu, 1954' not 'a battle scene'",
    "description": "Detailed description (2-3 sentences)",
    "keywords": ["keyword1", "keyword2", ...],  // 5-10 relevant keywords for matching to book content
    "category": "photo|illustration|diagram|chart|map|screenshot|art|infographic|other",
    "dominant_colors": ["color1", "color2", "color3"],
    "era_or_context": "Time period or context if identifiable, null if not",
    "mood": "Visual mood: dramatic, serene, clinical, playful, educational, etc.",
    "text_in_image": "Any visible text in the image, null if none",
    "quality_score": 0.0-1.0,  // Based on clarity, composition, relevance
    "suggested_layout": "full_page|inline|float_top|gallery|margin",
    "suggested_size": "small|medium|large|full"
}}

Quality scoring guide:
- 0.9-1.0: Professional, sharp, compelling — ideal for full-page display
- 0.7-0.8: Good quality, clear subject — suitable for inline or float
- 0.4-0.6: Acceptable, may need specific placement
- 0.0-0.3: Low quality, blur, or irrelevant — consider margin or skip

Layout suggestions:
- full_page: Stunning, high-impact images (landscape, high quality)
- inline: Standard content illustrations
- float_top: Context-setting images at section start
- gallery: Similar images that work together
- margin: Small supplementary images

Return ONLY the JSON object."""

GENRE_DETECTION_PROMPT = """Given these image descriptions from a book's image collection, determine the most likely book genre.

Image descriptions:
{descriptions}

Choose ONE genre from: fiction, non_fiction, children, technical, cookbook, travel, photography, memoir, academic

Return JSON:
{{
    "genre": "chosen_genre",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}"""
