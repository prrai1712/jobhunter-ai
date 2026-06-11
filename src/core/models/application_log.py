"""Application log, failure, screenshot, and HTML snapshot models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class ApplicationLog(Base, UUIDPrimaryKeyMixin):
    """Granular log entries for each application attempt."""

    __tablename__ = "application_logs"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship("Application", back_populates="logs")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<ApplicationLog(app={self.application_id}, event={self.event})>"


class ApplicationFailure(Base, UUIDPrimaryKeyMixin):
    """Records details of failed application attempts."""

    __tablename__ = "application_failures"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str] = mapped_column(String(255), nullable=False, default="unknown")
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    html_snapshot_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship("Application", back_populates="failures")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<ApplicationFailure(app={self.application_id}, reason={self.failure_reason[:50]})>"


class ApplicationScreenshot(Base, UUIDPrimaryKeyMixin):
    """Screenshots captured during browser-based application."""

    __tablename__ = "application_screenshots"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Application", back_populates="screenshots"
    )

    def __repr__(self) -> str:
        return f"<ApplicationScreenshot(app={self.application_id}, step={self.step_name})>"


class ApplicationHtmlSnapshot(Base, UUIDPrimaryKeyMixin):
    """HTML page snapshots captured during application for debugging."""

    __tablename__ = "application_html_snapshots"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    page_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Application", back_populates="html_snapshots"
    )

    def __repr__(self) -> str:
        return f"<ApplicationHtmlSnapshot(app={self.application_id}, url={self.page_url[:50]})>"
