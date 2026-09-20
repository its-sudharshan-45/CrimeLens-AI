"""
CrimeReportRepository
=====================
Responsible for all database operations on CrimeReport entities.

Key design decisions:
- generate_crime_number() uses a per-year PostgreSQL SEQUENCE, which is
  atomic and concurrency-safe — two concurrent requests will never receive
  the same crime number.
- get_all() builds the COUNT query separately (without selectinload) so
  the subquery is clean and avoids SQLAlchemy ORM eager-load issues.
- Relationships (reporter, category, location) are eagerly loaded on
  get_by_id_with_relations() and get_all() so callers never trigger
  async lazy-load errors.

Rules:
- No business logic.
- No transaction commits — the service layer owns commits.
"""
from datetime import datetime, timezone
from typing import Literal, List, Optional
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums.crime_status import CrimeStatus
from app.core.enums.priority import Priority
from app.models.crime_report import CrimeReport

from .base_repository import BaseRepository, PaginatedResult


# ---------------------------------------------------------------------------
# Whitelisted sort columns
# ---------------------------------------------------------------------------
_SORT_COLUMNS: dict = {
    "title": CrimeReport.title,
    "crime_number": CrimeReport.crime_number,
    "incident_date": CrimeReport.incident_date,
    "report_date": CrimeReport.report_date,
    "status": CrimeReport.status,
    "priority": CrimeReport.priority,
    "victim_count": CrimeReport.victim_count,
    "suspect_count": CrimeReport.suspect_count,
    "estimated_loss": CrimeReport.estimated_loss,
    "created_at": CrimeReport.created_at,
    "updated_at": CrimeReport.updated_at,
}

# Relationship options reused across queries
_LOAD_OPTIONS = [
    selectinload(CrimeReport.reporter),
    selectinload(CrimeReport.category),
    selectinload(CrimeReport.location),
]


class CrimeReportRepository(BaseRepository[CrimeReport]):
    """Pure data-access layer for CrimeReport."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, CrimeReport)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_id_with_relations(
        self, report_id: UUID
    ) -> Optional[CrimeReport]:
        """
        Fetch a single non-deleted CrimeReport with reporter, category,
        and location eagerly loaded to avoid async lazy-load errors.
        """
        stmt = (
            select(CrimeReport)
            .options(*_LOAD_OPTIONS)
            .where(
                CrimeReport.id == report_id,
                CrimeReport.is_deleted == False,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_crime_number(
        self, crime_number: str
    ) -> Optional[CrimeReport]:
        """Fetch a non-deleted report by its human-readable crime number."""
        stmt = select(CrimeReport).where(
            CrimeReport.crime_number == crime_number,
            CrimeReport.is_deleted == False,  # noqa: E712
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
        # Discrete filters
        status: Optional[CrimeStatus] = None,
        priority: Optional[Priority] = None,
        category_id: Optional[UUID] = None,
        reporter_id: Optional[UUID] = None,
        # Date range on incident_date
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> PaginatedResult[CrimeReport]:
        """
        Paginated, filtered, sorted list of non-deleted crime reports.

        Two separate queries are executed:
        1. COUNT(*) — lightweight, no eager loading.
        2. SELECT with selectinload — full data with relationships.

        This separation avoids SQLAlchemy subquery issues when combining
        COUNT with eager-load options.
        """
        # Build shared WHERE conditions (applied to both queries)
        conditions = [CrimeReport.is_deleted == False]  # noqa: E712

        if q:
            search_term = f"%{q.strip()}%"
            conditions.append(
                or_(
                    CrimeReport.title.ilike(search_term),
                    CrimeReport.description.ilike(search_term),
                    CrimeReport.crime_number.ilike(search_term),
                )
            )
        if status:
            conditions.append(CrimeReport.status == status)
        if priority:
            conditions.append(CrimeReport.priority == priority)
        if category_id:
            conditions.append(CrimeReport.category_id == category_id)
        if reporter_id:
            conditions.append(CrimeReport.reporter_id == reporter_id)
        if date_from:
            conditions.append(CrimeReport.incident_date >= date_from)
        if date_to:
            conditions.append(CrimeReport.incident_date <= date_to)

        # --- 1. COUNT query (no selectinload) ---
        count_stmt = (
            select(func.count())
            .select_from(CrimeReport)
            .where(*conditions)
        )
        total: int = (await self.db.execute(count_stmt)).scalar() or 0

        # --- 2. Data query (with selectinload) ---
        data_stmt = (
            select(CrimeReport)
            .options(*_LOAD_OPTIONS)
            .where(*conditions)
        )
        data_stmt = self._apply_sort(data_stmt, _SORT_COLUMNS, sort_by, order)
        data_stmt = self._apply_pagination(data_stmt, page, page_size)

        result = await self.db.execute(data_stmt)
        return PaginatedResult(
            items=list(result.scalars().all()),
            total=total,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # Crime Number Generation
    # ------------------------------------------------------------------

    async def generate_crime_number(self) -> str:
        """
        Generate a unique, concurrency-safe crime number.

        Format:  CR-{YEAR}-{6-digit-sequence}
        Example: CR-2026-000001

        Implementation:
        - A per-year PostgreSQL SEQUENCE is created on first use of each
          calendar year (CREATE SEQUENCE IF NOT EXISTS — idempotent).
        - nextval() is atomic: concurrent calls are guaranteed to receive
          distinct values, eliminating race conditions.
        - The sequence resets for each new year by using a new sequence
          name (crime_number_seq_2026, crime_number_seq_2027, ...).

        No application-level locking is required.
        """
        year = datetime.now(timezone.utc).year
        dialect_name = self.db.bind.dialect.name if self.db.bind is not None else "postgresql"

        if dialect_name == "sqlite":
            row = await self.db.execute(
                select(func.count()).select_from(CrimeReport).where(
                    CrimeReport.crime_number.like(f"CR-{year}-%")
                )
            )
            seq_val = int(row.scalar() or 0) + 1
            return f"CR-{year}-{seq_val:06d}"

        seq_name = f"crime_number_seq_{year}"

        # Idempotent sequence creation — safe to call on every request
        await self.db.execute(
            text(
                f"CREATE SEQUENCE IF NOT EXISTS {seq_name} "
                f"START 1 INCREMENT 1 NO CYCLE"
            )
        )

        # nextval() is guaranteed atomic by PostgreSQL
        row = await self.db.execute(text(f"SELECT nextval('{seq_name}')"))
        seq_val: int = int(row.scalar() or 1)

        return f"CR-{year}-{seq_val:06d}"

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        crime_number: str,
        title: str,
        description: str,
        incident_date: datetime,
        reporter_id: UUID,
        category_id: UUID,
        location_id: UUID,
        status: CrimeStatus = CrimeStatus.OPEN,
        priority: Priority = Priority.MEDIUM,
        victim_count: int = 0,
        suspect_count: int = 0,
        estimated_loss: float = 0.0,
    ) -> CrimeReport:
        """
        Persist a new CrimeReport. Does NOT commit.
        crime_number must be pre-generated via generate_crime_number().
        """
        report = CrimeReport(
            crime_number=crime_number,
            title=title.strip(),
            description=description.strip(),
            incident_date=incident_date,
            reporter_id=reporter_id,
            category_id=category_id,
            location_id=location_id,
            status=status,
            priority=priority,
            victim_count=victim_count,
            suspect_count=suspect_count,
            estimated_loss=estimated_loss,
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def update(
        self,
        report: CrimeReport,
        update_data: dict,
    ) -> CrimeReport:
        """Apply a partial update dict to an existing CrimeReport."""
        for key, value in update_data.items():
            if hasattr(report, key):
                setattr(report, key, value)
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def soft_delete(self, report: CrimeReport) -> CrimeReport:
        """Soft-delete a CrimeReport."""
        report.is_deleted = True
        report.deleted_at = datetime.now(timezone.utc)
        self.db.add(report)
        await self.db.flush()
        return report
