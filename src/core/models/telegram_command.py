"""Telegram command and audit log models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, UUIDPrimaryKeyMixin


class TelegramCommand(Base, UUIDPrimaryKeyMixin):
    """Logs every Telegram command received and processed."""

    __tablename__ = "telegram_commands"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    command: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    args: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TelegramCommand(cmd={self.command}, user={self.telegram_user_id})>"


class TelegramAuditLog(Base, UUIDPrimaryKeyMixin):
    """Audit trail for all Telegram interactions and system events."""

    __tablename__ = "telegram_audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TelegramAuditLog(action={self.action})>"
