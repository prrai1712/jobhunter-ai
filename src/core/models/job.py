"""Job model — the central entity representing a discovered job posting."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobStatus(str, enum.Enum):
    """Lifecycle status of a discovered job."""

    NEW = "new"
    SALARY_ESTIMATED = "salary_estimated"
    MATCHED = "matched"
    QUALIFIED = "qualified"
    REJECTED = "rejected"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    EXPIRED = "expired"


class JobType(str, enum.Enum):
    """Employment type."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    REMOTE = "remote"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    # Foreign keys
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_sources.id"), nullable=True, index=True
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    experience_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType), default=JobType.UNKNOWN, server_default="unknown"
    )
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Application
    apply_url: Mapped[str] = mapped_column(String(2000), nullable=False, unique=True, index=True)
    ats_provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Intelligence
    salary_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.NEW, server_default="new", index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="jobs")  # type: ignore[name-defined]  # noqa: F821
    source: Mapped["JobSource"] = relationship("JobSource")  # type: ignore[name-defined]  # noqa: F821
    salary_estimates: Mapped[list["SalaryEstimate"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SalaryEstimate", back_populates="job", lazy="selectin"
    )
    match: Mapped["JobMatch"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "JobMatch", back_populates="job", uselist=False, lazy="selectin"
    )
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Application", back_populates="job", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title={self.title}, status={self.status})>"
