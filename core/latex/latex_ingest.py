"""
Phase 2.1.0 - LaTeX Source Ingest & Detection

Detect and extract LaTeX sources from .tex, .zip, or .tar.gz files.
This is the foundation for the flagship LaTeX-first pipeline.

Design principles:
- Accept .tex files directly
- Accept .zip/.tar.gz archives (arXiv format)
- Find main .tex file automatically
- Validate LaTeX structure before proceeding
"""

import zipfile
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class LaTeXSourceIngestor:
    """
    Ingest and validate LaTeX source files for arXiv-quality translations.

    Supports:
    - Direct .tex files
    - .zip archives (arXiv download format)
    - .tar.gz/.tgz archives (arXiv source format)

    Workflow:
    1. detect_latex_source() - Check if input is LaTeX-compatible
    2. extract_source() - Extract archives if needed
    3. find_main_tex() - Locate main .tex file
    4. validate_latex_source() - Verify LaTeX validity
    """

    # Supported archive formats
    ARCHIVE_EXTENSIONS = ['.zip', '.tar.gz', '.tgz', '.tar']

    def __init__(self):
        """Initialize LaTeX ingestor."""
        self.temp_dirs = []  # Track temp dirs for cleanup

    def detect_latex_source(self, file_path: str) -> bool:
        """
        Check if file is .tex or archive containing .tex.

        Args:
            file_path: Path to input file

        Returns:
            True if file is LaTeX source or archive, False otherwise

        Examples:
            >>> ingestor.detect_latex_source("paper.tex")
            True
            >>> ingestor.detect_latex_source("2301.12345v1.tar.gz")
            True
            >>> ingestor.detect_latex_source("document.pdf")
            False
        """
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False

        # Direct .tex file
        if path.suffix.lower() == '.tex':
            logger.info(f"Detected direct LaTeX file: {file_path}")
            return True

        # Check archive extensions
        file_name = path.name.lower()
        for ext in self.ARCHIVE_EXTENSIONS:
            if file_name.endswith(ext):
                logger.info(f"Detected LaTeX archive ({ext}): {file_path}")
                return True

        logger.debug(f"Not a LaTeX source: {file_path}")
        return False

    def extract_source(self, source_path: str, output_dir: Optional[str] = None) -> str:
        """
        Extract .zip/.tar.gz to directory.

        Args:
            source_path: Path to archive or .tex file
            output_dir: Directory to extract to (creates temp dir if None)

        Returns:
            Path to extracted directory

        Raises:
            ValueError: If archive format not supported
            RuntimeError: If extraction fails

        Examples:
            >>> ingestor.extract_source("paper.zip")
            "/tmp/latex_extract_abc123"
            >>> ingestor.extract_source("paper.tex", "/path/to/dir")
            "/path/to/dir"  # Just copies .tex file
        """
        path = Path(source_path)

        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="latex_extract_")
            self.temp_dirs.append(output_dir)
            logger.info(f"Created temp directory: {output_dir}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Direct .tex file - just copy it
        if path.suffix.lower() == '.tex':
            dest = output_path / path.name
            shutil.copy2(str(path), str(dest))
            logger.info(f"Copied .tex file to: {dest}")
            return str(output_path)

        # Extract archive
        try:
            if path.name.lower().endswith('.zip'):
                self._extract_zip(path, output_path)
            elif any(path.name.lower().endswith(ext) for ext in ['.tar.gz', '.tgz', '.tar']):
                self._extract_tar(path, output_path)
            else:
                raise ValueError(f"Unsupported archive format: {path.suffix}")

            logger.info(f"Extracted archive to: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to extract {source_path}: {e}")
            raise RuntimeError(f"Archive extraction failed: {e}") from e

    def _extract_zip(self, zip_path: Path, output_dir: Path):
        """Extract .zip archive."""
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            zf.extractall(str(output_dir))
            logger.debug(f"Extracted {len(zf.namelist())} files from ZIP")

    def _extract_tar(self, tar_path: Path, output_dir: Path):
        """Extract .tar/.tar.gz/.tgz archive."""
        with tarfile.open(str(tar_path), 'r:*') as tf:
            tf.extractall(str(output_dir))
            logger.debug(f"Extracted {len(tf.getmembers())} files from TAR")

    def find_main_tex(self, source_dir: str) -> Optional[str]:
        """
        Find main .tex file with \\documentclass and \\begin{document}.

        Args:
            source_dir: Directory containing LaTeX sources

        Returns:
            Path to main .tex file, or None if not found

        Strategy:
        1. Look for .tex files with \\documentclass
        2. Prefer files with \\begin{document}
        3. Prefer files named main.tex, paper.tex, manuscript.tex
        4. If multiple candidates, choose the largest

        Examples:
            >>> ingestor.find_main_tex("/tmp/latex_extract")
            "/tmp/latex_extract/main.tex"
        """
        source_path = Path(source_dir)

        # Find all .tex files
        tex_files = list(source_path.rglob("*.tex"))

        if not tex_files:
            logger.warning(f"No .tex files found in {source_dir}")
            return None

        logger.debug(f"Found {len(tex_files)} .tex files")

        # Analyze each .tex file
        candidates = []
        for tex_file in tex_files:
            try:
                with open(tex_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)  # Read first 5KB

                has_documentclass = bool(re.search(r'\\documentclass', content))
                has_begin_doc = bool(re.search(r'\\begin\{document\}', content))
                file_size = tex_file.stat().st_size

                # Calculate priority score
                score = 0
                if has_documentclass:
                    score += 100
                if has_begin_doc:
                    score += 50

                # Prefer common main file names
                stem_lower = tex_file.stem.lower()
                if stem_lower in ['main', 'paper', 'manuscript', 'article']:
                    score += 20
                elif stem_lower.startswith('main'):
                    score += 10

                # Larger files more likely to be main
                score += min(file_size / 1000, 10)  # Up to 10 points for size

                if score > 0:
                    candidates.append((score, tex_file, has_documentclass, has_begin_doc))
                    logger.debug(
                        f"  {tex_file.name}: score={score:.1f}, "
                        f"documentclass={has_documentclass}, begin_doc={has_begin_doc}"
                    )

            except Exception as e:
                logger.warning(f"Failed to read {tex_file}: {e}")
                continue

        if not candidates:
            logger.warning("No valid LaTeX files found (no \\documentclass)")
            return None

        # Sort by score (highest first)
        candidates.sort(reverse=True)
        score, main_tex, has_dc, has_bd = candidates[0]

        logger.info(
            f"Selected main .tex: {main_tex.name} "
            f"(score={score:.1f}, documentclass={has_dc}, begin_doc={has_bd})"
        )

        return str(main_tex)

    def validate_latex_source(self, tex_path: str) -> Tuple[bool, str]:
        """
        Verify it's valid LaTeX (has \\documentclass, \\begin{document}).

        Args:
            tex_path: Path to .tex file

        Returns:
            (is_valid, error_message) tuple

        Validation checks:
        1. File exists and is readable
        2. Contains \\documentclass command
        3. Contains \\begin{document} environment
        4. No obvious syntax errors (matched braces in preamble)

        Examples:
            >>> ingestor.validate_latex_source("paper.tex")
            (True, "")
            >>> ingestor.validate_latex_source("broken.tex")
            (False, "Missing \\begin{document}")
        """
        path = Path(tex_path)

        # Check file exists
        if not path.exists():
            return False, f"File not found: {tex_path}"

        # Read file
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return False, f"Failed to read file: {e}"

        # Check for \documentclass
        if not re.search(r'\\documentclass', content):
            return False, "Missing \\documentclass command"

        # Check for \begin{document}
        if not re.search(r'\\begin\{document\}', content):
            return False, "Missing \\begin{document} environment"

        # Optional: Check for \end{document}
        if not re.search(r'\\end\{document\}', content):
            logger.warning(f"File {path.name} missing \\end{{document}} - may be incomplete")

        # Basic brace matching in preamble (before \begin{document})
        preamble_match = re.search(r'(.+?)\\begin\{document\}', content, re.DOTALL)
        if preamble_match:
            preamble = preamble_match.group(1)
            open_braces = preamble.count('{')
            close_braces = preamble.count('}')
            if abs(open_braces - close_braces) > 5:  # Allow small mismatches
                logger.warning(
                    f"Preamble has unmatched braces: {open_braces} open, {close_braces} close"
                )

        logger.info(f"LaTeX source validated: {path.name}")
        return True, ""

    def ingest(self, input_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Complete ingestion workflow: detect → extract → find → validate.

        Args:
            input_path: Path to .tex file or archive

        Returns:
            (main_tex_path, error_message) tuple
            - main_tex_path: Path to validated main .tex file (or None)
            - error_message: Error description if failed (or None)

        Examples:
            >>> main_tex, error = ingestor.ingest("paper.zip")
            >>> if main_tex:
            ...     print(f"Ready to process: {main_tex}")
            ... else:
            ...     print(f"Ingestion failed: {error}")
        """
        try:
            # Step 1: Detect
            if not self.detect_latex_source(input_path):
                return None, f"Not a LaTeX source: {input_path}"

            # Step 2: Extract
            source_dir = self.extract_source(input_path)

            # Step 3: Find main .tex
            main_tex = self.find_main_tex(source_dir)
            if not main_tex:
                return None, f"No main .tex file found in {source_dir}"

            # Step 4: Validate
            is_valid, error_msg = self.validate_latex_source(main_tex)
            if not is_valid:
                return None, f"Invalid LaTeX: {error_msg}"

            logger.info(f"✅ LaTeX ingestion successful: {main_tex}")
            return main_tex, None

        except Exception as e:
            logger.error(f"LaTeX ingestion failed: {e}")
            return None, str(e)

    def cleanup(self):
        """Clean up temporary directories created during extraction."""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp dir: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_dir}: {e}")
        self.temp_dirs.clear()

    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()
