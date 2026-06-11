"""Job repository — queries for job lifecycle management."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Sequence

from sqlalchemy import and_, func, select

from src.core.models.job import Job, JobStatus
from src.core.repositories.base_repository import BaseRepository


class JobRepository(BaseRepository[Job]):
    model_class = Job

    async def get_by_external_id(self, external_id: str, provider: str) -> Job | None:
        """Find a job by its external ATS ID and provider."""
        stmt = select(Job).where(
            Job.external_id == external_id,
            Job.ats_provider == provider,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_url(self, apply_url: str) -> bool:
        """Check if a job with the given apply URL already exists."""
        return await self.exists([Job.apply_url == apply_url])

    async def get_unmatched(self, limit: int = 100) -> Sequence[Job]:
        """Get jobs that haven't been scored by the matching engine yet."""
        stmt = (
            select(Job)
            .where(Job.status.in_([JobStatus.NEW, JobStatus.SALARY_ESTIMATED]))
            .order_by(Job.discovered_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_matched_unapplied(self, limit: int = 50) -> Sequence[Job]:
        """Get jobs that are qualified and not yet applied to."""
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.QUALIFIED)
            .order_by(Job.match_score.desc().nullslast())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_without_salary(self, limit: int = 100) -> Sequence[Job]:
        """Get jobs that don't have salary estimates yet."""
        stmt = (
            select(Job)
            .where(
                Job.status == JobStatus.NEW,
                Job.salary_estimate.is_(None),
            )
            .order_by(Job.discovered_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_today(self) -> Sequence[Job]:
        """Get all jobs discovered today."""
        today = date.today()
        start_of_day = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        stmt = (
            select(Job)
            .where(Job.discovered_at >= start_of_day)
            .order_by(Job.discovered_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(self, status: JobStatus, limit: int = 50) -> Sequence[Job]:
        """Get jobs filtered by status."""
        stmt = (
            select(Job)
            .where(Job.status == status)
            .order_by(Job.discovered_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        job_id: uuid.UUID,
        status: JobStatus,
        rejection_reason: str | None = None,
    ) -> Job | None:
        """Update a job's lifecycle status."""
        kwargs: dict = {"status": status}
        if rejection_reason:
            kwargs["rejection_reason"] = rejection_reason
        return await self.update(job_id, **kwargs)

    async def get_today_summary(self) -> dict:
        """Get summary counts of today's jobs by status."""
        today = date.today()
        start_of_day = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        stmt = (
            select(Job.status, func.count(Job.id))
            .where(Job.discovered_at >= start_of_day)
            .group_by(Job.status)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        summary = {status.value: 0 for status in JobStatus}
        for status, count in rows:
            summary[status.value] = count
        summary["total"] = sum(summary.values())
        return summary
