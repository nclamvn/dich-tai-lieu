"""
Agent 3: Professional PDF Renderer
AI Publisher Pro

Two rendering approaches:

1. SIMPLE (for small documents that fit in one call):
   - render_ebook(markdown, "book.pdf", title="...", author="...")
   - render_academic(markdown, "paper.pdf", title="...", author="...")

2. STREAMING (for large documents - unlimited length):
   - Agent2OutputBuilder: Build output folder with chapters
   - Agent3_StreamingPublisher: Consume folder and render PDF

Usage (Simple):
    from core.pdf_renderer import render_ebook, render_academic

    result = render_ebook(markdown, "book.pdf", title="...", author="...")
    result = render_academic(markdown, "paper.pdf", title="...", author="...")

Usage (Streaming - for large docs):
    from core.pdf_renderer import Agent2OutputBuilder, Agent3_StreamingPublisher

    # Agent 2: Build output folder
    builder = Agent2OutputBuilder("./book_output")
    builder.set_metadata(title="My Book", author="Author")
    builder.add_chapter("001", "Chapter 1", markdown_content)
    builder.add_chapter("002", "Chapter 2", markdown_content)
    builder.finalize()

    # Agent 3: Stream render PDF
    publisher = Agent3_StreamingPublisher("./book_output")
    result = publisher.render("book.pdf")
    print(f"Pages: {result['pages']}")
"""

# Simple renderers (single-call, small docs)
from .pdf_renderer import (
    # Main agent
    Agent3_PDFRenderer,

    # Renderers
    EbookRenderer,
    AcademicRenderer,

    # Configuration
    RenderMode as SimpleRenderMode,
    DocumentMetadata,
    EbookConfig,

    # Convenience functions
    render_ebook,
    render_academic,
)

# Streaming renderers (multi-chapter, large docs)
from .output_format import (
    # Contract types
    DocumentType,
    RenderMode,
    SectionInfo,
    ChapterInfo,
    DocumentStructure,
    RenderHints,
    Manifest,
    Metadata,
    Glossary,

    # Agent 2 output
    Agent2OutputBuilder,
    create_output_builder,

    # Agent 3 input
    Agent3InputReader,
    read_agent2_output,
)

from .streaming_publisher import (
    # Streaming renderers
    StreamingEbookRenderer,
    StreamingAcademicRenderer,

    # Main publisher
    Agent3_StreamingPublisher,

    # Convenience
    publish_from_folder,
)

__all__ = [
    # === SIMPLE RENDERERS (small docs) ===
    "Agent3_PDFRenderer",
    "EbookRenderer",
    "AcademicRenderer",
    "SimpleRenderMode",
    "DocumentMetadata",
    "EbookConfig",
    "render_ebook",
    "render_academic",

    # === STREAMING PIPELINE (large docs) ===
    # Contract types
    "DocumentType",
    "RenderMode",
    "SectionInfo",
    "ChapterInfo",
    "DocumentStructure",
    "RenderHints",
    "Manifest",
    "Metadata",
    "Glossary",

    # Agent 2 output builder
    "Agent2OutputBuilder",
    "create_output_builder",

    # Agent 3 input reader
    "Agent3InputReader",
    "read_agent2_output",

    # Streaming renderers
    "StreamingEbookRenderer",
    "StreamingAcademicRenderer",
    "Agent3_StreamingPublisher",
    "publish_from_folder",
]
