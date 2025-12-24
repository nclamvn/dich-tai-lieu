#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Template - Abstract base class for document templates.

Provides the foundation for all document templates with standardized
configuration for heading styles, body text, page layout, and TOC.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from copy import deepcopy


@dataclass
class TemplateConfig:
    """
    Complete template configuration.

    Contains all styling information needed to format a document
    according to a specific template style.
    """
    # Identity
    name: str
    display_name: str
    description: str

    # Typography - Heading styles for H1, H2, H3, H4
    heading_styles: Dict[str, dict] = field(default_factory=dict)

    # Typography - Body paragraph style
    body_style: dict = field(default_factory=dict)

    # Page Layout
    page_size: str = "A4"  # A4, Letter
    margins: str = "normal"  # normal, narrow, wide, book

    # Header/Footer
    header_footer_style: str = "default"

    # Table of Contents
    toc_config: dict = field(default_factory=dict)

    # Special sections
    has_title_page: bool = False
    has_abstract: bool = False
    has_appendix: bool = False

    # Language
    language: str = "en"

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTemplate(ABC):
    """
    Abstract base class for document templates.

    All templates must inherit from this class and implement
    the required abstract methods to provide template-specific
    configuration.

    Usage:
        class MyTemplate(BaseTemplate):
            @property
            def name(self) -> str:
                return "my_template"
            ...
    """

    def __init__(self):
        """Initialize template with default configuration."""
        self._config: Optional[TemplateConfig] = None
        self._overrides: Dict[str, Any] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Template identifier.

        Returns:
            Unique string identifier for this template
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable name.

        Returns:
            Display name for UI/user-facing contexts
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Template description.

        Returns:
            Brief description of template purpose and style
        """
        pass

    @abstractmethod
    def get_config(self) -> TemplateConfig:
        """
        Get complete template configuration.

        Returns:
            TemplateConfig with all styling settings
        """
        pass

    def get_heading_styles(self) -> Dict[str, dict]:
        """
        Get heading styles (H1-H4).

        Returns:
            Dictionary mapping heading levels to style dicts
        """
        return self.get_config().heading_styles

    def get_heading_style(self, level: int) -> dict:
        """
        Get style for specific heading level.

        Args:
            level: Heading level (1-4)

        Returns:
            Style dictionary for the heading level
        """
        key = f"H{level}"
        styles = self.get_heading_styles()
        return styles.get(key, styles.get("H4", {}))

    def get_body_style(self) -> dict:
        """
        Get body paragraph style.

        Returns:
            Style dictionary for body paragraphs
        """
        return self.get_config().body_style

    def get_page_layout(self) -> dict:
        """
        Get page layout configuration.

        Returns:
            Dictionary with page_size and margins
        """
        config = self.get_config()
        return {
            "page_size": config.page_size,
            "margins": config.margins,
        }

    def get_toc_config(self) -> dict:
        """
        Get Table of Contents configuration.

        Returns:
            Dictionary with TOC settings
        """
        return self.get_config().toc_config

    def get_header_footer_style(self) -> str:
        """
        Get header/footer style name.

        Returns:
            Style name for header/footer
        """
        return self.get_config().header_footer_style

    def has_title_page(self) -> bool:
        """Check if template includes title page."""
        return self.get_config().has_title_page

    def has_abstract(self) -> bool:
        """Check if template includes abstract/summary."""
        return self.get_config().has_abstract

    def has_appendix(self) -> bool:
        """Check if template includes appendix."""
        return self.get_config().has_appendix

    def customize(self, **overrides) -> 'BaseTemplate':
        """
        Create customized version of template.

        Creates a new template instance with specified overrides
        applied to the configuration.

        Args:
            **overrides: Key-value pairs to override in config

        Returns:
            New template instance with overrides

        Example:
            custom = book_template.customize(
                margins="wide",
                page_size="Letter"
            )
        """
        # Create a copy of self
        customized = self.__class__()
        customized._overrides = {**self._overrides, **overrides}
        return customized

    def _apply_overrides(self, config: TemplateConfig) -> TemplateConfig:
        """
        Apply stored overrides to configuration.

        Args:
            config: Base configuration

        Returns:
            Configuration with overrides applied
        """
        if not self._overrides:
            return config

        # Create a deep copy to avoid modifying original
        config_dict = {
            "name": config.name,
            "display_name": config.display_name,
            "description": config.description,
            "heading_styles": deepcopy(config.heading_styles),
            "body_style": deepcopy(config.body_style),
            "page_size": config.page_size,
            "margins": config.margins,
            "header_footer_style": config.header_footer_style,
            "toc_config": deepcopy(config.toc_config),
            "has_title_page": config.has_title_page,
            "has_abstract": config.has_abstract,
            "has_appendix": config.has_appendix,
            "language": config.language,
            "metadata": deepcopy(config.metadata),
        }

        # Apply overrides
        for key, value in self._overrides.items():
            if key in config_dict:
                if isinstance(config_dict[key], dict) and isinstance(value, dict):
                    config_dict[key].update(value)
                else:
                    config_dict[key] = value

        return TemplateConfig(**config_dict)

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(name='{self.name}')>"
