"""Match scorer — computes multi-dimensional match scores between candidate and job."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class MatchResult:
    """Result of matching a candidate against a job."""

    overall_score: float  # 0-100
    skill_score: float  # 0-100
    experience_score: float  # 0-100
    role_score: float  # 0-100
    technology_score: float  # 0-100
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    recommendation: str = "review"  # "apply", "review", "skip"


class MatchScorer:
    """Multi-dimensional match scoring engine.

    Weights:
    - Skill Score:      40%  (Jaccard similarity of skills)
    - Experience Score:  25%  (Gaussian match against required range)
    - Role Score:        20%  (Keyword overlap with target roles)
    - Technology Score:  15%  (Tech stack alignment)
    """

    SKILL_WEIGHT = 0.40
    EXPERIENCE_WEIGHT = 0.25
    ROLE_WEIGHT = 0.20
    TECHNOLOGY_WEIGHT = 0.15

    def score(
        self,
        candidate_skills: set[str],
        job_skills: set[str],
        candidate_experience: int,
        job_exp_min: int | None,
        job_exp_max: int | None,
        candidate_roles: list[str],
        job_title: str,
    ) -> MatchResult:
        """Compute overall match score.

        Args:
            candidate_skills: Normalized candidate skills.
            job_skills: Skills extracted from job description.
            candidate_experience: Years of experience.
            job_exp_min: Minimum required experience.
            job_exp_max: Maximum required experience.
            candidate_roles: Target role titles.
            job_title: The job's title.

        Returns:
            MatchResult with all sub-scores and recommendations.
        """
        # 1. Skill score (Jaccard similarity)
        matched = candidate_skills & job_skills
        missing = job_skills - candidate_skills
        if job_skills:
            skill_score = len(matched) / len(job_skills) * 100
        else:
            skill_score = 50.0  # No skills extracted, neutral

        # 2. Experience score (Gaussian match)
        experience_score = self._score_experience(
            candidate_experience, job_exp_min, job_exp_max
        )

        # 3. Role score (keyword overlap)
        role_score = self._score_role(candidate_roles, job_title)

        # 4. Technology score (deeper tech alignment)
        technology_score = self._score_technology(candidate_skills, job_skills)

        # Weighted overall
        overall = (
            skill_score * self.SKILL_WEIGHT
            + experience_score * self.EXPERIENCE_WEIGHT
            + role_score * self.ROLE_WEIGHT
            + technology_score * self.TECHNOLOGY_WEIGHT
        )

        # Recommendation
        if overall >= 85:
            recommendation = "apply"
        elif overall >= 65:
            recommendation = "review"
        else:
            recommendation = "skip"

        return MatchResult(
            overall_score=round(overall, 1),
            skill_score=round(skill_score, 1),
            experience_score=round(experience_score, 1),
            role_score=round(role_score, 1),
            technology_score=round(technology_score, 1),
            matched_skills=sorted(matched),
            missing_skills=sorted(missing),
            recommendation=recommendation,
        )

    def _score_experience(
        self,
        candidate_exp: int,
        req_min: int | None,
        req_max: int | None,
    ) -> float:
        """Score experience match using a Gaussian curve.

        - Exact match within range = 100
        - Close to range = high score
        - Far outside range = low score
        """
        if req_min is None and req_max is None:
            return 70.0  # No requirement specified, neutral-positive

        # Set defaults
        min_exp = req_min or 0
        max_exp = req_max or min_exp + 3

        # Perfect match: within range
        if min_exp <= candidate_exp <= max_exp:
            return 100.0

        # Calculate distance from nearest bound
        if candidate_exp < min_exp:
            distance = min_exp - candidate_exp
        else:
            distance = candidate_exp - max_exp

        # Gaussian decay: sigma=2 (2 years deviation = ~60% score)
        sigma = 2.0
        score = 100.0 * math.exp(-(distance ** 2) / (2 * sigma ** 2))

        return max(score, 0.0)

    def _score_role(self, target_roles: list[str], job_title: str) -> float:
        """Score role match based on keyword overlap."""
        if not target_roles or not job_title:
            return 50.0

        job_words = set(job_title.lower().split())
        best_score = 0.0

        for role in target_roles:
            role_words = set(role.lower().split())
            if not role_words:
                continue

            # Check for exact containment
            if role.lower() in job_title.lower():
                return 100.0

            # Word overlap
            overlap = len(job_words & role_words)
            score = overlap / len(role_words) * 100
            best_score = max(best_score, score)

        return best_score

    def _score_technology(
        self, candidate_skills: set[str], job_skills: set[str]
    ) -> float:
        """Score technology alignment — weighted by importance of skills."""
        if not job_skills:
            return 50.0

        # Core skills that carry more weight
        core_skills = {
            "python", "django", "rest apis", "postgresql", "mysql",
            "redis", "docker", "git", "linux",
        }

        core_matches = (candidate_skills & job_skills) & core_skills
        core_required = job_skills & core_skills

        if core_required:
            core_score = len(core_matches) / len(core_required) * 100
        else:
            core_score = 70.0

        # General technology overlap
        all_matches = candidate_skills & job_skills
        if job_skills:
            general_score = len(all_matches) / len(job_skills) * 100
        else:
            general_score = 50.0

        # Core skills matter more (60/40)
        return core_score * 0.6 + general_score * 0.4
