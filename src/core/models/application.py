"""Application model — tracks every job application submission."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationStatus(str, enum.Enum):
    """Application lifecycle status."""

    PENDING = "pending"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    FAILED = "failed"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class ApplicationMethod(str, enum.Enum):
    """How the application was submitted."""

    API = "api"
    BROWSER = "browser"
    MANUAL = "manual"


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "applications"

    # Foreign keys
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Status
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.PENDING,
        server_default="pending",
        index=True,
    )
    method: Mapped[ApplicationMethod] = mapped_column(
        Enum(ApplicationMethod),
        default=ApplicationMethod.API,
        server_default="api",
    )

    # Timing
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Data
    response_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="applications")  # type: ignore[name-defined]  # noqa: F821
    company: Mapped["Company"] = relationship("Company", back_populates="applications")  # type: ignore[name-defined]  # noqa: F821
    resume: Mapped["Resume"] = relationship("Resume")  # type: ignore[name-defined]  # noqa: F821
    user: Mapped["User"] = relationship("User", back_populates="applications")  # type: ignore[name-defined]  # noqa: F821
    logs: Mapped[list["ApplicationLog"]] = relationship(
        "ApplicationLog", back_populates="application", lazy="selectin"
    )
    failures: Mapped[list["ApplicationFailure"]] = relationship(
        "ApplicationFailure", back_populates="application", lazy="selectin"
    )
    screenshots: Mapped[list["ApplicationScreenshot"]] = relationship(
        "ApplicationScreenshot", back_populates="application", lazy="selectin"
    )
    html_snapshots: Mapped[list["ApplicationHtmlSnapshot"]] = relationship(
        "ApplicationHtmlSnapshot", back_populates="application", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, job={self.job_id}, status={self.status})>"
