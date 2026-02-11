"""Translation service - connects to AI Publisher Pro"""
import httpx
import asyncio
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

from ..models.schemas import (
    TranslationRequest,
    TranslationResponse,
    TranslationResult,
    JobStatus,
    JobType,
    BridgeJob
)
from .job_store import job_store
from ..utils.config import settings
from ..utils.webhook import send_webhook


class TranslationService:
    """Service to handle translation via AI Publisher Pro"""

    def __init__(self):
        self.app_base_url = settings.APP_API_URL
        self.timeout = httpx.Timeout(300.0)  # 5 minutes for long translations

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Queue a translation job"""
        # Create bridge job
        job = job_store.create_job(
            job_type=JobType.TRANSLATION,
            cw_project_id=request.cw_project_id,
            cw_draft_id=request.cw_draft_id
        )

        # Update status to queued
        job_store.update_job(job.job_id, status=JobStatus.QUEUED)

        # Start async translation task
        asyncio.create_task(
            self._execute_translation(job.job_id, request)
        )

        return TranslationResponse(
            job_id=job.job_id,
            bridge_job_id=job.job_id,
            status=JobStatus.QUEUED,
            message="Translation job queued successfully",
            tracking_url=f"/api/bridge/jobs/{job.job_id}"
        )

    async def _execute_translation(
        self,
        job_id: str,
        request: TranslationRequest
    ):
        """Execute translation by calling AI Publisher Pro API"""
        try:
            # Update status
            job_store.update_job(job_id, status=JobStatus.TRANSLATING, progress=10)

            # Prepare request for AI Publisher Pro
            # Using /api/v2/publish/text endpoint
            # Valid formats: docx, pdf, md (not txt)
            app_request = {
                "content": request.content,
                "source_language": request.source_lang,
                "target_language": request.target_lang,
                "output_formats": ["docx", "md"],
                "filename": f"translated_{request.cw_draft_id}",
                "profile_id": "novel"
            }

            start_time = datetime.utcnow()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Call AI Publisher Pro publish/text endpoint
                response = await client.post(
                    f"{self.app_base_url}/api/v2/publish/text",
                    json=app_request
                )

                if response.status_code != 200:
                    raise Exception(f"APP API error: {response.status_code} - {response.text}")

                result_data = response.json()
                app_job_id = result_data.get("job_id")

                # Update with APP job ID
                job_store.update_job(
                    job_id,
                    app_job_id=app_job_id,
                    progress=30
                )

                # Poll for completion
                translated_content = await self._poll_app_job(
                    client, app_job_id, job_id
                )

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # Build result
            result = {
                "translated_content": translated_content,
                "original_word_count": len(request.content.split()),
                "translated_word_count": len(translated_content.split()) if translated_content else 0,
                "provider_used": request.options.provider if request.options else "auto",
                "model_used": "gpt-4o",  # Default, should get from APP response
                "token_count": 0,  # Should get from APP response
                "cost": 0.0,  # Should get from APP response
                "duration_seconds": duration
            }

            # Mark completed
            job_store.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result=result
            )

            # Send webhook if callback URL provided
            if request.callback_url:
                await send_webhook(
                    request.callback_url,
                    {
                        "event": "translation.completed",
                        "job_id": job_id,
                        "cw_project_id": request.cw_project_id,
                        "cw_draft_id": request.cw_draft_id,
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

            # Send failure webhook
            if request.callback_url:
                await send_webhook(
                    request.callback_url,
                    {
                        "event": "translation.failed",
                        "job_id": job_id,
                        "error": error_msg
                    }
                )

    async def _poll_app_job(
        self,
        client: httpx.AsyncClient,
        app_job_id: str,
        bridge_job_id: str,
        max_attempts: int = 120,
        poll_interval: float = 5.0
    ) -> Optional[str]:
        """Poll AI Publisher Pro for job completion"""
        for attempt in range(max_attempts):
            try:
                response = await client.get(
                    f"{self.app_base_url}/api/v2/jobs/{app_job_id}"
                )

                if response.status_code != 200:
                    await asyncio.sleep(poll_interval)
                    continue

                data = response.json()
                status = data.get("status", "").lower()
                progress = data.get("progress", 0)

                # Update bridge job progress
                bridge_progress = 30 + int(progress * 0.6)  # Map 0-100 to 30-90
                job_store.update_job(bridge_job_id, progress=bridge_progress)

                if status in ["completed", "complete"]:
                    # Get translated content from result or download
                    content = data.get("result", {}).get("translated_content")
                    if not content:
                        # Try to download the output file (try md first, then txt)
                        content = await self._download_translation(client, app_job_id)
                    return content or "Translation completed (content in output files)"

                elif status in ["failed", "error"]:
                    raise Exception(data.get("error", "Translation failed"))

                await asyncio.sleep(poll_interval)

            except httpx.RequestError as e:
                await asyncio.sleep(poll_interval)

        raise Exception("Translation timeout - job did not complete in time")

    async def _download_translation(
        self,
        client: httpx.AsyncClient,
        app_job_id: str
    ) -> Optional[str]:
        """Download translated content from AI Publisher Pro"""
        # Try different formats
        for fmt in ["md", "txt", "docx"]:
            try:
                response = await client.get(
                    f"{self.app_base_url}/api/v2/jobs/{app_job_id}/download/{fmt}"
                )
                if response.status_code == 200:
                    if fmt == "docx":
                        # For docx, we can't extract text easily, skip
                        continue
                    return response.text
            except Exception as e:
                logger.debug("Failed to download translation format %s: %s", fmt, e)
                continue
        return None

    def get_job_status(self, job_id: str) -> Optional[BridgeJob]:
        """Get translation job status"""
        return job_store.get_job(job_id)
