#!/usr/bin/env python3
"""
Tests for Image Embedding Module

Run: pytest tests/test_image_embedding.py -v
"""

import pytest
import tempfile
from pathlib import Path
import io

# Test imports
def test_imports():
    """Test that all modules can be imported"""
    from core.image_embedding import (
        ImageBlock,
        ImageFormat,
        ImagePosition,
        ImageExtractor,
        ExtractionConfig,
        DocxImageEmbedder,
        ImageEmbeddingPipeline,
        PipelineConfig,
        ProcessingResult,
    )
    assert ImageBlock is not None
    assert ImageExtractor is not None
    assert DocxImageEmbedder is not None


def test_image_format():
    """Test ImageFormat enum"""
    from core.image_embedding import ImageFormat

    assert ImageFormat.PNG.value == "png"
    assert ImageFormat.JPEG.value == "jpeg"

    # Test from_extension
    assert ImageFormat.from_extension("png") == ImageFormat.PNG
    assert ImageFormat.from_extension("jpg") == ImageFormat.JPEG
    assert ImageFormat.from_extension(".PNG") == ImageFormat.PNG


def test_image_position():
    """Test ImagePosition dataclass"""
    from core.image_embedding import ImagePosition

    pos = ImagePosition(
        page=1,
        x=100.0,
        y=200.0,
        width=300.0,
        height=400.0
    )

    assert pos.page == 1
    assert pos.x == 100.0

    # Test serialization
    d = pos.to_dict()
    assert d["page"] == 1
    assert d["width"] == 300.0

    # Test deserialization
    pos2 = ImagePosition.from_dict(d)
    assert pos2.page == pos.page
    assert pos2.width == pos.width


def test_image_block():
    """Test ImageBlock dataclass"""
    from core.image_embedding import ImageBlock, ImageFormat, ImagePosition

    # Create a simple 1x1 PNG
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])

    block = ImageBlock(
        image_data=png_data,
        format=ImageFormat.PNG,
        width_px=100,
        height_px=200,
        caption="Test image",
        image_id="test_001"
    )

    assert block.size_bytes == len(png_data)
    assert block.aspect_ratio == 0.5  # 100/200
    assert block.mime_type == "image/png"
    assert block.file_extension == "png"

    # Test base64
    b64 = block.to_base64()
    assert isinstance(b64, str)
    assert len(b64) > 0

    # Test data URI
    uri = block.to_data_uri()
    assert uri.startswith("data:image/png;base64,")

    # Test serialization
    d = block.to_dict(include_data=False)
    assert d["format"] == "png"
    assert d["width_px"] == 100
    assert "image_data_base64" not in d

    d_with_data = block.to_dict(include_data=True)
    assert "image_data_base64" in d_with_data


def test_extraction_config():
    """Test ExtractionConfig defaults"""
    from core.image_embedding import ExtractionConfig, ImageFormat

    config = ExtractionConfig()
    assert config.min_width == 50
    assert config.min_height == 50
    assert config.output_format == ImageFormat.PNG
    assert config.skip_duplicates is True


def test_pipeline_config():
    """Test PipelineConfig defaults"""
    from core.image_embedding import PipelineConfig

    config = PipelineConfig()
    assert config.min_image_size == 50
    assert config.max_width_ratio == 0.8
    assert config.with_captions is True


def test_processing_result():
    """Test ProcessingResult dataclass"""
    from core.image_embedding import ProcessingResult

    result = ProcessingResult(
        success=True,
        images_extracted=5,
        images_embedded=5,
        source_path="input.pdf",
        output_path="output.docx"
    )

    assert result.success is True
    assert result.images_extracted == 5

    d = result.to_dict()
    assert d["success"] is True
    assert d["images_extracted"] == 5


class TestImageExtractor:
    """Tests for ImageExtractor class"""

    def test_init(self):
        """Test extractor initialization"""
        from core.image_embedding import ImageExtractor

        extractor = ImageExtractor()
        assert extractor is not None
        assert extractor.config is not None

    def test_init_with_config(self):
        """Test extractor with custom config"""
        from core.image_embedding import ImageExtractor, ExtractionConfig

        config = ExtractionConfig(min_width=100, min_height=100)
        extractor = ImageExtractor(config)
        assert extractor.config.min_width == 100

    def test_file_not_found(self):
        """Test error handling for missing file"""
        from core.image_embedding import ImageExtractor

        extractor = ImageExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract_from_pdf("nonexistent.pdf")


class TestDocxEmbedder:
    """Tests for DocxImageEmbedder class"""

    def test_init(self):
        """Test embedder initialization"""
        from core.image_embedding import DocxImageEmbedder

        embedder = DocxImageEmbedder()
        assert embedder is not None
        assert embedder.max_width_ratio == 0.8

    def test_init_with_options(self):
        """Test embedder with custom options"""
        from core.image_embedding import DocxImageEmbedder

        embedder = DocxImageEmbedder(
            max_width_ratio=0.6,
            center_images=False
        )
        assert embedder.max_width_ratio == 0.6
        assert embedder.center_images is False

    def test_reset_counter(self):
        """Test figure counter reset"""
        from core.image_embedding import DocxImageEmbedder

        embedder = DocxImageEmbedder()
        embedder._figure_counter = 10
        embedder.reset_counter()
        assert embedder._figure_counter == 0


class TestImageEmbeddingPipeline:
    """Tests for ImageEmbeddingPipeline class"""

    def test_init(self):
        """Test pipeline initialization"""
        from core.image_embedding import ImageEmbeddingPipeline

        pipeline = ImageEmbeddingPipeline()
        assert pipeline is not None
        assert pipeline.extractor is not None
        assert pipeline.embedder is not None

    def test_init_with_config(self):
        """Test pipeline with custom config"""
        from core.image_embedding import ImageEmbeddingPipeline, PipelineConfig

        config = PipelineConfig(min_image_size=100)
        pipeline = ImageEmbeddingPipeline(config)
        assert pipeline.config.min_image_size == 100


# Integration test with real PDF (if available)
@pytest.mark.skipif(
    not Path("/Users/mac/ai-publisher-pro-public/tests/samples").exists(),
    reason="Sample PDFs not available"
)
class TestIntegration:
    """Integration tests with real files"""

    def test_extract_from_sample_pdf(self):
        """Test extraction from a sample PDF"""
        from core.image_embedding import ImageExtractor

        sample_dir = Path("/Users/mac/ai-publisher-pro-public/tests/samples")
        pdfs = list(sample_dir.glob("*.pdf"))

        if not pdfs:
            pytest.skip("No sample PDFs found")

        extractor = ImageExtractor()
        images = extractor.extract_from_pdf(pdfs[0])

        # Just verify it runs without error
        assert isinstance(images, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
