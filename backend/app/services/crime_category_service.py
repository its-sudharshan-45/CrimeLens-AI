"""
CrimeCategoryService
====================
Business logic layer for CrimeCategory.

Responsibilities
----------------
- Duplicate name prevention (case-insensitive)
- In-use guard on delete (category referenced by active reports)
- Repository orchestration
- Audit logging (CREATE / UPDATE / DELETE)
- Transaction ownership — this layer calls db.commit()

The repository receives no business logic; it only receives clean,
validated data and returns ORM objects.
"""
import uuid
from typing import Literal, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.crime_category import CrimeCategory
from app.models.user import User
from app.repositories.base_repository import PaginatedResult
from app.repositories.crime_category_repository import CrimeCategoryRepository
from app.schemas.crime_category import CrimeCategoryCreate, CrimeCategoryUpdate
from app.services.audit_service import AuditService


class CrimeCategoryService:
    """Stateless service — all methods are classmethods."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, category_id: uuid.UUID
    ) -> CrimeCategory:
        """
        Return a single non-deleted category or raise 404.
        """
        repo = CrimeCategoryRepository(db)
        category = await repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(
                detail=f"Crime category '{category_id}' not found"
            )
        return category

    @classmethod
    async def get_all(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        q: Optional[str] = None,
        sort_by: str = "created_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> PaginatedResult[CrimeCategory]:
        """Return a paginated, optionally searched/sorted list of categories."""
        repo = CrimeCategoryRepository(db)
        return await repo.get_all(
            page=page,
            page_size=page_size,
            q=q,
            sort_by=sort_by,
            order=order,
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        data: CrimeCategoryCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> CrimeCategory:
        """
        Create a new crime category.

        Business rules enforced
        -----------------------
        - Category name must be unique (case-insensitive).
        """
        repo = CrimeCategoryRepository(db)

        # ── Business Rule: no duplicate names ─────────────────────────
        existing = await repo.get_by_name(data.name)
        if existing:
            raise ConflictException(
                detail=f"A crime category named '{data.name}' already exists"
            )

        category = await repo.create(
            name=data.name,
            description=data.description,
            severity_level=data.severity_level,
            color_code=data.color_code,
        )

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeCategory",
            entity_id=category.id,
            action="CREATE",
            details={
                "name": category.name,
                "severity_level": category.severity_level,
            },
            request=request,
        )

        await db.commit()
        await db.refresh(category)
        return category

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        category_id: uuid.UUID,
        data: CrimeCategoryUpdate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> CrimeCategory:
        """
        Partially update a crime category.

        Business rules enforced
        -----------------------
        - Target category must exist.
        - If name is changed, the new name must not belong to another category.
        """
        repo = CrimeCategoryRepository(db)

        category = await repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(
                detail=f"Crime category '{category_id}' not found"
            )

        update_data = data.model_dump(exclude_unset=True)

        # ── Business Rule: prevent name collision on rename ────────────
        if "name" in update_data:
            existing = await repo.get_by_name(update_data["name"])
            if existing and existing.id != category_id:
                raise ConflictException(
                    detail=f"A crime category named '{update_data['name']}' already exists"
                )

        category = await repo.update(category, update_data)

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeCategory",
            entity_id=category.id,
            action="UPDATE",
            details={"updated_fields": list(update_data.keys()), **update_data},
            request=request,
        )

        await db.commit()
        await db.refresh(category)
        return category

    @classmethod
    async def delete(
        cls,
        db: AsyncSession,
        category_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> None:
        """
        Soft-delete a crime category.

        Business rules enforced
        -----------------------
        - Target category must exist.
        - Category must not be referenced by any active crime reports.
        """
        repo = CrimeCategoryRepository(db)

        category = await repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(
                detail=f"Crime category '{category_id}' not found"
            )

        # ── Business Rule: in-use guard ────────────────────────────────
        report_count = await repo.count_reports(category_id)
        if report_count > 0:
            raise ConflictException(
                detail=(
                    f"Cannot delete category '{category.name}'. "
                    f"It is referenced by {report_count} active crime report(s). "
                    "Reassign or close those reports first."
                )
            )

        await repo.soft_delete(category)

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeCategory",
            entity_id=category_id,
            action="DELETE",
            details={"name": category.name},
            request=request,
        )

        await db.commit()
