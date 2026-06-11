"""Job discovery run model — tracks each discovery/scraping cycle."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class JobDiscoveryRun(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "job_discovery_runs"

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_sources.id"), nullable=True, index=True
    )
    provider_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_new: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_duplicate: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="running"
    )  # running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<JobDiscoveryRun(id={self.id}, status={self.status}, found={self.jobs_found})>"
