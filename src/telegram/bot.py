"""Telegram bot — initialization and handler registration."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.core.config.settings import get_settings
from src.telegram import notifications
from src.telegram.handlers.system import (
    start_command,
    start_system_command,
    stop_system_command,
    pause_applications_command,
    resume_applications_command,
    help_command,
)
from src.telegram.handlers.resume import (
    upload_resume_command,
    handle_document_upload,
    active_resume_command,
    list_resumes_command,
    set_active_resume_command,
    delete_resume_command,
)
from src.telegram.handlers.jobs import (
    jobs_today_command,
    job_details_command,
    approved_jobs_command,
    rejected_jobs_command,
)
from src.telegram.handlers.applications import (
    applications_today_command,
    application_stats_command,
    application_history_command,
)
from src.telegram.handlers.analytics import (
    company_stats_command,
    salary_stats_command,
    top_companies_command,
)
from src.telegram.handlers.admin import (
    system_status_command,
    restart_workers_command,
    database_health_command,
)
from src.telegram.handlers.export import export_report_command

logger = structlog.get_logger(__name__)


async def error_handler(update: object, context) -> None:  # type: ignore[no-untyped-def]
    """Global error handler for unhandled exceptions."""
    logger.error(
        "telegram_error",
        error=str(context.error),
        update=str(update)[:200] if update else None,
    )
    # Notify admin
    try:
        await notifications.notify_system_alert(
            f"Telegram error: {str(context.error)[:300]}",
            level="error",
        )
    except Exception:
        pass


async def post_init(application: Application) -> None:
    """Called after the application is fully initialized."""
    settings = get_settings()
    notifications.set_bot(application.bot)

    # Send startup notification
    try:
        await application.bot.send_message(
            chat_id=settings.telegram.log_chat_id,
            text="🤖 *JobHunter AI is online\\!*\n\nUse /help to see all commands\\.",
            parse_mode="MarkdownV2",
        )
    except Exception as e:
        logger.error("startup_notification_failed", error=str(e))


def create_bot() -> Application:
    """Create and configure the Telegram bot application."""
    settings = get_settings()

    if not settings.telegram.bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set. Get one from @BotFather.")

    app = (
        ApplicationBuilder()
        .token(settings.telegram.bot_token)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    # ─── System Commands ─────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("start_system", start_system_command))
    app.add_handler(CommandHandler("stop_system", stop_system_command))
    app.add_handler(CommandHandler("pause_applications", pause_applications_command))
    app.add_handler(CommandHandler("resume_applications", resume_applications_command))
    app.add_handler(CommandHandler("help", help_command))

    # ─── Resume Commands ─────────────────────────────────────────────
    app.add_handler(CommandHandler("upload_resume", upload_resume_command))
    app.add_handler(CommandHandler("active_resume", active_resume_command))
    app.add_handler(CommandHandler("list_resumes", list_resumes_command))
    app.add_handler(CommandHandler("set_active_resume", set_active_resume_command))
    app.add_handler(CommandHandler("delete_resume", delete_resume_command))

    # ─── Job Commands ────────────────────────────────────────────────
    app.add_handler(CommandHandler("jobs_today", jobs_today_command))
    app.add_handler(CommandHandler("job_details", job_details_command))
    app.add_handler(CommandHandler("approved_jobs", approved_jobs_command))
    app.add_handler(CommandHandler("rejected_jobs", rejected_jobs_command))

    # ─── Application Commands ────────────────────────────────────────
    app.add_handler(CommandHandler("applications_today", applications_today_command))
    app.add_handler(CommandHandler("application_stats", application_stats_command))
    app.add_handler(CommandHandler("application_history", application_history_command))

    # ─── Analytics Commands ──────────────────────────────────────────
    app.add_handler(CommandHandler("company_stats", company_stats_command))
    app.add_handler(CommandHandler("salary_stats", salary_stats_command))
    app.add_handler(CommandHandler("top_companies", top_companies_command))

    # ─── Admin Commands ──────────────────────────────────────────────
    app.add_handler(CommandHandler("system_status", system_status_command))
    app.add_handler(CommandHandler("restart_workers", restart_workers_command))
    app.add_handler(CommandHandler("database_health", database_health_command))

    # ─── Export Commands ─────────────────────────────────────────────
    app.add_handler(CommandHandler("export_report", export_report_command))

    # ─── Document Upload (for resume) ────────────────────────────────
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))

    # ─── Error Handler ───────────────────────────────────────────────
    app.add_error_handler(error_handler)

    logger.info("telegram_bot_created", handlers=len(app.handlers.get(0, [])))

    return app
