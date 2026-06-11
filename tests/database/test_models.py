"""Tests for SQLAlchemy model integrity and constraints."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.user import User
from src.core.models.company import Company
from src.core.models.job import Job, JobStatus


@pytest.mark.asyncio
async def test_user_unique_telegram_id(db_session: AsyncSession) -> None:
    # 1. Create a user
    user1 = User(
        telegram_id=98765,
        name="User 1",
        email="user1@test.com",
    )
    db_session.add(user1)
    await db_session.commit()

    # 2. Try creating another user with same telegram_id
    user2 = User(
        telegram_id=98765,
        name="User 2",
        email="user2@test.com",
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_job_relationships_and_cascades(db_session: AsyncSession) -> None:
    # 1. Create company
    company = Company(
        name="Acme Tech",
    )
    db_session.add(company)
    await db_session.commit()

    # 2. Create job tied to company
    job = Job(
        company_id=company.id,
        title="Software Dev",
        apply_url="https://acme.tech/apply",
        ats_provider="lever",
        external_id="ext-1",
        status=JobStatus.NEW,
    )
    db_session.add(job)
    await db_session.commit()

    # 3. Check relationships
    assert job.company.name == "Acme Tech"
    assert company.jobs[0].title == "Software Dev"
