import math
from dataclasses import dataclass, field
from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession


T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """
    Generic, immutable container for paginated query results.

    Computed properties (total_pages, has_next, has_prev) are derived
    from the raw values so callers never need to recompute them.
    """

    items: List[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return math.ceil(self.total / self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class BaseRepository(Generic[T]):
    """
    Generic async repository providing primitive data-access utilities.

    Responsibilities (this layer only):
    - Raw database CRUD operations
    - Pagination helpers
    - Sorting helpers
    - Counting helpers

    Rules:
    - NO business logic.
    - NO transaction commits — callers (services) own the transaction.
    - flush() is used after writes so the ID/timestamps are populated
      before returning, without prematurely committing.
    """

    def __init__(self, db: AsyncSession, model_class: Type[T]) -> None:
        self.db = db
        self.model_class = model_class

    # ------------------------------------------------------------------
    # Core read
    # ------------------------------------------------------------------

    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Fetch a single non-deleted entity by primary key.
        Returns None if not found or soft-deleted.
        """
        stmt = select(self.model_class).where(
            getattr(self.model_class, "id") == entity_id,
            getattr(self.model_class, "is_deleted") == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------
    # Helpers used by concrete repositories
    # ------------------------------------------------------------------

    async def _count_stmt(self, base_stmt) -> int:
        """
        Execute a COUNT(*) over the WHERE conditions of *base_stmt*.

        NOTE: Only pass statements that have NO relationship-loading
        options (selectinload / joinedload). For repos that use eager
        loading, build a separate count query without those options.
        """
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        result = await self.db.execute(count_stmt)
        return result.scalar() or 0

    @staticmethod
    def _apply_sort(stmt, allowed_columns: dict, sort_by: str, order: str):
        """
        Apply ORDER BY to *stmt* using a whitelist of allowed column names.

        Falls back to `created_at` if *sort_by* is not in the whitelist,
        preventing SQL injection through column name injection.
        """
        col = allowed_columns.get(sort_by) or allowed_columns.get("created_at")
        if col is None:
            return stmt
        order_func = asc if order == "asc" else desc
        return stmt.order_by(order_func(col))

    @staticmethod
    def _apply_pagination(stmt, page: int, page_size: int):
        """Apply LIMIT / OFFSET pagination (1-indexed page numbers)."""
        offset = (page - 1) * page_size
        return stmt.offset(offset).limit(page_size)
