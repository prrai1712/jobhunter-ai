"""Salary estimate and provider result models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class SalaryEstimate(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "salary_estimates"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(500), nullable=False)
    estimated_salary: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # type: ignore[assignment]
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="salary_estimates")  # type: ignore[name-defined]  # noqa: F821
    provider_results: Mapped[list["SalaryProviderResult"]] = relationship(
        "SalaryProviderResult", back_populates="salary_estimate", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<SalaryEstimate(job={self.job_id}, salary={self.estimated_salary})>"


class SalaryProviderResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "salary_provider_results"

    salary_estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("salary_estimates.id"), nullable=False, index=True
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # type: ignore[assignment]
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    salary_estimate: Mapped[SalaryEstimate] = relationship(
        "SalaryEstimate", back_populates="provider_results"
    )

    def __repr__(self) -> str:
        return f"<SalaryProviderResult(provider={self.provider_name}, median={self.salary_median})>"
