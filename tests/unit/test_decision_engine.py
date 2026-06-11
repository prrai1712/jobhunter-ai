"""Unit tests for DecisionEngine."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.appliers.engine import DecisionEngine
from src.core.models.job import Job


@pytest.mark.asyncio
async def test_decision_engine_all_criteria_met() -> None:
    # 1. Setup mock session and services
    session = AsyncMock()

    # Create dummy job that passes threshold
    job = Job(
        id=uuid.uuid4(),
        title="Senior Python Developer",
        salary_estimate=25.0,  # 25 LPA
        match_score=90.0,       # 90% match
    )
    user_id = uuid.uuid4()

    # 2. Patch services to return valid criteria
    with patch("src.appliers.engine.SystemService") as mock_sys_cls, \
         patch("src.appliers.engine.ApplicationService") as mock_app_cls, \
         patch("src.appliers.engine.ResumeService") as mock_res_cls, \
         patch("src.appliers.engine.get_settings") as mock_settings_fn:

        # Mock settings
        settings = MagicMock()
        settings.job_filter.min_salary_lpa = 15.0
        settings.job_filter.min_match_score = 80.0
        settings.application.max_daily_applications = 10
        mock_settings_fn.return_value = settings

        # Mock SystemService
        sys_service = AsyncMock()
        sys_service.can_apply.return_value = True
        mock_sys_cls.return_value = sys_service

        # Mock ApplicationService
        app_service = AsyncMock()
        app_service.get_today_count.return_value = 2  # applied 2 today, below 10 limit
        app_service.has_already_applied.return_value = False # not duplicate
        mock_app_cls.return_value = app_service

        # Mock ResumeService
        res_service = AsyncMock()
        res_service.get_active.return_value = MagicMock() # active resume exists
        mock_res_cls.return_value = res_service

        # Create engine
        engine = DecisionEngine(session)

        # Execute decision check
        should_apply, reason = await engine.should_apply(job, user_id)

        # Validate assertions
        assert should_apply is True
        assert reason == "All criteria met"


@pytest.mark.asyncio
async def test_decision_engine_rejection_reasons() -> None:
    session = AsyncMock()
    user_id = uuid.uuid4()

    with patch("src.appliers.engine.SystemService") as mock_sys_cls, \
         patch("src.appliers.engine.ApplicationService") as mock_app_cls, \
         patch("src.appliers.engine.ResumeService") as mock_res_cls, \
         patch("src.appliers.engine.get_settings") as mock_settings_fn:

        # Mock settings
        settings = MagicMock()
        settings.job_filter.min_salary_lpa = 15.0
        settings.job_filter.min_match_score = 80.0
        settings.application.max_daily_applications = 10
        mock_settings_fn.return_value = settings

        # Setup standard passing service behavior
        sys_service = AsyncMock()
        sys_service.can_apply.return_value = True
        mock_sys_cls.return_value = sys_service

        app_service = AsyncMock()
        app_service.get_today_count.return_value = 2
        app_service.has_already_applied.return_value = False
        mock_app_cls.return_value = app_service

        res_service = AsyncMock()
        res_service.get_active.return_value = MagicMock()
        mock_res_cls.return_value = res_service

        engine = DecisionEngine(session)

        # Scenario A: System is paused/not running
        sys_service.can_apply.return_value = False
        job_a = Job(id=uuid.uuid4(), title="Job A", salary_estimate=20.0, match_score=90.0)
        should_apply, reason = await engine.should_apply(job_a, user_id)
        assert should_apply is False
        assert "System is not in running state" in reason
        sys_service.can_apply.return_value = True  # reset

        # Scenario B: Daily limit reached
        app_service.get_today_count.return_value = 10
        job_b = Job(id=uuid.uuid4(), title="Job B", salary_estimate=20.0, match_score=90.0)
        should_apply, reason = await engine.should_apply(job_b, user_id)
        assert should_apply is False
        assert "Daily application limit reached" in reason
        app_service.get_today_count.return_value = 2  # reset

        # Scenario C: Low salary
        job_c = Job(id=uuid.uuid4(), title="Job C", salary_estimate=12.0, match_score=90.0) # 12L < 15L
        should_apply, reason = await engine.should_apply(job_c, user_id)
        assert should_apply is False
        assert "below threshold" in reason

        # Scenario D: Low match score
        job_d = Job(id=uuid.uuid4(), title="Job D", salary_estimate=20.0, match_score=75.0) # 75% < 80%
        should_apply, reason = await engine.should_apply(job_d, user_id)
        assert should_apply is False
        assert "below threshold" in reason

        # Scenario E: Duplicate application
        app_service.has_already_applied.return_value = True
        job_e = Job(id=uuid.uuid4(), title="Job E", salary_estimate=20.0, match_score=90.0)
        should_apply, reason = await engine.should_apply(job_e, user_id)
        assert should_apply is False
        assert "Already applied" in reason
        app_service.has_already_applied.return_value = False  # reset

        # Scenario F: No active resume
        res_service.get_active.return_value = None
        job_f = Job(id=uuid.uuid4(), title="Job F", salary_estimate=20.0, match_score=90.0)
        should_apply, reason = await engine.should_apply(job_f, user_id)
        assert should_apply is False
        assert "No active resume" in reason
