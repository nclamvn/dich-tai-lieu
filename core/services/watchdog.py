"""
QA-17 + QA-27: Job timeout watchdog.

Auto-fails jobs that have been running longer than MAX_JOB_DURATION_SECONDS.
Runs as an asyncio background task started at app startup.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MAX_JOB_DURATION = int(os.getenv("MAX_JOB_DURATION_SECONDS", "7200"))  # 2 hours
CHECK_INTERVAL = int(os.getenv("WATCHDOG_CHECK_INTERVAL", "300"))  # 5 minutes


async def watchdog_loop():
    """Background loop that checks for stuck jobs and times them out."""
    while True:
        try:
            await _check_stuck_jobs()
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


async def _check_stuck_jobs():
    """Find and timeout V2 jobs running too long."""
    try:
        from api.job_repository import get_job_repository
        repo = get_job_repository()
        cutoff = (datetime.now() - timedelta(seconds=MAX_JOB_DURATION)).isoformat()

        with repo._get_connection() as conn:
            rows = conn.execute(
                "SELECT job_id, updated_at FROM aps_jobs "
                "WHERE status IN ('running', 'processing', 'vision_reading', 'translating') "
                "AND deleted_at IS NULL AND updated_at < ?",
                (cutoff,)
            ).fetchall()

            for row in rows:
                job_id = row["job_id"]
                logger.warning(
                    f"Watchdog: timing out job {job_id} "
                    f"(last update: {row['updated_at']}, limit: {MAX_JOB_DURATION}s)"
                )
                conn.execute(
                    "UPDATE aps_jobs SET status = 'failed', "
                    "error = ?, updated_at = ? WHERE job_id = ?",
                    (
                        f"Timed out after {MAX_JOB_DURATION // 3600}h — job appeared stuck",
                        datetime.now().isoformat(),
                        job_id,
                    )
                )

            if rows:
                logger.info(f"Watchdog: timed out {len(rows)} stuck job(s)")
                # QA-25: Send alert for stuck jobs
                try:
                    from core.services.alerting import send_alert, SEVERITY_WARNING
                    job_ids = [r["job_id"] for r in rows]
                    send_alert(
                        f"Watchdog timed out {len(rows)} stuck job(s)",
                        severity=SEVERITY_WARNING,
                        context={"job_ids": job_ids[:5], "timeout_seconds": MAX_JOB_DURATION},
                    )
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Watchdog check skipped: {e}")
