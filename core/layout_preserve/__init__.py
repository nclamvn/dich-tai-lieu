"""
LLM-Native Layout-Preserving Translation
AI Publisher Pro

Uses Vision LLM to extract structured content and translate
while preserving tables, columns, and layout.

Philosophy: LLM does the heavy lifting, minimal dependencies.
"""

from .document_analyzer import (
    DocumentAnalyzer,
    AnalyzerConfig,
    StructuredDocument,
    DocumentPage,
    ContentBlock,
    ContentType,
    Table,
    TableCell,
    LLMProvider,
    analyze_business_document,
    create_analyzer,
)

from .document_renderer import (
    DocumentRenderer,
    render_to_docx,
    render_to_markdown,
    render_to_html,
)

from .translation_pipeline import (
    LayoutPreservingPipeline,
    PipelineConfig,
    TranslationResult,
    translate_business_document,
    create_pipeline,
)

__all__ = [
    # Analyzer
    "DocumentAnalyzer",
    "AnalyzerConfig",
    "StructuredDocument",
    "DocumentPage",
    "ContentBlock",
    "ContentType",
    "Table",
    "TableCell",
    "LLMProvider",
    "analyze_business_document",
    "create_analyzer",
    # Renderer
    "DocumentRenderer",
    "render_to_docx",
    "render_to_markdown",
    "render_to_html",
    # Pipeline
    "LayoutPreservingPipeline",
    "PipelineConfig",
    "TranslationResult",
    "translate_business_document",
    "create_pipeline",
]
