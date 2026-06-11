"""Unit tests for SalaryEngine."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.salary.base import SalaryResult
from src.salary.engine import SalaryEngine


@pytest.mark.asyncio
async def test_salary_engine_aggregation() -> None:
    # 1. Setup mock results for providers
    result_levels = SalaryResult(
        provider_name="levels_fyi",
        salary_lpa=20.0,
        salary_min=18.0,
        salary_max=22.0,
        confidence=0.8,
    )
    result_glassdoor = SalaryResult(
        provider_name="glassdoor",
        salary_lpa=16.0,
        salary_min=14.0,
        salary_max=18.0,
        confidence=0.7,
    )
    result_ambition = SalaryResult(
        provider_name="ambitionbox",
        salary_lpa=15.0,
        salary_min=12.0,
        salary_max=18.0,
        confidence=0.9,
    )

    # 2. Patch provider list to return mock results
    engine = SalaryEngine()
    engine.providers[0] = AsyncMock()
    engine.providers[0].estimate_salary.return_value = result_levels
    engine.providers[0].provider_name = "levels_fyi"

    engine.providers[1] = AsyncMock()
    engine.providers[1].estimate_salary.return_value = result_glassdoor
    engine.providers[1].provider_name = "glassdoor"

    engine.providers[2] = AsyncMock()
    engine.providers[2].estimate_salary.return_value = result_ambition
    engine.providers[2].provider_name = "ambitionbox"

    # 3. Execute aggregation
    aggregated = await engine.estimate("Google", "Software Engineer")

    # Math:
    # weights: levels=0.5, glassdoor=0.3, ambitionbox=0.2
    # weighted sum: (20*0.5 + 16*0.3 + 15*0.2) / 1.0 = (10.0 + 4.8 + 3.0) / 1.0 = 17.8 LPA
    assert aggregated.estimated_salary == 17.8
    assert "levels_fyi" in aggregated.source_breakdown
    assert "glassdoor" in aggregated.source_breakdown
    assert "ambitionbox" in aggregated.source_breakdown


@pytest.mark.asyncio
async def test_salary_engine_partial_failure() -> None:
    # Setup mock results where Glassdoor fails (returns None)
    result_levels = SalaryResult(
        provider_name="levels_fyi",
        salary_lpa=20.0,
        salary_min=18.0,
        salary_max=22.0,
        confidence=0.8,
    )

    engine = SalaryEngine()
    engine.providers[0] = AsyncMock()
    engine.providers[0].estimate_salary.return_value = result_levels
    engine.providers[0].provider_name = "levels_fyi"

    # Glassdoor returns None
    engine.providers[1] = AsyncMock()
    engine.providers[1].estimate_salary.return_value = None
    engine.providers[1].provider_name = "glassdoor"

    # Ambitionbox raises exception
    engine.providers[2] = AsyncMock()
    engine.providers[2].estimate_salary.side_effect = Exception("HTTP 500")
    engine.providers[2].provider_name = "ambitionbox"

    aggregated = await engine.estimate("Netflix", "Senior Developer")

    # Math: Only levels_fyi succeeds.
    # weights sum = 0.5.
    # weighted average: (20 * 0.5) / 0.5 = 20.0 LPA
    assert aggregated.estimated_salary == 20.0
    assert "levels_fyi" in aggregated.source_breakdown
    assert "glassdoor" not in aggregated.source_breakdown
    assert "ambitionbox" not in aggregated.source_breakdown
