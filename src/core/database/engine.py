"""Database engine and session management.

Provides both async (asyncpg) and sync (psycopg2) session factories.
The sync factory is specifically for APScheduler's SQLAlchemyJobStore,
which does not support async drivers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from src.core.config.settings import get_settings

# ---------------------------------------------------------------------------
# Async engine (asyncpg) — primary engine for all application queries
# ---------------------------------------------------------------------------
_async_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None

# ---------------------------------------------------------------------------
# Sync engine (psycopg2) — used exclusively by APScheduler
# ---------------------------------------------------------------------------
_sync_engine = None
_sync_session_factory: sessionmaker[Session] | None = None


def get_async_engine():  # type: ignore[no-untyped-def]
    """Lazily create the async engine."""
    global _async_engine
    if _async_engine is None:
        settings = get_settings().database
        _async_engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=get_settings().debug,
        )
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazily create the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session scope."""
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_sync_engine():  # type: ignore[no-untyped-def]
    """Lazily create the sync engine for APScheduler."""
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings().database
        _sync_engine = create_engine(
            settings.database_url_sync,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
    return _sync_engine


def get_sync_session_factory() -> sessionmaker[Session]:
    """Lazily create the sync session factory."""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            expire_on_commit=False,
        )
    return _sync_session_factory


async def check_database_health() -> dict[str, object]:
    """Run a health check against the database and return diagnostics."""
    engine = get_async_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()

            # Get pool stats
            pool = engine.pool
            return {
                "status": "healthy",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def dispose_engines() -> None:
    """Dispose of all engine connections. Call during shutdown."""
    global _async_engine, _sync_engine
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
