"""Scheduler tasks — wraps service calls for APScheduler execution."""

from __future__ import annotations

import structlog

from src.core.config.candidate import get_candidate_profile
from src.core.config.settings import get_settings
from src.core.database.engine import get_async_session
from src.core.models.job import JobStatus
from src.core.services.analytics_service import AnalyticsService
from src.core.services.job_service import JobService
from src.core.services.system_service import SystemService
from src.matching.engine import MatchingEngine
from src.salary.engine import SalaryEngine
from src.telegram import notifications

logger = structlog.get_logger(__name__)


async def discover_jobs_task() -> None:
    """Discover jobs from all active ATS sources."""
    async with get_async_session() as session:
        system = SystemService(session)
        if not await system.can_discover():
            logger.info("discover_skipped", reason="system not in discoverable state")
            return

    from src.providers.registry import ProviderRegistry, register_all_providers
    from src.core.repositories.other_repositories import JobSourceRepository

    register_all_providers()

    async with get_async_session() as session:
        source_repo = JobSourceRepository(session)
        sources = await source_repo.get_active_sources()

    total_found = 0
    total_new = 0

    for source in sources:
        try:
            provider = ProviderRegistry.get_provider(source.provider_type)
            discovered = await provider.discover_jobs(source.board_token)

            source_new = 0
            async with get_async_session() as session:
                job_service = JobService(session)
                for disc_job in discovered:
                    result = await job_service.process_discovered_job({
                        "title": disc_job.title,
                        "company_name": disc_job.company_name,
                        "description": disc_job.description,
                        "location": disc_job.location,
                        "apply_url": disc_job.apply_url,
                        "ats_provider": disc_job.ats_provider,
                        "external_id": disc_job.external_id,
                        "experience_min": disc_job.experience_min,
                        "experience_max": disc_job.experience_max,
                        "job_type": disc_job.job_type,
                        "department": disc_job.department,
                        "posted_at": disc_job.posted_at,
                        "source_id": source.id,
                    })
                    if result:
                        source_new += 1

                # Update source last crawled
                source_repo2 = JobSourceRepository(session)
                await source_repo2.update_last_crawled(source.id)

            total_found += len(discovered)
            total_new += source_new

            await notifications.notify_discovery_complete(
                provider=f"{source.provider_type}/{source.board_token}",
                jobs_found=len(discovered),
                jobs_new=source_new,
                jobs_duplicate=len(discovered) - source_new,
            )

        except Exception as e:
            logger.error(
                "discover_source_error",
                source=source.name,
                error=str(e),
            )

    logger.info(
        "discover_cycle_complete",
        total_found=total_found,
        total_new=total_new,
    )


async def estimate_salaries_task() -> None:
    """Estimate salaries for jobs without estimates."""
    async with get_async_session() as session:
        system = SystemService(session)
        if not await system.can_discover():
            return

    engine = SalaryEngine()

    async with get_async_session() as session:
        job_service = JobService(session)
        jobs = await job_service.get_jobs_without_salary(limit=50)

    for job in jobs:
        try:
            # Need company name for salary lookup
            async with get_async_session() as session:
                from src.core.repositories.company_repository import CompanyRepository
                company_repo = CompanyRepository(session)
                company = await company_repo.get_by_id(job.company_id)
                company_name = company.name if company else "Unknown"

            result = await engine.estimate(
                company=company_name,
                role=job.title,
                location=job.location or "India",
            )

            if result.estimated_salary > 0:
                async with get_async_session() as session:
                    job_service2 = JobService(session)
                    await job_service2.update_job_salary(
                        job.id,
                        salary=result.estimated_salary,
                        confidence=result.confidence,
                    )

                    # Store salary estimate record
                    from src.core.repositories.other_repositories import SalaryEstimateRepository, DailyStatsRepository
                    salary_repo = SalaryEstimateRepository(session)
                    await salary_repo.create(
                        job_id=job.id,
                        company_id=job.company_id,
                        role=job.title,
                        estimated_salary=result.estimated_salary,
                        confidence=result.confidence,
                        source_breakdown=result.source_breakdown,
                    )

                    stats_repo = DailyStatsRepository(session)
                    await stats_repo.increment_field("salary_lookups")

        except Exception as e:
            logger.error(
                "salary_estimate_error",
                job_id=str(job.id),
                error=str(e),
            )


async def match_jobs_task() -> None:
    """Score unmatched jobs against candidate profile."""
    async with get_async_session() as session:
        system = SystemService(session)
        if not await system.can_discover():
            return

    engine = MatchingEngine()
    candidate = get_candidate_profile()
    settings = get_settings()

    async with get_async_session() as session:
        job_service = JobService(session)
        jobs = await job_service.get_unmatched_jobs(limit=100)

    for job in jobs:
        try:
            result = engine.match(
                job_title=job.title,
                job_description=job.description,
                candidate=candidate,
                job_exp_min=job.experience_min,
                job_exp_max=job.experience_max,
            )

            # Determine status based on score
            if result.overall_score >= settings.job_filter.min_match_score:
                # Check salary too
                salary_ok = (
                    job.salary_estimate is None  # Unknown salary = give benefit
                    or job.salary_estimate >= settings.job_filter.min_salary_lpa
                )
                if salary_ok:
                    new_status = JobStatus.QUALIFIED
                else:
                    new_status = JobStatus.REJECTED
                    rejection_reason = f"Salary {job.salary_estimate}L below {settings.job_filter.min_salary_lpa}L threshold"
            else:
                new_status = JobStatus.REJECTED
                rejection_reason = f"Match score {result.overall_score} below {settings.job_filter.min_match_score} threshold"

            async with get_async_session() as session:
                job_service2 = JobService(session)
                if new_status == JobStatus.QUALIFIED:
                    await job_service2.update_job_match(
                        job.id, score=result.overall_score, status=new_status
                    )
                else:
                    await job_service2.update_job_match(
                        job.id,
                        score=result.overall_score,
                        status=new_status,
                        rejection_reason=rejection_reason,
                    )

                # Store match record
                from src.core.repositories.other_repositories import DailyStatsRepository
                from src.core.models.job_match import JobMatch
                session.add(JobMatch(
                    job_id=job.id,
                    user_id=(await UserIdHelper.get_user_id(session)),
                    overall_score=result.overall_score,
                    skill_score=result.skill_score,
                    experience_score=result.experience_score,
                    role_score=result.role_score,
                    technology_score=result.technology_score,
                    matched_skills=result.matched_skills,
                    missing_skills=result.missing_skills,
                    recommendation=result.recommendation,
                ))
                await session.flush()

                stats = DailyStatsRepository(session)
                if new_status == JobStatus.QUALIFIED:
                    await stats.increment_field("jobs_matched")
                    await stats.increment_field("jobs_qualified")
                else:
                    await stats.increment_field("jobs_rejected")

        except Exception as e:
            logger.error("match_job_error", job_id=str(job.id), error=str(e))


async def apply_jobs_task() -> None:
    """Run the auto-application cycle."""
    from src.appliers.engine import ApplicationEngine

    engine = ApplicationEngine()
    stats = await engine.run_apply_cycle()

    if stats["applied"] > 0 or stats["failed"] > 0:
        await notifications.notify_system_alert(
            f"Apply cycle: {stats['applied']} applied, "
            f"{stats['failed']} failed, {stats['skipped']} skipped",
            level="info",
        )


async def compute_daily_stats_task() -> None:
    """Recompute daily statistics."""
    async with get_async_session() as session:
        analytics = AnalyticsService(session)
        await analytics.compute_daily_stats()

    logger.info("daily_stats_computed")


async def health_check_task() -> None:
    """Update worker heartbeats and check system health."""
    from src.core.database.engine import check_database_health

    health = await check_database_health()
    if health.get("status") != "healthy":
        await notifications.notify_system_alert(
            f"Database unhealthy: {health.get('error', 'unknown')}",
            level="error",
        )


class UserIdHelper:
    """Helper to get the system user ID."""

    @staticmethod
    async def get_user_id(session) -> "uuid.UUID":  # type: ignore[name-defined]
        import uuid
        from src.core.repositories.user_repository import UserRepository
        user_repo = UserRepository(session)
        settings = get_settings()
        user = await user_repo.get_by_telegram_id(settings.telegram.allowed_user_id)
        if user:
            return user.id
        return uuid.uuid4()  # Fallback
