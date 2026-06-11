"""Matching engine — orchestrates skill extraction, scoring, and job matching."""

from __future__ import annotations

import structlog

from src.core.config.candidate import CandidateProfile
from src.matching.scorer import MatchResult, MatchScorer
from src.matching.skill_extractor import SkillExtractor
from src.matching.skills_db import normalize_skill

logger = structlog.get_logger(__name__)


class MatchingEngine:
    """Orchestrates the full matching pipeline.

    1. Extract skills from job description
    2. Normalize candidate skills
    3. Score match across multiple dimensions
    4. Generate recommendation
    """

    def __init__(self) -> None:
        self.extractor = SkillExtractor()
        self.scorer = MatchScorer()

    def match(
        self,
        job_title: str,
        job_description: str,
        candidate: CandidateProfile,
        job_exp_min: int | None = None,
        job_exp_max: int | None = None,
    ) -> MatchResult:
        """Match a candidate against a job.

        Args:
            job_title: The job's title.
            job_description: Full job description text.
            candidate: Candidate profile with skills and preferences.
            job_exp_min: Minimum experience required (if known).
            job_exp_max: Maximum experience required (if known).

        Returns:
            MatchResult with scores and recommendation.
        """
        # 1. Extract skills from job description
        raw_job_skills = self.extractor.extract_skills(job_description)
        job_skills = {normalize_skill(s) for s in raw_job_skills}

        # Also extract from title
        title_skills = self.extractor.extract_skills(job_title)
        job_skills |= {normalize_skill(s) for s in title_skills}

        # 2. Normalize candidate skills
        candidate_skills = {normalize_skill(s) for s in candidate.skills}

        # 3. Extract experience from description if not provided
        if job_exp_min is None:
            extracted_min, extracted_max = self.extractor.extract_experience_range(
                job_description
            )
            if extracted_min is not None:
                job_exp_min = extracted_min
            if extracted_max is not None and job_exp_max is None:
                job_exp_max = extracted_max

        # 4. Score
        result = self.scorer.score(
            candidate_skills=candidate_skills,
            job_skills=job_skills,
            candidate_experience=candidate.experience_years,
            job_exp_min=job_exp_min,
            job_exp_max=job_exp_max,
            candidate_roles=candidate.target_roles,
            job_title=job_title,
        )

        logger.info(
            "job_matched",
            title=job_title,
            overall=result.overall_score,
            skill=result.skill_score,
            exp=result.experience_score,
            role=result.role_score,
            recommendation=result.recommendation,
            matched=len(result.matched_skills),
            missing=len(result.missing_skills),
        )

        return result
