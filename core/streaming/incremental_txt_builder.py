#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Incremental TXT Builder - Phase 5.4

Build TXT documents incrementally to reduce memory usage.
Instead of building entire TXT in RAM, write batches to temp files.
"""

from pathlib import Path
from typing import List

from config.logging_config import get_logger
logger = get_logger(__name__)

from core.validator import TranslationResult
from .base_builder import BaseIncrementalBuilder


class IncrementalTxtBuilder(BaseIncrementalBuilder):
    """
    Build TXT incrementally in batches

    Instead of:
      - Load ALL results in memory → Build TXT → Save
      - Peak memory: ~500MB for large doc

    Do:
      - Build batch 1 TXT → Save to temp
      - Build batch 2 TXT → Save to temp
      - ...
      - Merge all temp TXTs → Final output
      - Peak memory: ~50MB (10x reduction)

    Usage:
        builder = IncrementalTxtBuilder(output_path)

        # Add batches
        for batch in batches:
            temp_file = await builder.add_batch(batch, batch_idx)

        # Merge all batches
        final_file = await builder.merge_all()
    """

    def get_format(self) -> str:
        """Get format identifier"""
        return 'txt'

    def _verify_txt(self, file_path: Path) -> None:
        """
        Verify TXT file is valid and readable

        Args:
            file_path: Path to TXT file to verify

        Raises:
            RuntimeError: If TXT is unreadable or empty
        """
        try:
            # Try to read the file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Verify it has content
            if len(content.strip()) == 0:
                raise RuntimeError(f"TXT file has no content: {file_path}")

        except UnicodeDecodeError as e:
            raise RuntimeError(f"TXT file has invalid encoding: {file_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to verify TXT: {file_path}: {e}")

    async def add_batch(
        self,
        batch_results: List[TranslationResult],
        batch_idx: int
    ) -> Path:
        """
        Add a batch and save to temp TXT file with error handling

        Args:
            batch_results: Translation results for this batch
            batch_idx: Batch index (0-based)

        Returns:
            Path to temp batch TXT file

        Raises:
            RuntimeError: If TXT creation fails
        """
        batch_file = self.temp_dir / f"batch_{batch_idx:04d}.txt"

        try:
            # Write batch content with encoding error handling
            with open(batch_file, 'w', encoding='utf-8', errors='replace') as f:
                for result in batch_results:
                    try:
                        # Write translated text with double newline separator
                        f.write(result.translated)
                        f.write('\n\n')
                    except Exception as e:
                        logger.warning(f"Failed to write chunk {result.chunk_id}: {e}")
                        # Write placeholder to maintain order
                        f.write(f"[Error: chunk {result.chunk_id} failed]\n\n")

            # Verify file created
            if not batch_file.exists():
                raise RuntimeError(f"TXT batch file not created: {batch_file}")

            # Deep verification - check TXT is readable and has content
            self._verify_txt(batch_file)

            self.batch_files.append(batch_file)
            return batch_file

        except PermissionError as e:
            raise RuntimeError(f"Permission denied: {batch_file}: {e}")
        except OSError as e:
            if "No space left" in str(e):
                raise RuntimeError(f"Disk full: {batch_file}: {e}")
            raise RuntimeError(f"OS error: {e}")
        except Exception as e:
            # Cleanup partial file
            if batch_file.exists():
                try:
                    batch_file.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"Failed to create TXT batch {batch_idx}: {e}")

    async def merge_all(self) -> Path:
        """
        Merge all batch TXT files into final output with error handling

        Returns:
            Path to final merged TXT

        Raises:
            RuntimeError: If merge fails
        """
        if not self.batch_files:
            raise ValueError("No batch files to merge")

        logger.info(f"Merging {len(self.batch_files)} TXT batches...")

        try:
            # Merge all batches into final file
            with open(self.output_path, 'w', encoding='utf-8', errors='replace') as outfile:
                for batch_idx, batch_file in enumerate(self.batch_files):
                    if not batch_file.exists():
                        raise RuntimeError(f"Batch file missing: {batch_file}")

                    try:
                        # Read batch content
                        with open(batch_file, 'r', encoding='utf-8', errors='replace') as infile:
                            content = infile.read()
                            outfile.write(content)
                        logger.debug(f"Batch {batch_idx + 1}/{len(self.batch_files)} merged")
                    except Exception as e:
                        raise RuntimeError(f"Failed to read batch {batch_idx}: {e}")

            # Verify output exists
            if not self.output_path.exists():
                raise RuntimeError("Final TXT not created")

            file_size = self.output_path.stat().st_size
            if file_size == 0:
                raise RuntimeError("Final TXT is empty")

            # Deep verification - check final TXT is readable and has content
            self._verify_txt(self.output_path)

            logger.info(f"Final TXT saved: {self.output_path} ({file_size / 1024:.1f} KB)")

            # Cleanup temp files
            await self.cleanup()

            return self.output_path

        except Exception as e:
            # Ensure cleanup even on error
            try:
                await self.cleanup()
            except Exception:
                pass
            raise
