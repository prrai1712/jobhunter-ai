"""Statistics models — daily and monthly aggregated metrics."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class DailyStatistics(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "daily_statistics"

    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)

    # Job metrics
    jobs_scraped: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_matched: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_rejected: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_qualified: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Application metrics
    applications_submitted: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    applications_failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    applications_success: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Discovery metrics
    companies_discovered: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    salary_lookups: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Salary metrics
    avg_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_salary: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<DailyStatistics(date={self.date}, scraped={self.jobs_scraped})>"


class MonthlyStatistics(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "monthly_statistics"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_monthly_stats_year_month"),
    )

    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Aggregate metrics
    jobs_scraped: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_matched: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_rejected: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jobs_qualified: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    applications_submitted: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    applications_failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    applications_success: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    companies_discovered: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    salary_lookups: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_salary: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<MonthlyStatistics(year={self.year}, month={self.month})>"
