from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums.evidence_type import EvidenceType
from app.models.evidence import Evidence
from app.repositories.base_repository import BaseRepository, PaginatedResult

_SORT_COLUMNS: dict = {
    "file_name": Evidence.file_name,
    "file_type": Evidence.file_type,
    "file_size": Evidence.file_size,
    "uploaded_at": Evidence.uploaded_at,
}

_LOAD_OPTIONS = [
    selectinload(Evidence.uploader),
    selectinload(Evidence.report),
]

class EvidenceRepository(BaseRepository[Evidence]):
    """Pure data-access layer for Evidence."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Evidence)

    async def get_by_id_with_relations(self, evidence_id: UUID) -> Optional[Evidence]:
        """Fetch a single non-deleted Evidence with relations loaded."""
        stmt = (
            select(Evidence)
            .options(*_LOAD_OPTIONS)
            .where(
                Evidence.id == evidence_id,
                Evidence.is_deleted.is_(False),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_report_id(
        self,
        report_id: UUID,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "uploaded_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> PaginatedResult[Evidence]:
        """Fetch all evidence linked to a specific crime report."""
        conditions = [
            Evidence.report_id == report_id,
            Evidence.is_deleted.is_(False),
        ]
        
        count_stmt = select(func.count()).select_from(Evidence).where(*conditions)
        total: int = (await self.db.execute(count_stmt)).scalar() or 0

        data_stmt = select(Evidence).options(*_LOAD_OPTIONS).where(*conditions)
        data_stmt = self._apply_sort(data_stmt, _SORT_COLUMNS, sort_by, order)
        data_stmt = self._apply_pagination(data_stmt, page, page_size)

        result = await self.db.execute(data_stmt)
        return PaginatedResult(
            items=list(result.scalars().all()),
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_by_uploader_id(
        self,
        uploader_id: UUID,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "uploaded_at",
        order: Literal["asc", "desc"] = "desc",
    ) -> PaginatedResult[Evidence]:
        """Fetch all evidence uploaded by a specific user."""
        conditions = [
            Evidence.uploaded_by == uploader_id,
            Evidence.is_deleted.is_(False),
        ]
        
        count_stmt = select(func.count()).select_from(Evidence).where(*conditions)
        total: int = (await self.db.execute(count_stmt)).scalar() or 0

        data_stmt = select(Evidence).options(*_LOAD_OPTIONS).where(*conditions)
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
        uploaded_by: UUID,
        file_name: str,
        file_type: EvidenceType,
        mime_type: str,
        file_size: int,
        file_url: str,
        storage_path: str,
        bucket_name: str,
        checksum: Optional[str] = None,
        file_extension: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evidence:
        """Persist a new Evidence record. Does NOT commit."""
        evidence = Evidence(
            report_id=report_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            file_type=file_type,
            mime_type=mime_type,
            file_size=file_size,
            file_url=file_url,
            storage_path=storage_path,
            bucket_name=bucket_name,
            checksum=checksum,
            file_extension=file_extension,
            description=description,
        )
        self.db.add(evidence)
        await self.db.flush()
        await self.db.refresh(evidence)
        return evidence

    async def update(self, evidence: Evidence, update_data: dict) -> Evidence:
        """Apply a partial update dict to an existing Evidence."""
        for key, value in update_data.items():
            if hasattr(evidence, key):
                setattr(evidence, key, value)
        self.db.add(evidence)
        await self.db.flush()
        await self.db.refresh(evidence)
        return evidence

    async def soft_delete(self, evidence: Evidence) -> Evidence:
        """Soft-delete an Evidence record."""
        evidence.is_deleted = True
        evidence.deleted_at = datetime.now(timezone.utc)
        self.db.add(evidence)
        await self.db.flush()
        return evidence
