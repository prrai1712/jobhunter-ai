"""Ashby ATS provider — job discovery and application via Ashby Posting API."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.providers.base import ATSProvider, ApplicationResult, DiscoveredJob

logger = structlog.get_logger(__name__)

ASHBY_API_BASE = "https://api.ashbyhq.com/posting-api"


class AshbyProvider(ATSProvider):
    """Ashby ATS integration via the Posting API.

    Discovery:     POST /posting-api/job-board/{board_slug}
    Job Info:      POST /posting-api/job-posting-info
    Apply:         POST /posting-api/application-form
    """

    @property
    def provider_name(self) -> str:
        return "ashby"

    async def discover_jobs(
        self, board_token: str, **kwargs: Any
    ) -> list[DiscoveredJob]:
        """Fetch all jobs from an Ashby job board."""
        jobs: list[DiscoveredJob] = []
        url = f"{ASHBY_API_BASE}/job-board/{board_token}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            job_postings = data.get("jobs", [])

            for job_data in job_postings:
                try:
                    job = self._parse_job(job_data, board_token)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(
                        "ashby_parse_error",
                        board=board_token,
                        error=str(e),
                    )

            logger.info(
                "ashby_discovery_complete",
                board=board_token,
                jobs_found=len(jobs),
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "ashby_api_error",
                board=board_token,
                status=e.response.status_code,
            )
        except Exception as e:
            logger.error(
                "ashby_discovery_failed",
                board=board_token,
                error=str(e),
            )

        return jobs

    def _parse_job(self, data: dict[str, Any], board_token: str) -> DiscoveredJob | None:
        """Parse an Ashby job posting into our standard format."""
        job_id = data.get("id", "")
        title = data.get("title", "")
        if not job_id or not title:
            return None

        # Description
        description_html = data.get("descriptionHtml", "")
        description = self._html_to_text(description_html)
        if not description:
            description = data.get("descriptionPlain", "")

        # Location
        location = data.get("location", "")
        if isinstance(location, dict):
            location = location.get("name", "")

        # Department
        department = data.get("department", "")
        if isinstance(department, dict):
            department = department.get("name", "")

        # Employment type
        employment_type = data.get("employmentType", "unknown")
        job_type = self._map_employment_type(employment_type)

        # Company name
        company_name = data.get("organizationName", board_token.replace("-", " ").title())

        # Apply URL
        apply_url = data.get("jobUrl", "")
        if not apply_url:
            apply_url = f"https://jobs.ashbyhq.com/{board_token}/{job_id}"

        # Experience
        exp_min, exp_max = self._extract_experience(description)

        return DiscoveredJob(
            title=title,
            company_name=company_name,
            description=description,
            apply_url=apply_url,
            ats_provider="ashby",
            external_id=job_id,
            location=location,
            experience_min=exp_min,
            experience_max=exp_max,
            job_type=job_type,
            department=department if isinstance(department, str) else None,
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
        """Submit an application via the Ashby Posting API.

        The Ashby API uses applicationForm.submit endpoint.
        We first fetch the form spec, then submit with the required fields.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Get form specification
                info_resp = await client.post(
                    f"{ASHBY_API_BASE}/job-posting-info",
                    json={"jobPostingId": external_id},
                )

                if info_resp.status_code != 200:
                    return ApplicationResult(
                        success=False,
                        method="api",
                        message=f"Failed to fetch form info: {info_resp.status_code}",
                        error_type="form_fetch_error",
                        status_code=info_resp.status_code,
                    )

                form_info = info_resp.json()

            # 2. Build submission data
            form_fields = self._build_form_data(form_info, candidate)

            # 3. Submit with resume as multipart
            files = {}
            try:
                with open(resume_path, "rb") as f:
                    resume_bytes = f.read()
                files["resume"] = ("resume.pdf", resume_bytes, "application/pdf")
            except FileNotFoundError:
                return ApplicationResult(
                    success=False,
                    method="api",
                    message="Resume file not found",
                    error_type="file_not_found",
                )

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ASHBY_API_BASE}/application-form",
                    data={
                        "jobPostingId": external_id,
                        **form_fields,
                    },
                    files=files,
                )

            response_data = {}
            try:
                response_data = response.json()
            except Exception:
                response_data = {"body": response.text[:500]}

            success = response_data.get("success", response.status_code in (200, 201))

            if success:
                return ApplicationResult(
                    success=True,
                    method="api",
                    message="Application submitted successfully via Ashby API",
                    response_data=response_data,
                    status_code=response.status_code,
                )
            else:
                error_msg = response_data.get("errors", response.text[:500])
                return ApplicationResult(
                    success=False,
                    method="api",
                    message=f"Ashby API error: {error_msg}",
                    response_data=response_data,
                    status_code=response.status_code,
                    error_type="validation_error",
                )

        except Exception as e:
            logger.error("ashby_apply_error", job_id=external_id, error=str(e))
            return ApplicationResult(
                success=False,
                method="api",
                message=f"Unexpected error: {str(e)}",
                error_type="unexpected",
            )

    def _build_form_data(
        self,
        form_info: dict[str, Any],
        candidate: dict[str, str],
    ) -> dict[str, str]:
        """Map Ashby form fields to candidate data."""
        form_data: dict[str, str] = {}

        # Standard fields
        form_data["_systemfield_name"] = (
            f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
        )
        form_data["_systemfield_email"] = candidate.get("email", "")
        form_data["_systemfield_phone"] = candidate.get("phone", "")

        # Parse form definition for custom fields
        form_def = form_info.get("info", {}).get("applicationFormDefinition", {})
        sections = form_def.get("sections", [])

        for section in sections:
            for field in section.get("fieldEntries", []):
                field_data = field.get("field", {})
                field_path = field_data.get("path", "")
                field_title = field_data.get("title", "").lower()
                required = field.get("isRequired", False)

                if "linkedin" in field_title:
                    form_data[field_path] = candidate.get("linkedin", "")
                elif "github" in field_title:
                    form_data[field_path] = candidate.get("github", "")
                elif "location" in field_title or "city" in field_title:
                    form_data[field_path] = candidate.get("location", "India")
                elif "experience" in field_title or "years" in field_title:
                    form_data[field_path] = candidate.get("experience_years", "1")
                elif required and not form_data.get(field_path):
                    form_data[field_path] = "N/A"

        return form_data

    @staticmethod
    def _html_to_text(html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _map_employment_type(emp_type: str) -> str:
        emp_lower = emp_type.lower() if emp_type else ""
        if "full" in emp_lower:
            return "full_time"
        elif "part" in emp_lower:
            return "part_time"
        elif "contract" in emp_lower:
            return "contract"
        elif "intern" in emp_lower:
            return "internship"
        return "unknown"

    @staticmethod
    def _extract_experience(text: str) -> tuple[int | None, int | None]:
        patterns = [
            r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return int(groups[0]), int(groups[1])
                return int(groups[0]), None
        return None, None
