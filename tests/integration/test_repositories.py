"""Integration tests for database repositories."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.user import User
from src.core.models.resume import Resume
from src.core.models.job import Job
from src.core.repositories.user_repository import UserRepository
from src.core.repositories.resume_repository import ResumeRepository
from src.core.repositories.job_repository import JobRepository


@pytest.mark.asyncio
async def test_user_repository_crud(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    # 1. Create User
    user = await repo.create(
        telegram_id=11223344,
        name="John Doe",
        email="john@example.com",
        phone="+919000000000",
        country="India",
    )
    assert user.id is not None
    assert user.telegram_id == 11223344

    # 2. Get by telegram ID
    fetched = await repo.get_by_telegram_id(11223344)
    assert fetched is not None
    assert fetched.name == "John Doe"

    # 3. Create or Update
    updated = await repo.get_or_create(
        telegram_id=11223344,
        name="John Updated",
        email="john@example.com",
        phone="+919000000000",
        country="India",
    )
    # The name should be updated
    assert updated.name == "John Updated"


@pytest.mark.asyncio
async def test_resume_repository_active(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    resume_repo = ResumeRepository(db_session)

    # Setup user
    user = await user_repo.create(
        telegram_id=998877,
        name="Candidate A",
        email="candidate@example.com",
        phone="+1234567890",
        country="US",
    )

    # Create Resume 1
    res1 = await resume_repo.create(
        user_id=user.id,
        name="resume1.pdf",
        file_path="/data/resume1.pdf",
        file_size=1024,
        is_active=False,
    )

    # Create Resume 2
    res2 = await resume_repo.create(
        user_id=user.id,
        name="resume2.pdf",
        file_path="/data/resume2.pdf",
        file_size=2048,
        is_active=True,
    )

    # Verify active resume
    active = await resume_repo.get_active(user.id)
    assert active is not None
    assert active.id == res2.id
    assert active.name == "resume2.pdf"

    # Set active to res1
    await resume_repo.set_active(res1.id, user.id)

    # Verify transition
    active = await resume_repo.get_active(user.id)
    assert active is not None
    assert active.id == res1.id
    assert active.name == "resume1.pdf"


@pytest.mark.asyncio
async def test_job_repository_deduplication(db_session: AsyncSession) -> None:
    job_repo = JobRepository(db_session)

    # Create first job
    job1 = await job_repo.create(
        company_id=None,
        source_id=None,
        title="Django Developer",
        description="Write cool code",
        location="Remote",
        apply_url="https://jobs.example.com/django-1",
        ats_provider="greenhouse",
        external_id="gh-django-1",
    )

    assert job1.id is not None

    # Check existence
    assert await job_repo.exists_by_url("https://jobs.example.com/django-1") is True
    assert await job_repo.exists_by_url("https://jobs.example.com/other") is False
