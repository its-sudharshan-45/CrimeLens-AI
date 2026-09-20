"""
CrimeReportService
==================
Business logic layer for CrimeReport — the most complex service in Phase 4.

Responsibilities
----------------
- Auto-generate unique crime number via PostgreSQL sequence
- Auto-assign reporter from authenticated user (never from client input)
- Force status = OPEN and validate status transitions
- Validate FK references (category, location) before persisting
- Prevent deletion of ARCHIVED reports
- Repository orchestration
- Audit logging (CREATE / UPDATE / DELETE)
- Transaction ownership

Status transition matrix
------------------------
OPEN              → UNDER_INVESTIGATION | CLOSED
UNDER_INVESTIGATION → CLOSED | OPEN
CLOSED            → ARCHIVED | OPEN
ARCHIVED          → (terminal — no transitions allowed)
"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums.crime_status import CrimeStatus
from app.core.enums.priority import Priority
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.crime_report import CrimeReport
from app.models.user import User
from app.repositories.base_repository import PaginatedResult
from app.repositories.crime_category_repository import CrimeCategoryRepository
from app.repositories.crime_location_repository import CrimeLocationRepository
from app.repositories.crime_report_repository import CrimeReportRepository
from app.schemas.crime_report import CrimeReportCreate, CrimeReportUpdate
from app.services.audit_service import AuditService


# ---------------------------------------------------------------------------
# Status transition whitelist
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS: dict[CrimeStatus, list[CrimeStatus]] = {
    CrimeStatus.OPEN: [
        CrimeStatus.UNDER_INVESTIGATION,
        CrimeStatus.CLOSED,
    ],
    CrimeStatus.UNDER_INVESTIGATION: [
        CrimeStatus.CLOSED,
        CrimeStatus.OPEN,
    ],
    CrimeStatus.CLOSED: [
        CrimeStatus.ARCHIVED,
        CrimeStatus.OPEN,
    ],
    CrimeStatus.ARCHIVED: [],  # Terminal state — no further transitions
}


class CrimeReportService:
    """Stateless service — all methods are classmethods."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, report_id: uuid.UUID
    ) -> CrimeReport:
        """Return a single non-deleted report (with relations) or raise 404."""
        repo = CrimeReportRepository(db)
        report = await repo.get_by_id_with_relations(report_id)
        if not report:
            raise NotFoundException(
                detail=f"Crime report '{report_id}' not found"
            )
        return report

    @classmethod
    async def get_all(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        q: Optional[str] = None,
        sort_by: str = "created_at",
        order: Literal["asc", "desc"] = "desc",
        status: Optional[CrimeStatus] = None,
        priority: Optional[Priority] = None,
        category_id: Optional[uuid.UUID] = None,
        reporter_id: Optional[uuid.UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> PaginatedResult[CrimeReport]:
        """Return a fully-filtered paginated list of crime reports."""
        repo = CrimeReportRepository(db)
        return await repo.get_all(
            page=page,
            page_size=page_size,
            q=q,
            sort_by=sort_by,
            order=order,
            status=status,
            priority=priority,
            category_id=category_id,
            reporter_id=reporter_id,
            date_from=date_from,
            date_to=date_to,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    async def _validate_fks(
        cls,
        db: AsyncSession,
        category_id: uuid.UUID,
        location_id: uuid.UUID,
    ) -> None:
        """
        Verify that both FK references resolve to non-deleted records.
        Raises 404 with a descriptive message if either is missing.
        """
        cat_repo = CrimeCategoryRepository(db)
        loc_repo = CrimeLocationRepository(db)

        if not await cat_repo.get_by_id(category_id):
            raise NotFoundException(
                detail=f"Crime category '{category_id}' not found or has been deleted"
            )
        if not await loc_repo.get_by_id(location_id):
            raise NotFoundException(
                detail=f"Crime location '{location_id}' not found or has been deleted"
            )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        data: CrimeReportCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> CrimeReport:
        """
        Create a new crime report.

        Business rules enforced
        -----------------------
        1. category_id and location_id must reference non-deleted records.
        2. crime_number is auto-generated (atomic PostgreSQL sequence).
        3. reporter_id is always set to current_user.id — never from the client.
        4. status is always forced to OPEN regardless of client input.
        """
        # ── Rule 1: Validate FK references ────────────────────────────
        await cls._validate_fks(db, data.category_id, data.location_id)

        report_repo = CrimeReportRepository(db)

        # ── Rule 2: Auto-generate crime number ────────────────────────
        crime_number = await report_repo.generate_crime_number()

        # ── Rule 3 & 4: Auto-assign reporter, force OPEN status ───────
        report = await report_repo.create(
            crime_number=crime_number,
            title=data.title,
            description=data.description,
            incident_date=data.incident_date,
            reporter_id=current_user.id,  # Always from session
            category_id=data.category_id,
            location_id=data.location_id,
            status=CrimeStatus.OPEN,      # Always starts OPEN
            priority=data.priority,
            victim_count=data.victim_count,
            suspect_count=data.suspect_count,
            estimated_loss=data.estimated_loss,
        )

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeReport",
            entity_id=report.id,
            action="CREATE",
            details={
                "crime_number": report.crime_number,
                "title": report.title,
                "status": report.status.value,
                "priority": report.priority.value,
                "category_id": str(report.category_id),
                "location_id": str(report.location_id),
            },
            request=request,
        )

        await db.commit()
        # Re-fetch with relationships eagerly loaded for the response
        fetched = await report_repo.get_by_id_with_relations(report.id)
        if fetched is None:
            raise RuntimeError("Report disappeared after create commit.")
        return fetched

    @classmethod
    async def update(
        cls,
        db: AsyncSession,
        report_id: uuid.UUID,
        data: CrimeReportUpdate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> CrimeReport:
        """
        Partially update a crime report.

        Business rules enforced
        -----------------------
        1. Report must exist.
        2. If category_id or location_id change, the new FKs must be valid.
        3. Status changes are validated against the transition matrix.
        """
        report_repo = CrimeReportRepository(db)

        report = await report_repo.get_by_id_with_relations(report_id)
        if not report:
            raise NotFoundException(
                detail=f"Crime report '{report_id}' not found"
            )

        update_data = data.model_dump(exclude_unset=True)

        # ── Rule 2: Validate changed FK references ─────────────────────
        if "category_id" in update_data or "location_id" in update_data:
            cat_id = update_data.get("category_id", report.category_id)
            loc_id = update_data.get("location_id", report.location_id)
            await cls._validate_fks(db, cat_id, loc_id)

        # ── Rule 3: Status transition validation ──────────────────────
        if "status" in update_data:
            new_status: CrimeStatus = update_data["status"]
            allowed = _VALID_TRANSITIONS.get(report.status, [])
            if new_status not in allowed:
                allowed_labels = (
                    [s.value for s in allowed] if allowed else ["none — terminal state"]
                )
                raise BadRequestException(
                    detail=(
                        f"Invalid status transition: "
                        f"'{report.status.value}' → '{new_status.value}'. "
                        f"Valid transitions from '{report.status.value}': "
                        f"{allowed_labels}"
                    )
                )

        status_before = report.status.value
        report = await report_repo.update(report, update_data)

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeReport",
            entity_id=report.id,
            action="UPDATE",
            details={
                "updated_fields": list(update_data.keys()),
                "status_before": status_before,
                "status_after": report.status.value,
            },
            request=request,
        )

        await db.commit()
        updated = await report_repo.get_by_id_with_relations(report.id)
        if updated is None:
            raise RuntimeError("Report disappeared after update commit.")
        return updated

    @classmethod
    async def delete(
        cls,
        db: AsyncSession,
        report_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> None:
        """
        Soft-delete a crime report.

        Business rules enforced
        -----------------------
        1. Report must exist.
        2. ARCHIVED reports cannot be deleted.
        """
        report_repo = CrimeReportRepository(db)

        report = await report_repo.get_by_id(report_id)
        if not report:
            raise NotFoundException(
                detail=f"Crime report '{report_id}' not found"
            )

        # ── Rule 2: Archived reports are immutable ─────────────────────
        if report.status == CrimeStatus.ARCHIVED:
            raise ConflictException(
                detail=(
                    f"Crime report '{report.crime_number}' is ARCHIVED and cannot be deleted. "
                    "Archived reports are permanent records."
                )
            )

        crime_number = report.crime_number
        await report_repo.soft_delete(report)

        await AuditService.log(
            db=db,
            user_id=current_user.id,
            entity_type="CrimeReport",
            entity_id=report_id,
            action="DELETE",
            details={"crime_number": crime_number, "title": report.title},
            request=request,
        )

        await db.commit()
