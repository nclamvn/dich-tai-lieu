#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base Incremental Builder - Phase 5.4

Abstract base class for format-specific incremental builders.
All format builders (DOCX, PDF, TXT) inherit from this interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from config.logging_config import get_logger
logger = get_logger(__name__)

from core.validator import TranslationResult


class BaseIncrementalBuilder(ABC):
    """
    Abstract base class for incremental document builders

    All format-specific builders must implement:
    - add_batch(): Add a batch of results and save to temp file
    - merge_all(): Merge all batches into final output
    - cleanup(): Clean up temporary files

    Usage:
        builder = SomeFormatBuilder(output_path)

        for batch in batches:
            temp_file = await builder.add_batch(batch, batch_idx)

        final_output = await builder.merge_all()
    """

    def __init__(self, output_path: Path):
        """
        Initialize builder

        Args:
            output_path: Final output file path
        """
        self.output_path = Path(output_path)
        self.temp_dir = self.output_path.parent / f".temp_{self.get_format()}_batches"
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.batch_files: List[Path] = []
        self._cleanup_done = False

    async def __aenter__(self):
        """Enter async context manager"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - cleanup even on error"""
        if not self._cleanup_done:
            await self.cleanup()
        return False  # Don't suppress exceptions

    @abstractmethod
    async def add_batch(
        self,
        batch_results: List[TranslationResult],
        batch_idx: int
    ) -> Path:
        """
        Add a batch of translation results

        Args:
            batch_results: Translation results for this batch
            batch_idx: Batch index (0-based)

        Returns:
            Path to temporary batch file
        """
        pass

    @abstractmethod
    async def merge_all(self) -> Path:
        """
        Merge all batch files into final output

        Returns:
            Path to final merged output file
        """
        pass

    @abstractmethod
    def get_format(self) -> str:
        """
        Get format identifier (e.g., 'docx', 'pdf', 'txt')

        Returns:
            Format string
        """
        pass

    async def cleanup(self):
        """Clean up temporary batch files"""
        if self._cleanup_done:
            return  # Already cleaned up

        for batch_file in self.batch_files:
            try:
                batch_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {batch_file}: {e}")

        # Remove temp directory if empty
        try:
            if self.temp_dir.exists() and not any(self.temp_dir.iterdir()):
                self.temp_dir.rmdir()
        except Exception:
            pass

        self._cleanup_done = True

    def get_batch_count(self) -> int:
        """Get number of batches added"""
        return len(self.batch_files)

    def get_temp_size_mb(self) -> float:
        """Get total size of temp files in MB"""
        total_bytes = sum(f.stat().st_size for f in self.batch_files if f.exists())
        return total_bytes / 1024 / 1024
