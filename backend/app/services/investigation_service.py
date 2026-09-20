from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums.investigation_status import InvestigationStatus
from app.core.enums.priority import Priority
from app.models.audit_log import AuditLog
from app.models.investigation import Investigation
from app.models.investigation_assignment import InvestigationAssignment
from app.models.investigation_note import InvestigationNote
from app.models.investigation_timeline import InvestigationTimeline

from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.investigation_assignment_repository import InvestigationAssignmentRepository
from app.repositories.investigation_note_repository import InvestigationNoteRepository
from app.repositories.investigation_timeline_repository import InvestigationTimelineRepository

class InvestigationService:
    def __init__(self):
        # We will instantiate repositories on demand passing the session, or they can be injected.
        # For simplicity within the service, we instantiate them per request.
        pass

    async def _log_audit(
        self, db: AsyncSession, action: str, entity_id: UUID, user_id: UUID, ip_address: str, user_agent: str, details: Optional[dict] = None
    ):
        """Creates an audit log for investigation operations."""
        audit = AuditLog(
            action=action,
            entity_type="INVESTIGATION",
            entity_id=entity_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
        db.add(audit)

    async def _create_timeline_event(
        self, db: AsyncSession, investigation_id: UUID, action: str, description: str, performed_by: UUID, metadata: Optional[dict] = None
    ) -> InvestigationTimeline:
        """Helper to create immutable timeline events."""
        repo = InvestigationTimelineRepository(db)
        return await repo.create(
            investigation_id=investigation_id,
            action=action,
            description=description,
            performed_by=performed_by,
            metadata_json=metadata
        )

    async def _reload_investigation(
        self, db: AsyncSession, investigation_id: UUID
    ) -> Investigation:
        repo = InvestigationRepository(db)
        investigation = await repo.get_by_id_with_relations(investigation_id)
        if investigation is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        return investigation

    async def create_investigation(
        self, db: AsyncSession, report_id: UUID, investigator_id: UUID, priority: Priority, 
        user_id: UUID, ip_address: str, user_agent: str, notes: Optional[str] = None
    ) -> Investigation:
        """Create a new investigation. Cannot duplicate for same report."""
        repo = InvestigationRepository(db)
        
        # In a real system, we'd check if an investigation already exists for this report
        # if await repo.exists_by_report(report_id): raise HTTPException(...)

        try:
            investigation = await repo.create(
                report_id=report_id,
                investigator_id=investigator_id,
                status=InvestigationStatus.OPEN,
                priority=priority,
                notes=notes
            )
            
            # Initial Assignment
            assignment_repo = InvestigationAssignmentRepository(db)
            await assignment_repo.create(investigation.id, investigator_id, assigned_by=user_id)
            
            # Timeline & Audit
            await self._create_timeline_event(db, investigation.id, "Investigation Created", f"Investigation started with Priority: {priority.value}", user_id)
            await self._create_timeline_event(db, investigation.id, "Officer Assigned", f"Assigned to {investigator_id}", user_id)
            
            await self._log_audit(db, "CREATE", investigation.id, user_id, ip_address, user_agent, {"report_id": str(report_id)})
            
            await db.commit()
            return await self._reload_investigation(db, investigation.id)
        except Exception:
            await db.rollback()
            raise

    async def assign_investigator(
        self, db: AsyncSession, investigation_id: UUID, new_investigator_id: UUID, user_id: UUID, ip_address: str, user_agent: str
    ) -> Investigation:
        """Assign or Reassign an investigator."""
        repo = InvestigationRepository(db)
        assign_repo = InvestigationAssignmentRepository(db)
        
        investigation = await repo.get_by_id(investigation_id)
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
        
        self._check_modifiable(investigation)

        try:
            active_assignment = await assign_repo.get_active_assignment(investigation_id)
            
            if active_assignment and active_assignment.investigator_id == new_investigator_id:
                raise HTTPException(status_code=400, detail="Investigator is already assigned to this case")

            action_str = "Officer Assigned"
            if active_assignment:
                action_str = "Officer Reassigned"
                await assign_repo.deactivate_assignment(active_assignment)

            await assign_repo.create(investigation_id, new_investigator_id, assigned_by=user_id)
            
            # Sync main record
            investigation.investigator_id = new_investigator_id
            if investigation.status == InvestigationStatus.OPEN:
                investigation.status = InvestigationStatus.UNDER_INVESTIGATION
                await self._create_timeline_event(db, investigation.id, "Status Updated", f"Status changed to UNDER_INVESTIGATION", user_id)

            await repo.update(investigation, {})
            
            await self._create_timeline_event(db, investigation.id, action_str, f"Assigned to {new_investigator_id}", user_id)
            await self._log_audit(db, "ASSIGNMENT", investigation.id, user_id, ip_address, user_agent, {"new_investigator_id": str(new_investigator_id)})
            
            await db.commit()
            return await self._reload_investigation(db, investigation.id)
        except HTTPException:
            await db.rollback()
            raise
        except Exception:
            await db.rollback()
            raise

    def _check_modifiable(self, investigation: Investigation):
        """Archived or Closed investigations are read-only (mostly)."""
        if investigation.status == InvestigationStatus.ARCHIVED:
            raise HTTPException(status_code=400, detail="Cannot modify an archived investigation")
        if investigation.status == InvestigationStatus.CLOSED:
            raise HTTPException(status_code=400, detail="Cannot modify a closed investigation except to archive")

    async def update_status(
        self, db: AsyncSession, investigation_id: UUID, new_status: InvestigationStatus, user_id: UUID, ip_address: str, user_agent: str
    ) -> Investigation:
        """Strict workflow state transitions."""
        repo = InvestigationRepository(db)
        investigation = await repo.get_by_id(investigation_id)
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")

        old_status = investigation.status
        
        if old_status == InvestigationStatus.ARCHIVED:
            raise HTTPException(status_code=400, detail="Archived investigations are read-only")
        
        # Valid Transitions logic based on requirements
        valid_transitions = {
            InvestigationStatus.OPEN: [InvestigationStatus.UNDER_INVESTIGATION],
            InvestigationStatus.UNDER_INVESTIGATION: [
                InvestigationStatus.WAITING_FOR_EVIDENCE, 
                InvestigationStatus.ON_HOLD, 
                InvestigationStatus.CLOSED
            ],
            InvestigationStatus.WAITING_FOR_EVIDENCE: [InvestigationStatus.UNDER_INVESTIGATION],
            InvestigationStatus.ON_HOLD: [InvestigationStatus.UNDER_INVESTIGATION],
            InvestigationStatus.CLOSED: [InvestigationStatus.ARCHIVED]
        }

        allowed = valid_transitions.get(old_status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status transition from {old_status} to {new_status}"
            )

        try:
            investigation.status = new_status
            if new_status == InvestigationStatus.CLOSED:
                investigation.closed_at = datetime.now(timezone.utc)
            
            await repo.update(investigation, {})
            
            await self._create_timeline_event(db, investigation.id, "Status Updated", f"Status changed from {old_status} to {new_status}", user_id)
            await self._log_audit(db, "STATUS_CHANGE", investigation.id, user_id, ip_address, user_agent, {"old_status": old_status, "new_status": new_status})
            
            await db.commit()
            return await self._reload_investigation(db, investigation.id)
        except Exception:
            await db.rollback()
            raise

    async def add_note(
        self, db: AsyncSession, investigation_id: UUID, note_text: str, user_id: UUID, ip_address: str, user_agent: str, attachment_evidence_id: Optional[UUID] = None
    ) -> InvestigationNote:
        inv_repo = InvestigationRepository(db)
        note_repo = InvestigationNoteRepository(db)
        
        investigation = await inv_repo.get_by_id(investigation_id)
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
        self._check_modifiable(investigation)

        try:
            note = await note_repo.create(investigation_id, user_id, note_text, attachment_evidence_id)
            
            await self._create_timeline_event(db, investigation_id, "Notes Added", "A new collaborative note was added", user_id)
            await self._log_audit(db, "NOTE_ADDED", investigation_id, user_id, ip_address, user_agent, {"note_id": str(note.id)})
            
            await db.commit()
            return await note_repo.get_by_id_with_author(note.id) or note
        except Exception:
            await db.rollback()
            raise

    async def edit_note(
        self, db: AsyncSession, note_id: UUID, new_text: str, user_id: UUID, ip_address: str, user_agent: str
    ) -> InvestigationNote:
        note_repo = InvestigationNoteRepository(db)
        inv_repo = InvestigationRepository(db)
        
        note = await note_repo.get_by_id(note_id)
        if not note or note.is_deleted:
            raise HTTPException(status_code=404, detail="Note not found")
        
        if note.author_id != user_id:
            raise HTTPException(status_code=403, detail="Can only edit your own notes")

        investigation = await inv_repo.get_by_id(note.investigation_id)
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
        self._check_modifiable(investigation)

        try:
            await note_repo.update(note, new_text)
            
            await self._create_timeline_event(db, note.investigation_id, "Notes Edited", "An existing note was modified", user_id)
            await self._log_audit(db, "NOTE_EDITED", note.investigation_id, user_id, ip_address, user_agent, {"note_id": str(note.id)})
            
            await db.commit()
            reloaded = await note_repo.get_by_id_with_author(note.id)
            return reloaded or note
        except Exception:
            await db.rollback()
            raise

investigation_service = InvestigationService()
