from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums.investigation_status import InvestigationStatus
from app.core.enums.priority import Priority

# ---------------------------------------------------------
# Nested / Base Schemas
# ---------------------------------------------------------

class UserRef(BaseModel):
    id: UUID
    full_name: str

    model_config = ConfigDict(from_attributes=True)

class ReportRef(BaseModel):
    id: UUID
    title: str

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# Investigation
# ---------------------------------------------------------

class InvestigationCreate(BaseModel):
    report_id: UUID
    investigator_id: UUID
    priority: Priority = Priority.MEDIUM
    notes: Optional[str] = None

class InvestigationStatusUpdate(BaseModel):
    status: InvestigationStatus

class InvestigationAssign(BaseModel):
    investigator_id: UUID

class InvestigationResponse(BaseModel):
    id: UUID
    report_id: UUID
    investigator_id: UUID
    status: InvestigationStatus
    priority: Priority
    notes: Optional[str]
    assigned_at: datetime
    closed_at: Optional[datetime]
    resolution_summary: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    report: Optional[ReportRef] = None
    investigator: Optional[UserRef] = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# Paginated Investigation
# ---------------------------------------------------------

class PaginatedInvestigations(BaseModel):
    items: List[InvestigationResponse]
    total: int
    page: int
    page_size: int

# ---------------------------------------------------------
# Investigation Note
# ---------------------------------------------------------

class InvestigationNoteCreate(BaseModel):
    note: str
    attachment_evidence_id: Optional[UUID] = None

class InvestigationNoteUpdate(BaseModel):
    note: str

class InvestigationNoteResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    author_id: UUID
    note: str
    attachment_evidence_id: Optional[UUID]
    edited: bool
    created_at: datetime
    updated_at: datetime

    author: Optional[UserRef] = None

    model_config = ConfigDict(from_attributes=True)

class PaginatedInvestigationNotes(BaseModel):
    items: List[InvestigationNoteResponse]
    total: int
    page: int
    page_size: int

# ---------------------------------------------------------
# Investigation Timeline
# ---------------------------------------------------------

class InvestigationTimelineResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    action: str
    description: str
    performed_by: Optional[UUID]
    metadata_json: Optional[dict] = Field(default=None, serialization_alias="metadata")
    created_at: datetime

    user: Optional[UserRef] = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# Investigation Assignment
# ---------------------------------------------------------

class InvestigationAssignmentResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    investigator_id: UUID
    assigned_by: UUID
    assigned_at: datetime
    unassigned_at: Optional[datetime]
    reason: Optional[str]
    is_active: bool

    investigator: Optional[UserRef] = None
    assigner: Optional[UserRef] = None

    model_config = ConfigDict(from_attributes=True)
