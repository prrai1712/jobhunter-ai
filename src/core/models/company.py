"""Company model — tracks discovered companies and their hiring activity."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estimated_salary_band_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_salary_band_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_applied: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="company", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Application", back_populates="company", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name})>"
