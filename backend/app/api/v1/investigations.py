from datetime import datetime
from typing import List, Optional, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_active_user
from app.core.enums.investigation_status import InvestigationStatus
from app.core.enums.priority import Priority
from app.models.user import User
from app.schemas.investigation import (
    InvestigationAssign,
    InvestigationCreate,
    InvestigationNoteCreate,
    InvestigationNoteResponse,
    InvestigationNoteUpdate,
    InvestigationResponse,
    InvestigationStatusUpdate,
    InvestigationTimelineResponse,
    PaginatedInvestigationNotes,
    PaginatedInvestigations,
)
from app.services.investigation_service import investigation_service
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.investigation_note_repository import InvestigationNoteRepository
from app.repositories.investigation_timeline_repository import InvestigationTimelineRepository

router = APIRouter()

def get_ip_and_agent(request: Request):
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return ip_address, user_agent

@router.post("", response_model=InvestigationResponse, dependencies=[Depends(get_current_active_user)])
async def create_investigation(
    investigation_in: InvestigationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.create_investigation(
        db=db,
        report_id=investigation_in.report_id,
        investigator_id=investigation_in.investigator_id,
        priority=investigation_in.priority,
        user_id=current_user.id,
        ip_address=ip,
        user_agent=user_agent,
        notes=investigation_in.notes
    )

@router.get("", response_model=PaginatedInvestigations, dependencies=[Depends(get_current_active_user)])
async def list_investigations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = None,
    sort_by: str = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
    status: Optional[InvestigationStatus] = None,
    priority: Optional[Priority] = None,
    investigator_id: Optional[UUID] = None,
    report_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    repo = InvestigationRepository(db)
    return await repo.get_all(
        page=page, page_size=page_size, q=q, sort_by=sort_by, order=order,
        status=status, priority=priority, investigator_id=investigator_id,
        report_id=report_id, date_from=date_from, date_to=date_to
    )

@router.get("/{investigation_id}", response_model=InvestigationResponse, dependencies=[Depends(get_current_active_user)])
async def get_investigation(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = InvestigationRepository(db)
    inv = await repo.get_by_id_with_relations(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv

@router.post("/{investigation_id}/assign", response_model=InvestigationResponse, dependencies=[Depends(get_current_active_user)])
async def assign_investigator(
    investigation_id: UUID,
    assign_in: InvestigationAssign,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.assign_investigator(
        db, investigation_id, assign_in.investigator_id, current_user.id, ip, user_agent
    )

@router.post("/{investigation_id}/transfer", response_model=InvestigationResponse, dependencies=[Depends(get_current_active_user)])
async def transfer_investigator(
    investigation_id: UUID,
    assign_in: InvestigationAssign,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Transfer is functionally identical to assign in our robust service which deactivates active assignments
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.assign_investigator(
        db, investigation_id, assign_in.investigator_id, current_user.id, ip, user_agent
    )

@router.patch("/{investigation_id}/status", response_model=InvestigationResponse, dependencies=[Depends(get_current_active_user)])
async def update_status(
    investigation_id: UUID,
    status_in: InvestigationStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.update_status(
        db, investigation_id, status_in.status, current_user.id, ip, user_agent
    )

@router.post("/{investigation_id}/close", response_model=InvestigationResponse, dependencies=[Depends(get_current_active_user)])
async def close_investigation(
    investigation_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.update_status(
        db, investigation_id, InvestigationStatus.CLOSED, current_user.id, ip, user_agent
    )

@router.post("/{investigation_id}/archive", response_model=InvestigationResponse, dependencies=[Depends(get_current_active_user)])
async def archive_investigation(
    investigation_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.update_status(
        db, investigation_id, InvestigationStatus.ARCHIVED, current_user.id, ip, user_agent
    )

@router.get("/{investigation_id}/timeline", response_model=List[InvestigationTimelineResponse], dependencies=[Depends(get_current_active_user)])
async def get_timeline(
    investigation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = InvestigationTimelineRepository(db)
    return await repo.get_by_investigation(investigation_id)

@router.get("/{investigation_id}/notes", response_model=PaginatedInvestigationNotes, dependencies=[Depends(get_current_active_user)])
async def get_notes(
    investigation_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    repo = InvestigationNoteRepository(db)
    return await repo.get_by_investigation(investigation_id, page, page_size)

@router.post("/{investigation_id}/notes", response_model=InvestigationNoteResponse, dependencies=[Depends(get_current_active_user)])
async def add_note(
    investigation_id: UUID,
    note_in: InvestigationNoteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.add_note(
        db, investigation_id, note_in.note, current_user.id, ip, user_agent, note_in.attachment_evidence_id
    )

@router.patch("/notes/{note_id}", response_model=InvestigationNoteResponse, dependencies=[Depends(get_current_active_user)])
async def edit_note(
    note_id: UUID,
    note_in: InvestigationNoteUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    ip, user_agent = get_ip_and_agent(request)
    return await investigation_service.edit_note(
        db, note_id, note_in.note, current_user.id, ip, user_agent
    )
