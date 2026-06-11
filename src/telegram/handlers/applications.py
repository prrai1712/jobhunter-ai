"""Application command handlers — /applications_today, /application_stats, /application_history."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database.engine import get_async_session
from src.core.services.application_service import ApplicationService
from src.telegram.formatters import escape_md, format_application_card, format_stats_table
from src.telegram.middleware import authorized_only


@authorized_only
async def applications_today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /applications_today — show all applications submitted today."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = ApplicationService(session)
        apps = await service.get_applications_today()

    if not apps:
        await update.message.reply_text(
            "📤 No applications submitted today\\.",
            parse_mode="MarkdownV2",
        )
        return

    text = f"📤 *Today's Applications* \\({escape_md(str(len(apps)))}\\)\n\n"
    for app in apps[:15]:
        text += format_application_card(app) + "\n\n"

    await update.message.reply_text(text, parse_mode="MarkdownV2")


@authorized_only
async def application_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /application_stats — show aggregate stats."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = ApplicationService(session)
        stats = await service.get_stats()

    text = (
        f"📊 *Application Statistics*\n\n"
        f"📋 Total: *{escape_md(str(stats['total']))}*\n"
        f"✅ Submitted: *{escape_md(str(stats['submitted']))}*\n"
        f"❌ Failed: *{escape_md(str(stats['failed']))}*\n"
        f"📈 Success Rate: *{escape_md(f\"{stats['success_rate']}%\")}*\n"
        f"🎯 Avg Match Score: *{escape_md(f\"{stats['avg_match_score']}\")}*\n"
        f"💰 Avg Salary: *{escape_md(f\"₹{stats['avg_salary_estimate']}L\")}*"
    )

    await update.message.reply_text(text, parse_mode="MarkdownV2")


@authorized_only
async def application_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /application_history — show paginated history."""
    if not update.message:
        return

    page = 0
    if context.args:
        try:
            page = int(context.args[0]) - 1
        except ValueError:
            page = 0

    limit = 10
    offset = page * limit

    async with get_async_session() as session:
        service = ApplicationService(session)
        apps = await service.get_history(offset=offset, limit=limit)
        total = (await service.get_stats())["total"]

    if not apps:
        await update.message.reply_text(
            "📋 No application history\\.",
            parse_mode="MarkdownV2",
        )
        return

    total_pages = (total + limit - 1) // limit

    text = f"📋 *Application History* \\(Page {escape_md(str(page + 1))}/{escape_md(str(total_pages))}\\)\n\n"
    for app in apps:
        text += format_application_card(app) + "\n\n"

    if total_pages > 1:
        text += f"_Use `/application_history {escape_md(str(page + 2))}` for next page_"

    await update.message.reply_text(text, parse_mode="MarkdownV2")
