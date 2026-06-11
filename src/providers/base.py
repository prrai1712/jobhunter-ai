"""Abstract base for ATS job discovery and application providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DiscoveredJob:
    """Standard representation of a job discovered from an ATS."""

    title: str
    company_name: str
    description: str
    apply_url: str
    ats_provider: str
    external_id: str
    location: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    job_type: str = "unknown"
    department: str | None = None
    posted_at: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationResult:
    """Result of an application attempt."""

    success: bool
    method: str  # "api" or "browser"
    message: str = ""
    response_data: dict[str, Any] = field(default_factory=dict)
    status_code: int | None = None
    screenshot_path: str | None = None
    html_snapshot_path: str | None = None
    error_type: str | None = None


class ATSProvider(ABC):
    """Abstract base class for ATS integration providers.

    Each ATS provider must implement:
    1. Job discovery — fetching available jobs from the ATS board
    2. Job application — submitting applications via API or browser
    """

    @abstractmethod
    async def discover_jobs(
        self, board_token: str, **kwargs: Any
    ) -> list[DiscoveredJob]:
        """Discover available jobs from an ATS board.

        Args:
            board_token: The company's board identifier/slug.

        Returns:
            List of discovered job postings.
        """
        ...

    @abstractmethod
    async def apply_to_job(
        self,
        job_url: str,
        external_id: str,
        board_token: str,
        resume_path: str,
        candidate: dict[str, str],
        **kwargs: Any,
    ) -> ApplicationResult:
        """Submit an application to a job.

        Args:
            job_url: The job's application URL.
            external_id: The ATS-specific job ID.
            board_token: The company's board identifier.
            resume_path: Local path to the resume PDF.
            candidate: Dict with first_name, last_name, email, phone.

        Returns:
            ApplicationResult indicating success or failure.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique name of this provider (e.g., 'greenhouse')."""
        ...
