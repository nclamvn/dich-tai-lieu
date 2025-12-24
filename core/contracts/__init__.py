#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Contracts Module

Defines formal contracts for communication between APS agents:
- Agent #1 (Manuscript Core) -> ManuscriptCoreOutput
- Agent #2 (Editorial Core) -> LayoutIntentPackage
- Agent #3 (Layout Core) -> Final document output

Usage:
    from core.contracts import (
        ManuscriptCoreOutput,
        LayoutIntentPackage,
        ContractValidator,
    )

    # Create manuscript output from Agent #1
    output = ManuscriptCoreOutput(
        source_language="ja",
        target_language="vi",
        segments=[...],
    )

    # Validate
    validator = ContractValidator()
    validator.validate_or_raise(output)

    # Serialize for Agent #2
    json_str = output.to_json()

    # Agent #2 receives and deserializes
    received_output = ManuscriptCoreOutput.from_json(json_str)

    # Agent #2 creates LayoutIntentPackage
    lip = LayoutIntentPackage(
        title="Document Title",
        template="book",
        blocks=[...],
    )

    # Validate chain
    validator.validate_chain(output, lip)

Version: 1.0.0
Author: AI Publishing System (APS)
"""

from .base import (
    BaseContract,
    ContractMetadata,
    ContractError,
    ContractValidationError,
)

from .manuscript_output import (
    ManuscriptCoreOutput,
    Segment,
    SegmentType,
    DocumentStructure,
    QualityMetrics,
)

from .layout_intent import (
    LayoutIntentPackage,
    Block,
    BlockType,
    SectionDefinition,
    SectionType,
    SpacingRule,
    TransitionType,
    ConsistencyReport,
)

from .validation import (
    ContractValidator,
    validate_manuscript_to_lip,
    create_contract_summary,
)

__all__ = [
    # Base
    "BaseContract",
    "ContractMetadata",
    "ContractError",
    "ContractValidationError",

    # Agent #1 Output (Manuscript Core)
    "ManuscriptCoreOutput",
    "Segment",
    "SegmentType",
    "DocumentStructure",
    "QualityMetrics",

    # Agent #2 Output (Layout Intent Package)
    "LayoutIntentPackage",
    "Block",
    "BlockType",
    "SectionDefinition",
    "SectionType",
    "SpacingRule",
    "TransitionType",
    "ConsistencyReport",

    # Validation
    "ContractValidator",
    "validate_manuscript_to_lip",
    "create_contract_summary",
]

__version__ = "1.0.0"
