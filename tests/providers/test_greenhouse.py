"""Unit tests for Greenhouse ATS provider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.providers.greenhouse import GreenhouseProvider


@pytest.fixture
def provider() -> GreenhouseProvider:
    return GreenhouseProvider()


@pytest.mark.asyncio
async def test_discover_jobs(provider: GreenhouseProvider) -> None:
    # 1. Mock JSON payload from Greenhouse API
    mock_payload = {
        "jobs": [
            {
                "id": 12345,
                "title": "Software Engineer (Python)",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
                "content": "<p>We are looking for a Python dev with 3+ years experience.</p>",
                "location": {"name": "Bangalore"},
                "departments": [{"name": "Engineering"}],
                "company": {"name": "Acme Inc"},
            }
        ]
    }

    # 2. Patch HTTP requests
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
        assert job.title == "Software Engineer (Python)"
        assert job.company_name == "Acme Inc"
        assert "3+ years" in job.description
        assert job.location == "Bangalore"
        assert job.department == "Engineering"
        assert job.experience_min == 3


@pytest.mark.asyncio
async def test_apply_to_job_success(provider: GreenhouseProvider) -> None:
    # Mock Greenhouse question payload and POST response
    mock_questions_payload = {
        "questions": [
            {
                "label": "LinkedIn Profile",
                "required": True,
                "fields": [{"name": "question_111", "type": "input_text"}],
            }
        ]
    }

    candidate = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@doe.com",
        "phone": "+919999999999",
        "linkedin": "https://linkedin.com/in/johndoe",
    }

    with patch("httpx.AsyncClient.get") as mock_get, \
         patch("httpx.AsyncClient.post") as mock_post, \
         patch("builtins.open", mock_open(read_data=b"pdf_bytes")):

        # Mock GET questions
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = mock_questions_payload
        mock_get_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_get_resp

        # Mock POST apply
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.text = '{"success": "ok"}'
        mock_post_resp.json.return_value = {"success": "ok"}
        mock_post.return_value = mock_post_resp

        result = await provider.apply_to_job(
            job_url="https://boards.greenhouse.io/acme/jobs/12345",
            external_id="12345",
            board_token="acme",
            resume_path="/dummy/resume.pdf",
            candidate=candidate,
        )

        assert result.success is True
        assert result.status_code == 201
        assert "submitted successfully" in result.message


# Re-import missing helpers inside tests
from unittest.mock import MagicMock, mock_open
