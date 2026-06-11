"""System command handlers — /start, /start_system, /stop_system, /pause, /resume, /help."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database.engine import get_async_session
from src.core.services.system_service import SystemService, SystemState
from src.telegram.formatters import escape_md, format_help, format_system_status
from src.telegram.middleware import authorized_only


@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    if not update.message:
        return
    await update.message.reply_text(
        "🤖 *Welcome to JobHunter AI\\!*\n\n"
        "I'm your automated job discovery and application platform\\.\n"
        "Everything is controlled right here in Telegram\\.\n\n"
        "Use /help to see all available commands\\.\n"
        "Use /start\\_system to begin job hunting\\!",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def start_system_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start_system — set system state to RUNNING."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = SystemService(session)
        current = await service.get_state()

        if current == SystemState.RUNNING:
            await update.message.reply_text("🟢 System is already running\\!", parse_mode="MarkdownV2")
            return

        # Use force_state for initial startup from STOPPED
        if current == SystemState.STOPPED:
            await service.force_state(SystemState.RUNNING, updated_by="telegram")
        else:
            success = await service.set_state(SystemState.RUNNING, updated_by="telegram")
            if not success:
                await update.message.reply_text(
                    f"❌ Cannot transition from `{escape_md(current.value)}` to `running`",
                    parse_mode="MarkdownV2",
                )
                return

    await update.message.reply_text(
        "🟢 *System started\\!*\n\n"
        "✅ Job discovery: Active\n"
        "✅ Salary estimation: Active\n"
        "✅ Matching: Active\n"
        "✅ Auto\\-apply: Active\n\n"
        "Use /system\\_status to monitor\\.",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def stop_system_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop_system — set system state to STOPPED."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = SystemService(session)
        await service.force_state(SystemState.STOPPED, updated_by="telegram")

    await update.message.reply_text(
        "🔴 *System stopped\\!*\n\nAll workers are paused\\. No discovery or applications will run\\.",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def pause_applications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pause_applications — pause auto-apply but continue discovery."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = SystemService(session)
        current = await service.get_state()

        if current != SystemState.RUNNING:
            await update.message.reply_text(
                f"⚠️ System is `{escape_md(current.value)}`, not running\\. "
                "Start system first with /start\\_system",
                parse_mode="MarkdownV2",
            )
            return

        await service.set_state(SystemState.PAUSED, updated_by="telegram")

    await update.message.reply_text(
        "🟡 *Applications paused\\!*\n\n"
        "✅ Job discovery: Still active\n"
        "✅ Salary estimation: Still active\n"
        "✅ Matching: Still active\n"
        "⏸ Auto\\-apply: PAUSED\n\n"
        "Use /resume\\_applications to resume\\.",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def resume_applications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resume_applications — resume auto-apply."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = SystemService(session)
        current = await service.get_state()

        if current != SystemState.PAUSED:
            await update.message.reply_text(
                f"⚠️ System is `{escape_md(current.value)}`, not paused\\.",
                parse_mode="MarkdownV2",
            )
            return

        await service.set_state(SystemState.RUNNING, updated_by="telegram")

    await update.message.reply_text(
        "🟢 *Applications resumed\\!* All systems active\\.",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show all commands."""
    if not update.message:
        return
    await update.message.reply_text(format_help(), parse_mode="MarkdownV2")
