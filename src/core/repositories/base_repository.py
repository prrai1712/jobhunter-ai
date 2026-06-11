"""Generic async repository base — provides CRUD operations for all models."""

from __future__ import annotations

import uuid
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository with standard CRUD operations.

    Subclass this for each model, specifying the model type.
    All methods require an AsyncSession to be passed in (no implicit session).
    """

    model_class: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        """Fetch a single record by primary key."""
        return await self.session.get(self.model_class, id)

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Any | None = None,
    ) -> Sequence[ModelT]:
        """Fetch all records with pagination."""
        stmt = select(self.model_class)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> ModelT:
        """Create and persist a new record."""
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, **kwargs: Any) -> ModelT | None:
        """Update an existing record's fields."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: uuid.UUID) -> bool:
        """Hard-delete a record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self, filters: list[Any] | None = None) -> int:
        """Count records matching optional filters."""
        stmt = select(func.count()).select_from(self.model_class)
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, filters: list[Any]) -> bool:
        """Check if any record matches the given filters."""
        stmt = select(func.count()).select_from(self.model_class)
        for f in filters:
            stmt = stmt.where(f)
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

    def _base_query(self) -> Select:
        """Return a base SELECT statement for this model."""
        return select(self.model_class)
