#!/usr/bin/env python3
"""
X-RAY CLASSIFICATION

Deep analysis of each component to determine:
1. What it does
2. Can Claude do this natively?
3. Classification decision with reasoning
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class Decision(Enum):
    KEEP = "KEEP"           # Keep, Claude can't do better
    TRANSFORM = "TRANSFORM" # Restructure to orchestration
    REPLACE = "REPLACE"     # Replace with Claude prompt
    REMOVE = "REMOVE"       # Delete, redundant


@dataclass
class ComponentAnalysis:
    name: str
    path: str
    lines: int
    purpose: str
    decision: Decision
    reasoning: str
    claude_alternative: str  # How Claude would do this
    new_implementation: str  # What replaces this


# Manual deep analysis of key components
COMPONENT_ANALYSES = [
    # ==================== CORE TRANSLATION ====================
    ComponentAnalysis(
        name="BatchProcessor",
        path="core/batch_processor.py",
        lines=1203,
        purpose="Orchestrates translation pipeline: OCR → Chunk → Translate → Merge",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Complex 1200+ lines of orchestration logic
            - Does chunking, parallel processing, checkpointing
            - Valuable: job management, progress tracking, streaming mode

            ANTHROPIC VIEW:
            - Most of this is "managing Claude" rather than "helping Claude"
            - Chunking logic tries to preserve context - Claude understands context natively
            - Parallel processing is rate-limit workaround, not value-add
            - Keep: progress tracking, job state management
        """,
        claude_alternative="Claude can process entire documents if context fits. For large docs, need semantic chunking only.",
        new_implementation="ContextOrchestrator: ~300 lines. Semantic chunking + context injection."
    ),

    ComponentAnalysis(
        name="TranslatorEngine",
        path="core/translator.py",
        lines=365,
        purpose="Builds prompts, calls API, validates results",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Core translation logic
            - Has useful: TM integration, glossary injection

            ANTHROPIC VIEW:
            - Prompt building is over-engineered
            - Claude doesn't need "translation rules" - it knows languages
            - Glossary injection is useful but can be simpler
        """,
        claude_alternative="Single well-crafted prompt with document DNA (terms, style).",
        new_implementation="PromptBuilder: ~100 lines. Inject context, let Claude translate."
    ),

    ComponentAnalysis(
        name="SmartChunker",
        path="core/chunker/smart_chunker.py",
        lines=200,
        purpose="Split text into chunks preserving sentence boundaries",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Important for context window management
            - Current: character-based with sentence boundary detection

            ANTHROPIC VIEW:
            - Should be SEMANTIC not character-based
            - Claude understands document structure
            - Split at chapters/sections, not arbitrary boundaries
        """,
        claude_alternative="Ask Claude to identify semantic boundaries, then split there.",
        new_implementation="SemanticChunker: ~150 lines. Use document structure for boundaries."
    ),

    # ==================== RENDERING ====================
    ComponentAnalysis(
        name="DocxRenderer",
        path="core/layout/renderer/docx_renderer.py",
        lines=119,
        purpose="Generate DOCX from translated content",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - 119 lines of python-docx formatting
            - Styles, fonts, margins, etc.

            ANTHROPIC VIEW:
            - Claude generates PERFECT LaTeX/Markdown natively
            - pandoc converts to DOCX in one command
            - Why maintain code when: Claude → Markdown → pandoc → DOCX
        """,
        claude_alternative="Claude outputs Markdown/LaTeX, pandoc converts to DOCX.",
        new_implementation="pandoc command: 1 line."
    ),

    ComponentAnalysis(
        name="PDFRenderer",
        path="core/layout/renderer/pdf_renderer.py",
        lines=147,
        purpose="Generate PDF with reportlab",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - PDF generation with reportlab
            - Font embedding, page layout

            ANTHROPIC VIEW:
            - Claude outputs perfect LaTeX
            - pdflatex generates publication-quality PDF
            - arXiv-ready without custom code
        """,
        claude_alternative="Claude → LaTeX → pdflatex → Perfect PDF",
        new_implementation="pdflatex command: 1 line."
    ),

    ComponentAnalysis(
        name="EPUBRenderer",
        path="core/layout/renderer/epub_renderer.py",
        lines=208,
        purpose="Generate EPUB ebook",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - ebooklib integration
            - Chapter splitting, TOC generation

            ANTHROPIC VIEW:
            - Claude outputs structured HTML
            - pandoc/calibre converts to EPUB perfectly
        """,
        claude_alternative="Claude → HTML chapters → pandoc → EPUB",
        new_implementation="pandoc command: 1 line."
    ),

    ComponentAnalysis(
        name="StyleEngine",
        path="core/formatting/style_engine.py",
        lines=231,
        purpose="Manage document styles",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - Complex style management

            ANTHROPIC VIEW:
            - Claude understands styles semantically
            - Just describe desired output format in prompt
        """,
        claude_alternative="Describe styles in prompt",
        new_implementation="Part of system prompt: ~20 lines."
    ),

    # ==================== ADN/EDITORIAL ====================
    ComponentAnalysis(
        name="ADNExtractor",
        path="core/adn/extractor.py",
        lines=250,
        purpose="Extract proper nouns, characters, terms, patterns",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Regex-based extraction
            - Useful for consistency

            ANTHROPIC VIEW:
            - Claude UNDERSTANDS entities semantically
            - One prompt: "Extract all named entities, characters, technical terms"
            - Result: Better than regex, handles context
        """,
        claude_alternative="Single Claude call: 'Analyze document, extract entities with roles'",
        new_implementation="DocumentDNA: ~50 lines. Prompt + parse JSON response."
    ),

    ComponentAnalysis(
        name="PatternDetector",
        path="core/adn/patterns.py",
        lines=291,
        purpose="Detect patterns in text",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Complex regex patterns

            ANTHROPIC VIEW:
            - Claude can identify patterns semantically
            - Better understanding of context
        """,
        claude_alternative="Ask Claude to identify patterns",
        new_implementation="Part of DocumentDNA prompt."
    ),

    ComponentAnalysis(
        name="SemanticExtractor",
        path="core/structure/semantic_extractor.py",
        lines=415,
        purpose="Extract semantic document structure",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Complex structure detection

            ANTHROPIC VIEW:
            - Claude understands document structure natively
            - Can identify chapters, sections, theorems
        """,
        claude_alternative="Ask Claude to analyze structure",
        new_implementation="Part of initial document analysis."
    ),

    ComponentAnalysis(
        name="FormatDetector",
        path="core/formatting/detector.py",
        lines=369,
        purpose="Detect document formatting",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Rule-based format detection

            ANTHROPIC VIEW:
            - Claude understands formatting from context
        """,
        claude_alternative="Claude analyzes formatting naturally",
        new_implementation="Part of document analysis."
    ),

    ComponentAnalysis(
        name="QualityValidator",
        path="core/validator.py",
        lines=296,
        purpose="Validate translation quality",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Rules-based validation

            ANTHROPIC VIEW:
            - Claude can self-validate
            - Better: use second Claude call for verification
        """,
        claude_alternative="Claude self-checks or verification call",
        new_implementation="Verification prompt: ~30 lines."
    ),

    # ==================== FORMULA/STEM ====================
    ComponentAnalysis(
        name="FormulaDetector",
        path="core/stem/formula_detector.py",
        lines=106,
        purpose="Detect and preserve math formulas during translation",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - Regex detection of LaTeX formulas
            - Placeholder replacement

            ANTHROPIC VIEW:
            - Claude UNDERSTANDS LaTeX natively
            - Claude knows "$E=mc^2$" is a formula
            - No preprocessing needed - just tell Claude to preserve formulas
        """,
        claude_alternative="Prompt: 'Preserve all mathematical formulas exactly as written'",
        new_implementation="0 lines - instruction in prompt."
    ),

    ComponentAnalysis(
        name="PDFReconstructor",
        path="core/stem/pdf_reconstructor.py",
        lines=287,
        purpose="Reconstruct PDF with translated text",
        decision=Decision.TRANSFORM,
        reasoning="""
            ARCHITECT VIEW:
            - Complex PDF manipulation

            ANTHROPIC VIEW:
            - Claude → LaTeX → pdflatex is cleaner
            - Keep only for scan overlay use case
        """,
        claude_alternative="LaTeX output → pdflatex",
        new_implementation="~50 lines for scan overlay case."
    ),

    ComponentAnalysis(
        name="MathReconstructor",
        path="core/math_reconstructor.py",
        lines=276,
        purpose="Handle math formulas during translation",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - Complex formula handling

            ANTHROPIC VIEW:
            - Claude handles LaTeX natively
            - No reconstruction needed
        """,
        claude_alternative="Claude preserves LaTeX naturally",
        new_implementation="0 lines."
    ),

    # ==================== POST-PROCESSING ====================
    ComponentAnalysis(
        name="VnAcademicPolisher",
        path="core/postprocess/vn_academic_polisher.py",
        lines=165,
        purpose="Polish Vietnamese academic text",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - Vietnamese-specific polishing

            ANTHROPIC VIEW:
            - Claude knows Vietnamese perfectly
            - Just ask for academic style output
        """,
        claude_alternative="Style instruction in prompt",
        new_implementation="Part of translation prompt."
    ),

    ComponentAnalysis(
        name="ParagraphMerger",
        path="core/post_formatting/paragraph_merger.py",
        lines=149,
        purpose="Merge split paragraphs",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - Post-processing to fix chunking artifacts

            ANTHROPIC VIEW:
            - With semantic chunking, no merging needed
            - Claude outputs complete paragraphs
        """,
        claude_alternative="Semantic chunking prevents this issue",
        new_implementation="0 lines."
    ),

    ComponentAnalysis(
        name="BookPolisher",
        path="core/post_formatting/book_polisher.py",
        lines=108,
        purpose="Polish book-format output",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - Book formatting polish

            ANTHROPIC VIEW:
            - Claude outputs book-ready text
            - Style in prompt
        """,
        claude_alternative="Book style in prompt",
        new_implementation="Part of prompt."
    ),

    ComponentAnalysis(
        name="SmartMerger",
        path="core/merger.py",
        lines=54,
        purpose="Merge translated chunks",
        decision=Decision.REPLACE,
        reasoning="""
            ARCHITECT VIEW:
            - Overlap detection, fuzzy matching

            ANTHROPIC VIEW:
            - With semantic chunking at natural boundaries, just concatenate
        """,
        claude_alternative="Simple concatenation",
        new_implementation="~10 lines."
    ),

    # ==================== KEEP AS-IS ====================
    ComponentAnalysis(
        name="JobQueue",
        path="core/job_queue.py",
        lines=189,
        purpose="Manage processing jobs",
        decision=Decision.KEEP,
        reasoning="""
            ARCHITECT VIEW:
            - Job management is infrastructure
            - Not Claude's job

            ANTHROPIC VIEW:
            - Correct. Claude processes content, we manage jobs.
        """,
        claude_alternative="N/A - infrastructure",
        new_implementation="Keep as-is."
    ),

    ComponentAnalysis(
        name="TranslationMemory",
        path="core/translation_memory.py",
        lines=296,
        purpose="Store and retrieve translations",
        decision=Decision.KEEP,
        reasoning="""
            ARCHITECT VIEW:
            - Essential for consistency and cost
            - Fuzzy matching useful

            ANTHROPIC VIEW:
            - Keep. But simplify integration with Claude
        """,
        claude_alternative="N/A - cost optimization",
        new_implementation="Keep, simplify interface."
    ),

    ComponentAnalysis(
        name="CacheManager",
        path="core/cache/aps_cache.py",
        lines=94,
        purpose="Multi-level caching",
        decision=Decision.KEEP,
        reasoning="""
            ARCHITECT VIEW:
            - Caching reduces API costs
            - Important for efficiency

            ANTHROPIC VIEW:
            - Essential. Cache Claude outputs.
        """,
        claude_alternative="N/A - infrastructure",
        new_implementation="Keep."
    ),

    ComponentAnalysis(
        name="CheckpointManager",
        path="core/cache/checkpoint_manager.py",
        lines=152,
        purpose="Save/restore processing state",
        decision=Decision.KEEP,
        reasoning="""
            ARCHITECT VIEW:
            - Fault tolerance for long jobs

            ANTHROPIC VIEW:
            - Keep. Important for large documents.
        """,
        claude_alternative="N/A - infrastructure",
        new_implementation="Keep."
    ),

    ComponentAnalysis(
        name="WebUI",
        path="ui-aps/*",
        lines=3000,
        purpose="Web interface",
        decision=Decision.KEEP,
        reasoning="""
            ARCHITECT VIEW:
            - Frontend for user interaction
            - Already well-built

            ANTHROPIC VIEW:
            - Keep. Update API calls only.
        """,
        claude_alternative="N/A - frontend",
        new_implementation="Keep, update API integration."
    ),

    ComponentAnalysis(
        name="APIRouter",
        path="api/*.py",
        lines=1500,
        purpose="FastAPI endpoints",
        decision=Decision.KEEP,
        reasoning="""
            ARCHITECT VIEW:
            - API infrastructure

            ANTHROPIC VIEW:
            - Keep. Simplify endpoints.
        """,
        claude_alternative="N/A - infrastructure",
        new_implementation="Keep, simplify."
    ),
]


def print_analysis_report():
    """Print formatted analysis report"""

    print("="*80)
    print("              COMPONENT CLASSIFICATION REPORT")
    print("              XRAY-R02: Deep Analysis")
    print("="*80)

    # Group by decision
    decisions = {d: [] for d in Decision}
    for analysis in COMPONENT_ANALYSES:
        decisions[analysis.decision].append(analysis)

    # Summary
    print("\n📊 SUMMARY BY DECISION")
    print("-"*80)

    total_current = sum(a.lines for a in COMPONENT_ANALYSES)

    for decision in Decision:
        components = decisions[decision]
        lines = sum(a.lines for a in components)
        pct = (lines / total_current * 100) if total_current > 0 else 0
        print(f"  {decision.value:<12}: {len(components):>3} components, {lines:>6,} lines ({pct:>5.1f}%)")

    print(f"  {'─'*60}")
    print(f"  {'TOTAL':<12}: {len(COMPONENT_ANALYSES):>3} components, {total_current:>6,} lines")

    # Detailed by decision
    for decision in [Decision.REPLACE, Decision.TRANSFORM, Decision.KEEP]:
        components = decisions[decision]
        if not components:
            continue

        print(f"\n\n{'='*80}")
        print(f"              {decision.value} COMPONENTS")
        print("="*80)

        for analysis in components:
            print(f"\n{'─'*80}")
            print(f"📦 {analysis.name}")
            print(f"   Path: {analysis.path}")
            print(f"   Lines: {analysis.lines}")
            print(f"   Purpose: {analysis.purpose}")
            print(f"\n   🔍 REASONING:")
            for line in analysis.reasoning.strip().split('\n'):
                if line.strip():
                    print(f"      {line.strip()}")
            print(f"\n   ✨ CLAUDE ALTERNATIVE:")
            print(f"      {analysis.claude_alternative}")
            print(f"\n   🔧 NEW IMPLEMENTATION:")
            print(f"      {analysis.new_implementation}")

    # Estimated savings
    print("\n\n" + "="*80)
    print("              ESTIMATED CODE REDUCTION")
    print("="*80)

    replace_lines = sum(a.lines for a in decisions[Decision.REPLACE])
    transform_lines = sum(a.lines for a in decisions[Decision.TRANSFORM])
    keep_lines = sum(a.lines for a in decisions[Decision.KEEP])

    # New architecture estimates
    new_orchestrator = 300
    new_chunker = 150
    new_dna = 50
    new_converter = 50
    new_prompts = 100
    new_total = new_orchestrator + new_chunker + new_dna + new_converter + new_prompts

    print(f"""
    ANALYZED COMPONENTS:
    ├── To Replace:    {replace_lines:,} lines  → 0 lines (use prompts)
    ├── To Transform:  {transform_lines:,} lines → ~{new_total} lines (new code)
    └── To Keep:       {keep_lines:,} lines  → {keep_lines:,} lines (as-is)
    ────────────────────────────────────────────────────────────────
    TOTAL ANALYZED:    {total_current:,} lines

    NEW ARCHITECTURE (Core Components Only):
    ├── Context Orchestrator:  ~{new_orchestrator} lines
    ├── Semantic Chunker:      ~{new_chunker} lines
    ├── Document DNA:          ~{new_dna} lines
    ├── Output Converter:      ~{new_converter} lines
    └── Prompts/Instructions:  ~{new_prompts} lines
    ────────────────────────────────────────────────────────────────
    TOTAL NEW CORE:            ~{new_total} lines

    📉 CORE LOGIC REDUCTION:
       Replace + Transform: {replace_lines + transform_lines:,} lines
       New implementation:  {new_total} lines
       Savings:             {replace_lines + transform_lines - new_total:,} lines
       Reduction:           {(1 - new_total/(replace_lines + transform_lines))*100:.0f}%
    """)

    # Claude-native benefits
    print("\n" + "="*80)
    print("              CLAUDE-NATIVE BENEFITS")
    print("="*80)

    print("""
    🎯 WHAT CLAUDE DOES NATIVELY (No code needed):

    1. FORMULA HANDLING
       - Understands LaTeX: $E=mc^2$, \\int_0^\\infty
       - Preserves formulas automatically
       - No placeholder system needed

    2. DOCUMENT STRUCTURE
       - Identifies chapters, sections, theorems
       - Maintains hierarchy naturally
       - No regex patterns needed

    3. STYLE & FORMATTING
       - Outputs Markdown, LaTeX, HTML
       - Knows academic vs casual style
       - Consistent formatting built-in

    4. ENTITY UNDERSTANDING
       - Recognizes named entities
       - Maintains character consistency
       - Understands context & roles

    5. QUALITY SELF-CHECK
       - Can verify own output
       - Identifies translation issues
       - Suggests improvements

    6. LANGUAGE EXPERTISE
       - Native Vietnamese knowledge
       - Academic terminology
       - Domain-specific terms
    """)

    # Action plan
    print("\n" + "="*80)
    print("              ACTION PLAN")
    print("="*80)

    print("""
    PHASE 2: NEW ARCHITECTURE DESIGN
    ├── ARCH-01: Context Orchestrator
    │   └── Manages document flow, not translation logic
    │
    ├── ARCH-02: Semantic Chunker
    │   └── Split at chapters/sections, not characters
    │
    ├── ARCH-03: Document DNA
    │   └── One Claude call to extract all entities
    │
    └── ARCH-04: Output Assembly
        └── pandoc for format conversion

    PHASE 3: IMPLEMENTATION
    ├── IMPL-01: ~300 lines orchestrator
    ├── IMPL-02: ~150 lines chunker
    ├── IMPL-03: ~50 lines DNA extractor
    └── IMPL-04: ~50 lines converter

    PHASE 4: MIGRATION
    ├── Keep: UI, API, Cache, Queue
    └── Replace: Core translation logic
    """)


def generate_dependency_map():
    """Generate component dependency map"""
    print("\n\n" + "="*80)
    print("              DEPENDENCY MAP")
    print("="*80)

    print("""
    CURRENT FLOW:
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Upload    │ ──▶ │   Chunker   │ ──▶ │  Translator │
    └─────────────┘     └─────────────┘     └─────────────┘
                              │                    │
                              ▼                    ▼
                        ┌─────────────┐     ┌─────────────┐
                        │   Merger    │ ◀── │  Validator  │
                        └─────────────┘     └─────────────┘
                              │
                              ▼
                        ┌─────────────┐
                        │  Renderer   │ (DOCX/PDF/EPUB)
                        └─────────────┘

    NEW FLOW (Claude-Native):
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Upload    │ ──▶ │  Semantic   │ ──▶ │   Claude    │
    │             │     │   Chunker   │     │   + DNA     │
    └─────────────┘     └─────────────┘     └─────────────┘
                                                  │
                                                  ▼
                                            ┌─────────────┐
                                            │   pandoc    │
                                            └─────────────┘
                                                  │
                                                  ▼
                                            ┌─────────────┐
                                            │   Output    │
                                            │ DOCX/PDF/   │
                                            │   EPUB      │
                                            └─────────────┘

    COMPONENTS ELIMINATED:
    ✗ Character chunker → Semantic chunker
    ✗ Complex translator → Simple Claude call
    ✗ Merger → Direct output (no overlap)
    ✗ Validator → Claude self-check
    ✗ DOCX/PDF/EPUB Renderer → pandoc
    ✗ Style engine → Prompt instructions
    ✗ Formula detector → Claude native
    ✗ Polishers → Part of translation prompt
    """)


if __name__ == "__main__":
    print_analysis_report()
    generate_dependency_map()

    print("\n" + "="*80)
    print("              XRAY-R02 COMPLETE")
    print("="*80)
