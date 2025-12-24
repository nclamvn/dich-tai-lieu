"""
LLM-Native Layout-Preserving Translation Pipeline
AI Publisher Pro

Complete pipeline for translating business documents
while preserving tables, columns, and layout.

Philosophy: LLM does extraction + translation, simple rendering.
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime

from .document_analyzer import (
    DocumentAnalyzer,
    AnalyzerConfig,
    StructuredDocument,
    DocumentPage,
    LLMProvider
)
from .document_renderer import DocumentRenderer


@dataclass
class TranslationResult:
    """Result of translation pipeline"""
    original_doc: StructuredDocument
    translated_doc: StructuredDocument
    output_path: str

    # Stats
    total_pages: int
    total_tables: int
    processing_time: float

    # Cost tracking
    vision_tokens: int = 0
    translation_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    # Provider
    provider: str = "openai"  # openai or anthropic

    # Models
    vision_model: str = "gpt-4o"  # For structure extraction
    translation_model: str = "gpt-4o-mini"  # For translation (cheaper)

    # Languages
    source_lang: str = "Chinese"
    target_lang: str = "Vietnamese"

    # Output
    output_format: str = "docx"  # docx, md, html
    output_dir: str = "./output"

    # Processing
    parallel_pages: int = 5  # Concurrent page processing


class LayoutPreservingPipeline:
    """
    LLM-Native Layout-Preserving Translation Pipeline

    Usage:
        pipeline = LayoutPreservingPipeline()
        result = await pipeline.translate_document("business_report.pdf")
        print(f"Output: {result.output_path}")
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

        # Initialize analyzer
        analyzer_config = AnalyzerConfig(
            vision_provider=LLMProvider(self.config.provider),
            translation_provider=LLMProvider.OPENAI,  # Always use OpenAI for translation
            vision_model=self.config.vision_model,
            translation_model=self.config.translation_model,
            source_lang=self.config.source_lang,
            target_lang=self.config.target_lang
        )
        self.analyzer = DocumentAnalyzer(analyzer_config)

        # Initialize renderer
        self.renderer = DocumentRenderer()

    async def translate_document(
        self,
        input_path: str,
        output_name: Optional[str] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> TranslationResult:
        """
        Translate a document while preserving layout.

        Args:
            input_path: Path to PDF or image folder
            output_name: Optional output filename
            on_progress: Callback(current, total, status)

        Returns:
            TranslationResult with paths and stats
        """
        start_time = datetime.now()

        input_path = Path(input_path)

        # Step 1: Convert PDF to images (if needed)
        if on_progress:
            on_progress(0, 100, "Converting PDF to images...")

        image_paths = await self._prepare_images(input_path)
        total_pages = len(image_paths)

        # Step 2: Process pages (extract + translate)
        original_pages = []
        translated_pages = []
        total_tables = 0

        # Process in batches for parallelism
        batch_size = self.config.parallel_pages

        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i + batch_size]

            tasks = [
                self._process_single_page(path, idx + i + 1)
                for idx, path in enumerate(batch)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Error processing page {i + j + 1}: {result}")
                    continue

                original, translated = result
                original_pages.append(original)
                translated_pages.append(translated)

                # Count tables
                for block in original.blocks:
                    if block.type.value == "table":
                        total_tables += 1

            # Progress callback
            if on_progress:
                progress = min(90, int((i + len(batch)) / total_pages * 80) + 10)
                on_progress(progress, 100, f"Processed {i + len(batch)}/{total_pages} pages")

        # Step 3: Create documents
        original_doc = StructuredDocument(pages=original_pages)
        translated_doc = StructuredDocument(pages=translated_pages)

        # Step 4: Render output
        if on_progress:
            on_progress(95, 100, "Rendering output...")

        output_path = self._render_output(
            translated_doc,
            input_path.stem if not output_name else output_name
        )

        # Calculate stats
        processing_time = (datetime.now() - start_time).total_seconds()

        # Estimate cost
        # GPT-4o vision: ~$0.01 per image (high detail)
        # GPT-4o-mini translation: ~$0.0015 per 1K tokens
        vision_cost = total_pages * 0.01
        translation_cost = total_pages * 0.002  # Rough estimate

        if on_progress:
            on_progress(100, 100, "Complete!")

        return TranslationResult(
            original_doc=original_doc,
            translated_doc=translated_doc,
            output_path=output_path,
            total_pages=total_pages,
            total_tables=total_tables,
            processing_time=processing_time,
            estimated_cost=vision_cost + translation_cost
        )

    async def _prepare_images(self, input_path: Path) -> List[str]:
        """Convert PDF to images or get image list"""
        if input_path.is_file() and input_path.suffix.lower() == ".pdf":
            # Convert PDF to images
            return await self._pdf_to_images(input_path)
        elif input_path.is_dir():
            # Get images from directory
            extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
            images = []
            for ext in extensions:
                images.extend(input_path.glob(f"*{ext}"))
                images.extend(input_path.glob(f"*{ext.upper()}"))
            images.sort(key=lambda p: p.name)
            return [str(p) for p in images]
        else:
            # Single image
            return [str(input_path)]

    async def _pdf_to_images(self, pdf_path: Path, dpi: int = 150) -> List[str]:
        """Convert PDF to images using pdf2image"""
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError("pdf2image required. Install with: pip install pdf2image")

        output_dir = pdf_path.parent / f"{pdf_path.stem}_pages"
        output_dir.mkdir(exist_ok=True)

        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        images = await loop.run_in_executor(
            None,
            lambda: convert_from_path(str(pdf_path), dpi=dpi)
        )

        paths = []
        for i, img in enumerate(images):
            path = output_dir / f"page_{i+1:04d}.png"
            img.save(path, "PNG")
            paths.append(str(path))

        return paths

    async def _process_single_page(
        self,
        image_path: str,
        page_number: int
    ) -> tuple[DocumentPage, DocumentPage]:
        """Process a single page"""
        return await self.analyzer.process_page(image_path, page_number)

    def _render_output(self, document: StructuredDocument, name: str) -> str:
        """Render document to output format"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.config.output_format == "docx":
            output_path = output_dir / f"{name}_{timestamp}.docx"
            return self.renderer.render_docx(document, str(output_path), name)

        elif self.config.output_format == "md":
            output_path = output_dir / f"{name}_{timestamp}.md"
            return self.renderer.render_markdown(document, str(output_path), name)

        elif self.config.output_format == "html":
            output_path = output_dir / f"{name}_{timestamp}.html"
            return self.renderer.render_html(document, str(output_path), name)

        else:
            # Default to docx
            output_path = output_dir / f"{name}_{timestamp}.docx"
            return self.renderer.render_docx(document, str(output_path), name)


# =========================================
# Quick Functions
# =========================================

async def translate_business_document(
    input_path: str,
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese",
    output_format: str = "docx",
    provider: str = "openai"
) -> TranslationResult:
    """
    Quick function to translate a business document.

    Example:
        result = await translate_business_document(
            "quarterly_report.pdf",
            source_lang="Chinese",
            target_lang="Vietnamese"
        )
        print(f"Output: {result.output_path}")
        print(f"Tables: {result.total_tables}")
        print(f"Cost: ${result.estimated_cost:.2f}")
    """
    config = PipelineConfig(
        provider=provider,
        source_lang=source_lang,
        target_lang=target_lang,
        output_format=output_format
    )

    pipeline = LayoutPreservingPipeline(config)
    return await pipeline.translate_document(input_path)


def create_pipeline(
    provider: str = "openai",
    vision_model: str = "gpt-4o",
    translation_model: str = "gpt-4o-mini",
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese",
    output_format: str = "docx"
) -> LayoutPreservingPipeline:
    """
    Create a configured pipeline.

    Example:
        pipeline = create_pipeline(
            provider="openai",
            source_lang="Chinese",
            target_lang="Vietnamese"
        )

        result = await pipeline.translate_document("report.pdf")
    """
    config = PipelineConfig(
        provider=provider,
        vision_model=vision_model,
        translation_model=translation_model,
        source_lang=source_lang,
        target_lang=target_lang,
        output_format=output_format
    )
    return LayoutPreservingPipeline(config)


# =========================================
# CLI Interface
# =========================================

async def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="LLM-Native Layout-Preserving Document Translation"
    )
    parser.add_argument("input", help="Input PDF or image folder")
    parser.add_argument("-s", "--source", default="Chinese", help="Source language")
    parser.add_argument("-t", "--target", default="Vietnamese", help="Target language")
    parser.add_argument("-f", "--format", default="docx", choices=["docx", "md", "html"])
    parser.add_argument("-p", "--provider", default="openai", choices=["openai", "anthropic"])
    parser.add_argument("-o", "--output", default="./output", help="Output directory")

    args = parser.parse_args()

    print(f"""
+======================================================================+
|                                                                      |
|         LLM-Native Layout-Preserving Translation                     |
|                                                                      |
+======================================================================+

   Input:    {args.input}
   From:     {args.source}
   To:       {args.target}
   Format:   {args.format}
   Provider: {args.provider}
""")

    config = PipelineConfig(
        provider=args.provider,
        source_lang=args.source,
        target_lang=args.target,
        output_format=args.format,
        output_dir=args.output
    )

    pipeline = LayoutPreservingPipeline(config)

    def progress_callback(current, total, status):
        bar_length = 30
        filled = int(bar_length * current / total)
        bar = "=" * filled + "-" * (bar_length - filled)
        print(f"\r  [{bar}] {current}% - {status}", end="", flush=True)

    try:
        result = await pipeline.translate_document(
            args.input,
            on_progress=progress_callback
        )

        print(f"""

[OK] Translation Complete!

   Output:     {result.output_path}
   Pages:      {result.total_pages}
   Tables:     {result.total_tables}
   Time:       {result.processing_time:.1f}s
   Est. Cost:  ${result.estimated_cost:.2f}
""")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
