"""Job command handlers — /jobs_today, /job_details, /approved_jobs, /rejected_jobs."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database.engine import get_async_session
from src.core.services.job_service import JobService
from src.telegram.formatters import escape_md, format_daily_summary, format_job_card
from src.telegram.middleware import authorized_only


@authorized_only
async def jobs_today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /jobs_today — show today's job summary."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = JobService(session)
        summary = await service.get_today_summary()

    await update.message.reply_text(
        format_daily_summary(summary),
        parse_mode="MarkdownV2",
    )


@authorized_only
async def job_details_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /job_details <id> — show detailed job info."""
    if not update.message:
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/job_details <job_id>`",
            parse_mode="MarkdownV2",
        )
        return

    job_id_str = args[0]

    async with get_async_session() as session:
        service = JobService(session)

        # Get all recent jobs and find by partial ID
        jobs = await service.get_jobs_today()
        matching = [j for j in jobs if str(j.id).startswith(job_id_str)]

        if not matching:
            await update.message.reply_text(
                f"❌ No job found with ID `{escape_md(job_id_str)}`",
                parse_mode="MarkdownV2",
            )
            return

        job = matching[0]

    description = (job.description or "")[:500]
    salary = f"₹{job.salary_estimate:.1f}L" if job.salary_estimate else "N/A"
    match = f"{job.match_score:.0f}%" if job.match_score else "N/A"
    confidence = f"{job.salary_confidence:.0%}" if job.salary_confidence else "N/A"

    text = (
        f"📋 *Job Details*\n\n"
        f"💼 *{escape_md(job.title)}*\n"
        f"📍 Location: {escape_md(job.location or 'N/A')}\n"
        f"📡 Provider: {escape_md(job.ats_provider)}\n"
        f"📋 Status: `{escape_md(job.status.value)}`\n"
        f"💰 Salary: {escape_md(salary)} \\(confidence: {escape_md(confidence)}\\)\n"
        f"🎯 Match: {escape_md(match)}\n"
        f"📅 Discovered: {escape_md(job.discovered_at.strftime('%Y-%m-%d %H:%M') if job.discovered_at else 'N/A')}\n\n"
        f"*Description:*\n{escape_md(description)}{'\\.\\.\\.' if len(job.description or '') > 500 else ''}\n\n"
        f"🔗 [Apply]({escape_md(job.apply_url)})"
    )

    await update.message.reply_text(text, parse_mode="MarkdownV2", disable_web_page_preview=True)


@authorized_only
async def approved_jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /approved_jobs — show qualified jobs."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = JobService(session)
        jobs = await service.get_approved_jobs(limit=10)

    if not jobs:
        await update.message.reply_text("✅ No qualified jobs pending\\.", parse_mode="MarkdownV2")
        return

    text = f"✅ *Qualified Jobs* \\({escape_md(str(len(jobs)))}\\)\n\n"
    for job in jobs[:10]:
        text += format_job_card(job) + "\n\n"

    await update.message.reply_text(text, parse_mode="MarkdownV2", disable_web_page_preview=True)


@authorized_only
async def rejected_jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rejected_jobs — show rejected jobs with reasons."""
    if not update.message:
        return

    async with get_async_session() as session:
        service = JobService(session)
        jobs = await service.get_rejected_jobs(limit=10)

    if not jobs:
        await update.message.reply_text("❌ No rejected jobs\\.", parse_mode="MarkdownV2")
        return

    text = f"❌ *Rejected Jobs* \\({escape_md(str(len(jobs)))}\\)\n\n"
    for job in jobs[:10]:
        reason = job.rejection_reason or "Unknown"
        text += (
            f"🏢 *{escape_md(job.title)}*\n"
            f"💥 Reason: {escape_md(reason)}\n"
            f"🆔 `{escape_md(str(job.id)[:8])}`\n\n"
        )

    await update.message.reply_text(text, parse_mode="MarkdownV2")
