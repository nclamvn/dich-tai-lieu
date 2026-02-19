"""
Publishing Profiles - Natural Language Publishing Standards

Instead of coding formatting rules, we describe what we want in natural language.
Claude knows ALL publishing standards - we just need to tell it which one to use.
"""

from dataclasses import dataclass
from typing import Optional


# ==================== RENDERING SKILL ====================
# Injected into assembly prompts so the LLM outputs markdown
# that our DOCX/PDF renderers can parse cleanly.

BASE_RENDERING_SKILL = """
MARKDOWN FORMATTING RULES (follow exactly):
- Use `##` for sections, `###` for subsections (never use single `#`)
- Separate paragraphs with blank lines
- Add blank lines before and after headings
- Use `**bold**` for key terms, `*italic*` for emphasis
- Use `>` for block quotes (one `>` per line)
- Use ``` with language tag for code blocks (e.g. ```python)
- Use `|` pipe syntax for tables with `---` separator row
- Use `- ` for bullet lists, `1. ` for numbered lists
- Use `---` on its own line for horizontal rules / scene breaks
"""


@dataclass
class PublishingProfile:
    """A publishing profile describes the desired output format in natural language."""

    id: str
    name: str
    description: str
    output_format: str  # docx, pdf, epub, etc.
    style_guide: str    # Natural language description of style
    special_instructions: str = ""
    template_name: str = "auto"  # DOCX/PDF template: ebook, academic, business, auto
    rendering_instructions: str = ""  # Profile-specific markdown formatting hints

    def to_prompt(self) -> str:
        """Convert profile to Claude prompt instructions."""
        parts = [
            f"Publishing Profile: {self.name}",
            f"\nStyle Guide:\n{self.style_guide}",
        ]
        if self.special_instructions:
            parts.append(f"\nSpecial Instructions: {self.special_instructions}")
        if self.rendering_instructions:
            parts.append(f"\nFormatting:\n{self.rendering_instructions}")
        return "\n".join(parts)


# ==================== PUBLISHING PROFILES ====================

PROFILES = {
    # === LITERATURE ===
    "novel": PublishingProfile(
        id="novel",
        name="Novel / Fiction",
        description="Literary fiction with emphasis on narrative flow",
        output_format="docx",
        template_name="ebook",
        style_guide="""
- Preserve author's voice and narrative style
- Maintain dialogue formatting with proper quotation marks
- Keep paragraph breaks as in original
- Preserve italics for emphasis and internal thoughts
- Chapter titles should be prominent
- Use em-dashes for interruptions
- Maintain pacing through paragraph length
""",
        special_instructions="Prioritize readability and emotional impact over literal translation.",
        rendering_instructions="""
- Start each dialogue on a new paragraph
- Use *italic* for character thoughts and internal monologue
- Use `---` on its own line for scene breaks
- Keep chapter titles as `## Chapter Title` (no numbering unless original has it)
""",
    ),

    "poetry": PublishingProfile(
        id="poetry",
        name="Poetry Collection",
        description="Poetry with attention to rhythm and line breaks",
        output_format="docx",
        template_name="ebook",
        style_guide="""
- Preserve line breaks exactly as original
- Maintain stanza separation
- Keep any visual formatting (indentation, spacing)
- Preserve rhyme schemes where possible in target language
- Maintain rhythm and meter patterns
- Title poems appropriately
""",
        special_instructions="If rhyme cannot be preserved, prioritize meaning and rhythm.",
        rendering_instructions="""
- Each poem title as `## Title`
- Preserve exact line breaks within stanzas
- Separate stanzas with a single blank line
- Use *italic* for epigraphs or dedications
""",
    ),

    "essay": PublishingProfile(
        id="essay",
        name="Essay / Non-Fiction",
        description="Essays, memoirs, and general non-fiction",
        output_format="docx",
        template_name="ebook",
        style_guide="""
- Clear paragraph structure
- Maintain author's argumentative flow
- Preserve quotations with proper attribution
- Keep section headings if present
- Footnotes at bottom of page
- Readable, flowing prose
""",
        rendering_instructions="""
- Use `## Section Title` for major sections
- Use `> Quote text` for block quotations
- Use **bold** for emphasis on key arguments
""",
    ),

    # === BUSINESS ===
    "business_report": PublishingProfile(
        id="business_report",
        name="Business Report",
        description="Corporate reports, analyses, and documentation",
        output_format="docx",
        template_name="business",
        style_guide="""
- Professional, formal tone
- Executive summary at start
- Clear section headings
- Bullet points for lists
- Tables should be clean and readable
- Charts/figures captioned properly
- Page numbers in footer
- Company branding space in header
""",
        rendering_instructions="""
- Use markdown tables with `|` for all data presentations
- Use `- ` bullet lists for findings and recommendations
- Use **bold** for action items and key metrics
- Use `## Section` for major sections, `### Subsection` for details
""",
    ),

    "white_paper": PublishingProfile(
        id="white_paper",
        name="White Paper",
        description="Technical white papers and research reports",
        output_format="pdf",
        template_name="business",
        style_guide="""
- Professional but accessible tone
- Abstract/Summary at beginning
- Numbered sections
- Technical terms defined on first use
- Citations in consistent format
- Clean, modern layout
- Figures and tables numbered
""",
        rendering_instructions="""
- Use numbered sections: `## 1. Introduction`, `### 1.1 Background`
- Use markdown tables for data
- Use `> ` for callout boxes and key takeaways
""",
    ),

    # === ACADEMIC ===
    "academic_paper": PublishingProfile(
        id="academic_paper",
        name="Academic Paper (General)",
        description="General academic papers and journal articles",
        output_format="pdf",
        template_name="academic",
        style_guide="""
- Follow standard academic structure: Abstract, Introduction, Methods, Results, Discussion, Conclusion
- Numbered sections and subsections
- Formal academic tone
- In-text citations preserved
- References section at end
- Figures and tables with captions
- Equations numbered
""",
        rendering_instructions="""
- Use numbered headings: `## 1. Introduction`, `### 1.1 Background`
- Use `> **Theorem 1.** Statement` for theorems and definitions
- Use `> **Proof.** Text` for proofs
- Preserve all $...$ and $$...$$ math delimiters exactly
""",
    ),

    "arxiv_paper": PublishingProfile(
        id="arxiv_paper",
        name="arXiv Paper (STEM)",
        description="STEM papers for arXiv submission",
        output_format="pdf",
        template_name="academic",
        style_guide="""
- LaTeX-ready formatting
- Mathematical notation preserved exactly
- Theorem/Lemma/Proof environments
- Algorithm blocks formatted properly
- Equations numbered and referenced
- Bibliography in BibTeX format
- Figure placement: [htbp]
- Two-column layout ready
""",
        special_instructions="Preserve ALL LaTeX commands and mathematical notation exactly.",
        rendering_instructions="""
- Preserve all $...$ and $$...$$ math delimiters exactly
- Use `> **Theorem N.** Statement` for theorem environments
- Use ```pseudo for algorithm blocks
- Use numbered headings: `## 1. Section`
""",
    ),

    "thesis": PublishingProfile(
        id="thesis",
        name="Thesis / Dissertation",
        description="Graduate-level theses and dissertations",
        output_format="pdf",
        template_name="academic",
        style_guide="""
- Title page with institution format
- Abstract page
- Table of contents
- List of figures/tables
- Chapter-based organization
- Numbered sections to 3 levels
- Footnotes or endnotes as original
- Bibliography at end
- Appendices if present
- Page margins for binding
""",
        rendering_instructions="""
- Use `## Chapter N: Title` for chapters
- Use `### N.1 Section` and `#### N.1.1 Subsection` for hierarchy
- Preserve all math notation in $...$ and $$...$$
""",
    ),

    "textbook": PublishingProfile(
        id="textbook",
        name="Textbook",
        description="Educational textbooks with exercises",
        output_format="docx",
        template_name="academic",
        style_guide="""
- Chapter organization with learning objectives
- Clear section headings
- Key terms highlighted or bolded
- Example boxes/callouts
- Practice problems numbered
- Answers in appendix or end of chapter
- Figures and diagrams captioned
- Margin notes for key concepts
- Summary at end of each chapter
""",
        rendering_instructions="""
- Use `> **Key Concept:** text` for callout boxes
- Use **bold** for key terms on first occurrence
- Use `1. ` numbered lists for exercises and problems
- Use `## Chapter Title`, `### Section` for hierarchy
""",
    ),

    # === TECHNICAL ===
    "technical_doc": PublishingProfile(
        id="technical_doc",
        name="Technical Documentation",
        description="Software documentation, specifications",
        output_format="docx",
        template_name="business",
        style_guide="""
- Clear section hierarchy
- Code blocks with syntax highlighting
- Step-by-step numbered instructions
- Warning/Note/Tip callouts
- Version information
- Table of contents
- Cross-references to other sections
- Consistent terminology throughout
""",
        rendering_instructions="""
- Use ``` with language tag for all code blocks (```python, ```bash, etc.)
- Use `> **Note:** text` for notes, `> **Warning:** text` for warnings
- Use `### Endpoint` for API-like sections
- Use markdown tables for parameter/option listings
""",
    ),

    "api_doc": PublishingProfile(
        id="api_doc",
        name="API Documentation",
        description="API reference documentation",
        output_format="docx",
        template_name="business",
        style_guide="""
- Endpoint format: METHOD /path
- Request/Response examples
- Parameter tables
- Authentication section
- Error codes documented
- Code examples in multiple languages
- Clean, technical formatting
""",
        rendering_instructions="""
- Use `### GET /path` or `### POST /path` for endpoints
- Use ``` with language tags for request/response examples
- Use markdown tables for parameters: | Name | Type | Required | Description |
- Use `> **Note:** text` for important callouts
""",
    ),

    "user_manual": PublishingProfile(
        id="user_manual",
        name="User Manual",
        description="Product user guides and manuals",
        output_format="docx",
        template_name="business",
        style_guide="""
- Clear, simple language
- Step-by-step procedures
- Screenshots/diagrams referenced
- Warning/Caution boxes
- Troubleshooting section
- Index at end
- Quick start guide at beginning
- Consistent terminology
""",
        rendering_instructions="""
- Use `1. ` numbered lists for step-by-step procedures
- Use `> **Warning:** text` for safety warnings
- Use `> **Tip:** text` for helpful tips
- Use **bold** for UI element names (buttons, menus)
""",
    ),
}


def get_profile(profile_id: str) -> Optional[PublishingProfile]:
    """Get a publishing profile by ID."""
    return PROFILES.get(profile_id)


def list_profiles() -> list:
    """List all available profile IDs."""
    return list(PROFILES.keys())
