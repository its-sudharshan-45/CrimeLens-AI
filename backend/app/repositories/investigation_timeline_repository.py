from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.investigation_timeline import InvestigationTimeline
from .base_repository import BaseRepository

class InvestigationTimelineRepository(BaseRepository[InvestigationTimeline]):
    """Pure data-access layer for Investigation Timeline."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, InvestigationTimeline)

    async def get_by_investigation(self, investigation_id: UUID) -> List[InvestigationTimeline]:
        """
        Fetch immutable timeline history in chronological order.
        """
        stmt = (
            select(InvestigationTimeline)
            .options(selectinload(InvestigationTimeline.user))
            .where(InvestigationTimeline.investigation_id == investigation_id)
            .order_by(asc(InvestigationTimeline.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        investigation_id: UUID,
        action: str,
        description: str,
        performed_by: Optional[UUID] = None,
        metadata_json: Optional[dict] = None
    ) -> InvestigationTimeline:
        """
        Creates an immutable timeline record.
        Notice: Update and Delete methods are deliberately NOT implemented for this repository.
        """
        timeline = InvestigationTimeline(
            investigation_id=investigation_id,
            action=action,
            description=description,
            performed_by=performed_by,
            metadata_json=metadata_json,
        )
        self.db.add(timeline)
        await self.db.flush()
        await self.db.refresh(timeline)
        return timeline
