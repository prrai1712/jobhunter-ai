"""Resume service — handles resume upload, validation, storage, and lifecycle."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config.settings import get_settings
from src.core.models.resume import Resume
from src.core.repositories.resume_repository import ResumeRepository


# PDF magic bytes
PDF_MAGIC = b"%PDF"
MAX_RESUME_SIZE = 10 * 1024 * 1024  # 10MB


class ResumeValidationError(Exception):
    """Raised when resume validation fails."""

    pass


class ResumeService:
    """Manages resume upload, selection, and lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ResumeRepository(session)
        self.storage_dir = get_settings().storage.resume_dir

    async def upload_resume(
        self,
        user_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
    ) -> Resume:
        """Validate, store, and register a new resume.

        Args:
            user_id: The user uploading the resume.
            file_bytes: Raw file content.
            filename: Original filename.

        Returns:
            The created Resume record.

        Raises:
            ResumeValidationError: If the file is invalid.
        """
        # Validation
        self._validate_file(file_bytes, filename)

        # Generate unique filename to avoid collisions
        ext = Path(filename).suffix or ".pdf"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = self.storage_dir / unique_name

        # Ensure directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path.write_bytes(file_bytes)

        # Create DB record
        resume = await self.repo.create(
            user_id=user_id,
            name=filename,
            file_path=str(file_path),
            file_size=len(file_bytes),
            mime_type="application/pdf",
            status="active",
            is_active=False,
        )

        # If this is the first resume, auto-activate it
        existing = await self.repo.get_by_user(user_id)
        if len(existing) == 1:
            await self.repo.set_active(user_id, resume.id)
            await self.session.refresh(resume)

        return resume

    def _validate_file(self, file_bytes: bytes, filename: str) -> None:
        """Validate the uploaded file."""
        if not file_bytes:
            raise ResumeValidationError("Empty file received.")

        if len(file_bytes) > MAX_RESUME_SIZE:
            raise ResumeValidationError(
                f"File too large ({len(file_bytes) / 1024 / 1024:.1f}MB). Max: 10MB."
            )

        if not filename.lower().endswith(".pdf"):
            raise ResumeValidationError("Only PDF files are supported.")

        if not file_bytes[:4].startswith(PDF_MAGIC):
            raise ResumeValidationError("File does not appear to be a valid PDF.")

    async def set_active(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume | None:
        """Set a resume as the active resume for applications."""
        resume = await self.repo.get_by_id(resume_id)
        if resume is None or resume.user_id != user_id or resume.is_deleted:
            return None
        return await self.repo.set_active(user_id, resume_id)

    async def get_active(self, user_id: uuid.UUID) -> Resume | None:
        """Get the currently active resume."""
        return await self.repo.get_active_resume(user_id)

    async def list_resumes(self, user_id: uuid.UUID) -> Sequence[Resume]:
        """List all non-deleted resumes for a user."""
        return await self.repo.get_by_user(user_id)

    async def delete_resume(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> bool:
        """Soft-delete a resume."""
        resume = await self.repo.get_by_id(resume_id)
        if resume is None or resume.user_id != user_id:
            return False

        # Don't allow deleting the active resume if it's the only one
        if resume.is_active:
            others = await self.repo.get_by_user(user_id)
            active_others = [r for r in others if r.id != resume_id]
            if active_others:
                # Activate the most recent other resume
                await self.repo.set_active(user_id, active_others[0].id)

        return await self.repo.soft_delete(resume_id)

    async def get_resume_file_path(self, resume_id: uuid.UUID) -> Path | None:
        """Get the file path of a resume."""
        resume = await self.repo.get_by_id(resume_id)
        if resume is None or resume.is_deleted:
            return None
        path = Path(resume.file_path)
        if not path.exists():
            return None
        return path
