"""Application repository."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Sequence

from sqlalchemy import and_, func, select

from src.core.models.application import Application, ApplicationStatus
from src.core.repositories.base_repository import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    model_class = Application

    async def get_today(self) -> Sequence[Application]:
        """Get all applications submitted today."""
        today = date.today()
        start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        stmt = (
            select(Application)
            .where(Application.created_at >= start)
            .order_by(Application.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self, status: ApplicationStatus, limit: int = 50
    ) -> Sequence[Application]:
        """Get applications filtered by status."""
        stmt = (
            select(Application)
            .where(Application.status == status)
            .order_by(Application.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_history(self, offset: int = 0, limit: int = 20) -> Sequence[Application]:
        """Get paginated application history."""
        stmt = (
            select(Application)
            .order_by(Application.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def has_applied_to_job(self, job_id: uuid.UUID) -> bool:
        """Check if we've already applied to this job."""
        return await self.exists([Application.job_id == job_id])

    async def get_today_count(self) -> int:
        """Count applications submitted today."""
        today = date.today()
        start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        return await self.count([Application.created_at >= start])

    async def get_stats(self) -> dict:
        """Aggregate application statistics."""
        total = await self.count()
        submitted = await self.count(
            [Application.status == ApplicationStatus.SUBMITTED]
        )
        failed = await self.count(
            [Application.status == ApplicationStatus.FAILED]
        )

        # Average match score
        stmt = select(func.avg(Application.match_score)).where(
            Application.match_score.isnot(None)
        )
        result = await self.session.execute(stmt)
        avg_match = result.scalar() or 0.0

        # Average salary
        stmt = select(func.avg(Application.salary_estimate)).where(
            Application.salary_estimate.isnot(None)
        )
        result = await self.session.execute(stmt)
        avg_salary = result.scalar() or 0.0

        return {
            "total": total,
            "submitted": submitted,
            "failed": failed,
            "success_rate": round(submitted / total * 100, 1) if total > 0 else 0,
            "avg_match_score": round(avg_match, 1),
            "avg_salary_estimate": round(avg_salary, 1),
        }

    async def get_by_company(self, company_id: uuid.UUID) -> Sequence[Application]:
        """Get all applications for a specific company."""
        stmt = (
            select(Application)
            .where(Application.company_id == company_id)
            .order_by(Application.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
