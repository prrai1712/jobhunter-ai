"""Unit tests for Lever ATS provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from src.providers.lever import LeverProvider


@pytest.fixture
def provider() -> LeverProvider:
    return LeverProvider()


@pytest.mark.asyncio
async def test_discover_jobs(provider: LeverProvider) -> None:
    # 1. Mock JSON payload from Lever API
    mock_payload = [
        {
            "id": "lever-job-123",
            "text": "Full Stack Engineer",
            "descriptionPlain": "We need a Full Stack developer.",
            "categories": {
                "location": "Remote",
                "department": "Engineering",
                "commitment": "Full-time",
            },
            "hostedUrl": "https://jobs.lever.co/acme/lever-job-123",
            "lists": [],
        }
    ]

    # 2. Patch HTTP client
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        # Call discovery
        jobs = await provider.discover_jobs("acme")

        # Verify parsing
        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Full Stack Engineer"
        assert job.company_name == "Acme"
        assert job.location == "Remote"
        assert job.job_type == "full_time"
        assert job.ats_provider == "lever"


@pytest.mark.asyncio
async def test_apply_to_job(provider: LeverProvider) -> None:
    candidate = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@doe.com",
        "phone": "+1234567",
        "linkedin": "https://linkedin.com/in/janedoe",
    }

    # Patch post and open file
    with patch("httpx.AsyncClient.post") as mock_post, \
         patch("builtins.open", mock_open(read_data=b"pdf_bytes")):

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "success"}
        mock_post.return_value = mock_resp

        result = await provider.apply_to_job(
            job_url="https://jobs.lever.co/acme/lever-job-123",
            external_id="lever-job-123",
            board_token="acme",
            resume_path="/dummy/resume.pdf",
            candidate=candidate,
        )

        assert result.success is True
        assert "submitted successfully" in result.message
        assert result.status_code == 200
