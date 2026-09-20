"""
Crime Category API — /api/v1/crime-categories
==============================================
All endpoints require authentication.
"""
from typing import Annotated, Literal, Optional, Any, cast
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, paginate
from app.schemas.crime_category import (
    CrimeCategoryCreate,
    CrimeCategoryResponse,
    CrimeCategoryUpdate,
)
from app.services.crime_category_service import CrimeCategoryService

router = APIRouter()

_authenticated = Depends(get_current_active_user)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=CrimeCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create crime category",
)
async def create_crime_category(
    payload: CrimeCategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
):
    """
    Create a new crime category. **Admin only.**

    Business rules
    --------------
    - `name` must be unique (case-insensitive).
    - `severity_level` must be between 1 and 10.
    - `color_code` must be a valid `#RRGGBB` hex string if provided.

    Audit log is created automatically.
    """
    return cast(Any, await CrimeCategoryService.create(db, payload, current_user, request))


@router.get(
    "",
    response_model=PaginatedResponse[CrimeCategoryResponse],
    summary="List crime categories",
)
async def list_crime_categories(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    q: Optional[str] = Query(None, description="Search name and description"),
    sort_by: str = Query("created_at", description="Sort field"),
    order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> PaginatedResponse[CrimeCategoryResponse]:
    """
    Retrieve a paginated list of crime categories. **All authenticated users.**

    Supports full-text search (`?q=`) across `name` and `description`.
    Sortable by: `name`, `severity_level`, `created_at`, `updated_at`.
    """
    result = await CrimeCategoryService.get_all(
        db,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        order=order,
    )
    return cast(Any, paginate(result))


@router.get(
    "/{category_id}",
    response_model=CrimeCategoryResponse,
    summary="Get crime category by ID",
)
async def get_crime_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> CrimeCategoryResponse:
    """Retrieve a single crime category by UUID. **All authenticated users.**"""
    return cast(Any, await CrimeCategoryService.get_by_id(db, category_id))


@router.patch(
    "/{category_id}",
    response_model=CrimeCategoryResponse,
    summary="Update crime category",
)
async def update_crime_category(
    category_id: uuid.UUID,
    payload: CrimeCategoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> CrimeCategoryResponse:
    """
    Partially update a crime category.
    """
    return cast(Any, await CrimeCategoryService.update(
        db, category_id, payload, current_user, request
    ))


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete crime category",
)
async def delete_crime_category(
    category_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> None:
    """
    Soft-delete a crime category. **Admin only.**

    Returns **409 Conflict** if the category is referenced by active crime reports.
    Audit log is created automatically.
    """
    await CrimeCategoryService.delete(db, category_id, current_user, request)
