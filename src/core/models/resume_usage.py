"""Resume usage history — tracks which resume was used for each application."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class ResumeUsageHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "resume_usage_history"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="usage_history")  # type: ignore[name-defined]  # noqa: F821
    application: Mapped["Application"] = relationship("Application")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<ResumeUsageHistory(resume={self.resume_id}, app={self.application_id})>"
