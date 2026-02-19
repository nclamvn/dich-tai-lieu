"""Export service - unified export from both systems"""
import httpx
import asyncio
import logging
from typing import Optional, List
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

from ..models.schemas import (
    ExportRequest,
    ExportResponse,
    ExportResult,
    ExportFile,
    ExportFormat,
    JobStatus,
    JobType,
    BridgeJob
)
from .job_store import job_store
from ..utils.config import settings
from ..utils.webhook import send_webhook


class ExportService:
    """Service to handle unified export from both systems"""

    def __init__(self):
        self.app_base_url = settings.APP_API_URL
        self.cw_base_url = settings.CW_API_URL
        self.timeout = httpx.Timeout(300.0)

    async def export(self, request: ExportRequest) -> ExportResponse:
        """Queue an export job"""
        # Create bridge job
        job = job_store.create_job(
            job_type=JobType.EXPORT,
            cw_project_id=request.project_id if request.source_system == "cw" else None
        )

        # Update status to queued
        job_store.update_job(job.job_id, status=JobStatus.QUEUED)

        # Start async export task
        asyncio.create_task(
            self._execute_export(job.job_id, request)
        )

        return ExportResponse(
            job_id=job.job_id,
            status=JobStatus.QUEUED,
            message="Export job queued successfully",
            tracking_url=f"/api/bridge/jobs/{job.job_id}"
        )

    async def _execute_export(
        self,
        job_id: str,
        request: ExportRequest
    ):
        """Execute export using appropriate system"""
        try:
            job_store.update_job(job_id, status=JobStatus.EXPORTING, progress=10)

            start_time = datetime.utcnow()
            files: List[ExportFile] = []

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get content if not provided
                content = request.content
                if not content:
                    content = await self._fetch_content(
                        client,
                        request.source_system,
                        request.project_id
                    )

                if not content:
                    raise Exception("No content to export")

                # Export each format
                total_formats = len(request.formats)
                for i, fmt in enumerate(request.formats):
                    progress = 10 + int((i / total_formats) * 80)
                    job_store.update_job(job_id, progress=progress)

                    # Use AI Publisher Pro for PDF/DOCX (better quality)
                    # Use CW for EPUB (has epub-gen-memory)
                    if fmt in [ExportFormat.PDF, ExportFormat.DOCX]:
                        file = await self._export_via_app(
                            client, content, request, fmt
                        )
                    elif fmt == ExportFormat.EPUB:
                        file = await self._export_via_cw(
                            client, content, request, fmt
                        )
                    else:
                        # MD and TXT - generate locally
                        file = await self._export_text(content, request, fmt)

                    if file:
                        files.append(file)

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result = {
                "files": [f.model_dump() for f in files],
                "total_pages": None,  # Could be calculated
                "duration_seconds": duration
            }

            job_store.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result=result
            )

            # Send webhook
            if request.callback_url:
                await send_webhook(
                    request.callback_url,
                    {
                        "event": "export.completed",
                        "job_id": job_id,
                        "result": result
                    }
                )

        except Exception as e:
            error_msg = str(e)
            job_store.update_job(
                job_id,
                status=JobStatus.FAILED,
                error_message=error_msg
            )

            if request.callback_url:
                await send_webhook(
                    request.callback_url,
                    {
                        "event": "export.failed",
                        "job_id": job_id,
                        "error": error_msg
                    }
                )

    async def _fetch_content(
        self,
        client: httpx.AsyncClient,
        source: str,
        project_id: str
    ) -> Optional[str]:
        """Fetch content from source system"""
        try:
            if source == "cw":
                # Fetch from Companion Writer
                response = await client.get(
                    f"{self.cw_base_url}/api/projects/{project_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("content") or data.get("draft", {}).get("content")
            else:
                # Fetch from AI Publisher Pro
                response = await client.get(
                    f"{self.app_base_url}/api/v2/jobs/{project_id}"
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("result", {}).get("translated_content")
        except Exception as e:
            logger.debug("Failed to fetch content from %s: %s", source, e)
        return None

    async def _export_via_app(
        self,
        client: httpx.AsyncClient,
        content: str,
        request: ExportRequest,
        fmt: ExportFormat
    ) -> Optional[ExportFile]:
        """Export via AI Publisher Pro (PDF/DOCX)"""
        try:
            # Create a temporary document and export
            export_request = {
                "content": content,
                "output_format": fmt.value,
                "title": request.title,
                "author": request.author or "Unknown",
                "template": request.template.value,
                "options": {
                    "include_toc": request.options.include_toc if request.options else True,
                    "font_family": request.options.font_family if request.options else "Times New Roman",
                    "font_size": request.options.font_size if request.options else 12
                }
            }

            response = await client.post(
                f"{self.app_base_url}/api/export/{fmt.value}",
                json=export_request
            )

            if response.status_code == 200:
                # Save file and return info
                filename = f"{request.title or 'document'}.{fmt.value}"
                download_url = f"/downloads/{filename}"

                return ExportFile(
                    format=fmt,
                    filename=filename,
                    download_url=download_url,
                    size_bytes=len(response.content)
                )
        except Exception as e:
            print(f"Export via APP failed: {e}")
        return None

    async def _export_via_cw(
        self,
        client: httpx.AsyncClient,
        content: str,
        request: ExportRequest,
        fmt: ExportFormat
    ) -> Optional[ExportFile]:
        """Export via Companion Writer (EPUB)"""
        try:
            export_request = {
                "content": content,
                "format": fmt.value,
                "title": request.title,
                "author": request.author
            }

            response = await client.post(
                f"{self.cw_base_url}/api/export/{fmt.value}",
                json=export_request
            )

            if response.status_code == 200:
                filename = f"{request.title or 'document'}.{fmt.value}"
                download_url = f"/downloads/{filename}"

                return ExportFile(
                    format=fmt,
                    filename=filename,
                    download_url=download_url,
                    size_bytes=len(response.content)
                )
        except Exception as e:
            print(f"Export via CW failed: {e}")
        return None

    async def _export_text(
        self,
        content: str,
        request: ExportRequest,
        fmt: ExportFormat
    ) -> Optional[ExportFile]:
        """Export to text formats locally"""
        try:
            if fmt == ExportFormat.MD:
                # Already markdown or convert
                text_content = content
                ext = "md"
            else:
                # Plain text - strip markdown
                import re
                text_content = re.sub(r'[#*_`\[\]()]', '', content)
                ext = "txt"

            filename = f"{request.title or 'document'}.{ext}"
            # In production, save to file storage and return URL
            download_url = f"/downloads/{filename}"

            return ExportFile(
                format=fmt,
                filename=filename,
                download_url=download_url,
                size_bytes=len(text_content.encode('utf-8'))
            )
        except Exception as e:
            logger.debug("Failed to export text format %s: %s", fmt, e)
        return None

    def get_job_status(self, job_id: str) -> Optional[BridgeJob]:
        """Get export job status"""
        return job_store.get_job(job_id)
