from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import func, or_, select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums.investigation_status import InvestigationStatus
from app.core.enums.priority import Priority
from app.models.investigation import Investigation
from .base_repository import BaseRepository, PaginatedResult

_SORT_COLUMNS: dict = {
    "created_at": Investigation.created_at,
    "updated_at": Investigation.updated_at,
    "priority": Investigation.priority,
    "status": Investigation.status,
    "assigned_at": Investigation.assigned_at,
}

_LOAD_OPTIONS = [
    selectinload(Investigation.report),
    selectinload(Investigation.investigator),
]

class InvestigationRepository(BaseRepository[Investigation]):
    """Pure data-access layer for Investigation."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Investigation)

    async def get_by_id_with_relations(self, investigation_id: UUID) -> Optional[Investigation]:
        stmt = (
            select(Investigation)
            .options(*_LOAD_OPTIONS)
            .where(
                Investigation.id == investigation_id,
                Investigation.is_deleted == False
            )
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
        status: Optional[InvestigationStatus] = None,
        priority: Optional[Priority] = None,
        investigator_id: Optional[UUID] = None,
        report_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> PaginatedResult[Investigation]:
        conditions = [Investigation.is_deleted == False]
        
        if q:
            search_term = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Investigation.notes.ilike(search_term),
                    Investigation.resolution_summary.ilike(search_term),
                )
            )
        if status:
            conditions.append(Investigation.status == status)
        if priority:
            conditions.append(Investigation.priority == priority)
        if investigator_id:
            conditions.append(Investigation.investigator_id == investigator_id)
        if report_id:
            conditions.append(Investigation.report_id == report_id)
        if date_from:
            conditions.append(Investigation.created_at >= date_from)
        if date_to:
            conditions.append(Investigation.created_at <= date_to)

        count_stmt = select(func.count()).select_from(Investigation).where(*conditions)
        total: int = (await self.db.execute(count_stmt)).scalar() or 0

        data_stmt = select(Investigation).options(*_LOAD_OPTIONS).where(*conditions)
        data_stmt = self._apply_sort(data_stmt, _SORT_COLUMNS, sort_by, order)
        data_stmt = self._apply_pagination(data_stmt, page, page_size)

        result = await self.db.execute(data_stmt)
        return PaginatedResult(
            items=list(result.scalars().all()),
            total=total,
            page=page,
            page_size=page_size,
        )

    async def create(
        self,
        report_id: UUID,
        investigator_id: UUID,
        status: InvestigationStatus = InvestigationStatus.OPEN,
        priority: Priority = Priority.MEDIUM,
        notes: Optional[str] = None
    ) -> Investigation:
        investigation = Investigation(
            report_id=report_id,
            investigator_id=investigator_id,
            status=status,
            priority=priority,
            notes=notes,
        )
        self.db.add(investigation)
        await self.db.flush()
        await self.db.refresh(investigation)
        return investigation

    async def update(self, investigation: Investigation, update_data: dict) -> Investigation:
        for key, value in update_data.items():
            if hasattr(investigation, key):
                setattr(investigation, key, value)
        self.db.add(investigation)
        await self.db.flush()
        await self.db.refresh(investigation)
        return investigation

    async def soft_delete(self, investigation: Investigation) -> Investigation:
        investigation.is_deleted = True
        investigation.deleted_at = datetime.now(timezone.utc)
        self.db.add(investigation)
        await self.db.flush()
        return investigation
