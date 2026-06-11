"""Abstract salary provider base."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SalaryResult:
    """Standard salary data from a provider."""

    provider_name: str
    salary_min: float | None = None
    salary_max: float | None = None
    salary_median: float | None = None
    confidence: float = 0.0  # 0-1
    currency: str = "INR"
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def salary_lpa(self) -> float:
        """Best estimate in LPA (lakhs per annum)."""
        if self.salary_median:
            return self.salary_median
        if self.salary_min and self.salary_max:
            return (self.salary_min + self.salary_max) / 2
        return self.salary_min or self.salary_max or 0.0


class SalaryProvider(ABC):
    """Abstract base for salary data providers."""

    @abstractmethod
    async def estimate_salary(
        self, company: str, role: str, location: str = "India"
    ) -> SalaryResult | None:
        """Estimate salary for a role at a company.

        Args:
            company: Company name.
            role: Job title/role.
            location: Geographic location.

        Returns:
            SalaryResult or None if data unavailable.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier."""
        ...

    @property
    @abstractmethod
    def weight(self) -> float:
        """Weight for this provider in the aggregation (0-1)."""
        ...
