"""AmbitionBox salary provider — scrapes Indian salary data."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.salary.base import SalaryProvider, SalaryResult

logger = structlog.get_logger(__name__)

AMBITIONBOX_BASE = "https://www.ambitionbox.com"


class AmbitionBoxProvider(SalaryProvider):
    """Scrapes salary data from AmbitionBox (Indian market focus)."""

    @property
    def provider_name(self) -> str:
        return "ambitionbox"

    @property
    def weight(self) -> float:
        return 0.20

    async def estimate_salary(
        self, company: str, role: str, location: str = "India"
    ) -> SalaryResult | None:
        """Estimate salary from AmbitionBox company page."""
        company_slug = self._slugify(company)
        url = f"{AMBITIONBOX_BASE}/overview/{company_slug}-overview/salaries"

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
                    # Try alternative URL format
                    alt_url = f"{AMBITIONBOX_BASE}/salaries/{company_slug}-salaries"
                    response = await client.get(alt_url, headers=headers)
                    if response.status_code != 200:
                        logger.debug(
                            "ambitionbox_not_found",
                            company=company,
                            status=response.status_code,
                        )
                        return None

            return self._parse_salary_page(response.text, company, role)

        except httpx.TimeoutException:
            logger.debug("ambitionbox_timeout", company=company)
            return None
        except Exception as e:
            logger.warning("ambitionbox_error", company=company, error=str(e))
            return None

    def _parse_salary_page(
        self, html: str, company: str, role: str
    ) -> SalaryResult | None:
        """Parse salary data from AmbitionBox HTML."""
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text()

        # AmbitionBox uses INR natively — find role-specific salaries
        role_salary = self._find_role_salary(text, role)
        if role_salary:
            return SalaryResult(
                provider_name=self.provider_name,
                salary_min=role_salary.get("min"),
                salary_max=role_salary.get("max"),
                salary_median=role_salary.get("median"),
                confidence=0.6,
                currency="INR",
                raw_data=role_salary,
            )

        # General salary extraction
        general_salary = self._extract_general_salary(text)
        if general_salary:
            return SalaryResult(
                provider_name=self.provider_name,
                salary_min=general_salary.get("min"),
                salary_max=general_salary.get("max"),
                salary_median=general_salary.get("median"),
                confidence=0.3,
                currency="INR",
                raw_data=general_salary,
            )

        return None

    def _find_role_salary(self, text: str, role: str) -> dict[str, float] | None:
        """Find salary data specific to the given role."""
        role_lower = role.lower()
        role_keywords = role_lower.split()

        lines = text.split("\n")
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Check if this line mentions the role
            if any(kw in line_lower for kw in role_keywords if len(kw) > 3):
                # Look around this line for salary data
                context = " ".join(lines[max(0, i - 2):min(len(lines), i + 5)])
                salary = self._extract_lpa(context)
                if salary:
                    return salary

        return None

    def _extract_general_salary(self, text: str) -> dict[str, float] | None:
        """Extract general salary information from the page."""
        return self._extract_lpa(text)

    def _extract_lpa(self, text: str) -> dict[str, float] | None:
        """Extract LPA salary figures from text."""
        patterns = [
            # ₹X.X L - ₹X.X L per year
            r"[₹Rs.]+\s*([\d.]+)\s*(?:L|Lakhs?|Lacs?)\s*[-–to]+\s*[₹Rs.]*\s*([\d.]+)\s*(?:L|Lakhs?|Lacs?)",
            # X.X LPA - X.X LPA
            r"([\d.]+)\s*(?:LPA|lpa)\s*[-–to]+\s*([\d.]+)\s*(?:LPA|lpa)",
            # Single value: ₹X.X L or X.X LPA
            r"[₹Rs.]+\s*([\d.]+)\s*(?:L|Lakhs?|Lacs?)",
            r"([\d.]+)\s*(?:LPA|lpa)",
        ]

        all_values = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        if m:
                            try:
                                val = float(m)
                                if 1 <= val <= 200:
                                    all_values.append(val)
                            except ValueError:
                                continue
                else:
                    try:
                        val = float(match)
                        if 1 <= val <= 200:
                            all_values.append(val)
                    except ValueError:
                        continue

        if all_values:
            all_values.sort()
            return {
                "min": all_values[0],
                "max": all_values[-1],
                "median": all_values[len(all_values) // 2],
            }

        return None

    @staticmethod
    def _slugify(company: str) -> str:
        slug = company.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")
