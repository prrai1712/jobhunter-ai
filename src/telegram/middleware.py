"""Telegram middleware — authentication and command logging."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Coroutine

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from src.core.config.settings import get_settings
from src.core.database.engine import get_async_session
from src.core.repositories.other_repositories import TelegramCommandRepository, TelegramAuditLogRepository
from src.core.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


def authorized_only(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to restrict Telegram commands to the authorized user only."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        if update.effective_user is None:
            return

        settings = get_settings()
        user_id = update.effective_user.id

        if user_id != settings.telegram.allowed_user_id:
            logger.warning(
                "unauthorized_access",
                telegram_id=user_id,
                username=update.effective_user.username,
            )
            if update.message:
                await update.message.reply_text(
                    "⛔ Unauthorized. This bot is private."
                )
            return

        # Log command
        command = ""
        if update.message and update.message.text:
            command = update.message.text.split()[0] if update.message.text.startswith("/") else ""

        try:
            async with get_async_session() as session:
                cmd_repo = TelegramCommandRepository(session)
                audit_repo = TelegramAuditLogRepository(session)

                # Get or create user
                user_repo = UserRepository(session)
                user, _ = await user_repo.get_or_create(
                    telegram_id=user_id,
                    name=update.effective_user.full_name or "",
                    email=settings.candidate.email,
                    phone=settings.candidate.phone,
                    country=settings.candidate.country,
                )

                # Log command
                await cmd_repo.log_command(
                    telegram_user_id=user_id,
                    command=command,
                    args={"text": update.message.text if update.message else ""},
                    user_id=user.id,
                )

                # Audit log
                await audit_repo.log_audit(
                    action=f"command:{command}",
                    details={"chat_id": update.effective_chat.id if update.effective_chat else None},
                    telegram_user_id=user_id,
                    user_id=user.id,
                )

        except Exception as e:
            logger.error("middleware_logging_error", error=str(e))

        return await func(update, context)

    return wrapper
