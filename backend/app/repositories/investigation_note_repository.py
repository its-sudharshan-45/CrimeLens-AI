from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.investigation_note import InvestigationNote
from .base_repository import BaseRepository, PaginatedResult

class InvestigationNoteRepository(BaseRepository[InvestigationNote]):
    """Pure data-access layer for Investigation Notes."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, InvestigationNote)

    async def get_by_investigation(
        self,
        investigation_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResult[InvestigationNote]:
        conditions = [
            InvestigationNote.investigation_id == investigation_id,
            InvestigationNote.is_deleted == False
        ]

        count_stmt = select(func.count()).select_from(InvestigationNote).where(*conditions)
        total: int = (await self.db.execute(count_stmt)).scalar() or 0

        data_stmt = (
            select(InvestigationNote)
            .options(
                selectinload(InvestigationNote.author),
                selectinload(InvestigationNote.attachment)
            )
            .where(*conditions)
            .order_by(desc(InvestigationNote.created_at))
        )
        data_stmt = self._apply_pagination(data_stmt, page, page_size)

        result = await self.db.execute(data_stmt)
        return PaginatedResult(
            items=list(result.scalars().all()),
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_by_id_with_author(self, note_id: UUID) -> Optional[InvestigationNote]:
        stmt = (
            select(InvestigationNote)
            .options(selectinload(InvestigationNote.author))
            .where(InvestigationNote.id == note_id, InvestigationNote.is_deleted == False)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(
        self,
        investigation_id: UUID,
        author_id: UUID,
        note: str,
        attachment_evidence_id: Optional[UUID] = None
    ) -> InvestigationNote:
        inv_note = InvestigationNote(
            investigation_id=investigation_id,
            author_id=author_id,
            note=note,
            attachment_evidence_id=attachment_evidence_id,
        )
        self.db.add(inv_note)
        await self.db.flush()
        await self.db.refresh(inv_note)
        return inv_note

    async def update(self, note_obj: InvestigationNote, note_text: str) -> InvestigationNote:
        note_obj.note = note_text
        note_obj.edited = True
        self.db.add(note_obj)
        await self.db.flush()
        await self.db.refresh(note_obj)
        return note_obj

    async def soft_delete(self, note_obj: InvestigationNote) -> InvestigationNote:
        note_obj.is_deleted = True
        note_obj.deleted_at = datetime.now(timezone.utc)
        self.db.add(note_obj)
        await self.db.flush()
        return note_obj
