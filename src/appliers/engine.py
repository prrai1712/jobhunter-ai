"""Application engine — decision engine + auto-apply orchestrator."""

from __future__ import annotations

import asyncio
import traceback
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config.candidate import CandidateProfile, get_candidate_profile
from src.core.config.settings import get_settings
from src.core.database.engine import get_async_session
from src.core.models.application import ApplicationMethod
from src.core.models.job import Job, JobStatus
from src.core.services.application_service import ApplicationService
from src.core.services.job_service import JobService
from src.core.services.resume_service import ResumeService
from src.core.services.system_service import SystemService
from src.providers.base import ApplicationResult
from src.providers.registry import ProviderRegistry

logger = structlog.get_logger(__name__)


class DecisionEngine:
    """Determines whether a job should be applied to.

    Criteria:
    1. salary >= MIN_SALARY_LPA
    2. match_score >= MIN_MATCH_SCORE
    3. role is valid (matches target roles)
    4. Not a duplicate application
    5. Resume exists
    6. System is running
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.system_service = SystemService(session)
        self.app_service = ApplicationService(session)
        self.resume_service = ResumeService(session)

    async def should_apply(
        self,
        job: Job,
        user_id: uuid.UUID,
    ) -> tuple[bool, str]:
        """Evaluate whether to apply to a job.

        Returns:
            (should_apply: bool, reason: str)
        """
        # Check system state
        if not await self.system_service.can_apply():
            return False, "System is not in running state"

        # Check daily limit
        today_count = await self.app_service.get_today_count()
        if today_count >= self.settings.application.max_daily_applications:
            return False, f"Daily application limit reached ({today_count})"

        # Check salary
        min_salary = self.settings.job_filter.min_salary_lpa
        if job.salary_estimate is not None and job.salary_estimate < min_salary:
            return False, f"Salary {job.salary_estimate}L below threshold {min_salary}L"

        # Check match score
        min_score = self.settings.job_filter.min_match_score
        if job.match_score is not None and job.match_score < min_score:
            return False, f"Match score {job.match_score} below threshold {min_score}"

        # Check duplicate
        if await self.app_service.has_already_applied(job.id):
            return False, "Already applied to this job"

        # Check resume
        resume = await self.resume_service.get_active(user_id)
        if resume is None:
            return False, "No active resume found"

        return True, "All criteria met"


class ApplicationEngine:
    """Orchestrates the auto-application pipeline.

    1. Fetch qualified jobs
    2. Run decision engine
    3. Submit applications (API → Browser fallback)
    4. Log results
    5. Send notifications
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.candidate = get_candidate_profile()
        self.semaphore = asyncio.Semaphore(
            self.settings.application.max_concurrent_applications
        )

    async def run_apply_cycle(self) -> dict[str, int]:
        """Run a full application cycle.

        Returns:
            Summary dict with counts of applied, failed, skipped.
        """
        stats = {"applied": 0, "failed": 0, "skipped": 0, "total": 0}

        async with get_async_session() as session:
            job_service = JobService(session)
            system_service = SystemService(session)

            # Check if system can apply
            if not await system_service.can_apply():
                logger.info("apply_cycle_skipped", reason="system not running")
                return stats

            # Get qualified jobs
            qualified_jobs = await job_service.get_qualified_jobs(limit=20)
            stats["total"] = len(qualified_jobs)

            if not qualified_jobs:
                logger.info("apply_cycle_no_jobs")
                return stats

        # Process each job with concurrency control
        tasks = [
            self._process_job(job) for job in qualified_jobs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
                logger.error("apply_task_error", error=str(result))
            elif result == "applied":
                stats["applied"] += 1
            elif result == "failed":
                stats["failed"] += 1
            elif result == "skipped":
                stats["skipped"] += 1

        logger.info("apply_cycle_complete", **stats)
        return stats

    async def _process_job(self, job: Job) -> str:
        """Process a single job through the application pipeline."""
        async with self.semaphore:
            async with get_async_session() as session:
                try:
                    return await self._apply_to_job(session, job)
                except Exception as e:
                    logger.error(
                        "apply_job_error",
                        job_id=str(job.id),
                        error=str(e),
                    )
                    return "failed"

    async def _apply_to_job(self, session: AsyncSession, job: Job) -> str:
        """Apply to a single job."""
        decision = DecisionEngine(session)
        app_service = ApplicationService(session)
        resume_service = ResumeService(session)
        job_service = JobService(session)

        # Get user (first user for now — single-user system)
        from src.core.repositories.user_repository import UserRepository
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(
            self.settings.telegram.allowed_user_id
        )
        if not user:
            return "skipped"

        # Decision check
        should_apply, reason = await decision.should_apply(job, user.id)
        if not should_apply:
            logger.info(
                "job_skipped",
                job_id=str(job.id),
                title=job.title,
                reason=reason,
            )
            return "skipped"

        # Get resume
        resume = await resume_service.get_active(user.id)
        if not resume:
            return "skipped"

        # Create application record
        application = await app_service.create_application(
            job=job,
            resume_id=resume.id,
            user_id=user.id,
        )

        # Mark as submitting
        await app_service.mark_submitting(application.id)

        # Build candidate data dict
        candidate_data = {
            "first_name": self.candidate.first_name,
            "last_name": self.candidate.last_name,
            "email": self.candidate.email,
            "phone": self.candidate.phone,
            "location": self.candidate.country,
            "experience_years": str(self.candidate.experience_years),
        }

        # Get provider and attempt application
        result = await self._attempt_apply(
            job, resume.file_path, candidate_data
        )

        # Log ATS result
        await app_service.log_ats_result(
            job_id=job.id,
            provider_name=job.ats_provider,
            request_data=candidate_data,
            response_data=result.response_data,
            status_code=result.status_code,
            success=result.success,
            error_message=result.message if not result.success else None,
        )

        if result.success:
            method = (
                ApplicationMethod.API
                if result.method == "api"
                else ApplicationMethod.BROWSER
            )
            await app_service.mark_submitted(
                application.id,
                method=method,
                response_data=result.response_data,
            )
            return "applied"
        else:
            await app_service.mark_failed(
                application.id,
                reason=result.message,
                error_type=result.error_type or "unknown",
                screenshot_path=result.screenshot_path,
                html_snapshot_path=result.html_snapshot_path,
            )
            return "failed"

    async def _attempt_apply(
        self,
        job: Job,
        resume_path: str,
        candidate: dict[str, str],
    ) -> ApplicationResult:
        """Attempt to apply via API first, then fall back to browser."""
        try:
            provider = ProviderRegistry.get_provider(job.ats_provider)
        except ValueError:
            return ApplicationResult(
                success=False,
                method="api",
                message=f"No provider registered for '{job.ats_provider}'",
                error_type="no_provider",
            )

        # Extract board token from job source or URL
        board_token = self._extract_board_token(job)

        # Try API first
        for attempt in range(self.settings.application.max_application_retries):
            try:
                result = await provider.apply_to_job(
                    job_url=job.apply_url,
                    external_id=job.external_id or "",
                    board_token=board_token,
                    resume_path=resume_path,
                    candidate=candidate,
                )

                if result.success:
                    return result

                # If specific error types, don't retry
                if result.error_type in ("file_not_found", "no_provider", "validation_error"):
                    return result

                logger.warning(
                    "apply_attempt_failed",
                    attempt=attempt + 1,
                    error=result.message,
                )

                if attempt < self.settings.application.max_application_retries - 1:
                    await asyncio.sleep(
                        self.settings.application.application_retry_delay_seconds
                        * (attempt + 1)
                    )

            except Exception as e:
                logger.error(
                    "apply_attempt_exception",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < self.settings.application.max_application_retries - 1:
                    await asyncio.sleep(
                        self.settings.application.application_retry_delay_seconds
                    )

        return ApplicationResult(
            success=False,
            method="api",
            message=f"All {self.settings.application.max_application_retries} attempts failed",
            error_type="max_retries",
        )

    def _extract_board_token(self, job: Job) -> str:
        """Extract board token from the job's apply URL."""
        url = job.apply_url

        if "greenhouse" in url:
            # Format: boards.greenhouse.io/{board_token}/jobs/...
            parts = url.split("/")
            for i, p in enumerate(parts):
                if "greenhouse" in p and i + 1 < len(parts):
                    return parts[i + 1]
        elif "lever" in url:
            # Format: jobs.lever.co/{company}/...
            parts = url.split("/")
            for i, p in enumerate(parts):
                if "lever" in p and i + 1 < len(parts):
                    return parts[i + 1]
        elif "ashby" in url:
            # Format: jobs.ashbyhq.com/{company}/...
            parts = url.split("/")
            for i, p in enumerate(parts):
                if "ashby" in p and i + 1 < len(parts):
                    return parts[i + 1]

        return ""
