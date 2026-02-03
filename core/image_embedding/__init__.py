"""
Image Embedding Module - AI Publisher Pro

Extract images from PDFs and embed them into DOCX/PDF outputs.

Usage:
    from core.image_embedding import ImageExtractor, DocxImageEmbedder, ImageBlock

    # Extract images from PDF
    extractor = ImageExtractor()
    images = extractor.extract_from_pdf("input.pdf")

    # Embed into DOCX
    embedder = DocxImageEmbedder()
    embedder.embed_images(doc, images)

    # Or use the pipeline for complete workflow
    from core.image_embedding import extract_and_embed
    result = extract_and_embed("input.pdf", "output.docx")
"""

from .models import ImageBlock, ImageFormat, ImagePosition
from .extractor import ImageExtractor, ExtractionConfig, extract_images
from .docx_embedder import DocxImageEmbedder, create_document_with_images
from .pdf_embedder import (
    PdfImageEmbedder,
    create_pdf_with_images,
    add_images_to_pdf_flowables,
)
from .cover_embedder import (
    CoverEmbedder,
    add_cover_to_document,
    decode_cover_image,
)
from .pipeline import (
    ImageEmbeddingPipeline,
    PipelineConfig,
    ProcessingResult,
    extract_and_embed,
    add_images_to_document,
    save_extracted_images,
)

__all__ = [
    # Models
    "ImageBlock",
    "ImageFormat",
    "ImagePosition",
    # Extractor
    "ImageExtractor",
    "ExtractionConfig",
    "extract_images",
    # DOCX Embedder
    "DocxImageEmbedder",
    "create_document_with_images",
    # PDF Embedder
    "PdfImageEmbedder",
    "create_pdf_with_images",
    "add_images_to_pdf_flowables",
    # Cover Embedder
    "CoverEmbedder",
    "add_cover_to_document",
    "decode_cover_image",
    # Pipeline
    "ImageEmbeddingPipeline",
    "PipelineConfig",
    "ProcessingResult",
    "extract_and_embed",
    "add_images_to_document",
    "save_extracted_images",
]
