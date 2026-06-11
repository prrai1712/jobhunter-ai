"""JobHunter AI — Main entry point.

Initializes all subsystems and runs the Telegram bot with the scheduler.
"""

from __future__ import annotations

import asyncio
import signal
import sys

import structlog

from src.core.config.settings import get_settings
from src.core.database.engine import dispose_engines, get_async_session
from src.logging.logger import setup_logging
from src.providers.registry import register_all_providers
from src.storage.file_storage import FileStorage


logger = structlog.get_logger(__name__)


async def seed_initial_data() -> None:
    """Seed the database with initial job sources from config."""
    settings = get_settings()

    async with get_async_session() as session:
        from src.core.repositories.other_repositories import (
            JobSourceRepository,
            SystemSettingsRepository,
        )
        from src.core.repositories.user_repository import UserRepository

        # Create or update user
        user_repo = UserRepository(session)
        await user_repo.get_or_create(
            telegram_id=settings.telegram.allowed_user_id,
            name=settings.candidate.name,
            email=settings.candidate.email,
            phone=settings.candidate.phone,
            country=settings.candidate.country,
        )

        # Seed job sources
        source_repo = JobSourceRepository(session)

        # Greenhouse boards
        for board in settings.job_sources.greenhouse_boards:
            existing = await source_repo.get_by_provider_and_token("greenhouse", board)
            if not existing:
                await source_repo.create(
                    name=f"Greenhouse/{board}",
                    provider_type="greenhouse",
                    board_token=board,
                    base_url=f"https://boards-api.greenhouse.io/v1/boards/{board}",
                    is_active=True,
                )

        # Lever companies
        for company in settings.job_sources.lever_companies:
            existing = await source_repo.get_by_provider_and_token("lever", company)
            if not existing:
                await source_repo.create(
                    name=f"Lever/{company}",
                    provider_type="lever",
                    board_token=company,
                    base_url=f"https://api.lever.co/v0/postings/{company}",
                    is_active=True,
                )

        # Ashby boards
        for board in settings.job_sources.ashby_boards:
            existing = await source_repo.get_by_provider_and_token("ashby", board)
            if not existing:
                await source_repo.create(
                    name=f"Ashby/{board}",
                    provider_type="ashby",
                    board_token=board,
                    base_url=f"https://api.ashbyhq.com/posting-api/job-board/{board}",
                    is_active=True,
                )

        # Initialize system state if not set
        settings_repo = SystemSettingsRepository(session)
        state = await settings_repo.get_setting("system_state")
        if state is None:
            await settings_repo.set_setting(
                "system_state",
                {"state": "stopped"},
                description="Global system state",
                updated_by="init",
            )

    logger.info("initial_data_seeded")


async def run_migrations() -> None:
    """Run Alembic migrations programmatically."""
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("migrations_complete")
    except Exception as e:
        logger.warning("migrations_skipped", reason=str(e))
        # Create tables directly as fallback
        from src.core.database.engine import get_async_engine
        from src.core.database.base import Base
        # Import all models to register them
        from src.core.models import (  # noqa: F401
            user, resume, resume_usage, company, job, job_source,
            salary_estimate, job_match, application, application_log,
            ats_provider_result, job_discovery_run, scheduler_run,
            telegram_command, system_setting, worker_status, statistics,
        )
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("tables_created_directly")


def main() -> None:
    """Main entry point — sets up everything and runs the bot."""
    # 1. Setup logging
    setup_logging()
    logger.info("jobhunter_starting")

    # 2. Load settings
    settings = get_settings()
    logger.info(
        "settings_loaded",
        environment=settings.environment,
        debug=settings.debug,
    )

    # 3. Ensure storage directories
    storage = FileStorage()
    storage.ensure_directories()

    # 4. Register providers
    register_all_providers()

    # 5. Run async setup
    asyncio.get_event_loop().run_until_complete(_async_setup())

    # 6. Create and run bot with scheduler
    _run_bot()


async def _async_setup() -> None:
    """Async initialization tasks."""
    # Run migrations / create tables
    await run_migrations()

    # Seed initial data
    await seed_initial_data()


def _run_bot() -> None:
    """Create the Telegram bot and scheduler, then run."""
    from src.telegram.bot import create_bot
    from src.scheduler.scheduler import create_scheduler

    # Create scheduler
    scheduler = create_scheduler()

    # Create bot
    app = create_bot()

    # Start scheduler when bot starts
    async def on_startup(_app) -> None:  # type: ignore[no-untyped-def]
        scheduler.start()
        logger.info("scheduler_started")

    async def on_shutdown(_app) -> None:  # type: ignore[no-untyped-def]
        scheduler.shutdown(wait=False)
        await dispose_engines()
        logger.info("shutdown_complete")

    app.post_init = on_startup  # type: ignore[assignment]
    app.post_shutdown = on_shutdown  # type: ignore[assignment]

    # Run bot (blocking)
    logger.info("starting_telegram_bot")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
