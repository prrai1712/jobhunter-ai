"""Salary intelligence engine — aggregates estimates from multiple providers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.salary.base import SalaryProvider, SalaryResult
from src.salary.levels import LevelsFyiProvider
from src.salary.glassdoor import GlassdoorProvider
from src.salary.ambitionbox import AmbitionBoxProvider

logger = structlog.get_logger(__name__)


@dataclass
class AggregatedSalary:
    """Final salary estimate after weighted aggregation."""

    estimated_salary: float
    confidence: float
    source_breakdown: dict[str, Any] = field(default_factory=dict)
    provider_results: list[SalaryResult] = field(default_factory=list)


class SalaryEngine:
    """Aggregates salary estimates from multiple providers using weighted scoring.

    Weights:
    - Levels.fyi:    50%
    - Glassdoor:     30%
    - AmbitionBox:   20%
    """

    def __init__(self) -> None:
        self.providers: list[SalaryProvider] = [
            LevelsFyiProvider(),
            GlassdoorProvider(),
            AmbitionBoxProvider(),
        ]

    async def estimate(
        self, company: str, role: str, location: str = "India"
    ) -> AggregatedSalary:
        """Run all providers concurrently and compute weighted estimate.

        Args:
            company: Company name.
            role: Job title.
            location: Geographic location.

        Returns:
            AggregatedSalary with weighted estimate and per-provider breakdown.
        """
        # Run all providers concurrently
        tasks = [
            self._safe_estimate(provider, company, role, location)
            for provider in self.providers
        ]
        results = await asyncio.gather(*tasks)

        # Filter out None results
        valid_results = [r for r in results if r is not None and r.salary_lpa > 0]

        if not valid_results:
            logger.info(
                "salary_no_data",
                company=company,
                role=role,
                location=location,
            )
            return AggregatedSalary(
                estimated_salary=0.0,
                confidence=0.0,
                source_breakdown={"message": "No salary data available"},
                provider_results=[],
            )

        # Compute weighted average
        total_weight = sum(
            self._get_weight(r.provider_name) for r in valid_results
        )
        weighted_salary = sum(
            r.salary_lpa * self._get_weight(r.provider_name)
            for r in valid_results
        ) / total_weight

        # Confidence: average of provider confidences, boosted by # of providers
        avg_confidence = sum(r.confidence for r in valid_results) / len(valid_results)
        provider_boost = min(len(valid_results) / len(self.providers), 1.0)
        final_confidence = avg_confidence * 0.7 + provider_boost * 0.3

        # Build breakdown
        breakdown = {}
        for r in valid_results:
            breakdown[r.provider_name] = {
                "salary_lpa": round(r.salary_lpa, 2),
                "min": r.salary_min,
                "max": r.salary_max,
                "median": r.salary_median,
                "confidence": round(r.confidence, 2),
                "weight": self._get_weight(r.provider_name),
            }

        logger.info(
            "salary_estimated",
            company=company,
            role=role,
            salary=round(weighted_salary, 2),
            confidence=round(final_confidence, 2),
            providers=len(valid_results),
        )

        return AggregatedSalary(
            estimated_salary=round(weighted_salary, 2),
            confidence=round(final_confidence, 2),
            source_breakdown=breakdown,
            provider_results=valid_results,
        )

    async def _safe_estimate(
        self, provider: SalaryProvider, company: str, role: str, location: str
    ) -> SalaryResult | None:
        """Run a single provider with error handling."""
        try:
            return await provider.estimate_salary(company, role, location)
        except Exception as e:
            logger.warning(
                "salary_provider_error",
                provider=provider.provider_name,
                company=company,
                role=role,
                error=str(e),
            )
            return None

    def _get_weight(self, provider_name: str) -> float:
        """Get the weight for a provider."""
        weights = {
            "levels_fyi": 0.50,
            "glassdoor": 0.30,
            "ambitionbox": 0.20,
        }
        return weights.get(provider_name, 0.1)
