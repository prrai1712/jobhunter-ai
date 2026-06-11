"""Scheduler run model — records every scheduled task execution."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class SchedulerRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "scheduler_runs"

    job_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="interval"
    )  # interval, cron
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running"
    )  # running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    items_processed: Mapped[int | None] = mapped_column(default=0)

    def __repr__(self) -> str:
        return f"<SchedulerRun(job={self.job_name}, status={self.status})>"
