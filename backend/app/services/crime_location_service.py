"""
CrimeLocationService
====================
Business logic layer for CrimeLocation.

Responsibilities
----------------
- In-use guard on delete (location referenced by active reports)
- IndianState enum → string conversion before persistence
- Repository orchestration
- Audit logging (CREATE / UPDATE / DELETE)
- Transaction ownership

Note: Lat/lon boundary validation and IndianState validation are enforced
at the Pydantic schema layer (CrimeLocationCreate / CrimeLocationUpdate).
This service layer does not duplicate schema-level validations.
"""
import uuid
from typing import Literal, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.crime_location import CrimeLocation
from app.models.user import User
from app.repositories.base_repository import PaginatedResult
from app.repositories.crime_location_repository import CrimeLocationRepository
from app.schemas.crime_location import CrimeLocationCreate, CrimeLocationUpdate
from app.services.audit_service import AuditService


class CrimeLocationService:
    """Stateless service — all methods are classmethods."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, location_id: uuid.UUID
    ) -> CrimeLocation:
        """Return a single non-deleted location or raise 404."""
        repo = CrimeLocationRepository(db)
        location = await repo.get_by_id(location_id)
        if not location:
            raise NotFoundException(
                detail=f"Crime location '{location_id}' not found"
            )
        return location

    @classmethod
    async def get_all(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        q: Optional[str] = None,
        sort_by: str = "created_at",
        order: Literal["asc", "desc"] = "desc",
        city: Optional[str] = None,
        district: Optional[str] = None,
        state: Optional[str] = None,
    ) -> PaginatedResult[CrimeLocation]:
        """Return a paginated, filtered list of locations."""
        repo = CrimeLocationRepository(db)
        return await repo.get_all(
            page=page,
            page_size=page_size,
            q=q,
            sort_by=sort_by,
            order=order,
            city=city,
            district=district,
            state=state,
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        data: CrimeLocationCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> CrimeLocation:
        """
        Create a new crime location.

        The IndianState enum value is unwrapped to its string representation
        before being stored (the DB column is a plain VARCHAR).
        """
        repo = CrimeLocationRepository(db)

        location = await repo.create(
            latitude=data.latitude,
            longitude=data.longitude,
            address=data.address,
            landmark=data.landmark,
            city=data.city,
            district=data.district,
            # Convert IndianState enum to its string value for DB storage
            state=data.state.value,
            zip_code=data.zip_code,
        )

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeLocation",
            entity_id=location.id,
            action="CREATE",
            details={
                "city": location.city,
                "district": location.district,
                "state": location.state,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            request=request,
        )

        await db.commit()
        await db.refresh(location)
        return location

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        location_id: uuid.UUID,
        data: CrimeLocationUpdate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> CrimeLocation:
        """
        Partially update a crime location.

        Business rules enforced
        -----------------------
        - Target location must exist.
        """
        repo = CrimeLocationRepository(db)

        location = await repo.get_by_id(location_id)
        if not location:
            raise NotFoundException(
                detail=f"Crime location '{location_id}' not found"
            )

        update_data = data.model_dump(exclude_unset=True)

        # Unwrap IndianState enum to string if state is being updated
        if "state" in update_data and update_data["state"] is not None:
            update_data["state"] = update_data["state"].value

        location = await repo.update(location, update_data)

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeLocation",
            entity_id=location.id,
            action="UPDATE",
            details={"updated_fields": list(update_data.keys())},
            request=request,
        )

        await db.commit()
        await db.refresh(location)
        return location

    @classmethod
    async def delete(
        cls,
        db: AsyncSession,
        location_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> None:
        """
        Soft-delete a crime location.

        Business rules enforced
        -----------------------
        - Target location must exist.
        - Location must not be referenced by any active crime reports.
        """
        repo = CrimeLocationRepository(db)

        location = await repo.get_by_id(location_id)
        if not location:
            raise NotFoundException(
                detail=f"Crime location '{location_id}' not found"
            )

        # ── Business Rule: in-use guard ────────────────────────────────
        report_count = await repo.count_reports(location_id)
        if report_count > 0:
            raise ConflictException(
                detail=(
                    f"Cannot delete this location. "
                    f"It is referenced by {report_count} active crime report(s). "
                    "Update those reports to use a different location first."
                )
            )

        await repo.soft_delete(location)

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeLocation",
            entity_id=location_id,
            action="DELETE",
            details={
                "city": location.city,
                "district": location.district,
                "state": location.state,
            },
            request=request,
        )

        await db.commit()
