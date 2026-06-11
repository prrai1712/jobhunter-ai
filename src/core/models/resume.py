"""Resume model — tracks uploaded resumes and active resume selection."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, SoftDeleteMixin


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, archived, deleted
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes")  # type: ignore[name-defined]  # noqa: F821
    usage_history: Mapped[list["ResumeUsageHistory"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ResumeUsageHistory", back_populates="resume", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, name={self.name}, active={self.is_active})>"
