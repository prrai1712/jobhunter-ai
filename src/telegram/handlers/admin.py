"""Admin command handlers — /system_status, /restart_workers, /database_health."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database.engine import check_database_health, get_async_session
from src.core.services.system_service import SystemService
from src.telegram.formatters import escape_md, format_system_status
from src.telegram.middleware import authorized_only


@authorized_only
async def system_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /system_status — show comprehensive system health."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = SystemService(session)
        status = await service.get_system_status()

    # Add DB health
    db_health = await check_database_health()
    db_status = db_health.get("status", "unknown")
    db_emoji = "🟢" if db_status == "healthy" else "🔴"

    text = format_system_status(status)
    text += (
        f"\n\n*Database:*\n"
        f"  {db_emoji} Status: `{escape_md(db_status)}`\n"
    )

    if db_status == "healthy":
        text += (
            f"  Pool: {escape_md(str(db_health.get('pool_size', 'N/A')))} "
            f"\\(in: {escape_md(str(db_health.get('checked_in', 0)))}, "
            f"out: {escape_md(str(db_health.get('checked_out', 0)))}\\)"
        )

    await update.message.reply_text(text, parse_mode="MarkdownV2")


@authorized_only
async def restart_workers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /restart_workers — restart scheduler jobs."""
    if not update.message:
        return

    # The scheduler will be restarted through the system state
    async with get_async_session() as session:
        service = SystemService(session)
        from src.core.services.system_service import SystemState
        await service.force_state(SystemState.RUNNING, updated_by="telegram_restart")

    await update.message.reply_text(
        "🔄 *Workers restarted\\!*\n\nAll scheduled tasks have been re\\-initialized\\.",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def database_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /database_health — show database diagnostics."""
    if not update.message:
        return

    health = await check_database_health()

    if health.get("status") == "healthy":
        text = (
            f"🗄 *Database Health*\n\n"
            f"🟢 Status: `healthy`\n"
            f"🏊 Pool Size: {escape_md(str(health.get('pool_size', 'N/A')))}\n"
            f"📥 Checked In: {escape_md(str(health.get('checked_in', 0)))}\n"
            f"📤 Checked Out: {escape_md(str(health.get('checked_out', 0)))}\n"
            f"📈 Overflow: {escape_md(str(health.get('overflow', 0)))}"
        )
    else:
        text = (
            f"🗄 *Database Health*\n\n"
            f"🔴 Status: `unhealthy`\n"
            f"💥 Error: {escape_md(str(health.get('error', 'Unknown')))}"
        )

    await update.message.reply_text(text, parse_mode="MarkdownV2")
