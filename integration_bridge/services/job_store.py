"""In-memory job store for Integration Bridge"""
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from ..models.schemas import BridgeJob, JobStatus, JobType


class JobStore:
    """In-memory store for bridge jobs"""

    def __init__(self):
        self._jobs: Dict[str, BridgeJob] = {}
        self._app_to_bridge: Dict[str, str] = {}  # APP job ID -> Bridge job ID

    def create_job(
        self,
        job_type: JobType,
        cw_project_id: Optional[str] = None,
        cw_draft_id: Optional[str] = None
    ) -> BridgeJob:
        """Create a new bridge job"""
        job_id = f"bridge_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        job = BridgeJob(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            progress=0,
            cw_project_id=cw_project_id,
            cw_draft_id=cw_draft_id,
            created_at=now,
            updated_at=now
        )

        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[BridgeJob]:
        """Get job by ID"""
        return self._jobs.get(job_id)

    def get_job_by_app_id(self, app_job_id: str) -> Optional[BridgeJob]:
        """Get job by AI Publisher Pro job ID"""
        bridge_job_id = self._app_to_bridge.get(app_job_id)
        if bridge_job_id:
            return self._jobs.get(bridge_job_id)
        return None

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        app_job_id: Optional[str] = None,
        result: Optional[dict] = None,
        error_message: Optional[str] = None
    ) -> Optional[BridgeJob]:
        """Update job status and details"""
        job = self._jobs.get(job_id)
        if not job:
            return None

        if status:
            job.status = status
        if progress is not None:
            job.progress = progress
        if app_job_id:
            job.app_job_id = app_job_id
            self._app_to_bridge[app_job_id] = job_id
        if result:
            job.result = result
        if error_message:
            job.error_message = error_message

        job.updated_at = datetime.utcnow()

        if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.completed_at = datetime.utcnow()

        return job

    def list_jobs(
        self,
        job_type: Optional[JobType] = None,
        status: Optional[JobStatus] = None,
        limit: int = 50
    ) -> List[BridgeJob]:
        """List jobs with optional filters"""
        jobs = list(self._jobs.values())

        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            if job.app_job_id and job.app_job_id in self._app_to_bridge:
                del self._app_to_bridge[job.app_job_id]
            del self._jobs[job_id]
            return True
        return False

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Remove jobs older than max_age_hours"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        old_jobs = [
            job_id for job_id, job in self._jobs.items()
            if job.created_at < cutoff
        ]
        for job_id in old_jobs:
            self.delete_job(job_id)
        return len(old_jobs)


# Global singleton
job_store = JobStore()
