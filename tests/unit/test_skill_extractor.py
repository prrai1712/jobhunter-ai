"""Unit tests for SkillExtractor."""

from __future__ import annotations

import pytest
from src.matching.skill_extractor import SkillExtractor


@pytest.fixture
def extractor() -> SkillExtractor:
    return SkillExtractor()


def test_extract_skills(extractor: SkillExtractor) -> None:
    text = (
        "We are looking for a Senior Software Engineer with strong experience in Python, "
        "Django, PostgreSQL, and Docker. Experience with React or AWS is a plus."
    )
    skills = extractor.extract_skills(text)

    assert "Python" in skills
    assert "Django" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "React" in skills
    assert "AWS" in skills
    assert "Java" not in skills


def test_extract_skills_normalization(extractor: SkillExtractor) -> None:
    text = "We use JS, DRF, Postgres, and k8s."
    skills = extractor.extract_skills(text)

    # Aliases should resolve to canonical forms
    assert "JavaScript" in skills
    assert "Django REST Framework" in skills
    assert "PostgreSQL" in skills
    assert "Kubernetes" in skills


def test_extract_experience_range(extractor: SkillExtractor) -> None:
    # Test "3-5 years"
    text1 = "Requires 3-5 years of experience in backend development."
    min_exp, max_exp = extractor.extract_experience_range(text1)
    assert min_exp == 3
    assert max_exp == 5

    # Test "5+ years"
    text2 = "Looking for someone with 5+ years of experience."
    min_exp, max_exp = extractor.extract_experience_range(text2)
    assert min_exp == 5
    assert max_exp is None

    # Test "minimum 2 years"
    text3 = "Minimum 2 years of relevant experience."
    min_exp, max_exp = extractor.extract_experience_range(text3)
    assert min_exp == 2
    assert max_exp is None

    # Test "no mention"
    text4 = "Looking for a fresh graduate."
    min_exp, max_exp = extractor.extract_experience_range(text4)
    assert min_exp is None
    assert max_exp is None


def test_extract_job_type(extractor: SkillExtractor) -> None:
    assert extractor.extract_job_type("This is a full-time role") == "full_time"
    assert extractor.extract_job_type("Part-time job offer") == "part_time"
    assert extractor.extract_job_type("Looking for contract base developer") == "contract"
    assert extractor.extract_job_type("This is a summer internship") == "internship"
    assert extractor.extract_job_type("100% remote working option") == "remote"
    assert extractor.extract_job_type("Hybrid model (2 days office)") == "hybrid"
    assert extractor.extract_job_type("Unknown setup details") == "unknown"
