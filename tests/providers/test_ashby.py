"""Unit tests for Ashby ATS provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from src.providers.ashby import AshbyProvider


@pytest.fixture
def provider() -> AshbyProvider:
    return AshbyProvider()


@pytest.mark.asyncio
async def test_discover_jobs(provider: AshbyProvider) -> None:
    # 1. Mock JSON payload from Ashby API
    mock_payload = {
        "jobs": [
            {
                "id": "ashby-job-99",
                "title": "Machine Learning Engineer",
                "descriptionHtml": "<p>Build models with Python and PyTorch.</p>",
                "location": {"name": "SF"},
                "department": {"name": "AI Lab"},
                "employmentType": "FullTime",
                "organizationName": "Acme Robots",
                "jobUrl": "https://jobs.ashbyhq.com/acme/ashby-job-99",
            }
        ]
    }

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
        assert job.title == "Machine Learning Engineer"
        assert job.company_name == "Acme Robots"
        assert job.location == "SF"
        assert job.job_type == "full_time"
        assert job.ats_provider == "ashby"


@pytest.mark.asyncio
async def test_apply_to_job(provider: AshbyProvider) -> None:
    mock_form_info = {
        "info": {
            "applicationFormDefinition": {
                "sections": [
                    {
                        "fieldEntries": [
                            {
                                "field": {
                                    "path": "field_linkedin",
                                    "title": "LinkedIn URL",
                                },
                                "isRequired": True,
                            }
                        ]
                    }
                ]
            }
        }
    }

    candidate = {
        "first_name": "Bob",
        "last_name": "Smith",
        "email": "bob@smith.com",
        "phone": "+12345",
        "linkedin": "https://linkedin.com/in/bobsmith",
    }

    with patch("httpx.AsyncClient.post") as mock_post, \
         patch("builtins.open", mock_open(read_data=b"pdf_bytes")):

        # Mock form spec response
        mock_info_resp = MagicMock()
        mock_info_resp.status_code = 200
        mock_info_resp.json.return_value = mock_form_info

        # Mock submit response
        mock_submit_resp = MagicMock()
        mock_submit_resp.status_code = 200
        mock_submit_resp.json.return_value = {"success": True}

        # Sequence of calls: 1. info post, 2. submit post
        mock_post.side_effect = [mock_info_resp, mock_submit_resp]

        result = await provider.apply_to_job(
            job_url="https://jobs.ashbyhq.com/acme/ashby-job-99",
            external_id="ashby-job-99",
            board_token="acme",
            resume_path="/dummy/resume.pdf",
            candidate=candidate,
        )

        assert result.success is True
        assert "submitted successfully" in result.message
        assert result.status_code == 200
