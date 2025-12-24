#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consistency Module

Provides consistency checking and enforcement.
"""

from .engine import ConsistencyEngine, TermInconsistency, StyleInconsistency

__all__ = [
    "ConsistencyEngine",
    "TermInconsistency",
    "StyleInconsistency",
]
