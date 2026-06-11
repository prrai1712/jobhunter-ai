"""Export command handler — /export_report."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database.engine import get_async_session
from src.core.services.export_service import ExportService
from src.telegram.formatters import escape_md
from src.telegram.middleware import authorized_only


@authorized_only
async def export_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /export_report — generate and send report files."""
    if not update.message:
        return

    # Determine format from args
    fmt = "csv"
    report_type = "all"
    if context.args:
        arg = context.args[0].lower()
        if arg in ("csv", "excel", "pdf"):
            fmt = arg
        if len(context.args) > 1:
            report_type = context.args[1].lower()

    await update.message.reply_text(
        f"📊 Generating {escape_md(fmt.upper())} report\\.\\.\\.",
        parse_mode="MarkdownV2",
    )

    try:
        async with get_async_session() as session:
            service = ExportService(session)

            if fmt == "csv":
                filepath = await service.export_csv(report_type)
            elif fmt == "excel":
                filepath = await service.export_excel(report_type)
            elif fmt == "pdf":
                filepath = await service.export_pdf(report_type)
            else:
                filepath = await service.export_csv(report_type)

        # Send the file
        with open(filepath, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=filepath.name,
                caption=f"📊 {fmt.upper()} Report — {report_type}",
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Export failed: {escape_md(str(e)[:500])}",
            parse_mode="MarkdownV2",
        )
