"""Integration tests for JobService."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.services.job_service import JobService
from src.core.models.job import JobStatus


@pytest.mark.asyncio
async def test_process_discovered_job_flow(db_session: AsyncSession) -> None:
    service = JobService(db_session)

    job_data = {
        "title": "Staff Backend Engineer",
        "company_name": "Acme Corp",
        "description": "Awesome Django backend work.",
        "location": "Remote, India",
        "apply_url": "https://boards.greenhouse.io/acme/jobs/999",
        "ats_provider": "greenhouse",
        "external_id": "999",
        "experience_min": 5,
        "experience_max": 8,
        "job_type": "full_time",
    }

    # 1. First processing should succeed and create company and job
    job = await service.process_discovered_job(job_data)
    assert job is not None
    assert job.title == "Staff Backend Engineer"
    assert job.status == JobStatus.NEW
    assert job.company_id is not None

    # Check that company Acme Corp is created
    company = await service.company_repo.get_by_id(job.company_id)
    assert company is not None
    assert company.name == "Acme Corp"
    assert company.jobs_discovered == 1

    # 2. Second processing with the same URL should return None (deduplicated)
    duplicate_job = await service.process_discovered_job(job_data)
    assert duplicate_job is None

    # 3. Third processing with different URL but same external ID should also return None
    job_data_diff_url = job_data.copy()
    job_data_diff_url["apply_url"] = "https://boards.greenhouse.io/acme/jobs/999-dup"
    duplicate_external = await service.process_discovered_job(job_data_diff_url)
    assert duplicate_external is None
