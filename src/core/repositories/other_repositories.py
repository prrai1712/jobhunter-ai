"""Statistics, system settings, job source, and telegram repositories."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Sequence

from sqlalchemy import select, update

from src.core.database.base import utcnow
from src.core.models.job_source import JobSource
from src.core.models.statistics import DailyStatistics, MonthlyStatistics
from src.core.models.system_setting import SystemSetting
from src.core.models.telegram_command import TelegramAuditLog, TelegramCommand
from src.core.models.worker_status import WorkerStatus
from src.core.models.job_discovery_run import JobDiscoveryRun
from src.core.models.scheduler_run import SchedulerRun
from src.core.models.salary_estimate import SalaryEstimate, SalaryProviderResult
from src.core.models.application_log import (
    ApplicationLog,
    ApplicationFailure,
    ApplicationScreenshot,
    ApplicationHtmlSnapshot,
)
from src.core.models.ats_provider_result import ATSProviderResult
from src.core.repositories.base_repository import BaseRepository


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
class DailyStatsRepository(BaseRepository[DailyStatistics]):
    model_class = DailyStatistics

    async def get_or_create_today(self) -> DailyStatistics:
        """Get or create today's statistics record."""
        today = date.today()
        stmt = select(DailyStatistics).where(DailyStatistics.date == today)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            return record
        return await self.create(date=today)

    async def increment_field(self, field_name: str, amount: int = 1) -> None:
        """Atomically increment a counter field on today's record."""
        record = await self.get_or_create_today()
        current = getattr(record, field_name, 0) or 0
        setattr(record, field_name, current + amount)
        await self.session.flush()

    async def get_date_range(
        self, start: date, end: date
    ) -> Sequence[DailyStatistics]:
        """Get statistics for a date range."""
        stmt = (
            select(DailyStatistics)
            .where(DailyStatistics.date.between(start, end))
            .order_by(DailyStatistics.date.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class MonthlyStatsRepository(BaseRepository[MonthlyStatistics]):
    model_class = MonthlyStatistics

    async def get_or_create(self, year: int, month: int) -> MonthlyStatistics:
        """Get or create a monthly statistics record."""
        stmt = select(MonthlyStatistics).where(
            MonthlyStatistics.year == year,
            MonthlyStatistics.month == month,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            return record
        return await self.create(year=year, month=month)


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------
class SystemSettingsRepository(BaseRepository[SystemSetting]):
    model_class = SystemSetting

    async def get_setting(self, key: str) -> Any:
        """Get a setting value by key."""
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return record.value

    async def set_setting(
        self, key: str, value: Any, description: str | None = None, updated_by: str = "system"
    ) -> SystemSetting:
        """Set or update a setting."""
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            record.value = value
            if description:
                record.description = description
            record.updated_by = updated_by
            await self.session.flush()
            return record
        return await self.create(
            key=key,
            value=value,
            description=description,
            updated_by=updated_by,
        )

    async def get_system_state(self) -> str:
        """Get the current system state (running/paused/stopped/maintenance)."""
        value = await self.get_setting("system_state")
        if value is None:
            return "stopped"
        return value.get("state", "stopped") if isinstance(value, dict) else str(value)


# ---------------------------------------------------------------------------
# Job Source
# ---------------------------------------------------------------------------
class JobSourceRepository(BaseRepository[JobSource]):
    model_class = JobSource

    async def get_active_sources(self) -> Sequence[JobSource]:
        """Get all active job sources."""
        stmt = (
            select(JobSource)
            .where(JobSource.is_active == True)  # noqa: E712
            .order_by(JobSource.provider_type)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_provider_and_token(
        self, provider_type: str, board_token: str
    ) -> JobSource | None:
        """Find a source by provider type and board token."""
        stmt = select(JobSource).where(
            JobSource.provider_type == provider_type,
            JobSource.board_token == board_token,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_crawled(self, source_id: uuid.UUID) -> None:
        """Update the last crawled timestamp."""
        stmt = (
            update(JobSource)
            .where(JobSource.id == source_id)
            .values(last_crawled_at=utcnow())
        )
        await self.session.execute(stmt)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
class TelegramCommandRepository(BaseRepository[TelegramCommand]):
    model_class = TelegramCommand

    async def log_command(
        self,
        telegram_user_id: int,
        command: str,
        args: dict | None = None,
        response_summary: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> TelegramCommand:
        """Log a Telegram command execution."""
        return await self.create(
            telegram_user_id=telegram_user_id,
            command=command,
            args=args,
            response_summary=response_summary,
            user_id=user_id,
        )


class TelegramAuditLogRepository(BaseRepository[TelegramAuditLog]):
    model_class = TelegramAuditLog

    async def log_audit(
        self,
        action: str,
        details: dict | None = None,
        telegram_user_id: int | None = None,
        user_id: uuid.UUID | None = None,
    ) -> TelegramAuditLog:
        """Create an audit log entry."""
        return await self.create(
            action=action,
            details=details,
            telegram_user_id=telegram_user_id,
            user_id=user_id,
        )


# ---------------------------------------------------------------------------
# Worker Status
# ---------------------------------------------------------------------------
class WorkerStatusRepository(BaseRepository[WorkerStatus]):
    model_class = WorkerStatus

    async def get_by_name(self, worker_name: str) -> WorkerStatus | None:
        """Get worker status by name."""
        stmt = select(WorkerStatus).where(WorkerStatus.worker_name == worker_name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_status(
        self,
        worker_name: str,
        status: str,
        **kwargs: Any,
    ) -> WorkerStatus:
        """Update or create worker status."""
        existing = await self.get_by_name(worker_name)
        if existing:
            existing.status = status
            existing.last_heartbeat = utcnow()
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self.session.flush()
            return existing
        return await self.create(
            worker_name=worker_name,
            status=status,
            last_heartbeat=utcnow(),
            **kwargs,
        )

    async def get_all_workers(self) -> Sequence[WorkerStatus]:
        """Get all worker statuses."""
        stmt = select(WorkerStatus).order_by(WorkerStatus.worker_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()


# ---------------------------------------------------------------------------
# Discovery Run
# ---------------------------------------------------------------------------
class JobDiscoveryRunRepository(BaseRepository[JobDiscoveryRun]):
    model_class = JobDiscoveryRun


# ---------------------------------------------------------------------------
# Scheduler Run
# ---------------------------------------------------------------------------
class SchedulerRunRepository(BaseRepository[SchedulerRun]):
    model_class = SchedulerRun


# ---------------------------------------------------------------------------
# Salary
# ---------------------------------------------------------------------------
class SalaryEstimateRepository(BaseRepository[SalaryEstimate]):
    model_class = SalaryEstimate

    async def get_by_job(self, job_id: uuid.UUID) -> SalaryEstimate | None:
        """Get salary estimate for a job."""
        stmt = select(SalaryEstimate).where(SalaryEstimate.job_id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class SalaryProviderResultRepository(BaseRepository[SalaryProviderResult]):
    model_class = SalaryProviderResult


# ---------------------------------------------------------------------------
# Application sub-tables
# ---------------------------------------------------------------------------
class ApplicationLogRepository(BaseRepository[ApplicationLog]):
    model_class = ApplicationLog


class ApplicationFailureRepository(BaseRepository[ApplicationFailure]):
    model_class = ApplicationFailure


class ApplicationScreenshotRepository(BaseRepository[ApplicationScreenshot]):
    model_class = ApplicationScreenshot


class ApplicationHtmlSnapshotRepository(BaseRepository[ApplicationHtmlSnapshot]):
    model_class = ApplicationHtmlSnapshot


class ATSProviderResultRepository(BaseRepository[ATSProviderResult]):
    model_class = ATSProviderResult
