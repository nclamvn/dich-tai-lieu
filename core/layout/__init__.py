#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layout Core Module (Agent #3)

Transforms LayoutIntentPackage into publish-ready documents.

Components:
- BlockFlowExecutor: Execute block flow
- SectionManager: Manage sections and numbering
- DocxRenderer: Render to DOCX

Usage:
    from core.layout import LayoutAgent

    agent = LayoutAgent(template="book", page_size="A4")
    output_path = agent.process(lip, "output.docx")

Version: 1.0.0
"""

from .agent import LayoutAgent
from .executor.block_flow import BlockFlowExecutor, FlowedBlock, FlowState
from .sections.manager import SectionManager, SectionConfig, PageInfo, NumberingStyle
from .renderer.docx_renderer import DocxRenderer

__all__ = [
    "LayoutAgent",
    "BlockFlowExecutor",
    "FlowedBlock",
    "FlowState",
    "SectionManager",
    "SectionConfig",
    "PageInfo",
    "NumberingStyle",
    "DocxRenderer",
]

__version__ = "1.0.0"
