"""Job source model — ATS board configurations for job discovery."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # greenhouse, lever, ashby
    board_token: Mapped[str] = mapped_column(String(500), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    total_jobs_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<JobSource(id={self.id}, name={self.name}, provider={self.provider_type})>"
