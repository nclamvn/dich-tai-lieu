#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Editorial Agent (Agent #2)

Main orchestrator for the Editorial Core.
Takes ManuscriptCoreOutput and produces LayoutIntentPackage.

Version: 1.0.0
"""

from typing import Optional, Dict, Any, List, Tuple
import logging

from core.contracts import (
    ManuscriptCoreOutput,
    LayoutIntentPackage,
    ContractValidator,
    Block,
    SectionDefinition,
    ConsistencyReport,
)

from .consistency.engine import ConsistencyEngine
from .intent.mapper import IntentMapper
from .packager.lip_builder import LIPBuilder

logger = logging.getLogger(__name__)


class EditorialAgent:
    """
    Agent #2 - Editorial Core

    Responsibilities:
    1. Check consistency (terminology, style, numbering)
    2. Map segments to layout intent blocks
    3. Define sections and transitions
    4. Generate Layout Intent Package (LIP)

    Usage:
        agent = EditorialAgent(template="book")
        lip = agent.process(manuscript_output)

        # Or step by step:
        report = agent.check_consistency(manuscript)
        blocks, sections = agent.map_intent(manuscript)
        lip = agent.build_package(manuscript, blocks, sections, report)
    """

    def __init__(
        self,
        template: str = "default",
        strict_consistency: bool = False,
        auto_fix: bool = True,
    ):
        """
        Initialize Editorial Agent.

        Args:
            template: Template to use (book, report, academic, legal)
            strict_consistency: If True, fail on any consistency issue
            auto_fix: If True, attempt to auto-fix consistency issues
        """
        self.template = template
        self.strict_consistency = strict_consistency
        self.auto_fix = auto_fix

        # Initialize components
        self.consistency_engine = ConsistencyEngine(strict=strict_consistency)
        self.intent_mapper = IntentMapper(template=template)
        self.lip_builder = LIPBuilder(template=template)
        self.validator = ContractValidator()

        logger.info(f"EditorialAgent initialized with template={template}")

    def process(
        self,
        manuscript: ManuscriptCoreOutput,
    ) -> LayoutIntentPackage:
        """
        Process manuscript through full editorial pipeline.

        Args:
            manuscript: Output from Agent #1 (Manuscript Core)

        Returns:
            LayoutIntentPackage for Agent #3 (Layout Core)
        """
        logger.info("=== AGENT #2: Editorial Core Processing ===")

        # 1. Validate input contract
        logger.info("Step 1: Validating input contract...")
        self.validator.validate_or_raise(manuscript)

        # 2. Check consistency
        logger.info("Step 2: Checking consistency...")
        report = self.check_consistency(manuscript)

        # 3. Auto-fix if enabled
        if self.auto_fix and report.unresolved_count > 0:
            logger.info("Step 2b: Auto-fixing consistency issues...")
            manuscript = self.consistency_engine.auto_fix(manuscript, report)

        # 4. Map intent
        logger.info("Step 3: Mapping layout intent...")
        blocks, sections = self.map_intent(manuscript)

        # 5. Build package
        logger.info("Step 4: Building Layout Intent Package...")
        lip = self.build_package(manuscript, blocks, sections, report)

        # 6. Validate output contract
        logger.info("Step 5: Validating output contract...")
        self.validator.validate_or_raise(lip)

        logger.info("=== Editorial Core Processing Complete ===")
        logger.info(f"Output: {len(lip.blocks)} blocks, {len(lip.sections)} sections")

        return lip

    def check_consistency(
        self,
        manuscript: ManuscriptCoreOutput,
    ) -> ConsistencyReport:
        """
        Run consistency checks on manuscript.

        Args:
            manuscript: Input manuscript

        Returns:
            ConsistencyReport
        """
        return self.consistency_engine.check(manuscript)

    def map_intent(
        self,
        manuscript: ManuscriptCoreOutput,
    ) -> Tuple[List[Block], List[SectionDefinition]]:
        """
        Map manuscript to layout intent.

        Args:
            manuscript: Input manuscript

        Returns:
            Tuple of (blocks, sections)
        """
        return self.intent_mapper.map(manuscript)

    def build_package(
        self,
        manuscript: ManuscriptCoreOutput,
        blocks: List[Block],
        sections: List[SectionDefinition],
        report: ConsistencyReport,
    ) -> LayoutIntentPackage:
        """
        Build final Layout Intent Package.

        Args:
            manuscript: Original manuscript
            blocks: Mapped blocks
            sections: Section definitions
            report: Consistency report

        Returns:
            LayoutIntentPackage
        """
        return self.lip_builder.build(manuscript, blocks, sections, report)

    @classmethod
    def from_json(cls, json_str: str, **kwargs) -> LayoutIntentPackage:
        """
        Process manuscript from JSON string.

        Args:
            json_str: ManuscriptCoreOutput as JSON
            **kwargs: Agent init arguments

        Returns:
            LayoutIntentPackage
        """
        manuscript = ManuscriptCoreOutput.from_json(json_str)
        agent = cls(**kwargs)
        return agent.process(manuscript)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary with agent stats
        """
        return {
            "template": self.template,
            "strict_consistency": self.strict_consistency,
            "auto_fix": self.auto_fix,
        }
