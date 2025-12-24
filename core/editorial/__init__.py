#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Editorial Core Module (Agent #2)

Transforms ManuscriptCoreOutput into LayoutIntentPackage.

Components:
- ConsistencyEngine: Terminology and style consistency
- IntentMapper: Layout intent mapping
- LIPBuilder: Package builder

Usage:
    from core.editorial import EditorialAgent

    agent = EditorialAgent(template="book")
    lip = agent.process(manuscript_output)

    # Get JSON for Agent #3
    lip_json = lip.to_json()

Version: 1.0.0
"""

from .agent import EditorialAgent
from .consistency.engine import ConsistencyEngine
from .intent.mapper import IntentMapper
from .packager.lip_builder import LIPBuilder

__all__ = [
    "EditorialAgent",
    "ConsistencyEngine",
    "IntentMapper",
    "LIPBuilder",
]

__version__ = "1.0.0"
