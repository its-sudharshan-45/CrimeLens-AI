"""
CrimeLocationRepository
=======================
Responsible for all database operations on CrimeLocation entities.

Rules:
- No business logic.
- No transaction commits — the service layer owns commits.
- flush() is called after writes so DB-generated values are available.
"""
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crime_location import CrimeLocation
from app.models.crime_report import CrimeReport

from .base_repository import BaseRepository, PaginatedResult


# ---------------------------------------------------------------------------
# Whitelisted sort columns
# ---------------------------------------------------------------------------
_SORT_COLUMNS: dict = {
    "city": CrimeLocation.city,
    "district": CrimeLocation.district,
    "state": CrimeLocation.state,
    "latitude": CrimeLocation.latitude,
    "longitude": CrimeLocation.longitude,
    "created_at": CrimeLocation.created_at,
    "updated_at": CrimeLocation.updated_at,
}


class CrimeLocationRepository(BaseRepository[CrimeLocation]):
    """Pure data-access layer for CrimeLocation."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, CrimeLocation)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        q: Optional[str] = None,
        sort_by: str = "created_at",
        order: Literal["asc", "desc"] = "desc",
        city: Optional[str] = None,
        district: Optional[str] = None,
        state: Optional[str] = None,
    ) -> PaginatedResult[CrimeLocation]:
        """
        Paginated list of all non-deleted locations with optional filtering.

        Args:
            page:       1-indexed page number.
            page_size:  Maximum results per page.
            q:          Full-text search across address, city, district, landmark.
            sort_by:    Column to sort by (whitelisted).
            order:      'asc' or 'desc'.
            city:       Partial-match filter on city name.
            district:   Partial-match filter on district name.
            state:      Exact-match filter on state (IndianState enum value).
        """
        base_stmt = select(CrimeLocation).where(
            CrimeLocation.is_deleted == False  # noqa: E712
        )

        # Free-text search
        if q:
            search_term = f"%{q.strip()}%"
            base_stmt = base_stmt.where(
                or_(
                    CrimeLocation.address.ilike(search_term),
                    CrimeLocation.city.ilike(search_term),
                    CrimeLocation.district.ilike(search_term),
                    CrimeLocation.landmark.ilike(search_term),
                )
            )

        # Discrete filters
        if city:
            base_stmt = base_stmt.where(
                CrimeLocation.city.ilike(f"%{city.strip()}%")
            )
        if district:
            base_stmt = base_stmt.where(
                CrimeLocation.district.ilike(f"%{district.strip()}%")
            )
        if state:
            base_stmt = base_stmt.where(CrimeLocation.state == state)

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

    async def count_reports(self, location_id: UUID) -> int:
        """
        Return the number of active crime reports referencing this location.

        Used by the service layer to enforce the business rule:
        'A location with active reports cannot be deleted.'
        """
        stmt = select(func.count()).select_from(CrimeReport).where(
            CrimeReport.location_id == location_id,
            CrimeReport.is_deleted == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        latitude: float,
        longitude: float,
        city: str,
        district: str,
        state: str,
        address: Optional[str] = None,
        landmark: Optional[str] = None,
        zip_code: Optional[str] = None,
    ) -> CrimeLocation:
        """Persist a new CrimeLocation. Does NOT commit."""
        location = CrimeLocation(
            latitude=latitude,
            longitude=longitude,
            address=address,
            landmark=landmark,
            city=city.strip(),
            district=district.strip(),
            state=state,
            zip_code=zip_code,
        )
        self.db.add(location)
        await self.db.flush()
        await self.db.refresh(location)
        return location

    async def update(
        self,
        location: CrimeLocation,
        update_data: dict,
    ) -> CrimeLocation:
        """Apply a partial update dict to an existing CrimeLocation."""
        for key, value in update_data.items():
            if hasattr(location, key):
                setattr(location, key, value)
        self.db.add(location)
        await self.db.flush()
        await self.db.refresh(location)
        return location

    async def soft_delete(self, location: CrimeLocation) -> CrimeLocation:
        """Soft-delete a CrimeLocation."""
        location.is_deleted = True
        location.deleted_at = datetime.now(timezone.utc)
        self.db.add(location)
        await self.db.flush()
        return location
