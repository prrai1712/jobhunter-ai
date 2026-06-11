"""Analytics service — aggregation, reporting, and statistics for Telegram commands."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.application import Application, ApplicationStatus
from src.core.models.company import Company
from src.core.models.job import Job, JobStatus
from src.core.models.salary_estimate import SalaryEstimate
from src.core.repositories.application_repository import ApplicationRepository
from src.core.repositories.company_repository import CompanyRepository
from src.core.repositories.job_repository import JobRepository
from src.core.repositories.other_repositories import DailyStatsRepository, SalaryEstimateRepository


class AnalyticsService:
    """Provides analytics data for Telegram reporting commands."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.job_repo = JobRepository(session)
        self.app_repo = ApplicationRepository(session)
        self.company_repo = CompanyRepository(session)
        self.stats_repo = DailyStatsRepository(session)
        self.salary_repo = SalaryEstimateRepository(session)

    async def get_daily_stats(self, target_date: date | None = None) -> dict[str, Any]:
        """Get comprehensive statistics for a specific day."""
        if target_date is None:
            target_date = date.today()

        # Try pre-computed stats first
        stats = await self.stats_repo.get_or_create_today()

        return {
            "date": target_date.isoformat(),
            "jobs_scraped": stats.jobs_scraped,
            "jobs_matched": stats.jobs_matched,
            "jobs_rejected": stats.jobs_rejected,
            "jobs_qualified": stats.jobs_qualified,
            "applications_submitted": stats.applications_submitted,
            "applications_failed": stats.applications_failed,
            "applications_success": stats.applications_success,
            "companies_discovered": stats.companies_discovered,
            "salary_lookups": stats.salary_lookups,
            "avg_salary": stats.avg_salary,
            "max_salary": stats.max_salary,
            "min_salary": stats.min_salary,
        }

    async def get_company_stats(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get company statistics for reporting."""
        return await self.company_repo.get_stats()

    async def get_salary_stats(self) -> dict[str, Any]:
        """Get salary distribution and statistics."""
        stmt = select(
            func.avg(SalaryEstimate.estimated_salary).label("avg"),
            func.max(SalaryEstimate.estimated_salary).label("max"),
            func.min(SalaryEstimate.estimated_salary).label("min"),
            func.count(SalaryEstimate.id).label("total"),
            func.avg(SalaryEstimate.confidence).label("avg_confidence"),
        )
        result = await self.session.execute(stmt)
        row = result.one()

        # Distribution buckets
        buckets = {
            "0-10L": 0,
            "10-15L": 0,
            "15-20L": 0,
            "20-30L": 0,
            "30-50L": 0,
            "50L+": 0,
        }

        dist_stmt = select(SalaryEstimate.estimated_salary).where(
            SalaryEstimate.estimated_salary.isnot(None)
        )
        dist_result = await self.session.execute(dist_stmt)
        for (salary,) in dist_result.all():
            if salary < 10:
                buckets["0-10L"] += 1
            elif salary < 15:
                buckets["10-15L"] += 1
            elif salary < 20:
                buckets["15-20L"] += 1
            elif salary < 30:
                buckets["20-30L"] += 1
            elif salary < 50:
                buckets["30-50L"] += 1
            else:
                buckets["50L+"] += 1

        return {
            "average": round(row.avg or 0, 2),
            "highest": round(row.max or 0, 2),
            "lowest": round(row.min or 0, 2),
            "total_estimates": row.total or 0,
            "avg_confidence": round((row.avg_confidence or 0) * 100, 1),
            "distribution": buckets,
        }

    async def get_top_companies(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top hiring companies."""
        companies = await self.company_repo.get_top_by_jobs(limit)
        return [
            {
                "name": c.name,
                "jobs_found": c.jobs_discovered,
                "jobs_applied": c.jobs_applied,
                "salary_range": (
                    f"₹{c.estimated_salary_band_low or 0}-{c.estimated_salary_band_high or 0}L"
                ),
            }
            for c in companies
        ]

    async def get_application_stats(self) -> dict[str, Any]:
        """Get comprehensive application statistics."""
        return await self.app_repo.get_stats()

    async def compute_daily_stats(self) -> None:
        """Recompute daily statistics from raw data (called by scheduler)."""
        today = date.today()
        stats = await self.stats_repo.get_or_create_today()

        # Compute salary stats for today
        stmt = select(
            func.avg(SalaryEstimate.estimated_salary),
            func.max(SalaryEstimate.estimated_salary),
            func.min(SalaryEstimate.estimated_salary),
        ).where(func.date(SalaryEstimate.searched_at) == today)
        result = await self.session.execute(stmt)
        row = result.one()

        stats.avg_salary = round(row[0] or 0, 2) if row[0] else None
        stats.max_salary = round(row[1] or 0, 2) if row[1] else None
        stats.min_salary = round(row[2] or 0, 2) if row[2] else None

        await self.session.flush()

    async def get_weekly_trend(self) -> list[dict[str, Any]]:
        """Get 7-day trend data."""
        end = date.today()
        start = end - timedelta(days=6)
        daily_records = await self.stats_repo.get_date_range(start, end)
        return [
            {
                "date": r.date.isoformat(),
                "scraped": r.jobs_scraped,
                "applied": r.applications_submitted,
                "failed": r.applications_failed,
            }
            for r in daily_records
        ]
