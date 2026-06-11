"""Candidate profile dataclass — used throughout the application pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.config.settings import get_settings


@dataclass(frozen=True)
class CandidateProfile:
    """Immutable candidate profile for job matching and application submission."""

    name: str
    first_name: str
    last_name: str
    email: str
    phone: str
    country: str
    current_position: str
    current_company: str
    experience_years: int
    skills: list[str] = field(default_factory=list)
    target_roles: list[str] = field(default_factory=list)
    min_experience: int = 1
    max_experience: int = 4

    @property
    def skills_lower(self) -> list[str]:
        """Lowercase skills for case-insensitive matching."""
        return [s.lower() for s in self.skills]

    @property
    def target_roles_lower(self) -> list[str]:
        """Lowercase target roles for case-insensitive matching."""
        return [r.lower() for r in self.target_roles]


def get_candidate_profile() -> CandidateProfile:
    """Build candidate profile from application settings."""
    settings = get_settings()
    candidate = settings.candidate
    filters = settings.job_filter

    name_parts = candidate.name.strip().split(maxsplit=1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    return CandidateProfile(
        name=candidate.name,
        first_name=first_name,
        last_name=last_name,
        email=candidate.email,
        phone=candidate.phone,
        country=candidate.country,
        current_position=candidate.current_position,
        current_company=candidate.current_company,
        experience_years=candidate.experience_years,
        skills=filters.candidate_skills,
        target_roles=filters.target_roles,
        min_experience=filters.min_experience_years,
        max_experience=filters.max_experience_years,
    )
