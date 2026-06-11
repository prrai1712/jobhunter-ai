"""Resume command handlers — /upload_resume, /active_resume, /list_resumes, /delete_resume."""

from __future__ import annotations

import uuid

from telegram import Update
from telegram.ext import ContextTypes

from src.core.config.settings import get_settings
from src.core.database.engine import get_async_session
from src.core.repositories.user_repository import UserRepository
from src.core.services.resume_service import ResumeService, ResumeValidationError
from src.telegram.formatters import escape_md, format_stats_table
from src.telegram.middleware import authorized_only


@authorized_only
async def upload_resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /upload_resume — prompt user to send a PDF."""
    if not update.message:
        return
    await update.message.reply_text(
        "📄 *Upload Resume*\n\n"
        "Please send me your resume as a PDF document\\.\n"
        "Just drag and drop or attach the PDF file\\.",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document upload — save resume PDF."""
    if not update.message or not update.message.document:
        return

    document = update.message.document
    filename = document.file_name or "resume.pdf"

    # Download file
    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()

    async with get_async_session() as session:
        settings = get_settings()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(
            telegram_id=update.effective_user.id,
            name=update.effective_user.full_name or "",
            email=settings.candidate.email,
        )

        resume_service = ResumeService(session)

        try:
            resume = await resume_service.upload_resume(
                user_id=user.id,
                file_bytes=bytes(file_bytes),
                filename=filename,
            )
        except ResumeValidationError as e:
            await update.message.reply_text(
                f"❌ *Upload Failed*\n\n{escape_md(str(e))}",
                parse_mode="MarkdownV2",
            )
            return

    active_str = "✅ Active" if resume.is_active else "📋 Stored"

    await update.message.reply_text(
        f"✅ *Resume Uploaded\\!*\n\n"
        f"📄 Name: `{escape_md(resume.name)}`\n"
        f"📦 Size: {escape_md(f'{resume.file_size / 1024:.1f}KB')}\n"
        f"🔖 Status: {escape_md(active_str)}\n"
        f"🆔 ID: `{escape_md(str(resume.id)[:8])}`\n\n"
        f"Use `/set_active_resume {escape_md(str(resume.id)[:8])}` to make it active\\.",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def active_resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /active_resume — show the currently active resume."""
    if not update.message:
        return

    async with get_async_session() as session:
        settings = get_settings()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(
            telegram_id=update.effective_user.id,
            name=update.effective_user.full_name or "",
            email=settings.candidate.email,
        )

        resume_service = ResumeService(session)
        resume = await resume_service.get_active(user.id)

    if resume is None:
        await update.message.reply_text(
            "📄 No active resume\\. Upload one with /upload\\_resume",
            parse_mode="MarkdownV2",
        )
        return

    uploaded = resume.created_at.strftime("%Y-%m-%d %H:%M") if resume.created_at else "N/A"

    await update.message.reply_text(
        f"📄 *Active Resume*\n\n"
        f"📋 Name: `{escape_md(resume.name)}`\n"
        f"📦 Size: {escape_md(f'{resume.file_size / 1024:.1f}KB')}\n"
        f"📅 Uploaded: {escape_md(uploaded)}\n"
        f"🆔 ID: `{escape_md(str(resume.id)[:8])}`",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def list_resumes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_resumes — show all uploaded resumes."""
    if not update.message:
        return

    async with get_async_session() as session:
        settings = get_settings()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(
            telegram_id=update.effective_user.id,
            name=update.effective_user.full_name or "",
            email=settings.candidate.email,
        )

        resume_service = ResumeService(session)
        resumes = await resume_service.list_resumes(user.id)

    if not resumes:
        await update.message.reply_text(
            "📄 No resumes uploaded\\. Use /upload\\_resume to add one\\.",
            parse_mode="MarkdownV2",
        )
        return

    headers = ["ID", "Name", "Size", "Active", "Uploaded"]
    rows = []
    for r in resumes:
        rows.append([
            str(r.id)[:8],
            r.name[:20],
            f"{r.file_size / 1024:.0f}KB",
            "✅" if r.is_active else "—",
            r.created_at.strftime("%m/%d") if r.created_at else "",
        ])

    table = format_stats_table(headers, rows)
    await update.message.reply_text(
        f"📄 *Your Resumes*\n\n{table}",
        parse_mode="MarkdownV2",
    )


@authorized_only
async def set_active_resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /set_active_resume <id> — set a resume as active."""
    if not update.message:
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/set_active_resume <resume_id>`",
            parse_mode="MarkdownV2",
        )
        return

    resume_id_str = args[0]

    async with get_async_session() as session:
        settings = get_settings()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(
            telegram_id=update.effective_user.id,
            name=update.effective_user.full_name or "",
            email=settings.candidate.email,
        )

        resume_service = ResumeService(session)

        # Try to find the resume by partial ID
        resumes = await resume_service.list_resumes(user.id)
        matching = [r for r in resumes if str(r.id).startswith(resume_id_str)]

        if not matching:
            await update.message.reply_text(
                f"❌ No resume found with ID starting with `{escape_md(resume_id_str)}`",
                parse_mode="MarkdownV2",
            )
            return

        result = await resume_service.set_active(user.id, matching[0].id)

    if result:
        await update.message.reply_text(
            f"✅ Resume `{escape_md(result.name)}` is now active\\!",
            parse_mode="MarkdownV2",
        )
    else:
        await update.message.reply_text("❌ Failed to set active resume\\.", parse_mode="MarkdownV2")


@authorized_only
async def delete_resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_resume <id> — delete a resume."""
    if not update.message:
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/delete_resume <resume_id>`",
            parse_mode="MarkdownV2",
        )
        return

    resume_id_str = args[0]

    async with get_async_session() as session:
        settings = get_settings()
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(
            telegram_id=update.effective_user.id,
            name=update.effective_user.full_name or "",
            email=settings.candidate.email,
        )

        resume_service = ResumeService(session)
        resumes = await resume_service.list_resumes(user.id)
        matching = [r for r in resumes if str(r.id).startswith(resume_id_str)]

        if not matching:
            await update.message.reply_text(
                f"❌ No resume found with ID `{escape_md(resume_id_str)}`",
                parse_mode="MarkdownV2",
            )
            return

        deleted = await resume_service.delete_resume(user.id, matching[0].id)

    if deleted:
        await update.message.reply_text("✅ Resume deleted\\.", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("❌ Failed to delete resume\\.", parse_mode="MarkdownV2")
