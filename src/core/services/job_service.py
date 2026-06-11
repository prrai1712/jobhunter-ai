"""Job service — orchestrates job discovery, deduplication, and enrichment."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.job import Job, JobStatus
from src.core.repositories.company_repository import CompanyRepository
from src.core.repositories.job_repository import JobRepository
from src.core.repositories.other_repositories import (
    DailyStatsRepository,
    JobDiscoveryRunRepository,
)

logger = structlog.get_logger(__name__)


class JobService:
    """Manages job discovery, deduplication, and lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.job_repo = JobRepository(session)
        self.company_repo = CompanyRepository(session)
        self.stats_repo = DailyStatsRepository(session)
        self.discovery_repo = JobDiscoveryRunRepository(session)

    async def process_discovered_job(self, job_data: dict[str, Any]) -> Job | None:
        """Process a discovered job: deduplicate, create company, store.

        Args:
            job_data: Dict with keys: title, company_name, description, location,
                      apply_url, ats_provider, external_id, experience_min,
                      experience_max, job_type, department, posted_at, source_id

        Returns:
            Created Job record or None if duplicate.
        """
        apply_url = job_data.get("apply_url", "")
        if not apply_url:
            logger.warning("job_missing_url", data=job_data)
            return None

        # Check for duplicate
        if await self.job_repo.exists_by_url(apply_url):
            logger.debug("job_duplicate", url=apply_url)
            return None

        # Also check by external ID
        external_id = job_data.get("external_id")
        provider = job_data.get("ats_provider", "unknown")
        if external_id:
            existing = await self.job_repo.get_by_external_id(external_id, provider)
            if existing:
                logger.debug("job_duplicate_external", external_id=external_id)
                return None

        # Get or create company
        company_name = job_data.get("company_name", "Unknown")
        company, created = await self.company_repo.get_or_create_by_name(company_name)
        if created:
            await self.stats_repo.increment_field("companies_discovered")

        await self.company_repo.increment_jobs_discovered(company.id)

        # Create job
        job = await self.job_repo.create(
            company_id=company.id,
            source_id=job_data.get("source_id"),
            title=job_data.get("title", "Untitled"),
            description=job_data.get("description", ""),
            location=job_data.get("location"),
            experience_min=job_data.get("experience_min"),
            experience_max=job_data.get("experience_max"),
            job_type=job_data.get("job_type", "unknown"),
            department=job_data.get("department"),
            apply_url=apply_url,
            ats_provider=provider,
            external_id=external_id,
            status=JobStatus.NEW,
            posted_at=job_data.get("posted_at"),
        )

        await self.stats_repo.increment_field("jobs_scraped")

        logger.info(
            "job_discovered",
            job_id=str(job.id),
            title=job.title,
            company=company_name,
            provider=provider,
        )

        return job

    async def get_jobs_today(self) -> Sequence[Job]:
        """Get all jobs discovered today."""
        return await self.job_repo.get_today()

    async def get_today_summary(self) -> dict:
        """Get summary counts of today's jobs."""
        return await self.job_repo.get_today_summary()

    async def get_job_details(self, job_id: uuid.UUID) -> Job | None:
        """Get full job details."""
        return await self.job_repo.get_by_id(job_id)

    async def get_unmatched_jobs(self, limit: int = 100) -> Sequence[Job]:
        """Get jobs pending matching."""
        return await self.job_repo.get_unmatched(limit)

    async def get_jobs_without_salary(self, limit: int = 100) -> Sequence[Job]:
        """Get jobs without salary estimates."""
        return await self.job_repo.get_without_salary(limit)

    async def get_qualified_jobs(self, limit: int = 50) -> Sequence[Job]:
        """Get jobs ready for application."""
        return await self.job_repo.get_matched_unapplied(limit)

    async def update_job_salary(
        self,
        job_id: uuid.UUID,
        salary: float,
        confidence: float,
    ) -> Job | None:
        """Update a job's salary estimate."""
        return await self.job_repo.update(
            job_id,
            salary_estimate=salary,
            salary_confidence=confidence,
            status=JobStatus.SALARY_ESTIMATED,
        )

    async def update_job_match(
        self,
        job_id: uuid.UUID,
        score: float,
        status: JobStatus,
        rejection_reason: str | None = None,
    ) -> Job | None:
        """Update a job's match score and status."""
        kwargs: dict[str, Any] = {"match_score": score, "status": status}
        if rejection_reason:
            kwargs["rejection_reason"] = rejection_reason
        return await self.job_repo.update(job_id, **kwargs)

    async def get_rejected_jobs(self, limit: int = 50) -> Sequence[Job]:
        """Get rejected jobs."""
        return await self.job_repo.get_by_status(JobStatus.REJECTED, limit)

    async def get_approved_jobs(self, limit: int = 50) -> Sequence[Job]:
        """Get approved/qualified jobs."""
        return await self.job_repo.get_by_status(JobStatus.QUALIFIED, limit)
