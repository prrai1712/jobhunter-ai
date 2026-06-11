"""Analytics command handlers — /company_stats, /salary_stats, /top_companies."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database.engine import get_async_session
from src.core.services.analytics_service import AnalyticsService
from src.telegram.formatters import escape_md, format_salary_card, format_stats_table
from src.telegram.middleware import authorized_only


@authorized_only
async def company_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /company_stats — show company statistics."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = AnalyticsService(session)
        stats = await service.get_company_stats()

    if not stats:
        await update.message.reply_text(
            "🏢 No company data yet\\.",
            parse_mode="MarkdownV2",
        )
        return

    headers = ["Company", "Found", "Applied", "Rate"]
    rows = []
    for s in stats[:15]:
        rows.append([
            s["name"][:15],
            str(s["jobs_found"]),
            str(s["jobs_applied"]),
            f"{s['success_rate']}%",
        ])

    table = format_stats_table(headers, rows)
    await update.message.reply_text(
        f"🏢 *Company Statistics*\n\n{table}",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def salary_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /salary_stats — show salary intelligence."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = AnalyticsService(session)
        stats = await service.get_salary_stats()

    await update.message.reply_text(
        format_salary_card(stats),
        parse_mode="MarkdownV2",
    )


@authorized_only
async def top_companies_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /top_companies — show top hiring companies."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = AnalyticsService(session)
        companies = await service.get_top_companies(limit=10)

    if not companies:
        await update.message.reply_text(
            "🏢 No company data yet\\.",
            parse_mode="MarkdownV2",
        )
        return

    text = "🏆 *Top Hiring Companies*\n\n"
    for i, c in enumerate(companies, 1):
        text += (
            f"{escape_md(str(i))}\\. *{escape_md(c['name'])}*\n"
            f"   📋 Jobs: {escape_md(str(c['jobs_found']))} \\| "
            f"📤 Applied: {escape_md(str(c['jobs_applied']))} \\| "
            f"💰 {escape_md(c['salary_range'])}\n\n"
        )

    await update.message.reply_text(text, parse_mode="MarkdownV2")
