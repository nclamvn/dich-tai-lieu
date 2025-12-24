#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Block Flow Executor

Executes the block flow from LayoutIntentPackage:
- Apply spacing rules
- Handle transitions (page breaks, section breaks)
- Maintain block sequence

Version: 1.0.0
"""

from typing import List, Dict, Optional, Any, Generator
from dataclasses import dataclass, field
import logging

from core.contracts import (
    LayoutIntentPackage,
    Block,
    BlockType,
    SectionType,
    SpacingRule,
    TransitionType,
)

logger = logging.getLogger(__name__)


@dataclass
class FlowState:
    """Current state of block flow execution"""
    current_page: int = 1
    current_section: SectionType = SectionType.MAIN_BODY
    y_position: float = 0  # Current vertical position (for tracking)
    page_height: float = 792  # Default letter size in points
    margin_top: float = 72
    margin_bottom: float = 72
    content_height: float = 648  # page_height - margins

    def available_space(self) -> float:
        """Calculate available space on current page"""
        return self.content_height - self.y_position

    def new_page(self):
        """Start a new page"""
        self.current_page += 1
        self.y_position = 0

    def advance(self, height: float):
        """Advance position by height"""
        self.y_position += height


@dataclass
class FlowedBlock:
    """A block with flow information applied"""
    block: Block
    page_number: int
    y_start: float
    y_end: float
    actual_spacing_before: float
    actual_spacing_after: float
    page_break_before: bool = False

    def to_dict(self) -> Dict:
        return {
            "block_id": self.block.id,
            "page_number": self.page_number,
            "y_start": self.y_start,
            "y_end": self.y_end,
            "spacing_before": self.actual_spacing_before,
            "spacing_after": self.actual_spacing_after,
            "page_break_before": self.page_break_before,
        }


class BlockFlowExecutor:
    """
    Executes block flow according to LayoutIntentPackage.

    This is the core of Agent #3 - it takes the intent and
    produces a flowed document with exact positioning.

    Usage:
        executor = BlockFlowExecutor(page_size="A4")
        flowed_blocks = executor.execute(lip)
    """

    # Page sizes in points (width, height)
    PAGE_SIZES = {
        "letter": (612, 792),
        "A4": (595, 842),
        "A5": (420, 595),
        "B5": (516, 729),
    }

    # Default margins by template
    TEMPLATE_MARGINS = {
        "book": {"top": 72, "bottom": 72, "left": 90, "right": 72},
        "report": {"top": 72, "bottom": 72, "left": 72, "right": 72},
        "academic": {"top": 72, "bottom": 72, "left": 72, "right": 72},
        "legal": {"top": 72, "bottom": 72, "left": 72, "right": 72},
        "default": {"top": 72, "bottom": 72, "left": 72, "right": 72},
    }

    def __init__(
        self,
        page_size: str = "A4",
        template: str = "default",
        custom_margins: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize block flow executor.

        Args:
            page_size: Page size name (letter, A4, A5, B5)
            template: Template name for margin defaults
            custom_margins: Custom margin values
        """
        self.page_size = page_size
        self.template = template

        # Get page dimensions
        width, height = self.PAGE_SIZES.get(page_size, self.PAGE_SIZES["A4"])
        self.page_width = width
        self.page_height = height

        # Get margins
        margins = dict(self.TEMPLATE_MARGINS.get(template, self.TEMPLATE_MARGINS["default"]))
        if custom_margins:
            margins.update(custom_margins)
        self.margins = margins

        # Calculate content area
        self.content_width = width - margins["left"] - margins["right"]
        self.content_height = height - margins["top"] - margins["bottom"]

        logger.info(f"BlockFlowExecutor initialized: {page_size}, {template}")

    def execute(self, lip: LayoutIntentPackage) -> List[FlowedBlock]:
        """
        Execute block flow for entire document.

        Args:
            lip: LayoutIntentPackage from Agent #2

        Returns:
            List of FlowedBlocks with positioning
        """
        logger.info(f"Executing block flow for {len(lip.blocks)} blocks...")

        # Initialize state
        state = FlowState(
            page_height=self.page_height,
            margin_top=self.margins["top"],
            margin_bottom=self.margins["bottom"],
            content_height=self.content_height,
        )

        flowed_blocks: List[FlowedBlock] = []

        for i, block in enumerate(lip.blocks):
            # Handle transitions
            page_break = self._handle_transition(block, state)

            # Calculate spacing
            spacing_before = self._calculate_spacing_before(block, state, i == 0)

            # Estimate block height (simplified - actual would measure text)
            block_height = self._estimate_block_height(block)

            # Check if block fits
            total_height = spacing_before + block_height
            if total_height > state.available_space() and state.y_position > 0:
                state.new_page()
                spacing_before = 0  # No spacing at top of page
                page_break = True

            # Apply spacing before
            state.advance(spacing_before)

            # Record flow position
            y_start = state.y_position
            state.advance(block_height)
            y_end = state.y_position

            # Apply spacing after
            spacing_after = block.spacing.after if block.spacing else 0
            state.advance(spacing_after)

            # Create flowed block
            flowed = FlowedBlock(
                block=block,
                page_number=state.current_page,
                y_start=y_start,
                y_end=y_end,
                actual_spacing_before=spacing_before,
                actual_spacing_after=spacing_after,
                page_break_before=page_break,
            )

            flowed_blocks.append(flowed)

            # Update section
            state.current_section = block.section

        logger.info(f"Flow complete: {len(flowed_blocks)} blocks across {state.current_page} pages")

        return flowed_blocks

    def _handle_transition(self, block: Block, state: FlowState) -> bool:
        """Handle block transitions (page/section breaks)"""
        page_break = False

        if block.break_before == TransitionType.PAGE_BREAK:
            state.new_page()
            page_break = True

        elif block.break_before == TransitionType.SECTION_BREAK:
            state.new_page()
            page_break = True

        elif block.break_before == TransitionType.CHAPTER_BREAK:
            # Chapter starts on odd page (right-hand)
            state.new_page()
            if state.current_page % 2 == 0:  # Even page
                state.new_page()  # Skip to odd
            page_break = True

        return page_break

    def _calculate_spacing_before(
        self,
        block: Block,
        state: FlowState,
        is_first: bool,
    ) -> float:
        """Calculate actual spacing before block"""
        if is_first or state.y_position == 0:
            return 0  # No spacing at top of page

        if block.spacing:
            return block.spacing.before

        return 12  # Default spacing

    def _estimate_block_height(self, block: Block) -> float:
        """
        Estimate block height based on content.

        In production, this would actually measure rendered text.
        Here we use a simplified estimation.
        """
        # Base heights by type
        base_heights = {
            BlockType.TITLE: 48,
            BlockType.SUBTITLE: 24,
            BlockType.CHAPTER: 36,
            BlockType.SECTION: 24,
            BlockType.HEADING_1: 24,
            BlockType.HEADING_2: 20,
            BlockType.HEADING_3: 18,
            BlockType.PARAGRAPH: 14,
            BlockType.QUOTE: 14,
            BlockType.LIST: 14,
            BlockType.CODE: 12,
            BlockType.FOOTNOTE: 10,
        }

        base = base_heights.get(block.type, 14)

        # Estimate lines (rough: 80 chars per line)
        chars = len(block.content)
        lines = max(1, chars // 80 + 1)

        # Line spacing
        line_spacing = block.spacing.line_spacing if block.spacing else 1.5

        return base * lines * line_spacing

    def get_page_count(self, flowed_blocks: List[FlowedBlock]) -> int:
        """Get total page count"""
        if not flowed_blocks:
            return 0
        return max(fb.page_number for fb in flowed_blocks)

    def get_blocks_on_page(
        self,
        flowed_blocks: List[FlowedBlock],
        page: int,
    ) -> List[FlowedBlock]:
        """Get blocks on a specific page"""
        return [fb for fb in flowed_blocks if fb.page_number == page]
