"""Glassdoor salary provider — scrapes public salary pages."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.salary.base import SalaryProvider, SalaryResult

logger = structlog.get_logger(__name__)


class GlassdoorProvider(SalaryProvider):
    """Scrapes salary data from Glassdoor public pages."""

    @property
    def provider_name(self) -> str:
        return "glassdoor"

    @property
    def weight(self) -> float:
        return 0.30

    async def estimate_salary(
        self, company: str, role: str, location: str = "India"
    ) -> SalaryResult | None:
        """Estimate salary from Glassdoor search results."""
        search_query = f"{company} {role} salary {location}"
        url = f"https://www.glassdoor.co.in/Salaries/{self._slugify(company)}-salary-SRCH_KE0,{len(company)}.htm"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-IN,en;q=0.9",
            }

            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    logger.debug(
                        "glassdoor_not_found",
                        company=company,
                        status=response.status_code,
                    )
                    return None

            return self._parse_salary_page(response.text, company, role)

        except httpx.TimeoutException:
            logger.debug("glassdoor_timeout", company=company)
            return None
        except Exception as e:
            logger.warning("glassdoor_error", company=company, error=str(e))
            return None

    def _parse_salary_page(
        self, html: str, company: str, role: str
    ) -> SalaryResult | None:
        """Parse salary data from Glassdoor HTML."""
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text()

        # Look for Indian salary patterns (₹ or Rs or lakh/lakhs)
        salary = self._extract_inr_salary(text)
        if salary:
            return SalaryResult(
                provider_name=self.provider_name,
                salary_min=salary.get("min"),
                salary_max=salary.get("max"),
                salary_median=salary.get("median"),
                confidence=0.5,
                currency="INR",
                raw_data=salary,
            )

        # Try extracting from structured data
        script_data = soup.find_all("script", type="application/ld+json")
        for script in script_data:
            try:
                import json
                data = json.loads(script.string or "{}")
                if "baseSalary" in data:
                    base = data["baseSalary"]
                    value = base.get("value", {})
                    return SalaryResult(
                        provider_name=self.provider_name,
                        salary_min=self._to_lpa(value.get("minValue", 0)),
                        salary_max=self._to_lpa(value.get("maxValue", 0)),
                        salary_median=self._to_lpa(value.get("value", 0)),
                        confidence=0.6,
                        currency="INR",
                        raw_data=data,
                    )
            except Exception:
                continue

        return None

    def _extract_inr_salary(self, text: str) -> dict[str, float] | None:
        """Extract Indian salary figures from text."""
        patterns = [
            # ₹X.X Lakhs or ₹X Lakhs
            r"[₹Rs.]+\s*([\d.]+)\s*(?:L|Lakhs?|Lacs?)\s*(?:[-–to]+\s*[₹Rs.]*\s*([\d.]+)\s*(?:L|Lakhs?|Lacs?))?",
            # X.X LPA
            r"([\d.]+)\s*(?:LPA|lpa)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                salaries = []
                for match in matches:
                    if isinstance(match, tuple):
                        for m in match:
                            if m:
                                try:
                                    val = float(m)
                                    if 1 <= val <= 200:  # Reasonable LPA range
                                        salaries.append(val)
                                except ValueError:
                                    continue
                    else:
                        try:
                            val = float(match)
                            if 1 <= val <= 200:
                                salaries.append(val)
                        except ValueError:
                            continue

                if salaries:
                    return {
                        "min": min(salaries),
                        "max": max(salaries),
                        "median": sorted(salaries)[len(salaries) // 2],
                    }

        return None

    @staticmethod
    def _to_lpa(value: float) -> float:
        """Convert a value to LPA (assuming it might be annual INR)."""
        if value > 10000:
            return round(value / 100000, 2)
        return round(value, 2)

    @staticmethod
    def _slugify(company: str) -> str:
        slug = company.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")
