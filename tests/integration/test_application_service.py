"""Integration tests for ApplicationService."""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.application import ApplicationStatus, ApplicationMethod
from src.core.models.job import JobStatus
from src.core.repositories.user_repository import UserRepository
from src.core.repositories.job_repository import JobRepository
from src.core.repositories.resume_repository import ResumeRepository
from src.core.services.application_service import ApplicationService


@pytest.mark.asyncio
async def test_application_lifecycle_state_machine(db_session: AsyncSession) -> None:
    # 1. Setup entities
    user_repo = UserRepository(db_session)
    job_repo = JobRepository(db_session)
    resume_repo = ResumeRepository(db_session)
    app_service = ApplicationService(db_session)

    user = await user_repo.create(
        telegram_id=9876, name="Candidate B", email="b@test.com", phone="+1", country="US"
    )
    job = await job_repo.create(
        company_id=None,
        source_id=None,
        title="Python Dev",
        description="Write Django views",
        apply_url="https://lever.co/job-1",
        ats_provider="lever",
        external_id="lever-1",
    )
    resume = await resume_repo.create(
        user_id=user.id, name="r.pdf", file_path="/r.pdf", file_size=10
    )

    # 2. Create Application (PENDING)
    app = await app_service.create_application(job=job, resume_id=resume.id, user_id=user.id)
    assert app.id is not None
    assert app.status == ApplicationStatus.PENDING

    # 3. Mark Submitting
    await app_service.mark_submitting(app.id)
    # Refresh application status
    app_updated = await app_service.app_repo.get_by_id(app.id)
    assert app_updated.status == ApplicationStatus.SUBMITTING

    # 4. Mark Submitted (Success)
    await app_service.mark_submitted(app.id, method=ApplicationMethod.API, response_data={"status": "ok"})
    app_final = await app_service.app_repo.get_by_id(app.id)
    assert app_final.status == ApplicationStatus.SUBMITTED
    assert app_final.method == ApplicationMethod.API
    assert app_final.response_data == {"status": "ok"}

    # Job status should also update to APPLIED
    job_final = await job_repo.get_by_id(job.id)
    assert job_final.status == JobStatus.APPLIED
