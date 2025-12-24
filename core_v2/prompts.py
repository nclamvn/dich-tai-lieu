"""
Prompts for Claude-Native Pipeline

Contains all prompts with proper LaTeX preservation instructions.
"""

# =============================================================================
# TRANSLATION PROMPT - WITH LATEX PRESERVATION
# =============================================================================

TRANSLATION_PROMPT = """You are a professional translator specializing in {genre} documents.

TASK: Translate the following text from {source_lang} to {target_lang}.

CRITICAL REQUIREMENTS FOR MATHEMATICAL CONTENT:

1. **PRESERVE ALL LaTeX MATH NOTATION EXACTLY AS-IS:**
   - Keep `$...$` (inline math) delimiters unchanged
   - Keep `$$...$$` (display math) delimiters unchanged
   - Keep `\\[...\\]` and `\\(...\\)` delimiters unchanged
   - Keep ALL LaTeX commands inside math mode: \\sum, \\frac, \\int, \\nabla, \\mathbb, etc.
   - Keep ALL subscripts and superscripts: x_{{i}}, x^{{2}}, etc.
   - Keep ALL Greek letters: \\alpha, \\beta, \\gamma, etc.

2. **ONLY TRANSLATE SURROUNDING TEXT, NEVER FORMULA CONTENT:**

   CORRECT Example:
   Input:  "The gradient descent update rule is $x_{{t+1}} = x_t - \\eta \\nabla f(x_t)$ where $\\eta$ is the learning rate."
   Output: "Quy tắc cập nhật gradient descent là $x_{{t+1}} = x_t - \\eta \\nabla f(x_t)$ trong đó $\\eta$ là tốc độ học."

   WRONG Example:
   Input:  "The formula $\\sum_{{j=1}}^n f(j)$ shows..."
   Output: "Công thức tổng j=1 đến n f(j) cho thấy..."  ← WRONG! Lost LaTeX!

3. **PRESERVE EQUATION ENVIRONMENTS:**
   - Keep \\begin{{equation}}, \\end{{equation}}
   - Keep \\begin{{align}}, \\end{{align}}
   - Keep \\begin{{theorem}}, \\end{{theorem}}
   - Keep all LaTeX structural commands

4. **PRESERVE SPECIAL NOTATION:**
   - Citations: [1], [Author2024], \\cite{{...}}
   - References: Section 3.1, Theorem 2, Figure 1
   - Code blocks: ```...```
   - URLs and links

5. **STYLE REQUIREMENTS:**
{style_guide}

6. **SPECIAL INSTRUCTIONS:**
{special_instructions}

TEXT TO TRANSLATE:
---
{content}
---

OUTPUT:
Provide ONLY the translated text. Preserve ALL LaTeX math notation exactly as in the original.
Do not add explanations or meta-commentary.
"""

# =============================================================================
# DNA EXTRACTION PROMPT
# =============================================================================

DNA_EXTRACTION_PROMPT = """Analyze this document and extract its "DNA" - key characteristics for translation.

DOCUMENT:
---
{content}
---

DETECT AND RETURN JSON:
{{
  "detected_genre": "novel|academic_paper|business_report|technical_doc|...",
  "detected_language": "en|vi|zh|...",
  "has_formulas": true/false,
  "has_code": true/false,
  "has_tables": true/false,
  "has_citations": true/false,
  "formula_notation": "latex|unicode|plain",
  "characters": [
    {{"name": "...", "role": "...", "aliases": ["..."]}}
  ],
  "places": [
    {{"name": "...", "type": "city|country|fictional", "context": "..."}}
  ],
  "organizations": [
    {{"name": "...", "type": "company|institution|...", "context": "..."}}
  ],
  "terminology": [
    {{"term": "...", "definition": "...", "translation": "suggested translation"}}
  ],
  "style": {{
    "formality": "formal|informal|academic",
    "tone": "neutral|persuasive|narrative",
    "tense": "present|past|mixed"
  }}
}}

IMPORTANT: Detect if document contains LaTeX math notation ($...$, \\sum, \\frac, etc.)
and set has_formulas=true and formula_notation="latex" if so.
"""

# =============================================================================
# CHUNK BOUNDARY PROMPT
# =============================================================================

CHUNK_BOUNDARY_PROMPT = """Analyze this document and identify natural semantic boundaries for chunking.

DOCUMENT:
---
{content}
---

IDENTIFY:
1. Chapter/Section breaks
2. Major topic transitions
3. Natural paragraph groupings

IMPORTANT: For academic papers with LaTeX math:
- Keep equations with their surrounding context
- Don't split in the middle of a proof or derivation
- Keep theorem statements with their proofs

RETURN JSON:
{{
  "chunks": [
    {{
      "start_marker": "text at start of chunk",
      "end_marker": "text at end of chunk",
      "type": "chapter|section|paragraph_group",
      "title": "optional title",
      "has_math": true/false
    }}
  ]
}}
"""

# =============================================================================
# ASSEMBLY PROMPT
# =============================================================================

ASSEMBLY_PROMPT = """You are assembling translated chunks into a coherent document.

IMPORTANT: The chunks are ALREADY TRANSLATED to {target_lang}.
DO NOT translate or change the language. Preserve the existing translation.

Your task is ONLY to:
1. Combine chunks maintaining logical flow
2. Ensure consistent terminology across sections
3. Fix any transition issues between chunks
4. **PRESERVE ALL LaTeX MATH NOTATION EXACTLY**

ORIGINAL STRUCTURE:
{structure_info}

TRANSLATED CHUNKS (in {target_lang}):
{chunks}

OUTPUT FORMAT: {output_format}

For LaTeX output, ensure:
- All $...$ delimiters are preserved
- All \\begin/\\end environments are balanced
- Document has proper LaTeX structure

Provide the assembled document in {target_lang} only, no commentary.
Keep all content in {target_lang}. Do NOT translate anything.
"""

# =============================================================================
# VERIFICATION PROMPT
# =============================================================================

VERIFICATION_PROMPT = """Review this translation for quality.

ORIGINAL ({source_lang}):
---
{original}
---

TRANSLATION ({target_lang}):
---
{translation}
---

CHECK:
1. Completeness - Is all content translated?
2. Accuracy - Is the meaning preserved?
3. **LaTeX Preservation** - Are ALL math formulas preserved exactly?
   - Check: $...$ delimiters present?
   - Check: \\sum, \\frac, \\int commands intact?
   - Check: Subscripts/superscripts preserved (x_{{i}}, x^{{2}})?
4. Terminology consistency
5. Style appropriateness for {genre}

RETURN JSON:
{{
  "quality_score": 0.0-1.0,
  "completeness": 0.0-1.0,
  "accuracy": 0.0-1.0,
  "latex_preservation": 0.0-1.0,
  "issues": [
    {{"type": "...", "severity": "low|medium|high", "description": "...", "suggestion": "..."}}
  ],
  "verdict": "pass|needs_revision|fail"
}}
"""

# =============================================================================
# SIMPLE TRANSLATION PROMPT (for non-formula content)
# =============================================================================

SIMPLE_TRANSLATION_PROMPT = """You are a professional translator.

Translate the following text from {source_lang} to {target_lang}.

DOCUMENT DNA:
{dna_context}

PUBLISHING PROFILE:
{profile_prompt}

CONTEXT:
- This is chunk {chunk_index} of {total_chunks}
- Previous content: {previous_summary}
- Next content: {next_preview}

Source Text:
{source_text}

REQUIREMENTS:
1. Follow the publishing profile's style guide exactly
2. Maintain consistency with the document DNA
3. Preserve all formatting and special elements
4. Keep proper nouns as specified in the DNA
5. Use consistent terminology throughout

OUTPUT:
Provide ONLY the translated text, no explanations or meta-commentary.
"""


# =============================================================================
# NOVEL READING PROMPT - FOR LITERATURE
# =============================================================================

NOVEL_PAGE_READING_PROMPT = """You are reading a page from a literary novel/book.
Your task is to perfectly transcribe the content, preserving literary structure.

CRITICAL INSTRUCTIONS FOR NOVELS:

1. **CHAPTER HEADINGS:**
   - Format as: ## Chapter X or ## CHƯƠNG X
   - Include chapter titles if present
   - Note page breaks between chapters

2. **PARAGRAPHS:**
   - Preserve paragraph breaks
   - Keep first-line indentation intent (mark with > if notable)
   - Maintain paragraph flow across page breaks

3. **DIALOGUE:**
   - Preserve quotation marks exactly: "..." or «...» or '...'
   - Keep dialogue attribution on same line
   - Maintain em-dashes for interrupted speech

4. **SPECIAL ELEMENTS:**
   - Scene breaks: Mark as *** or ---
   - Letters/Documents within text: Use blockquote >
   - Poetry/Verse: Preserve line breaks
   - Footnotes: Mark as [^1] with content at bottom

5. **FORMATTING:**
   - *Italics* for emphasis, thoughts, foreign words
   - **Bold** for strong emphasis
   - Keep ALL punctuation exactly as shown

OUTPUT: Clean Markdown preserving all literary structure.
Do not summarize. Transcribe completely."""


# =============================================================================
# BUSINESS DOCUMENT PROMPT - FOR TABLES & REPORTS
# =============================================================================

BUSINESS_PAGE_READING_PROMPT = """You are reading a page from a business document.
Your task is to extract ALL content including complex tables.

CRITICAL INSTRUCTIONS FOR BUSINESS DOCUMENTS:

1. **TABLES - CRITICAL:**
   For tables with merged cells or complex structure, output as HTML:

   <table>
     <thead>
       <tr>
         <th rowspan="2">Region</th>
         <th colspan="3">Revenue ($M)</th>
       </tr>
       <tr>
         <th>Q1</th>
         <th>Q2</th>
         <th>Q3</th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td>North</td>
         <td>1.2</td>
         <td>1.5</td>
         <td>1.8</td>
       </tr>
     </tbody>
   </table>

   For simple tables (no merging), use Markdown:
   | Col1 | Col2 | Col3 |
   |------|------|------|
   | A    | B    | C    |

2. **NUMBERS - PRESERVE EXACTLY:**
   - Keep all decimal places: 1.234, not 1.23
   - Keep currency symbols: $, EUR, ¥
   - Keep percentages: 45.6%
   - Keep thousands separators: 1,234,567

3. **CHARTS/GRAPHS:**
   - Describe chart type and key data points
   - Extract any visible data values
   - Note: [CHART: Bar chart showing Q1-Q4 revenue growth]

4. **STRUCTURE:**
   - ## for section headings
   - ### for subsections
   - Bullet points for lists
   - Numbered lists for procedures

OUTPUT: Markdown with HTML tables for complex structures."""


# =============================================================================
# FOOTNOTE HANDLING PROMPT
# =============================================================================

FOOTNOTE_EXTRACTION_PROMPT = """Extract all footnotes from this page.

OUTPUT FORMAT (JSON):
{
  "footnotes": [
    {
      "marker": "1",
      "content": "Full footnote text here",
      "location": "bottom"
    }
  ],
  "endnotes": [
    {
      "marker": "i",
      "content": "Endnote text"
    }
  ]
}

Include the marker type (number, letter, symbol) exactly as shown."""
