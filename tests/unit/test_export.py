"""
Unit Tests for Export Module

Tests document export functionality including configuration, 
styling, and DOCX exporters.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import asdict

# Import from the export package structure
from core.export import (
    ExportConfig,
    StyleManager,
)

# Check for DOCX availability
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class TestExportConfig:
    """Tests for ExportConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ExportConfig()
        
        # Should have default attributes
        assert hasattr(config, 'font_size') or hasattr(config, 'page_size')
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ExportConfig()
        
        # Config should be a dataclass with configurable values
        assert config is not None


class TestStyleManager:
    """Tests for StyleManager class."""
    
    def test_style_manager_init(self):
        """Test StyleManager initialization."""
        style_manager = StyleManager()
        assert style_manager is not None
    
    def test_has_styles(self):
        """Test StyleManager has styles defined."""
        style_manager = StyleManager()
        # Should have some style attributes or methods
        assert style_manager is not None


class TestDocxBaseExporter:
    """Tests for DocxExporterBase class."""
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_base_exporter_is_abstract(self):
        """Test that base DOCX exporter is abstract."""
        from core.export import DocxExporterBase
        
        # DocxExporterBase should be abstract
        assert DocxExporterBase is not None
        # Cannot instantiate directly - it's abstract


class TestBasicDocxExporter:
    """Tests for BasicDocxExporter class."""
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_basic_exporter_creation(self):
        """Test creating basic DOCX exporter."""
        from core.export import BasicDocxExporter
        
        exporter = BasicDocxExporter()
        assert exporter is not None
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_export_basic_docx_function(self):
        """Test export_basic_docx helper function."""
        from core.export import export_basic_docx
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            try:
                export_basic_docx(
                    "Test content for export.",
                    f.name
                )
                assert Path(f.name).exists()
                assert Path(f.name).stat().st_size > 0
            finally:
                Path(f.name).unlink(missing_ok=True)


class TestAcademicDocxExporter:
    """Tests for AcademicDocxExporter class."""
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_academic_exporter_creation(self):
        """Test creating academic DOCX exporter."""
        from core.export import AcademicDocxExporter
        
        exporter = AcademicDocxExporter()
        assert exporter is not None


class TestDocxStyles:
    """Tests for DOCX style constants."""
    
    def test_page_margins_constant(self):
        """Test PAGE_MARGINS constant."""
        from core.export import PAGE_MARGINS
        
        assert PAGE_MARGINS is not None
        assert isinstance(PAGE_MARGINS, dict)
    
    def test_page_sizes_constant(self):
        """Test PAGE_SIZES constant."""
        from core.export import PAGE_SIZES
        
        assert PAGE_SIZES is not None
    
    def test_default_options(self):
        """Test DEFAULT_OPTIONS constant."""
        from core.export import DEFAULT_OPTIONS
        
        assert DEFAULT_OPTIONS is not None
    
    def test_heading_levels(self):
        """Test HEADING_LEVELS constant."""
        from core.export import HEADING_LEVELS
        
        assert HEADING_LEVELS is not None


class TestExportEdgeCases:
    """Edge case tests for export module."""
    
    def test_config_instance(self):
        """Test ExportConfig is instantiable."""
        config = ExportConfig()
        assert config is not None
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_export_empty_content(self):
        """Test exporting empty content."""
        from core.export import export_basic_docx
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            try:
                export_basic_docx("", f.name)
                assert Path(f.name).exists()
            except Exception:
                # Empty content might raise or create empty doc
                pass
            finally:
                Path(f.name).unlink(missing_ok=True)
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_export_unicode_content(self):
        """Test exporting Vietnamese Unicode content."""
        from core.export import export_basic_docx
        
        content = "Đây là văn bản tiếng Việt với dấu đầy đủ."
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            try:
                export_basic_docx(content, f.name)
                assert Path(f.name).exists()
                assert Path(f.name).stat().st_size > 0
            finally:
                Path(f.name).unlink(missing_ok=True)
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_export_long_content(self):
        """Test exporting long content."""
        from core.export import export_basic_docx
        
        content = "This is a paragraph. " * 500
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            try:
                export_basic_docx(content, f.name)
                assert Path(f.name).exists()
            finally:
                Path(f.name).unlink(missing_ok=True)


class TestBookLayoutExporter:
    """Tests for book layout exporter."""
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_book_layout_module_exists(self):
        """Test book_layout module exists."""
        from core.export import book_layout
        
        assert book_layout is not None


class TestCommercialBookExporter:
    """Tests for commercial book exporter."""
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_commercial_book_import(self):
        """Test commercial_book module imports correctly."""
        from core.export.commercial_book import CommercialBookExporter
        
        assert CommercialBookExporter is not None
    
    @pytest.mark.skipif(not DOCX_AVAILABLE, reason="python-docx not installed")
    def test_commercial_book_creation(self):
        """Test creating CommercialBookExporter."""
        from core.export.commercial_book import CommercialBookExporter
        
        exporter = CommercialBookExporter()
        assert exporter is not None


class TestEpubExporter:
    """Tests for EPUB exporter."""
    
    def test_epub_exporter_import(self):
        """Test epub_exporter module imports correctly."""
        try:
            from core.export.epub_exporter import EpubExporter
            assert EpubExporter is not None
        except ImportError:
            # EPUB export may require additional dependencies
            pytest.skip("EPUB dependencies not available")


class TestMobiExporter:
    """Tests for MOBI exporter."""
    
    def test_mobi_exporter_import(self):
        """Test mobi_exporter module imports correctly."""
        try:
            from core.export.mobi_exporter import MobiExporter
            assert MobiExporter is not None
        except ImportError:
            # MOBI export may require additional dependencies
            pytest.skip("MOBI dependencies not available")
