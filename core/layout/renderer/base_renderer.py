#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Renderer Interface

Defines common interface for all renderers.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path

from core.contracts import LayoutIntentPackage

if TYPE_CHECKING:
    from ..executor.block_flow import FlowedBlock
    from ..sections.manager import SectionManager


class BaseRenderer(ABC):
    """
    Abstract base class for document renderers.

    All renderers must implement:
    - render(): Main rendering method
    - supports_format(): Check if format is supported
    """

    def __init__(
        self,
        template: str = "default",
        page_size: str = "A4",
    ):
        """
        Initialize renderer.

        Args:
            template: Template name
            page_size: Page size (A4, letter, A5, B5)
        """
        self.template = template
        self.page_size = page_size

    @abstractmethod
    def render(
        self,
        lip: LayoutIntentPackage,
        flowed_blocks: List,  # List[FlowedBlock]
        output_path: str,
        section_manager: Optional[Any] = None,
    ) -> Path:
        """
        Render to output file.

        Args:
            lip: LayoutIntentPackage
            flowed_blocks: Flowed blocks from executor
            output_path: Output file path
            section_manager: Optional section manager

        Returns:
            Path to created file
        """
        pass

    @classmethod
    @abstractmethod
    def supports_format(cls, format_name: str) -> bool:
        """Check if renderer supports given format"""
        pass

    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """Get list of supported formats"""
        return []
