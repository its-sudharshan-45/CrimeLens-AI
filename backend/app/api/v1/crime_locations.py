"""
Crime Location API — /api/v1/crime-locations
=============================================
All endpoints require authentication.
"""
from typing import Literal, Optional, Any, cast
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, paginate
from app.schemas.crime_location import (
    CrimeLocationCreate,
    CrimeLocationResponse,
    CrimeLocationUpdate,
)
from app.services.crime_location_service import CrimeLocationService

router = APIRouter()

_authenticated = Depends(get_current_active_user)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=CrimeLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create crime location",
)
async def create_crime_location(
    payload: CrimeLocationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
):
    """
    Create a new crime location. **Police Officer / Investigator / Admin.**

    Validation rules
    ----------------
    - `latitude` must be between 6.0°N and 38.0°N (Indian territory).
    - `longitude` must be between 68.0°E and 98.0°E (Indian territory).
    - `state` must be a valid Indian State or Union Territory.
    - `zip_code` must be a 6-digit Indian PIN code if provided.

    Audit log is created automatically.
    """
    return cast(Any, await CrimeLocationService.create(db, payload, current_user, request))


@router.get(
    "",
    response_model=PaginatedResponse[CrimeLocationResponse],
    summary="List crime locations",
)
async def list_crime_locations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    q: Optional[str] = Query(
        None, description="Search address, city, district, or landmark"
    ),
    sort_by: str = Query("created_at", description="Sort field"),
    order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    district: Optional[str] = Query(
        None, description="Filter by district (partial match)"
    ),
    state: Optional[str] = Query(
        None, description="Filter by state (exact match — Indian State name)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> PaginatedResponse[CrimeLocationResponse]:
    """
    Retrieve a paginated, filtered list of crime locations. **All authenticated users.**

    Supports free-text search (`?q=`) and discrete filters for `city`, `district`, `state`.
    Sortable by: `city`, `district`, `state`, `latitude`, `longitude`, `created_at`, `updated_at`.
    """
    result = await CrimeLocationService.get_all(
        db,
        page=page,
        page_size=page_size,
        q=q,
        sort_by=sort_by,
        order=order,
        city=city,
        district=district,
        state=state,
    )
    return cast(Any, paginate(result))


@router.get(
    "/{location_id}",
    response_model=CrimeLocationResponse,
    summary="Get crime location by ID",
)
async def get_crime_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> CrimeLocationResponse:
    """Retrieve a single crime location by UUID. **All authenticated users.**"""
    return cast(Any, await CrimeLocationService.get_by_id(db, location_id))


@router.patch(
    "/{location_id}",
    response_model=CrimeLocationResponse,
    summary="Update crime location",
)
async def update_crime_location(
    location_id: uuid.UUID,
    payload: CrimeLocationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> CrimeLocationResponse:
    """
    Partially update a crime location.
    """
    return cast(Any, await CrimeLocationService.update(
        db, location_id, payload, current_user, request
    ))


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete crime location",
)
async def delete_crime_location(
    location_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = _authenticated,
) -> None:
    """
    Soft-delete a crime location. **Admin only.**

    Returns **409 Conflict** if the location is referenced by active crime reports.
    Audit log is created automatically.
    """
    await CrimeLocationService.delete(db, location_id, current_user, request)
