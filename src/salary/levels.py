"""Levels.fyi salary provider — scrapes public company salary pages."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.salary.base import SalaryProvider, SalaryResult

logger = structlog.get_logger(__name__)

# USD to INR approximate conversion for LPA calculation
USD_TO_INR = 83.0
LEVELS_BASE = "https://www.levels.fyi"


class LevelsFyiProvider(SalaryProvider):
    """Scrapes salary data from Levels.fyi public pages."""

    @property
    def provider_name(self) -> str:
        return "levels_fyi"

    @property
    def weight(self) -> float:
        return 0.50

    async def estimate_salary(
        self, company: str, role: str, location: str = "India"
    ) -> SalaryResult | None:
        """Estimate salary by scraping Levels.fyi company page."""
        company_slug = self._slugify(company)
        url = f"{LEVELS_BASE}/companies/{company_slug}/salaries/software-engineer"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }

            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    logger.debug(
                        "levels_fyi_not_found",
                        company=company,
                        status=response.status_code,
                    )
                    return None

            return self._parse_salary_page(response.text, company, role)

        except httpx.TimeoutException:
            logger.debug("levels_fyi_timeout", company=company)
            return None
        except Exception as e:
            logger.warning("levels_fyi_error", company=company, error=str(e))
            return None

    def _parse_salary_page(
        self, html: str, company: str, role: str
    ) -> SalaryResult | None:
        """Parse salary data from the Levels.fyi HTML page."""
        soup = BeautifulSoup(html, "lxml")

        # Try to find salary data in the page content
        salary_data = self._extract_salary_from_page(soup)

        if salary_data:
            # Convert from USD to INR LPA if needed
            salary_min_lpa = salary_data.get("min", 0) * USD_TO_INR / 100000
            salary_max_lpa = salary_data.get("max", 0) * USD_TO_INR / 100000
            salary_median_lpa = salary_data.get("median", 0) * USD_TO_INR / 100000

            return SalaryResult(
                provider_name=self.provider_name,
                salary_min=round(salary_min_lpa, 2),
                salary_max=round(salary_max_lpa, 2),
                salary_median=round(salary_median_lpa, 2),
                confidence=0.7,
                currency="INR",
                raw_data=salary_data,
            )

        # Fallback: try regex on the raw text
        text = soup.get_text()
        salary = self._extract_salary_regex(text)
        if salary:
            salary_lpa = salary * USD_TO_INR / 100000
            return SalaryResult(
                provider_name=self.provider_name,
                salary_median=round(salary_lpa, 2),
                confidence=0.4,
                currency="INR",
                raw_data={"extracted": salary, "source": "regex"},
            )

        return None

    def _extract_salary_from_page(self, soup: BeautifulSoup) -> dict[str, float] | None:
        """Try to extract structured salary data."""
        # Look for salary figures in common Levels.fyi patterns
        salary_elements = soup.find_all(
            string=re.compile(r"\$[\d,]+K?", re.IGNORECASE)
        )

        salaries = []
        for elem in salary_elements:
            match = re.findall(r"\$\s*([\d,]+)\s*K?", str(elem))
            for m in match:
                value = float(m.replace(",", ""))
                if value > 1000:
                    value = value  # Already in USD
                elif value > 0:
                    value = value * 1000  # Was in K
                if 30000 < value < 1000000:  # Reasonable salary range
                    salaries.append(value)

        if salaries:
            return {
                "min": min(salaries),
                "max": max(salaries),
                "median": sorted(salaries)[len(salaries) // 2],
            }

        return None

    @staticmethod
    def _extract_salary_regex(text: str) -> float | None:
        """Extract a salary figure from raw text using regex."""
        patterns = [
            r"Total\s*Comp[:\s]*\$\s*([\d,]+)",
            r"Base\s*Salary[:\s]*\$\s*([\d,]+)",
            r"\$([\d,]+)\s*(?:per year|/yr|annually)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _slugify(company: str) -> str:
        """Convert company name to URL slug."""
        slug = company.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")
