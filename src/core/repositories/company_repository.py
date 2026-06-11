"""Company repository."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select, update

from src.core.database.base import utcnow
from src.core.models.company import Company
from src.core.repositories.base_repository import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    model_class = Company

    async def get_or_create_by_name(self, name: str, **kwargs) -> tuple[Company, bool]:  # type: ignore[no-untyped-def]
        """Get a company by name or create if not exists. Returns (company, created)."""
        stmt = select(Company).where(func.lower(Company.name) == name.lower().strip())
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            # Update last_seen_at
            existing.last_seen_at = utcnow()
            await self.session.flush()
            return existing, False
        company = await self.create(name=name.strip(), last_seen_at=utcnow(), **kwargs)
        return company, True

    async def get_top_by_jobs(self, limit: int = 10) -> Sequence[Company]:
        """Get top companies by number of jobs discovered."""
        stmt = (
            select(Company)
            .order_by(Company.jobs_discovered.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_top_by_applications(self, limit: int = 10) -> Sequence[Company]:
        """Get companies with most applications."""
        stmt = (
            select(Company)
            .order_by(Company.jobs_applied.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def increment_jobs_discovered(self, company_id) -> None:  # type: ignore[no-untyped-def]
        """Atomically increment jobs_discovered counter."""
        stmt = (
            update(Company)
            .where(Company.id == company_id)
            .values(jobs_discovered=Company.jobs_discovered + 1)
        )
        await self.session.execute(stmt)

    async def increment_jobs_applied(self, company_id) -> None:  # type: ignore[no-untyped-def]
        """Atomically increment jobs_applied counter."""
        stmt = (
            update(Company)
            .where(Company.id == company_id)
            .values(jobs_applied=Company.jobs_applied + 1)
        )
        await self.session.execute(stmt)

    async def get_stats(self) -> list[dict]:
        """Get company statistics for reporting."""
        stmt = (
            select(Company)
            .where(Company.jobs_discovered > 0)
            .order_by(Company.jobs_discovered.desc())
        )
        result = await self.session.execute(stmt)
        companies = result.scalars().all()
        return [
            {
                "name": c.name,
                "jobs_found": c.jobs_discovered,
                "jobs_applied": c.jobs_applied,
                "salary_low": c.estimated_salary_band_low,
                "salary_high": c.estimated_salary_band_high,
                "success_rate": (
                    round(c.jobs_applied / c.jobs_discovered * 100, 1)
                    if c.jobs_discovered > 0
                    else 0
                ),
            }
            for c in companies
        ]
