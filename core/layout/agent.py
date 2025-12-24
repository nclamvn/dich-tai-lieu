#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layout Agent (Agent #3)

Main orchestrator for the Layout Core.
Takes LayoutIntentPackage and produces publish-ready documents.

Version: 1.0.0
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from core.contracts import (
    LayoutIntentPackage,
    ContractValidator,
)

from .executor.block_flow import BlockFlowExecutor, FlowedBlock
from .sections.manager import SectionManager
from .renderer.docx_renderer import DocxRenderer
from .renderer.docx_renderer_optimized import OptimizedDocxRenderer
from .renderer.docx_template_renderer import TemplateDocxRenderer, ensure_templates_exist
from .renderer.pdf_renderer import PDFRenderer
from .renderer.epub_renderer import EPUBRenderer

logger = logging.getLogger(__name__)


class LayoutAgent:
    """
    Agent #3 - Layout Core

    Responsibilities:
    1. Execute block flow with spacing
    2. Manage sections and numbering
    3. Render to output formats (DOCX, PDF, EPUB)

    Usage:
        agent = LayoutAgent(template="book", page_size="A4")
        output_path = agent.process(lip, "output.docx")

        # Or step by step:
        flowed = agent.execute_flow(lip)
        agent.setup_sections(lip, flowed)
        path = agent.render(lip, flowed, "output.docx")
    """

    def __init__(
        self,
        template: str = "default",
        page_size: str = "A4",
        output_format: str = "docx",
        language: str = "vi",
        use_optimized: bool = True,
        use_template: bool = False,  # Default False - Optimized is faster
    ):
        """
        Initialize Layout Agent.

        Args:
            template: Template name (book, report, academic, legal)
            page_size: Page size (A4, letter, A5, B5)
            output_format: Output format (docx, pdf, epub)
            language: Document language (vi, en, ja, etc.)
            use_optimized: Use optimized renderer (fastest - 1.14x speedup)
            use_template: Use template-based renderer (has parsing overhead)
        """
        self.template = template
        self.page_size = page_size
        self.output_format = output_format
        self.language = language
        self.use_optimized = use_optimized
        self.use_template = use_template

        # Initialize components
        self.flow_executor = BlockFlowExecutor(
            page_size=page_size,
            template=template,
        )
        self.section_manager = SectionManager()
        self.validator = ContractValidator()

        # Choose DOCX renderer based on flags (priority: template > optimized > original)
        if use_template:
            ensure_templates_exist()
            docx_renderer = TemplateDocxRenderer(template=template, page_size=page_size)
        elif use_optimized:
            docx_renderer = OptimizedDocxRenderer(template=template, page_size=page_size)
        else:
            docx_renderer = DocxRenderer(template=template, page_size=page_size)

        # Renderers
        self.renderers: Dict[str, Any] = {
            "docx": docx_renderer,
            "pdf": PDFRenderer(template=template, page_size=page_size),
            "epub": EPUBRenderer(template=template, language=language),
        }

        renderer_type = "template" if use_template else ("optimized" if use_optimized else "original")
        logger.info(f"LayoutAgent initialized: {template}, {page_size}, {output_format}, {language}, renderer={renderer_type}")

    def process(
        self,
        lip: LayoutIntentPackage,
        output_path: str,
    ) -> Path:
        """
        Process LIP through full layout pipeline.

        Args:
            lip: LayoutIntentPackage from Agent #2
            output_path: Output file path

        Returns:
            Path to created file
        """
        logger.info("=== AGENT #3: Layout Core Processing ===")

        # 1. Validate input contract
        logger.info("Step 1: Validating input contract...")
        self.validator.validate_or_raise(lip)

        # 2. Execute block flow
        logger.info("Step 2: Executing block flow...")
        flowed_blocks = self.execute_flow(lip)

        # 3. Setup sections
        logger.info("Step 3: Setting up sections...")
        self.setup_sections(lip, flowed_blocks)

        # 4. Render output
        logger.info("Step 4: Rendering output...")
        output = self.render(lip, flowed_blocks, output_path)

        logger.info("=== Layout Core Processing Complete ===")
        logger.info(f"Output: {output}")

        return output

    def execute_flow(self, lip: LayoutIntentPackage) -> List[FlowedBlock]:
        """
        Execute block flow.

        Args:
            lip: LayoutIntentPackage

        Returns:
            List of FlowedBlocks
        """
        return self.flow_executor.execute(lip)

    def setup_sections(
        self,
        lip: LayoutIntentPackage,
        flowed_blocks: List[FlowedBlock],
    ):
        """
        Setup section management.

        Args:
            lip: LayoutIntentPackage
            flowed_blocks: Flowed blocks
        """
        self.section_manager.configure_sections(lip)
        self.section_manager.assign_pages(flowed_blocks)

    def render(
        self,
        lip: LayoutIntentPackage,
        flowed_blocks: List[FlowedBlock],
        output_path: str,
    ) -> Path:
        """
        Render to output file.

        Args:
            lip: LayoutIntentPackage
            flowed_blocks: Flowed blocks
            output_path: Output path

        Returns:
            Path to created file
        """
        # Determine format from extension or setting
        path = Path(output_path)
        ext = path.suffix.lower().lstrip('.')

        if ext not in self.renderers:
            ext = self.output_format

        renderer = self.renderers.get(ext)

        if renderer is None:
            raise ValueError(f"Unsupported output format: {ext}")

        return renderer.render(
            lip,
            flowed_blocks,
            output_path,
            self.section_manager,
        )

    def get_stats(self, flowed_blocks: List[FlowedBlock]) -> Dict[str, Any]:
        """Get layout statistics"""
        return {
            "total_blocks": len(flowed_blocks),
            "total_pages": self.flow_executor.get_page_count(flowed_blocks),
            "sections": len(self.section_manager.section_pages),
        }

    @classmethod
    def from_json(cls, json_str: str, output_path: str, **kwargs) -> Path:
        """
        Process LIP from JSON string.

        Args:
            json_str: LayoutIntentPackage as JSON
            output_path: Output path
            **kwargs: Agent init arguments

        Returns:
            Path to created file
        """
        lip = LayoutIntentPackage.from_json(json_str)
        agent = cls(**kwargs)
        return agent.process(lip, output_path)
