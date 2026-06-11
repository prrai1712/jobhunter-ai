"""Telegram message formatters — Markdown V2, tables, cards."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special)}])", r"\\\1", str(text))


def format_job_card(job: Any) -> str:
    """Format a compact job card for Telegram."""
    salary = f"₹{job.salary_estimate:.1f}L" if job.salary_estimate else "N/A"
    match = f"{job.match_score:.0f}%" if job.match_score else "N/A"
    status = job.status.value if hasattr(job.status, "value") else str(job.status)

    return (
        f"🏢 *{escape_md(job.title)}*\n"
        f"📍 {escape_md(job.location or 'Remote')}\n"
        f"💰 Salary: {escape_md(salary)} \\| Match: {escape_md(match)}\n"
        f"📋 Status: `{escape_md(status)}`\n"
        f"🔗 [Apply]({escape_md(job.apply_url)})\n"
        f"🆔 `{escape_md(str(job.id)[:8])}`"
    )


def format_application_card(app: Any, job: Any = None) -> str:
    """Format an application card for Telegram."""
    status_emoji = {
        "submitted": "✅",
        "failed": "❌",
        "pending": "⏳",
        "submitting": "🔄",
    }
    status = app.status.value if hasattr(app.status, "value") else str(app.status)
    emoji = status_emoji.get(status, "📋")
    title = job.title if job else "Unknown"
    salary = f"₹{app.salary_estimate:.1f}L" if app.salary_estimate else "N/A"
    match = f"{app.match_score:.0f}%" if app.match_score else "N/A"
    applied = app.applied_at.strftime("%H:%M") if app.applied_at else "pending"

    return (
        f"{emoji} *{escape_md(title)}*\n"
        f"💰 {escape_md(salary)} \\| Match: {escape_md(match)}\n"
        f"📋 Status: `{escape_md(status)}` \\| Time: {escape_md(applied)}\n"
        f"🆔 `{escape_md(str(app.id)[:8])}`"
    )


def format_stats_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as a monospace table for Telegram."""
    if not rows:
        return "```\nNo data available\n```"

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Build table
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in widths)

    lines = [header_line, separator]
    for row in rows:
        line = " | ".join(
            str(cell).ljust(widths[i]) if i < len(widths) else str(cell)
            for i, cell in enumerate(row)
        )
        lines.append(line)

    return "```\n" + "\n".join(lines) + "\n```"


def format_salary_card(salary_stats: dict) -> str:
    """Format salary statistics card."""
    dist = salary_stats.get("distribution", {})
    dist_lines = []
    for bucket, count in dist.items():
        bar = "█" * min(count, 20) if count > 0 else "░"
        dist_lines.append(f"  {bucket:>8}: {bar} ({count})")

    return (
        f"📊 *Salary Intelligence*\n\n"
        f"💰 Average: {escape_md(f'₹{salary_stats.get(\"average\", 0)}L')}\n"
        f"📈 Highest: {escape_md(f'₹{salary_stats.get(\"highest\", 0)}L')}\n"
        f"📉 Lowest: {escape_md(f'₹{salary_stats.get(\"lowest\", 0)}L')}\n"
        f"📋 Total Estimates: {escape_md(str(salary_stats.get('total_estimates', 0)))}\n"
        f"🎯 Avg Confidence: {escape_md(f'{salary_stats.get(\"avg_confidence\", 0)}%')}\n\n"
        f"*Distribution:*\n```\n" + "\n".join(dist_lines) + "\n```"
    )


def format_system_status(status: dict) -> str:
    """Format system status for the /system_status command."""
    state_emoji = {
        "running": "🟢",
        "paused": "🟡",
        "stopped": "🔴",
        "maintenance": "🔧",
    }
    state = status.get("state", "unknown")
    emoji = state_emoji.get(state, "⚪")

    lines = [
        f"🤖 *JobHunter AI Status*\n",
        f"{emoji} System: `{escape_md(state.upper())}`\n",
        f"*Workers:*",
    ]

    workers = status.get("workers", [])
    if not workers:
        lines.append("  No workers registered")
    else:
        for w in workers:
            w_emoji = state_emoji.get(w.get("status", ""), "⚪")
            name = w.get("name", "unknown")
            w_status = w.get("status", "unknown")
            heartbeat = w.get("last_heartbeat", "never")
            if isinstance(heartbeat, str) and heartbeat != "never":
                try:
                    dt = datetime.fromisoformat(heartbeat)
                    heartbeat = dt.strftime("%H:%M:%S")
                except ValueError:
                    pass
            lines.append(
                f"  {w_emoji} `{escape_md(name)}`: {escape_md(w_status)} "
                f"\\(heartbeat: {escape_md(str(heartbeat))}\\)"
            )

    return "\n".join(lines)


def format_daily_summary(stats: dict) -> str:
    """Format daily summary for /jobs_today."""
    return (
        f"📅 *Today's Summary*\n\n"
        f"🔍 Jobs Scraped: *{escape_md(str(stats.get('jobs_scraped', 0)))}*\n"
        f"✅ Jobs Matched: *{escape_md(str(stats.get('jobs_matched', 0)))}*\n"
        f"❌ Jobs Rejected: *{escape_md(str(stats.get('jobs_rejected', 0)))}*\n"
        f"🎯 Jobs Qualified: *{escape_md(str(stats.get('jobs_qualified', 0)))}*\n"
        f"📤 Applied: *{escape_md(str(stats.get('applications_submitted', 0)))}*\n"
        f"💥 Failed: *{escape_md(str(stats.get('applications_failed', 0)))}*\n"
        f"🏢 New Companies: *{escape_md(str(stats.get('companies_discovered', 0)))}*\n"
        f"💰 Salary Lookups: *{escape_md(str(stats.get('salary_lookups', 0)))}*\n"
    )


def format_help() -> str:
    """Format the help message with all available commands."""
    return (
        "🤖 *JobHunter AI \\- Command Center*\n\n"
        "*🔧 System Control:*\n"
        "/start \\- Welcome message\n"
        "/start\\_system \\- Start all workers\n"
        "/stop\\_system \\- Stop all workers\n"
        "/pause\\_applications \\- Pause auto\\-apply\n"
        "/resume\\_applications \\- Resume auto\\-apply\n"
        "/system\\_status \\- System health\n"
        "/restart\\_workers \\- Restart workers\n"
        "/database\\_health \\- DB diagnostics\n\n"
        "*📄 Resume Management:*\n"
        "/upload\\_resume \\- Upload a PDF resume\n"
        "/active\\_resume \\- Show active resume\n"
        "/list\\_resumes \\- List all resumes\n"
        "/delete\\_resume \\- Delete a resume\n\n"
        "*💼 Jobs \\& Applications:*\n"
        "/jobs\\_today \\- Today's job summary\n"
        "/applications\\_today \\- Today's applications\n"
        "/application\\_stats \\- Application statistics\n"
        "/application\\_history \\- Full history\n"
        "/job\\_details \\- Detailed job info\n"
        "/approved\\_jobs \\- Qualified jobs\n"
        "/rejected\\_jobs \\- Rejected jobs\n\n"
        "*📊 Analytics:*\n"
        "/company\\_stats \\- Company statistics\n"
        "/salary\\_stats \\- Salary intelligence\n"
        "/top\\_companies \\- Top hiring companies\n\n"
        "*📤 Export:*\n"
        "/export\\_report \\- Generate report \\(CSV/Excel/PDF\\)\n\n"
        "/help \\- Show this message"
    )
