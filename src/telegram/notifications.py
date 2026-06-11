"""Telegram push notifications — sends alerts for application events."""

from __future__ import annotations

from typing import Any

import structlog
from telegram import Bot

from src.core.config.settings import get_settings
from src.telegram.formatters import escape_md

logger = structlog.get_logger(__name__)

# Module-level bot reference set during startup
_bot: Bot | None = None


def set_bot(bot: Bot) -> None:
    """Set the bot reference for sending notifications."""
    global _bot
    _bot = bot


async def notify_application_success(job: Any, application: Any) -> None:
    """Send a success notification for a completed application."""
    if _bot is None:
        return

    settings = get_settings()
    chat_id = settings.telegram.log_chat_id

    salary = f"₹{job.salary_estimate:.1f}L" if job.salary_estimate else "N/A"
    match = f"{job.match_score:.0f}%" if job.match_score else "N/A"
    applied_at = application.applied_at.strftime("%H:%M:%S") if application.applied_at else "N/A"

    text = (
        f"✅ *Application Submitted\\!*\n\n"
        f"🏢 *Company:* {escape_md(str(getattr(job, 'company_name', 'Unknown')))}\n"
        f"💼 *Role:* {escape_md(job.title)}\n"
        f"💰 *Est\\. Salary:* {escape_md(salary)}\n"
        f"🎯 *Match Score:* {escape_md(match)}\n"
        f"⏰ *Applied At:* {escape_md(applied_at)}\n"
        f"🔗 [Job Link]({escape_md(job.apply_url)})"
    )

    try:
        await _bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error("notify_success_failed", error=str(e))


async def notify_application_failure(job: Any, reason: str, screenshot_path: str | None = None) -> None:
    """Send a failure notification for a failed application."""
    if _bot is None:
        return

    settings = get_settings()
    chat_id = settings.telegram.log_chat_id

    text = (
        f"❌ *Application Failed*\n\n"
        f"🏢 *Role:* {escape_md(job.title)}\n"
        f"📍 *Provider:* {escape_md(job.ats_provider)}\n"
        f"💥 *Reason:* {escape_md(reason[:500])}\n"
        f"🔗 [Job Link]({escape_md(job.apply_url)})"
    )

    try:
        await _bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )

        # Send screenshot if available
        if screenshot_path:
            try:
                with open(screenshot_path, "rb") as f:
                    await _bot.send_photo(
                        chat_id=chat_id,
                        photo=f,
                        caption="Screenshot at failure point",
                    )
            except Exception:
                pass

    except Exception as e:
        logger.error("notify_failure_failed", error=str(e))


async def notify_discovery_complete(
    provider: str,
    jobs_found: int,
    jobs_new: int,
    jobs_duplicate: int,
) -> None:
    """Send notification after a discovery run completes."""
    if _bot is None:
        return

    settings = get_settings()
    chat_id = settings.telegram.log_chat_id

    text = (
        f"🔍 *Discovery Complete*\n\n"
        f"📡 Provider: {escape_md(provider)}\n"
        f"📋 Found: {escape_md(str(jobs_found))}\n"
        f"🆕 New: {escape_md(str(jobs_new))}\n"
        f"🔄 Duplicate: {escape_md(str(jobs_duplicate))}"
    )

    try:
        await _bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.error("notify_discovery_failed", error=str(e))


async def notify_system_alert(message: str, level: str = "info") -> None:
    """Send a system alert notification."""
    if _bot is None:
        return

    settings = get_settings()
    chat_id = settings.telegram.log_chat_id

    emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🚨", "critical": "🔥"}.get(level, "ℹ️")

    text = f"{emoji} *System Alert*\n\n{escape_md(message)}"

    try:
        await _bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.error("notify_alert_failed", error=str(e))
