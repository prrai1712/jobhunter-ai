"""Resume repository."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, update

from src.core.models.resume import Resume
from src.core.repositories.base_repository import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    model_class = Resume

    async def get_active_resume(self, user_id: uuid.UUID) -> Resume | None:
        """Get the currently active resume for a user."""
        stmt = select(Resume).where(
            Resume.user_id == user_id,
            Resume.is_active == True,  # noqa: E712
            Resume.is_deleted == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> Sequence[Resume]:
        """Get all non-deleted resumes for a user."""
        stmt = (
            select(Resume)
            .where(Resume.user_id == user_id, Resume.is_deleted == False)  # noqa: E712
            .order_by(Resume.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def set_active(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume | None:
        """Set a specific resume as active, deactivating all others."""
        # Deactivate all resumes for this user
        await self.deactivate_all(user_id)
        # Activate the specified resume
        return await self.update(resume_id, is_active=True, status="active")

    async def deactivate_all(self, user_id: uuid.UUID) -> None:
        """Deactivate all resumes for a user."""
        stmt = (
            update(Resume)
            .where(Resume.user_id == user_id)
            .values(is_active=False)
        )
        await self.session.execute(stmt)

    async def soft_delete(self, resume_id: uuid.UUID) -> bool:
        """Soft-delete a resume."""
        from src.core.database.base import utcnow

        result = await self.update(
            resume_id,
            is_deleted=True,
            is_active=False,
            deleted_at=utcnow(),
            status="deleted",
        )
        return result is not None
