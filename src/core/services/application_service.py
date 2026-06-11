"""Application service — orchestrates auto-apply, logging, and status tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.application import Application, ApplicationMethod, ApplicationStatus
from src.core.models.job import Job, JobStatus
from src.core.repositories.application_repository import ApplicationRepository
from src.core.repositories.company_repository import CompanyRepository
from src.core.repositories.job_repository import JobRepository
from src.core.repositories.other_repositories import (
    ApplicationFailureRepository,
    ApplicationLogRepository,
    ATSProviderResultRepository,
    DailyStatsRepository,
)

logger = structlog.get_logger(__name__)


class ApplicationService:
    """Manages job application submission and tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.app_repo = ApplicationRepository(session)
        self.job_repo = JobRepository(session)
        self.company_repo = CompanyRepository(session)
        self.log_repo = ApplicationLogRepository(session)
        self.failure_repo = ApplicationFailureRepository(session)
        self.ats_repo = ATSProviderResultRepository(session)
        self.stats_repo = DailyStatsRepository(session)

    async def create_application(
        self,
        job: Job,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Application:
        """Create a pending application record."""
        app = await self.app_repo.create(
            job_id=job.id,
            company_id=job.company_id,
            resume_id=resume_id,
            user_id=user_id,
            status=ApplicationStatus.PENDING,
            match_score=job.match_score,
            salary_estimate=job.salary_estimate,
        )
        await self.log_repo.create(
            application_id=app.id,
            event="created",
            message=f"Application created for {job.title}",
        )
        return app

    async def mark_submitting(self, app_id: uuid.UUID) -> None:
        """Mark application as currently being submitted."""
        await self.app_repo.update(app_id, status=ApplicationStatus.SUBMITTING)
        await self.log_repo.create(
            application_id=app_id,
            event="submitting",
            message="Application submission started",
        )

    async def mark_submitted(
        self,
        app_id: uuid.UUID,
        method: ApplicationMethod,
        response_data: dict | None = None,
    ) -> None:
        """Mark application as successfully submitted."""
        now = datetime.now(timezone.utc)
        await self.app_repo.update(
            app_id,
            status=ApplicationStatus.SUBMITTED,
            method=method,
            applied_at=now,
            response_data=response_data,
        )

        # Get the application to update related records
        app = await self.app_repo.get_by_id(app_id)
        if app:
            await self.job_repo.update_status(app.job_id, JobStatus.APPLIED)
            await self.company_repo.increment_jobs_applied(app.company_id)
            await self.stats_repo.increment_field("applications_submitted")
            await self.stats_repo.increment_field("applications_success")

        await self.log_repo.create(
            application_id=app_id,
            event="submitted",
            message=f"Application submitted via {method.value}",
            metadata_json=response_data,
        )

        logger.info("application_submitted", app_id=str(app_id), method=method.value)

    async def mark_failed(
        self,
        app_id: uuid.UUID,
        reason: str,
        error_type: str = "unknown",
        stack_trace: str | None = None,
        screenshot_path: str | None = None,
        html_snapshot_path: str | None = None,
    ) -> None:
        """Mark application as failed and log the failure."""
        await self.app_repo.update(app_id, status=ApplicationStatus.FAILED)

        # Get app for job_id
        app = await self.app_repo.get_by_id(app_id)
        job_id = app.job_id if app else None

        if job_id:
            await self.job_repo.update_status(job_id, JobStatus.FAILED)

        await self.failure_repo.create(
            application_id=app_id,
            job_id=job_id,
            failure_reason=reason,
            error_type=error_type,
            stack_trace=stack_trace,
            screenshot_path=screenshot_path,
            html_snapshot_path=html_snapshot_path,
        )

        await self.stats_repo.increment_field("applications_failed")

        await self.log_repo.create(
            application_id=app_id,
            event="failed",
            message=f"Application failed: {reason}",
            metadata_json={"error_type": error_type},
        )

        logger.warning(
            "application_failed",
            app_id=str(app_id),
            reason=reason,
            error_type=error_type,
        )

    async def log_ats_result(
        self,
        job_id: uuid.UUID,
        provider_name: str,
        request_data: dict | None,
        response_data: dict | None,
        status_code: int | None,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Log an ATS API interaction result."""
        await self.ats_repo.create(
            job_id=job_id,
            provider_name=provider_name,
            request_data=request_data,
            response_data=response_data,
            status_code=status_code,
            success=success,
            error_message=error_message,
        )

    async def has_already_applied(self, job_id: uuid.UUID) -> bool:
        """Check if we've already applied to this job."""
        return await self.app_repo.has_applied_to_job(job_id)

    async def get_today_count(self) -> int:
        """Get count of today's applications."""
        return await self.app_repo.get_today_count()

    async def get_applications_today(self) -> Sequence[Application]:
        """Get all applications submitted today."""
        return await self.app_repo.get_today()

    async def get_history(self, offset: int = 0, limit: int = 20) -> Sequence[Application]:
        """Get paginated application history."""
        return await self.app_repo.get_history(offset, limit)

    async def get_stats(self) -> dict:
        """Get application statistics."""
        return await self.app_repo.get_stats()
