"""
Prompt Templates for Author Engine (Phase 4.1 MVP)

Provides prompt-based style control without corpus learning.
Supports co-writing, rewriting, and expansion modes.
"""

# ==============================================================================
# CO-WRITING PROMPTS
# ==============================================================================

CO_WRITE_PROMPT = """You are a professional co-writer helping an author continue their manuscript.

**Context (what has been written so far):**
{context}

**Style instruction:** {style_instruction}

**User's additional instruction:** {instruction}

**Task:** Write the next paragraph that naturally continues from the context above. The paragraph should:
1. Flow smoothly from the previous content
2. Match the established tone and style
3. Move the narrative/argument forward
4. Be approximately {target_length} words

Write only the next paragraph, nothing else."""

CO_WRITE_VARIATION_PROMPT = """You are a professional co-writer helping an author continue their manuscript.

**Context (what has been written so far):**
{context}

**Style instruction:** {style_instruction}

**User's additional instruction:** {instruction}

**Task:** Generate {n_variations} different variations for the next paragraph. Each variation should:
1. Continue naturally from the context
2. Match the style instruction
3. Offer a different approach or angle
4. Be approximately {target_length} words each

Format your response as:

VARIATION A:
[First paragraph variation]

VARIATION B:
[Second paragraph variation]

VARIATION C:
[Third paragraph variation]

{extra_variations}"""


# ==============================================================================
# REWRITING PROMPTS
# ==============================================================================

REWRITE_PROMPT = """You are a professional editor helping improve a manuscript.

**Original text:**
{original_text}

**Style instruction:** {style_instruction}

**Improvements requested:**
{improvements}

**Task:** Rewrite the text above incorporating the improvements while:
1. Maintaining the core message and information
2. Matching the style instruction
3. Improving clarity, flow, and impact
4. Keeping approximately the same length

Write only the rewritten text, nothing else."""

REWRITE_DEFAULT_IMPROVEMENTS = """- Improve clarity and readability
- Strengthen word choice and phrasing
- Enhance flow and coherence
- Fix any grammar or style issues"""


# ==============================================================================
# EXPANSION PROMPTS
# ==============================================================================

EXPAND_PROMPT = """You are a professional co-writer helping develop ideas into full content.

**Brief idea/outline:**
{idea}

**Style instruction:** {style_instruction}

**Target length:** Approximately {target_length} words

**Additional context:** {context}

**Task:** Expand the brief idea above into a fully developed {content_type}. The expansion should:
1. Elaborate on all key points
2. Add relevant details, examples, or arguments
3. Maintain coherent structure and flow
4. Match the style instruction
5. Reach approximately the target length

Write the expanded content, nothing else."""


# ==============================================================================
# CHAPTER/SECTION GENERATION PROMPTS
# ==============================================================================

CHAPTER_FROM_OUTLINE_PROMPT = """You are a professional ghostwriter helping write a book chapter.

**Book context:**
Title: {book_title}
Genre: {genre}
Style: {style_instruction}

**Previous chapters summary:**
{previous_summary}

**This chapter outline:**
{chapter_outline}

**Target length:** Approximately {target_length} words

**Task:** Write the complete chapter based on the outline above. The chapter should:
1. Follow the outline's structure and key points
2. Connect smoothly with previous chapters
3. Match the book's style and tone
4. Include engaging narrative/exposition as appropriate for the genre
5. Reach approximately the target length

Write the complete chapter, nothing else."""


# ==============================================================================
# BRAINSTORMING PROMPTS
# ==============================================================================

BRAINSTORM_PROMPT = """You are a creative writing consultant helping an author develop ideas.

**Current project context:**
{context}

**Brainstorming focus:**
{focus}

**Style/genre:** {style_instruction}

**Task:** Generate {n_ideas} creative ideas or suggestions for the focus area above. Each idea should:
1. Be relevant to the project context
2. Offer a unique angle or approach
3. Be practical and actionable
4. Match the style and genre

Format your response as:

IDEA 1:
[First idea with brief explanation]

IDEA 2:
[Second idea with brief explanation]

IDEA 3:
[Third idea with brief explanation]

{extra_ideas}"""


# ==============================================================================
# CRITIQUE/FEEDBACK PROMPTS
# ==============================================================================

CRITIQUE_PROMPT = """You are a professional manuscript editor providing constructive feedback.

**Text to review:**
{text}

**Review focus areas:**
{focus_areas}

**Task:** Provide detailed, constructive feedback on the text above. Your critique should:
1. Identify strengths and what works well
2. Point out areas for improvement
3. Suggest specific, actionable changes
4. Maintain a supportive, professional tone

Structure your feedback clearly with sections for strengths and areas for improvement."""


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def get_style_instruction(style: str, custom_instruction: str = None) -> str:
    """Get style instruction for prompts"""
    from .models import AuthorConfig

    config = AuthorConfig()
    base_instruction = config.style_instructions.get(
        style,
        config.style_instructions["neutral"]
    )

    if custom_instruction:
        return f"{base_instruction}\n\nCustom instruction: {custom_instruction}"

    return base_instruction


def format_extra_variations(n: int, start_letter: str = 'D') -> str:
    """Generate variation labels for more than 3 variations"""
    if n <= 3:
        return ""

    labels = []
    for i in range(n - 3):
        letter = chr(ord(start_letter) + i)
        labels.append(f"VARIATION {letter}:\n[Variation {letter.lower()}]")

    return "\n\n".join(labels)


def format_extra_ideas(n: int, start_num: int = 4) -> str:
    """Generate idea labels for more than 3 ideas"""
    if n <= 3:
        return ""

    labels = []
    for i in range(n - 3):
        num = start_num + i
        labels.append(f"IDEA {num}:\n[Idea {num} with brief explanation]")

    return "\n\n".join(labels)
