"""
CrimeCategoryRepository
=======================
Responsible for all database operations on CrimeCategory entities.

Rules:
- No business logic.
- No transaction commits — the service layer owns commits.
- flush() is called after writes to populate DB-generated values
  (id, created_at, updated_at) before returning.
"""
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crime_category import CrimeCategory
from app.models.crime_report import CrimeReport

from .base_repository import BaseRepository, PaginatedResult


# ---------------------------------------------------------------------------
# Whitelisted sort columns — protects against column-name injection
# ---------------------------------------------------------------------------
_SORT_COLUMNS: dict = {
    "name": CrimeCategory.name,
    "severity_level": CrimeCategory.severity_level,
    "created_at": CrimeCategory.created_at,
    "updated_at": CrimeCategory.updated_at,
}


class CrimeCategoryRepository(BaseRepository[CrimeCategory]):
    """Pure data-access layer for CrimeCategory."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, CrimeCategory)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_name(self, name: str) -> Optional[CrimeCategory]:
        """
        Case-insensitive exact-name lookup (non-deleted only).
        Used by the service layer to prevent duplicate category names.
        """
        stmt = select(CrimeCategory).where(
            func.lower(CrimeCategory.name) == name.strip().lower(),
            CrimeCategory.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        q: Optional[str] = None,
        sort_by: str = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> PaginatedResult[CrimeCategory]:
        """
        Paginated list of all non-deleted categories.

        Args:
            page:       1-indexed page number.
            page_size:  Maximum results per page.
            q:          Full-text search across `name` and `description`.
            sort_by:    Column to sort by (whitelisted).
            order:      'asc' or 'desc'.

        Returns:
            PaginatedResult containing items + pagination metadata.
        """
        base_stmt = select(CrimeCategory).where(
            CrimeCategory.is_deleted == False  # noqa: E712
        )

        if q:
            search_term = f"%{q.strip()}%"
            base_stmt = base_stmt.where(
                or_(
                    CrimeCategory.name.ilike(search_term),
                    CrimeCategory.description.ilike(search_term),
                )
            )

        total = await self._count_stmt(base_stmt)
        base_stmt = self._apply_sort(base_stmt, _SORT_COLUMNS, sort_by, order)
        base_stmt = self._apply_pagination(base_stmt, page, page_size)

        result = await self.db.execute(base_stmt)
        return PaginatedResult(
            items=list(result.scalars().all()),
            total=total,
            page=page,
            page_size=page_size,
        )

    async def count_reports(self, category_id: UUID) -> int:
        """
        Return the number of active (non-deleted) crime reports
        that reference this category.

        Used by the service layer to enforce the business rule:
        'A category with active reports cannot be deleted.'
        """
        stmt = select(func.count()).select_from(CrimeReport).where(
            CrimeReport.category_id == category_id,
            CrimeReport.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    # ------------------------------------------------------------------
    # Writes (no commits — service owns the transaction)
    # ------------------------------------------------------------------

    async def create(
        self,
        name: str,
        severity_level: int = 1,
        description: Optional[str] = None,
        color_code: Optional[str] = None,
    ) -> CrimeCategory:
        """
        Persist a new CrimeCategory.
        flush() is called so the DB-generated `id` and timestamps are
        populated on the returned object without committing.
        """
        category = CrimeCategory(
            name=name.strip(),
            description=description,
            severity_level=severity_level,
            color_code=color_code,
        )
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def update(
        self,
        category: CrimeCategory,
        update_data: dict,
    ) -> CrimeCategory:
        """
        Apply a partial update dict to an existing CrimeCategory.
        Only keys present in update_data are written.
        """
        for key, value in update_data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def soft_delete(self, category: CrimeCategory) -> CrimeCategory:
        """
        Mark a category as deleted without removing the DB row.
        Sets is_deleted=True and records deleted_at timestamp.
        """
        category.is_deleted = True
        category.deleted_at = datetime.now(timezone.utc)
        self.db.add(category)
        await self.db.flush()
        return category
