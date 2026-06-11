"""APScheduler configuration — AsyncIOScheduler with PostgreSQL job store."""

from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.core.config.settings import get_settings

logger = structlog.get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    global _scheduler
    settings = get_settings()

    # Use sync engine URL for APScheduler's job store (it doesn't support async)
    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.database.database_url_sync),
    }

    _scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        },
    )

    # ─── Register scheduled jobs ─────────────────────────────────────

    # Job Discovery — every 2 hours
    _scheduler.add_job(
        "src.scheduler.tasks:discover_jobs_task",
        trigger=IntervalTrigger(hours=settings.scheduler.discover_interval_hours),
        id="discover_jobs",
        name="Job Discovery",
        replace_existing=True,
    )

    # Salary Estimation — every 2.5 hours
    _scheduler.add_job(
        "src.scheduler.tasks:estimate_salaries_task",
        trigger=IntervalTrigger(hours=settings.scheduler.salary_estimate_interval_hours),
        id="estimate_salaries",
        name="Salary Estimation",
        replace_existing=True,
    )

    # Job Matching — every 3 hours
    _scheduler.add_job(
        "src.scheduler.tasks:match_jobs_task",
        trigger=IntervalTrigger(hours=settings.scheduler.match_interval_hours),
        id="match_jobs",
        name="Job Matching",
        replace_existing=True,
    )

    # Auto Apply — every 4 hours
    _scheduler.add_job(
        "src.scheduler.tasks:apply_jobs_task",
        trigger=IntervalTrigger(hours=settings.scheduler.apply_interval_hours),
        id="apply_jobs",
        name="Auto Apply",
        replace_existing=True,
    )

    # Daily Stats — 11:55 PM
    _scheduler.add_job(
        "src.scheduler.tasks:compute_daily_stats_task",
        trigger=CronTrigger(
            hour=settings.scheduler.stats_hour,
            minute=settings.scheduler.stats_minute,
        ),
        id="compute_daily_stats",
        name="Daily Statistics",
        replace_existing=True,
    )

    # Health Check — every 30 minutes
    _scheduler.add_job(
        "src.scheduler.tasks:health_check_task",
        trigger=IntervalTrigger(minutes=settings.scheduler.health_check_interval_minutes),
        id="health_check",
        name="Health Check",
        replace_existing=True,
    )

    logger.info(
        "scheduler_created",
        jobs=len(_scheduler.get_jobs()),
    )

    return _scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the scheduler instance."""
    return _scheduler
