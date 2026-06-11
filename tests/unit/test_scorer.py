"""Unit tests for MatchScorer."""

from __future__ import annotations

import pytest
from src.matching.scorer import MatchScorer


@pytest.fixture
def scorer() -> MatchScorer:
    return MatchScorer()


def test_score_exact_match(scorer: MatchScorer) -> None:
    candidate_skills = {"python", "django", "postgresql", "docker"}
    job_skills = {"python", "django", "postgresql", "docker"}
    candidate_exp = 5
    job_exp_min = 3
    job_exp_max = 6
    candidate_roles = ["Backend Engineer", "Python Developer"]
    job_title = "Backend Engineer - Python"

    result = scorer.score(
        candidate_skills=candidate_skills,
        job_skills=job_skills,
        candidate_experience=candidate_exp,
        job_exp_min=job_exp_min,
        job_exp_max=job_exp_max,
        candidate_roles=candidate_roles,
        job_title=job_title,
    )

    assert result.overall_score == 100.0
    assert result.skill_score == 100.0
    assert result.experience_score == 100.0
    assert result.role_score == 100.0
    assert result.recommendation == "apply"


def test_score_experience_gaussian_decay(scorer: MatchScorer) -> None:
    # Exact match within range
    assert scorer._score_experience(5, 3, 7) == 100.0

    # Minimum exp only, matching
    assert scorer._score_experience(5, 3, None) == 100.0

    # Outside range - minor deviation
    score_close = scorer._score_experience(2, 3, 5) # 1 year below
    assert 50 < score_close < 100

    # Outside range - major deviation
    score_far = scorer._score_experience(0, 5, 8) # 5 years below
    assert score_far < 10.0


def test_score_role_overlap(scorer: MatchScorer) -> None:
    # Exact substring match
    assert scorer._score_role(["Backend Engineer"], "Senior Backend Engineer") == 100.0

    # Partial match
    assert scorer._score_role(["Backend Developer"], "Python Developer") == 50.0

    # No match
    assert scorer._score_role(["Data Scientist"], "Frontend UI Engineer") == 0.0


def test_score_partial_match(scorer: MatchScorer) -> None:
    candidate_skills = {"python", "docker"}
    job_skills = {"python", "django", "postgresql", "docker"} # 2 out of 4 matches
    candidate_exp = 2
    job_exp_min = 4
    job_exp_max = 6 # 2 years below range -> decay
    candidate_roles = ["Backend Engineer"]
    job_title = "Senior Frontend Developer" # No role match

    result = scorer.score(
        candidate_skills=candidate_skills,
        job_skills=job_skills,
        candidate_experience=candidate_exp,
        job_exp_min=job_exp_min,
        job_exp_max=job_exp_max,
        candidate_roles=candidate_roles,
        job_title=job_title,
    )

    assert result.overall_score < 70.0
    assert result.recommendation in ("review", "skip")
