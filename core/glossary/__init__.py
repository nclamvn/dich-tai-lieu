"""
Glossary Management Module
AI Publisher Pro - Terminology consistency for translations

Features:
- Glossary CRUD operations
- Term management with import/export
- Term matching engine
- Prompt injection for LLM
- Pre-built glossaries (Medical, Legal, Tech, Finance, Academic)

Usage:
    from core.glossary import GlossaryService, TermMatcher

    # Create glossary
    service = GlossaryService()
    glossary = await service.create_glossary(data)

    # Find matches
    matcher = TermMatcher()
    matches = matcher.find_matches(text, glossary_id)
"""

from .service import GlossaryService
from .matcher import TermMatcher
from .injector import GlossaryInjector
from .models import Glossary, GlossaryTerm

__all__ = [
    "GlossaryService",
    "TermMatcher",
    "GlossaryInjector",
    "Glossary",
    "GlossaryTerm",
]

__version__ = "1.0.0"
