"""User repository."""

from __future__ import annotations

from sqlalchemy import select

from src.core.models.user import User
from src.core.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model_class = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Find user by Telegram user ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, **kwargs) -> tuple[User, bool]:  # type: ignore[no-untyped-def]
        """Get existing user or create a new one. Returns (user, created)."""
        existing = await self.get_by_telegram_id(telegram_id)
        if existing:
            return existing, False
        user = await self.create(telegram_id=telegram_id, **kwargs)
        return user, True
