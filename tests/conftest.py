"""pytest configuration and global fixtures."""

from __future__ import annotations

import asyncio
import inspect
from typing import Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config.candidate import CandidateProfile
from src.core.config.settings import AppSettings, get_settings
from src.core.database.base import Base


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Run async test functions in the event loop without requiring pytest-asyncio."""
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        # Get the fixture arguments for this test function
        testargs = {
            arg: pyfuncitem.funcargs[arg]
            for arg in pyfuncitem._fixtureinfo.argnames
            if arg in pyfuncitem.funcargs
        }
        loop = asyncio.get_event_loop()
        loop.run_until_complete(pyfuncitem.obj(**testargs))
        return True
    return None


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> AppSettings:
    """Provide settings configured for test environment."""
    settings = get_settings()
    settings.debug = True
    settings.environment = "test"
    settings.database.database_url = "sqlite+aiosqlite:///:memory:"
    settings.database.database_url_sync = "sqlite:///:memory:"
    settings.telegram.allowed_user_id = 123456789
    settings.telegram.bot_token = "mock_bot_token"
    return settings


@pytest.fixture(scope="function")
def db_engine(test_settings: AppSettings) -> Generator[object, None, None]:
    """Initialize in-memory SQLite engine and create all schema tables."""
    engine = create_async_engine(
        test_settings.database.database_url,
        echo=False,
    )

    from src.core.models import (  # noqa: F401
        user, resume, resume_usage, company, job, job_source,
        salary_estimate, job_match, application, application_log,
        ats_provider_result, job_discovery_run, scheduler_run,
        telegram_command, system_setting, worker_status, statistics,
    )

    async def create_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_tables())

    yield engine

    loop.run_until_complete(drop_tables())


@pytest.fixture(scope="function")
def db_session(db_engine: object) -> Generator[AsyncSession, None, None]:
    """Provide a clean async database session within a transaction that rolls back."""
    session_factory = async_sessionmaker(
        bind=db_engine,  # type: ignore[arg-type]
        class_=AsyncSession,
        expire_on_commit=False,
    )

    loop = asyncio.get_event_loop()
    session = session_factory()

    yield session

    async def cleanup() -> None:
        await session.rollback()
        await session.close()

    loop.run_until_complete(cleanup())


@pytest.fixture
def candidate_profile() -> CandidateProfile:
    """Provide a standard candidate profile for testing."""
    return CandidateProfile(
        name="Test Candidate",
        email="test@example.com",
        phone="+919999999999",
        country="India",
        experience_years=5,
        skills=["Python", "Django", "PostgreSQL", "Docker", "Git"],
        target_roles=["Backend Engineer", "Software Engineer"],
    )
