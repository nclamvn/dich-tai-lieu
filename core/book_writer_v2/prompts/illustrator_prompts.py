"""
Illustrator Agent Prompts (Sprint K)
"""

MATCH_PROMPT = """You are matching an image to book chapter content.

Image subject: {image_subject}
Image description: {image_description}
Image keywords: {image_keywords}
Image category: {image_category}

Chapter title: {chapter_title}
Chapter topics: {chapter_topics}
Chapter keywords: {chapter_keywords}

Rate the relevance of this image to this chapter on a scale of 0.0 to 1.0.
Consider subject matter overlap, thematic connection, era/period alignment,
and how well the image could illustrate concepts discussed in the chapter.

Return JSON only:
{{
    "relevance": 0.0-1.0,
    "reasoning": "Brief explanation",
    "suggested_paragraph": 0
}}"""

CAPTION_PROMPT = """Generate a caption for this image in a {genre} book.

Image: {image_description}
Chapter context: {chapter_title}
Section context: {section_title}

Style guidelines:
- Fiction: evocative, atmospheric captions
- Non-fiction: informative, descriptive captions
- Children's: simple, engaging captions
- Technical: precise, figure-reference style (e.g., "Figure 1.2: ...")
- Cookbook: ingredient/dish focused
- Travel: location and atmosphere focused

Return a single caption string (1-2 sentences, no quotes around it)."""
