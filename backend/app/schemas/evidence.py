from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums.evidence_type import EvidenceType

class EvidenceBase(BaseModel):
    description: Optional[str] = None
    file_name: str
    file_type: EvidenceType
    mime_type: str
    file_size: int
    file_url: str
    storage_path: str
    bucket_name: str
    checksum: Optional[str] = None
    file_extension: Optional[str] = None
    report_id: UUID
    uploaded_by: UUID

class EvidenceCreate(EvidenceBase):
    pass

class EvidenceUpdate(BaseModel):
    description: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[EvidenceType] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    file_url: Optional[str] = None
    storage_path: Optional[str] = None

class EvidenceResponse(EvidenceBase):
    id: UUID
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)
