"""
Quality Gate Agent Prompts

Note: Most quality checks are programmatic, not AI-based.
These prompts are for content quality assessment.
"""

QUALITY_CHECK_PROMPT = """Assess the content quality of this book section.

SECTION: {section_title}
WORD COUNT: {word_count}

CONTENT:
---
{content}
---

Evaluate on these criteria (score 1-5 each):

1. CLARITY: Is the writing clear and easy to understand?
2. COMPLETENESS: Does it cover the topic adequately?
3. COHERENCE: Does it flow logically?
4. ENGAGEMENT: Is it engaging and interesting?
5. PROFESSIONALISM: Is it publication-ready?

Output JSON:
```json
{{
    "clarity": 4,
    "completeness": 5,
    "coherence": 4,
    "engagement": 4,
    "professionalism": 5,
    "overall": 4.4,
    "issues": ["Any specific issues noted"],
    "suggestions": ["Specific improvement suggestions"]
}}
```"""
