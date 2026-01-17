# core/pdf_renderer_v2/__init__.py

"""
PDF Renderer V2 - Pandoc + WeasyPrint Pipeline

High-quality PDF rendering with CSS-based templates.
Quality: 95%+ (vs 40-70% with ReportLab V1)
"""

from .renderer import PDFRendererV2

__all__ = ['PDFRendererV2']
__version__ = '2.0.0'
