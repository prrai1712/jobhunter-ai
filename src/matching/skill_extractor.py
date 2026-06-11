"""Skill extractor — extracts technical skills from job descriptions using NLP and pattern matching."""

from __future__ import annotations

import re

from src.matching.skills_db import ALIAS_TO_CANONICAL, SKILL_ALIASES, normalize_skill


class SkillExtractor:
    """Extracts and normalizes technical skills from text using pattern matching.

    Uses the curated skills database for:
    1. Direct keyword matching (case-insensitive)
    2. Alias resolution (e.g., "DRF" -> "django rest framework")
    3. Multi-word phrase matching
    """

    def __init__(self) -> None:
        # Build patterns sorted by length (longest first to match multi-word skills)
        all_terms = sorted(ALIAS_TO_CANONICAL.keys(), key=len, reverse=True)
        # Only keep terms with 2+ characters to avoid false positives
        self.search_terms = [t for t in all_terms if len(t) >= 2]

    def extract_skills(self, text: str) -> set[str]:
        """Extract normalized skills from text.

        Args:
            text: Job description or any text to extract skills from.

        Returns:
            Set of canonical skill names found in the text.
        """
        if not text:
            return set()

        text_lower = text.lower()
        found_skills: set[str] = set()

        for term in self.search_terms:
            # Use word boundary matching to avoid partial matches
            # e.g., "go" shouldn't match "google" but should match "Go "
            pattern = r"(?<![a-z])" + re.escape(term) + r"(?![a-z])"
            if re.search(pattern, text_lower):
                canonical = ALIAS_TO_CANONICAL.get(term, term)
                found_skills.add(canonical)

        return found_skills

    def extract_experience_range(self, text: str) -> tuple[int | None, int | None]:
        """Extract experience requirements from text.

        Returns:
            Tuple of (min_years, max_years) or (None, None) if not found.
        """
        if not text:
            return None, None

        patterns = [
            # "3-5 years of experience"
            r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:\+)?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
            # "3+ years"
            r"(\d+)\s*\+\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
            # "minimum 3 years"
            r"(?:minimum|min|at\s*least)\s*(\d+)\s*(?:years?|yrs?)",
            # "3 years experience"
            r"(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp|relevant)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return int(groups[0]), int(groups[1])
                elif len(groups) == 1:
                    return int(groups[0]), None

        return None, None

    def extract_job_type(self, text: str) -> str:
        """Detect job type from text."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["full-time", "full time", "permanent"]):
            return "full_time"
        if any(w in text_lower for w in ["part-time", "part time"]):
            return "part_time"
        if any(w in text_lower for w in ["contract", "freelance", "consultant"]):
            return "contract"
        if any(w in text_lower for w in ["internship", "intern"]):
            return "internship"
        if any(w in text_lower for w in ["remote", "work from home", "wfh"]):
            return "remote"
        if any(w in text_lower for w in ["hybrid"]):
            return "hybrid"

        return "unknown"
