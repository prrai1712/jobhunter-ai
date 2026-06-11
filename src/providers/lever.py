"""Lever ATS provider — job discovery and application via Lever Postings API."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.providers.base import ATSProvider, ApplicationResult, DiscoveredJob

logger = structlog.get_logger(__name__)

LEVER_API_BASE = "https://api.lever.co/v0/postings"


class LeverProvider(ATSProvider):
    """Lever ATS integration via the Postings API.

    Discovery: GET https://api.lever.co/v0/postings/{company}
    Apply:     POST https://api.lever.co/v0/postings/{company}/{id}/apply
    """

    @property
    def provider_name(self) -> str:
        return "lever"

    async def discover_jobs(
        self, board_token: str, **kwargs: Any
    ) -> list[DiscoveredJob]:
        """Fetch all jobs from a Lever company board."""
        jobs: list[DiscoveredJob] = []
        url = f"{LEVER_API_BASE}/{board_token}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            if not isinstance(data, list):
                logger.warning("lever_unexpected_format", board=board_token)
                return jobs

            for job_data in data:
                try:
                    job = self._parse_job(job_data, board_token)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(
                        "lever_parse_error",
                        board=board_token,
                        job_id=job_data.get("id"),
                        error=str(e),
                    )

            logger.info(
                "lever_discovery_complete",
                board=board_token,
                jobs_found=len(jobs),
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "lever_api_error",
                board=board_token,
                status=e.response.status_code,
            )
        except Exception as e:
            logger.error(
                "lever_discovery_failed",
                board=board_token,
                error=str(e),
            )

        return jobs

    def _parse_job(self, data: dict[str, Any], board_token: str) -> DiscoveredJob | None:
        """Parse a Lever job posting into our standard format."""
        job_id = data.get("id", "")
        text = data.get("text", "")
        if not job_id or not text:
            return None

        # Description from lists (Lever uses a structured format)
        description_parts = []
        if data.get("descriptionPlain"):
            description_parts.append(data["descriptionPlain"])
        for section in data.get("lists", []):
            section_text = section.get("text", "")
            content = section.get("content", "")
            if section_text:
                description_parts.append(f"\n{section_text}")
            if content:
                clean = self._html_to_text(content)
                description_parts.append(clean)
        if data.get("additionalPlain"):
            description_parts.append(data["additionalPlain"])
        description = "\n".join(description_parts)

        # Categories
        categories = data.get("categories", {})
        location = categories.get("location", "")
        department = categories.get("department", "")
        commitment = categories.get("commitment", "")  # e.g., "Full-time"

        # Map commitment to job_type
        job_type = self._map_commitment(commitment)

        # Apply URL
        apply_url = data.get("applyUrl") or data.get("hostedUrl", "")

        # Company name
        company_name = board_token.replace("-", " ").title()

        # Extract experience
        exp_min, exp_max = self._extract_experience(description)

        return DiscoveredJob(
            title=text,
            company_name=company_name,
            description=description,
            apply_url=apply_url,
            ats_provider="lever",
            external_id=job_id,
            location=location,
            experience_min=exp_min,
            experience_max=exp_max,
            job_type=job_type,
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
        """Submit an application via the Lever Postings API.

        POST /v0/postings/{company}/{id}/apply
        Accepts multipart/form-data with name, email, phone, resume.
        """
        api_url = f"{LEVER_API_BASE}/{board_token}/{external_id}/apply"

        try:
            # Build form data
            form_data = {
                "name": f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip(),
                "email": candidate.get("email", ""),
                "phone": candidate.get("phone", ""),
            }

            # Optional fields
            if candidate.get("linkedin"):
                form_data["urls[LinkedIn]"] = candidate["linkedin"]
            if candidate.get("website"):
                form_data["urls[Portfolio]"] = candidate["website"]
            if candidate.get("github"):
                form_data["urls[GitHub]"] = candidate["github"]

            # Resume file
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

            # Submit
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, data=form_data, files=files)

            if response.status_code in (200, 201):
                response_data = {}
                try:
                    response_data = response.json()
                except Exception:
                    response_data = {"body": response.text[:500]}

                return ApplicationResult(
                    success=True,
                    method="api",
                    message="Application submitted successfully via Lever API",
                    response_data=response_data,
                    status_code=response.status_code,
                )
            else:
                return ApplicationResult(
                    success=False,
                    method="api",
                    message=f"Lever API returned {response.status_code}: {response.text[:500]}",
                    response_data={"body": response.text[:1000]},
                    status_code=response.status_code,
                    error_type="api_error",
                )

        except Exception as e:
            logger.error("lever_apply_error", job_id=external_id, error=str(e))
            return ApplicationResult(
                success=False,
                method="api",
                message=f"Unexpected error: {str(e)}",
                error_type="unexpected",
            )

    @staticmethod
    def _html_to_text(html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _map_commitment(commitment: str) -> str:
        commitment_lower = commitment.lower()
        if "full" in commitment_lower:
            return "full_time"
        elif "part" in commitment_lower:
            return "part_time"
        elif "contract" in commitment_lower:
            return "contract"
        elif "intern" in commitment_lower:
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
