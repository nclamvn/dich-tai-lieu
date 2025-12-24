"""
Phase 2.1.0 - arXiv Integration Helper

Simple integration layer to inject LaTeX source into the translation pipeline.
"""

from pathlib import Path
from typing import Optional, List
from core.arxiv_equation_mapper import ArxivEquationMapper, EquationMapping
from core.arxiv_latex_extractor import LatexEquation

from config.logging_config import get_logger
logger = get_logger(__name__)


class ArxivLatexIntegration:
    """
    Integration helper for Phase 2.1.0 arXiv LaTeX extraction.

    Automatically detects .tar.gz files and provides LaTeX lookup for equations.
    """

    def __init__(self, pdf_path: str):
        """
        Initialize integration for a PDF file.

        Args:
            pdf_path: Path to PDF file (e.g., arXiv-1509.05363v6.pdf)
        """
        self.pdf_path = Path(pdf_path)
        self.mapper: Optional[ArxivEquationMapper] = None
        self.tar_gz_path: Optional[Path] = None
        self.enabled = False

        # Auto-detect .tar.gz
        self._detect_and_load()

    def _detect_and_load(self):
        """
        Detect if .tar.gz exists and load equations if found.

        Search locations (in order):
        1. Same directory as PDF
        2. Project root (for uploaded files in uploads/ subdirectory)
        3. Parent directories
        """
        import re

        # Look for .tar.gz with same base name in same directory
        tar_gz_path = self.pdf_path.with_suffix('.tar.gz')

        logger.debug(f"Searching for .tar.gz for {self.pdf_path.name}")
        logger.debug(f"PDF path: {self.pdf_path}")
        logger.debug(f"Try #1 (same dir): {tar_gz_path}")

        if not tar_gz_path.exists():
            # Try other common patterns in same directory
            stem_without_prefix = self.pdf_path.stem.replace('arXiv-', '').replace('arxiv-', '')
            alt_tar_gz = self.pdf_path.parent / f"{stem_without_prefix}.tar.gz"
            logger.debug(f"Try #2 (no prefix): {alt_tar_gz}")

            if alt_tar_gz.exists():
                tar_gz_path = alt_tar_gz
            else:
                # Extract original arXiv filename from uploaded filename
                # Example: 64b149d536c14d8eb9a4388f6b6e329d_arXiv-1509.05363v6.pdf -> arXiv-1509.05363v6
                # Pattern: hash_original_name.pdf -> original_name
                filename = self.pdf_path.stem

                # Remove hash prefix if present (pattern: [hexchars]_filename)
                original_name = re.sub(r'^[0-9a-f]{32}_', '', filename)
                logger.debug(f"Extracted original name: {original_name}")

                # Search in project root directory
                # Get project root (go up from uploads/ if needed)
                project_root = self.pdf_path.parent
                if project_root.name == 'uploads':
                    project_root = project_root.parent

                root_tar_gz = project_root / f"{original_name}.tar.gz"
                logger.debug(f"Try #3 (project root): {root_tar_gz}")

                if root_tar_gz.exists():
                    tar_gz_path = root_tar_gz
                    logger.debug("Found .tar.gz in project root!")
                else:
                    # Also try without arXiv- prefix in project root
                    name_no_prefix = original_name.replace('arXiv-', '').replace('arxiv-', '')
                    root_tar_gz_no_prefix = project_root / f"{name_no_prefix}.tar.gz"
                    logger.debug(f"Try #4 (root, no prefix): {root_tar_gz_no_prefix}")

                    if root_tar_gz_no_prefix.exists():
                        tar_gz_path = root_tar_gz_no_prefix
                        logger.debug("Found .tar.gz in project root (no prefix)!")
                    else:
                        logger.debug(f"No .tar.gz found for {self.pdf_path.name}, Phase 2.1.0 disabled")
                        return

        # Load equations
        try:
            logger.info(f"📦 Phase 2.1.0: Found LaTeX source: {tar_gz_path.name}")
            self.tar_gz_path = tar_gz_path
            self.mapper = ArxivEquationMapper(str(tar_gz_path))
            equations = self.mapper.extract_equations()

            if equations:
                self.enabled = True
                stats = self.mapper.get_statistics()
                logger.info(
                    f"   Extracted {stats['total_equations']} equations "
                    f"({stats['inline']} inline, {stats['display']} display, {stats['environment']} env)"
                )
            else:
                logger.warning(f"No equations extracted from {tar_gz_path.name}")

        except Exception as e:
            logger.error(f"Failed to load LaTeX from {tar_gz_path}: {e}")
            self.enabled = False

    def get_latex_for_text(
        self,
        pdf_text: str,
        min_confidence: float = 0.5
    ) -> Optional[str]:
        """
        Get LaTeX source for given PDF-extracted text.

        Args:
            pdf_text: Text extracted from PDF (may be broken Unicode)
            min_confidence: Minimum match confidence (0.0 to 1.0)

        Returns:
            LaTeX source string if match found, None otherwise
        """
        if not self.enabled or not self.mapper:
            return None

        try:
            mapping = self.mapper.map_pdf_text_to_latex(
                pdf_text=pdf_text,
                page_num=0,  # We don't track page numbers in this simple version
                char_offset=0,
                min_confidence=min_confidence
            )

            if mapping:
                logger.debug(
                    f"✓ Phase 2.1.0: Mapped equation (confidence: {mapping.confidence:.2%})"
                )
                return mapping.latex_source.latex

            return None

        except Exception as e:
            logger.error(f"Error mapping equation: {e}")
            return None

    def is_enabled(self) -> bool:
        """Check if Phase 2.1.0 is enabled for this document."""
        return self.enabled

    def get_stats(self) -> dict:
        """Get statistics about extracted equations."""
        if not self.enabled or not self.mapper:
            return {
                'enabled': False,
                'total_equations': 0
            }

        stats = self.mapper.get_statistics()
        stats['enabled'] = True
        stats['tar_gz_path'] = str(self.tar_gz_path)
        return stats


def create_arxiv_integration(input_file: str) -> Optional[ArxivLatexIntegration]:
    """
    Factory function to create ArxivLatexIntegration if applicable.

    Args:
        input_file: Path to input file

    Returns:
        ArxivLatexIntegration instance if PDF, None otherwise
    """
    file_path = Path(input_file)

    # Only for PDF files
    if file_path.suffix.lower() != '.pdf':
        return None

    try:
        integration = ArxivLatexIntegration(str(file_path))

        if integration.is_enabled():
            logger.info(f"✅ Phase 2.1.0 active for {file_path.name}")
            return integration
        else:
            logger.debug(f"Phase 2.1.0 not applicable for {file_path.name}")
            return None

    except Exception as e:
        logger.error(f"Failed to create arXiv integration: {e}")
        return None


def enrich_docnodes_with_latex(
    doc_nodes: List,
    arxiv_integration: Optional[ArxivLatexIntegration],
    min_confidence: float = 0.5
) -> int:
    """
    Enrich equation DocNodes with LaTeX source from arXiv extraction.

    This is a post-processing step that adds 'latex_source' to equation node metadata.

    Args:
        doc_nodes: List of DocNode objects from semantic extraction
        arxiv_integration: ArxivLatexIntegration instance (can be None)
        min_confidence: Minimum match confidence (0.0 to 1.0)

    Returns:
        Number of equations successfully enriched
    """
    if not arxiv_integration or not arxiv_integration.is_enabled():
        return 0

    enriched_count = 0

    try:
        for node in doc_nodes:
            # Only process equation nodes
            if not node.is_equation():
                continue

            # Get PDF-extracted text
            pdf_text = node.text

            if not pdf_text:
                continue

            # Try to get proper LaTeX source
            latex_source = arxiv_integration.get_latex_for_text(
                pdf_text=pdf_text,
                min_confidence=min_confidence
            )

            if latex_source:
                # Phase 2.1.0: Add compound LaTeX source to metadata
                node.metadata['latex_source'] = latex_source

                # Phase 2.1.2: Extract individual equations from compound LaTeX blocks
                try:
                    from core.latex_utils.latex_math_extractor import enrich_node_with_equations
                    enrich_node_with_equations(node, latex_source)
                except Exception as e:
                    logger.debug(f"Phase 2.1.2 extraction failed, using fallback: {e}")

                enriched_count += 1

        if enriched_count > 0:
            logger.info(
                f"📐 Phase 2.1.0: Enriched {enriched_count} equations with LaTeX source"
            )

        return enriched_count

    except Exception as e:
        logger.error(f"Error enriching DocNodes with LaTeX: {e}")
        return enriched_count
