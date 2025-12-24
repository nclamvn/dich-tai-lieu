"""
Batch Processor - Multi-file Processing Support

Handles batch translation jobs with:
- Parallel processing
- Progress tracking per file
- Zip output generation
- Queue management
"""

import asyncio
import logging
import zipfile
import uuid
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Batch job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    PARTIAL = "partial"  # Some files failed
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchFile:
    """Single file in a batch"""
    file_id: str
    filename: str
    file_path: Path
    status: str = "pending"
    progress: float = 0.0
    job_id: Optional[str] = None
    output_paths: Dict[str, Path] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class BatchJob:
    """Batch translation job"""
    batch_id: str
    files: List[BatchFile]

    # Settings (same for all files)
    source_language: str = "en"
    target_language: str = "vi"
    profile_id: str = "novel"
    output_formats: List[str] = field(default_factory=lambda: ["docx", "pdf"])
    use_vision: bool = True

    # Status
    status: BatchStatus = BatchStatus.PENDING
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0

    # Progress
    overall_progress: float = 0.0
    current_file: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Output
    zip_path: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "overall_progress": self.overall_progress,
            "current_file": self.current_file,
            "files": [
                {
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "status": f.status,
                    "progress": f.progress,
                    "job_id": f.job_id,
                    "error": f.error,
                }
                for f in self.files
            ],
            "source_language": self.source_language,
            "target_language": self.target_language,
            "profile_id": self.profile_id,
            "output_formats": self.output_formats,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "zip_available": self.zip_path is not None and self.zip_path.exists(),
        }


class BatchProcessor:
    """
    Batch Processing Manager

    Handles multi-file translation jobs with parallel processing.
    """

    def __init__(
        self,
        publisher,
        output_dir: str = "outputs/batch",
        max_concurrent: int = 2,
    ):
        """
        Initialize Batch Processor

        Args:
            publisher: UniversalPublisher instance
            output_dir: Directory for batch outputs
            max_concurrent: Max files to process in parallel
        """
        self.publisher = publisher
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent

        # Active batches
        self._batches: Dict[str, BatchJob] = {}
        self._batch_tasks: Dict[str, asyncio.Task] = {}

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)

        logger.info(f"BatchProcessor initialized: output={self.output_dir}, max_concurrent={max_concurrent}")

    def create_batch(
        self,
        files: List[tuple],  # [(filename, file_path), ...]
        source_language: str = "en",
        target_language: str = "vi",
        profile_id: str = "novel",
        output_formats: List[str] = None,
        use_vision: bool = True,
    ) -> BatchJob:
        """
        Create a new batch job

        Args:
            files: List of (filename, file_path) tuples
            source_language: Source language code
            target_language: Target language code
            profile_id: Publishing profile
            output_formats: Output format list
            use_vision: Whether to use Vision mode

        Returns:
            BatchJob instance
        """
        batch_id = str(uuid.uuid4())[:8]

        batch_files = [
            BatchFile(
                file_id=f"{batch_id}_{i}",
                filename=filename,
                file_path=Path(file_path),
            )
            for i, (filename, file_path) in enumerate(files)
        ]

        batch = BatchJob(
            batch_id=batch_id,
            files=batch_files,
            source_language=source_language,
            target_language=target_language,
            profile_id=profile_id,
            output_formats=output_formats or ["docx", "pdf"],
            use_vision=use_vision,
            total_files=len(batch_files),
        )

        self._batches[batch_id] = batch
        logger.info(f"[Batch:{batch_id}] Created with {len(files)} files")

        return batch

    async def start_batch(
        self,
        batch_id: str,
        progress_callback: Optional[Callable] = None,
    ) -> BatchJob:
        """
        Start processing a batch

        Args:
            batch_id: Batch ID to process
            progress_callback: Called with batch updates

        Returns:
            Updated BatchJob
        """
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        if batch.status != BatchStatus.PENDING:
            raise ValueError(f"Batch {batch_id} is not pending (status: {batch.status.value})")

        # Start processing
        batch.status = BatchStatus.PROCESSING
        batch.started_at = datetime.now()

        # Create task
        task = asyncio.create_task(
            self._process_batch(batch, progress_callback)
        )
        self._batch_tasks[batch_id] = task

        logger.info(f"[Batch:{batch_id}] Started processing")

        return batch

    async def _process_batch(
        self,
        batch: BatchJob,
        progress_callback: Optional[Callable],
    ):
        """Process all files in batch"""
        try:
            # Process files sequentially (to avoid rate limits)
            # Could use semaphore for parallel processing if needed
            for batch_file in batch.files:
                await self._process_file(batch, batch_file, progress_callback)

            # Update batch status
            if batch.failed_files == 0:
                batch.status = BatchStatus.COMPLETE
            elif batch.completed_files > 0:
                batch.status = BatchStatus.PARTIAL
            else:
                batch.status = BatchStatus.FAILED

            batch.completed_at = datetime.now()

            # Create zip if any files completed
            if batch.completed_files > 0:
                await self._create_batch_zip(batch)

            logger.info(
                f"[Batch:{batch.batch_id}] Complete: "
                f"{batch.completed_files}/{batch.total_files} success, "
                f"{batch.failed_files} failed"
            )

        except asyncio.CancelledError:
            batch.status = BatchStatus.CANCELLED
            logger.info(f"[Batch:{batch.batch_id}] Cancelled")
        except Exception as e:
            batch.status = BatchStatus.FAILED
            logger.error(f"[Batch:{batch.batch_id}] Failed: {e}")

    async def _process_file(
        self,
        batch: BatchJob,
        batch_file: BatchFile,
        progress_callback: Optional[Callable],
    ):
        """Process single file in batch"""
        try:
            batch_file.status = "processing"
            batch_file.started_at = datetime.now()
            batch.current_file = batch_file.filename

            logger.info(f"[Batch:{batch.batch_id}] Processing: {batch_file.filename}")

            if progress_callback:
                progress_callback(batch)

            # Read file content - pass path for Vision mode
            content = str(batch_file.file_path)

            # File progress callback
            def file_progress(progress: float, stage: str):
                batch_file.progress = progress * 100
                batch_file.status = "processing"
                self._update_batch_progress(batch)
                if progress_callback:
                    progress_callback(batch)

            # Process with publisher
            job = await self.publisher.publish(
                source_text=content,
                source_lang=batch.source_language,
                target_lang=batch.target_language,
                profile_id=batch.profile_id,
                output_format=batch.output_formats[0] if batch.output_formats else "docx",
                progress_callback=file_progress,
                use_vision=batch.use_vision,
            )

            # Update file status
            if job.status.value == "complete":
                batch_file.status = "complete"
                batch_file.progress = 100.0
                batch_file.job_id = job.job_id

                # Store output paths
                if job.output_path:
                    fmt = batch.output_formats[0] if batch.output_formats else "docx"
                    batch_file.output_paths[fmt] = job.output_path

                batch_file.completed_at = datetime.now()
                batch.completed_files += 1
                logger.info(f"[Batch:{batch.batch_id}] File complete: {batch_file.filename}")
            else:
                batch_file.status = "failed"
                batch_file.error = job.error or "Unknown error"
                batch.failed_files += 1
                logger.error(f"[Batch:{batch.batch_id}] File failed: {batch_file.filename} - {batch_file.error}")

        except Exception as e:
            batch_file.status = "failed"
            batch_file.error = str(e)
            batch.failed_files += 1
            logger.error(f"[Batch:{batch.batch_id}] File {batch_file.filename} failed: {e}")

        finally:
            self._update_batch_progress(batch)
            if progress_callback:
                progress_callback(batch)

    def _update_batch_progress(self, batch: BatchJob):
        """Update overall batch progress"""
        if batch.total_files == 0:
            batch.overall_progress = 0
            return

        total_progress = sum(f.progress for f in batch.files)
        batch.overall_progress = total_progress / batch.total_files

    async def _create_batch_zip(self, batch: BatchJob):
        """Create zip file with all outputs"""
        zip_dir = self.output_dir / batch.batch_id
        zip_dir.mkdir(parents=True, exist_ok=True)

        zip_path = zip_dir / f"batch_{batch.batch_id}_outputs.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for batch_file in batch.files:
                if batch_file.status == "complete":
                    for fmt, path in batch_file.output_paths.items():
                        path = Path(path)
                        if path.exists():
                            # Use filename without extension + format
                            base_name = Path(batch_file.filename).stem
                            arcname = f"{base_name}_translated.{fmt}"
                            zf.write(path, arcname)

        batch.zip_path = zip_path
        logger.info(f"[Batch:{batch.batch_id}] Created zip: {zip_path}")

    def get_batch(self, batch_id: str) -> Optional[BatchJob]:
        """Get batch by ID"""
        return self._batches.get(batch_id)

    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a running batch"""
        if batch_id in self._batch_tasks:
            task = self._batch_tasks[batch_id]
            if not task.done():
                task.cancel()
                return True
        return False

    def list_batches(self) -> List[Dict[str, Any]]:
        """List all batches"""
        return [b.to_dict() for b in self._batches.values()]

    def clear_batch(self, batch_id: str) -> bool:
        """Clear a batch from memory"""
        if batch_id in self._batches:
            del self._batches[batch_id]
            if batch_id in self._batch_tasks:
                del self._batch_tasks[batch_id]
            return True
        return False
