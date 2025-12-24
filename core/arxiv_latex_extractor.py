"""
Phase 2.1.0 - arXiv LaTeX Source Extractor

Extracts LaTeX equations from arXiv source .tar.gz files for perfect OMML rendering.
"""

import tarfile
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LatexEquation:
    """Represents an extracted LaTeX equation with metadata."""
    latex: str  # The LaTeX source code
    equation_type: str  # 'inline', 'display', 'environment'
    line_number: int  # Line number in source file
    context_before: str  # Text before equation (for matching)
    context_after: str  # Text after equation (for matching)


class ArxivLatexExtractor:
    """
    Extracts LaTeX equations from arXiv source .tar.gz archives.

    This enables perfect equation rendering by using source LaTeX instead of
    attempting to parse rendered PDF text.
    """

    # Regex patterns for equation detection
    DISPLAY_MATH_PATTERN = r'\$\$(.+?)\$\$'
    INLINE_MATH_PATTERN = r'\$(.+?)\$'
    BRACKET_DISPLAY_PATTERN = r'\\\[(.+?)\\\]'
    PAREN_INLINE_PATTERN = r'\\\((.+?)\\\)'

    # Math environment patterns
    MATH_ENVIRONMENTS = [
        'equation', 'equation*', 'align', 'align*', 'gather', 'gather*',
        'multline', 'multline*', 'eqnarray', 'eqnarray*', 'displaymath'
    ]

    def __init__(self, tar_gz_path: str):
        """
        Initialize extractor with path to arXiv .tar.gz file.

        Args:
            tar_gz_path: Path to arXiv source archive (e.g., arXiv-1509.05363v6.tar.gz)
        """
        self.tar_gz_path = Path(tar_gz_path)
        self.equations: List[LatexEquation] = []

    def extract(self) -> List[LatexEquation]:
        """
        Extract all LaTeX equations from the archive.

        Returns:
            List of LatexEquation objects with extracted equations
        """
        logger.info(f"Extracting LaTeX from {self.tar_gz_path}")

        # Find and read the main .tex file
        tex_content = self._find_main_tex_file()
        if not tex_content:
            logger.error("No main .tex file found in archive")
            return []

        # Extract equations
        self.equations = self._extract_equations_from_tex(tex_content)

        logger.info(f"Extracted {len(self.equations)} equations from LaTeX source")
        return self.equations

    def _find_main_tex_file(self) -> Optional[str]:
        """
        Find and extract the main .tex file from the archive.

        Returns:
            Contents of main .tex file, or None if not found
        """
        try:
            with tarfile.open(self.tar_gz_path, 'r:gz') as tar:
                # List all .tex files
                tex_files = [m for m in tar.getmembers() if m.name.endswith('.tex')]

                if not tex_files:
                    return None

                # Heuristic: Choose largest .tex file (usually main paper)
                # or one with common names like 'main.tex', 'paper.tex', or filename matching archive
                main_tex = None
                for member in tex_files:
                    basename = Path(member.name).stem.lower()
                    if basename in ['main', 'paper', 'ms'] or \
                       self.tar_gz_path.stem.lower().startswith(basename):
                        main_tex = member
                        break

                # Fallback: use largest file
                if not main_tex:
                    main_tex = max(tex_files, key=lambda m: m.size)

                # Extract and read
                f = tar.extractfile(main_tex)
                if f:
                    content = f.read().decode('utf-8', errors='ignore')
                    logger.info(f"Found main .tex file: {main_tex.name} ({main_tex.size} bytes)")
                    return content

        except Exception as e:
            logger.error(f"Error extracting .tex file: {e}")

        return None

    def _extract_equations_from_tex(self, tex_content: str) -> List[LatexEquation]:
        """
        Extract all equations from LaTeX content.

        Args:
            tex_content: Full content of .tex file

        Returns:
            List of extracted LatexEquation objects
        """
        equations = []
        lines = tex_content.split('\n')

        for i, line in enumerate(lines):
            # Get context
            context_before = ' '.join(lines[max(0, i-2):i]) if i > 0 else ''
            context_after = ' '.join(lines[i+1:min(len(lines), i+3)]) if i < len(lines)-1 else ''

            # Extract display math: $$...$$
            for match in re.finditer(self.DISPLAY_MATH_PATTERN, line, re.DOTALL):
                equations.append(LatexEquation(
                    latex=match.group(1).strip(),
                    equation_type='display',
                    line_number=i+1,
                    context_before=context_before,
                    context_after=context_after
                ))

            # Extract bracket display: \[...\]
            for match in re.finditer(self.BRACKET_DISPLAY_PATTERN, line, re.DOTALL):
                equations.append(LatexEquation(
                    latex=match.group(1).strip(),
                    equation_type='display',
                    line_number=i+1,
                    context_before=context_before,
                    context_after=context_after
                ))

            # Extract inline math: $...$  (but not $$)
            clean_line = re.sub(self.DISPLAY_MATH_PATTERN, '', line)  # Remove display math first
            for match in re.finditer(self.INLINE_MATH_PATTERN, clean_line):
                equations.append(LatexEquation(
                    latex=match.group(1).strip(),
                    equation_type='inline',
                    line_number=i+1,
                    context_before=context_before,
                    context_after=context_after
                ))

            # Extract parenthesis inline: \(...\)
            for match in re.finditer(self.PAREN_INLINE_PATTERN, line, re.DOTALL):
                equations.append(LatexEquation(
                    latex=match.group(1).strip(),
                    equation_type='inline',
                    line_number=i+1,
                    context_before=context_before,
                    context_after=context_after
                ))

        # Extract environment-based equations
        equations.extend(self._extract_math_environments(tex_content))

        return equations

    def _extract_math_environments(self, tex_content: str) -> List[LatexEquation]:
        """
        Extract equations from LaTeX math environments.

        Args:
            tex_content: Full LaTeX content

        Returns:
            List of equations from environments
        """
        equations = []

        for env in self.MATH_ENVIRONMENTS:
            # Pattern: \begin{equation}...\end{equation}
            pattern = rf'\\begin\{{{env}\}}(.+?)\\end\{{{env}\}}'

            for match in re.finditer(pattern, tex_content, re.DOTALL):
                # Find line number
                pos = match.start()
                line_num = tex_content[:pos].count('\n') + 1

                equations.append(LatexEquation(
                    latex=match.group(1).strip(),
                    equation_type='environment',
                    line_number=line_num,
                    context_before='',
                    context_after=''
                ))

        return equations

    def get_equation_by_content_match(self, text_fragment: str, fuzzy: bool = True) -> Optional[LatexEquation]:
        """
        Find equation that matches given text fragment from translated content.

        This allows mapping PDF-extracted text to proper LaTeX source.

        Args:
            text_fragment: Text fragment from PDF extraction
            fuzzy: Allow fuzzy matching

        Returns:
            Matching LatexEquation or None
        """
        # Try exact match first
        for eq in self.equations:
            if text_fragment in eq.context_before or text_fragment in eq.context_after:
                return eq

        # Fuzzy match: check for similar content
        if fuzzy:
            # Implement simple similarity check
            # (Could be enhanced with more sophisticated matching)
            pass

        return None
