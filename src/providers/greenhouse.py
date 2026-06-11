"""Greenhouse ATS provider — job discovery and application via Greenhouse Job Board API."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.providers.base import ATSProvider, ApplicationResult, DiscoveredJob

logger = structlog.get_logger(__name__)

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"
GREENHOUSE_BOARD_BASE = "https://boards.greenhouse.io"


class GreenhouseProvider(ATSProvider):
    """Greenhouse ATS integration via the public Job Board API.

    Discovery: GET /v1/boards/{board_token}/jobs
    Details:   GET /v1/boards/{board_token}/jobs/{id}?questions=true
    Apply:     POST /v1/boards/{board_token}/jobs/{id} (multipart/form-data)
    """

    @property
    def provider_name(self) -> str:
        return "greenhouse"

    async def discover_jobs(
        self, board_token: str, **kwargs: Any
    ) -> list[DiscoveredJob]:
        """Fetch all jobs from a Greenhouse board.

        The Greenhouse Job Board API is public and requires no authentication.
        """
        jobs: list[DiscoveredJob] = []
        url = f"{GREENHOUSE_API_BASE}/{board_token}/jobs"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params={"content": "true"})
                response.raise_for_status()
                data = response.json()

            for job_data in data.get("jobs", []):
                try:
                    job = self._parse_job(job_data, board_token)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(
                        "greenhouse_parse_error",
                        board=board_token,
                        job_id=job_data.get("id"),
                        error=str(e),
                    )

            logger.info(
                "greenhouse_discovery_complete",
                board=board_token,
                jobs_found=len(jobs),
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "greenhouse_api_error",
                board=board_token,
                status=e.response.status_code,
                error=str(e),
            )
        except Exception as e:
            logger.error(
                "greenhouse_discovery_failed",
                board=board_token,
                error=str(e),
            )

        return jobs

    def _parse_job(self, data: dict[str, Any], board_token: str) -> DiscoveredJob | None:
        """Parse a Greenhouse job JSON into our standard format."""
        job_id = data.get("id")
        title = data.get("title", "")
        if not job_id or not title:
            return None

        # Extract content (HTML) and clean it
        content_html = data.get("content", "")
        description = self._html_to_text(content_html)

        # Location
        location_data = data.get("location", {})
        location = location_data.get("name", "") if isinstance(location_data, dict) else ""

        # Departments
        departments = data.get("departments", [])
        department = departments[0].get("name", "") if departments else None

        # Apply URL
        apply_url = data.get("absolute_url", "")
        if not apply_url:
            apply_url = f"{GREENHOUSE_BOARD_BASE}/{board_token}/jobs/{job_id}"

        # Extract experience from description
        exp_min, exp_max = self._extract_experience(description)

        # Extract company name from metadata or board token
        company_name = data.get("company", {}).get("name", board_token.replace("-", " ").title())

        return DiscoveredJob(
            title=title,
            company_name=company_name,
            description=description,
            apply_url=apply_url,
            ats_provider="greenhouse",
            external_id=str(job_id),
            location=location,
            experience_min=exp_min,
            experience_max=exp_max,
            department=department,
            raw_data=data,
        )

    async def apply_to_job(
        self,
        job_url: str,
        external_id: str,
        board_token: str,
        resume_path: str,
        candidate: dict[str, str],
        **kwargs: Any,
    ) -> ApplicationResult:
        """Submit an application via the Greenhouse Job Board API.

        The API accepts multipart/form-data with:
        - first_name, last_name, email, phone
        - resume (file upload)
        """
        api_url = f"{GREENHOUSE_API_BASE}/{board_token}/jobs/{external_id}"

        try:
            # First, fetch form questions
            async with httpx.AsyncClient(timeout=30.0) as client:
                detail_resp = await client.get(api_url, params={"questions": "true"})
                detail_resp.raise_for_status()
                job_details = detail_resp.json()

            # Build form data
            form_data = {
                "first_name": candidate.get("first_name", ""),
                "last_name": candidate.get("last_name", ""),
                "email": candidate.get("email", ""),
                "phone": candidate.get("phone", ""),
            }

            # Map custom questions if they exist
            questions = job_details.get("questions", [])
            form_data = self._map_questions(form_data, questions, candidate)

            # Prepare the file
            files = {}
            try:
                with open(resume_path, "rb") as f:
                    resume_bytes = f.read()
                files["resume"] = (
                    "resume.pdf",
                    resume_bytes,
                    "application/pdf",
                )
            except FileNotFoundError:
                return ApplicationResult(
                    success=False,
                    method="api",
                    message="Resume file not found",
                    error_type="file_not_found",
                )

            # Submit application
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    api_url,
                    data=form_data,
                    files=files,
                )

            if response.status_code in (200, 201):
                return ApplicationResult(
                    success=True,
                    method="api",
                    message="Application submitted successfully via Greenhouse API",
                    response_data=response.json() if response.text else {},
                    status_code=response.status_code,
                )
            else:
                return ApplicationResult(
                    success=False,
                    method="api",
                    message=f"Greenhouse API returned {response.status_code}: {response.text[:500]}",
                    response_data={"body": response.text[:1000]},
                    status_code=response.status_code,
                    error_type="api_error",
                )

        except httpx.HTTPStatusError as e:
            return ApplicationResult(
                success=False,
                method="api",
                message=f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code,
                error_type="http_error",
            )
        except Exception as e:
            logger.error(
                "greenhouse_apply_error",
                job_id=external_id,
                error=str(e),
            )
            return ApplicationResult(
                success=False,
                method="api",
                message=f"Unexpected error: {str(e)}",
                error_type="unexpected",
            )

    def _map_questions(
        self,
        form_data: dict[str, str],
        questions: list[dict],
        candidate: dict[str, str],
    ) -> dict[str, str]:
        """Map Greenhouse custom questions to candidate data."""
        for q in questions:
            label = (q.get("label") or "").lower()
            required = q.get("required", False)
            fields = q.get("fields", [])

            for field in fields:
                field_name = field.get("name", "")
                field_type = field.get("type", "")

                # Map known fields
                if "linkedin" in label:
                    form_data[field_name] = candidate.get("linkedin", "")
                elif "github" in label:
                    form_data[field_name] = candidate.get("github", "")
                elif "website" in label or "portfolio" in label:
                    form_data[field_name] = candidate.get("website", "")
                elif "phone" in label:
                    form_data[field_name] = candidate.get("phone", "")
                elif "location" in label or "city" in label:
                    form_data[field_name] = candidate.get("location", "India")
                elif "experience" in label or "years" in label:
                    form_data[field_name] = candidate.get("experience_years", "1")
                elif required and field_type == "input_text":
                    # Fill required text fields with a reasonable default
                    form_data[field_name] = candidate.get("default_answer", "N/A")

        return form_data

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML to clean text."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _extract_experience(text: str) -> tuple[int | None, int | None]:
        """Extract experience requirements from job description text."""
        patterns = [
            r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
            r"minimum\s*(\d+)\s*(?:years?|yrs?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return int(groups[0]), int(groups[1])
                return int(groups[0]), None
        return None, None
