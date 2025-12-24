"""
Phase 2.1 + 2.2 - LaTeX Source Pipeline

This module handles LaTeX source ingestion and translation for arXiv papers.

Metadata Fields (stored in job.metadata dict):
    latex_source_path (str): Path to original LaTeX source (.tex or archive)
    latex_main_tex (str): Path to extracted main .tex file
    has_latex_source (bool): True if job was created from LaTeX source
    latex_archive_type (str): Archive format ("zip", "tar.gz", "direct")

Phase 2.1 Example usage:
    >>> from core.latex.latex_ingest import LaTeXSourceIngestor
    >>> ingestor = LaTeXSourceIngestor()
    >>> main_tex, error = ingestor.ingest("paper.zip")
    >>> if main_tex:
    ...     job.metadata['has_latex_source'] = True
    ...     job.metadata['latex_source_path'] = "paper.zip"
    ...     job.metadata['latex_main_tex'] = main_tex

Phase 2.2.0 Example usage:
    >>> from core.latex.eq_splitter import split_latex_equations
    >>> result = split_latex_equations("Given $f$ in $H$ where $ ... $")
    >>> if result.is_confident:
    ...     for eq in result.equation_segments:
    ...         convert_to_omml(eq)
"""

from core.latex.latex_ingest import LaTeXSourceIngestor
from core.latex.eq_splitter import (
    SplitEquationResult,
    split_latex_equations,
    get_splitter_statistics,
)

__all__ = [
    'LaTeXSourceIngestor',
    'SplitEquationResult',
    'split_latex_equations',
    'get_splitter_statistics',
]
