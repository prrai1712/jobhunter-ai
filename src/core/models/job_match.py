"""Job match model — stores matching engine results per job."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class JobMatch(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "job_matches"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, unique=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Scores
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    role_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    technology_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Details
    matched_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # type: ignore[assignment]
    missing_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # type: ignore[assignment]
    recommendation: Mapped[str] = mapped_column(
        String(50), nullable=False, default="review"
    )  # apply, review, skip

    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="match")  # type: ignore[name-defined]  # noqa: F821
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<JobMatch(job={self.job_id}, score={self.overall_score})>"
