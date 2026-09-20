from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.investigation_assignment import InvestigationAssignment
from .base_repository import BaseRepository

class InvestigationAssignmentRepository(BaseRepository[InvestigationAssignment]):
    """Pure data-access layer for Investigation Assignments."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, InvestigationAssignment)

    async def get_active_assignment(self, investigation_id: UUID) -> Optional[InvestigationAssignment]:
        stmt = (
            select(InvestigationAssignment)
            .options(selectinload(InvestigationAssignment.investigator))
            .where(
                InvestigationAssignment.investigation_id == investigation_id,
                InvestigationAssignment.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_history(self, investigation_id: UUID) -> List[InvestigationAssignment]:
        stmt = (
            select(InvestigationAssignment)
            .options(
                selectinload(InvestigationAssignment.investigator),
                selectinload(InvestigationAssignment.assigner)
            )
            .where(InvestigationAssignment.investigation_id == investigation_id)
            .order_by(desc(InvestigationAssignment.assigned_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        investigation_id: UUID,
        investigator_id: UUID,
        assigned_by: UUID,
        reason: Optional[str] = None
    ) -> InvestigationAssignment:
        assignment = InvestigationAssignment(
            investigation_id=investigation_id,
            investigator_id=investigator_id,
            assigned_by=assigned_by,
            reason=reason,
            is_active=True
        )
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def deactivate_assignment(self, assignment: InvestigationAssignment) -> InvestigationAssignment:
        assignment.is_active = False
        assignment.unassigned_at = datetime.now(timezone.utc)
        self.db.add(assignment)
        await self.db.flush()
        return assignment
