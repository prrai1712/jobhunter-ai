"""Unit tests for MatchingEngine."""

from __future__ import annotations

import pytest
from src.core.config.candidate import CandidateProfile
from src.matching.engine import MatchingEngine


@pytest.fixture
def matching_engine() -> MatchingEngine:
    return MatchingEngine()


def test_matching_engine_match_flow(
    matching_engine: MatchingEngine, candidate_profile: CandidateProfile
) -> None:
    job_title = "Python Backend Engineer"
    job_description = (
        "We need a Python developer who is expert in Django and PostgreSQL. "
        "Experience with Docker and Git is required. Minimum 4 years of experience."
    )

    result = matching_engine.match(
        job_title=job_title,
        job_description=job_description,
        candidate=candidate_profile,
    )

    # Candidate profile has Python, Django, PostgreSQL, Docker, Git.
    # Job has: Python, Django, PostgreSQL, Docker, Git (exact match on all!).
    # Candidate experience is 5 years, job minimum is 4 years.
    # Target roles match "Backend Engineer".
    assert result.overall_score > 90.0
    assert result.recommendation == "apply"
    assert "Python" in result.matched_skills
    assert "Django" in result.matched_skills
    assert "PostgreSQL" in result.matched_skills
    assert len(result.missing_skills) == 0


def test_matching_engine_unmatched_flow(
    matching_engine: MatchingEngine, candidate_profile: CandidateProfile
) -> None:
    job_title = "Senior Frontend Developer"
    job_description = (
        "We are looking for a React / Vue wizard with CSS3, HTML5 and Tailwind. "
        "Requires 10 years of experience."
    )

    result = matching_engine.match(
        job_title=job_title,
        job_description=job_description,
        candidate=candidate_profile,
    )

    # Candidate skills do not match React/Vue/CSS3/HTML5.
    # Candidate experience is 5, job requires 10 (substantial deviation).
    # Job title does not match Target Roles (Backend Engineer).
    assert result.overall_score < 50.0
    assert result.recommendation == "skip"
    assert len(result.matched_skills) == 0
    assert len(result.missing_skills) > 0
