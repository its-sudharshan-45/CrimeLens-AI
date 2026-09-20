"""
backend/app/api/v1/backup.py
============================
Admin-only Backup & Recovery endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.services.backup_service import BackupService

router = APIRouter()


class BackupCreateRequest(BaseModel):
    notes: Optional[str] = Field(default=None, description="Optional description/notes for the backup")


class BackupRestoreRequest(BaseModel):
    confirm: bool = Field(..., description="Explicit boolean confirmation to perform restore")


@router.post("/create", dependencies=[Depends(get_current_active_user)], status_code=status.HTTP_201_CREATED)
async def create_backup(
    payload: Optional[BackupCreateRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Creates a verifiable snapshot of the system database."""
    notes = payload.notes if payload else None
    return await BackupService.create_backup(db=db, user=current_user, notes=notes)


@router.get("/list", dependencies=[Depends(get_current_active_user)])
async def list_backups() -> List[Dict[str, Any]]:
    """Lists all available database backups."""
    return BackupService.list_backups()


@router.get("/{backup_id}", dependencies=[Depends(get_current_active_user)])
async def get_backup_details(backup_id: str) -> Dict[str, Any]:
    """Retrieves metadata and status for a specific backup."""
    backup = BackupService.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found.")
    return backup


@router.post("/{backup_id}/validate", dependencies=[Depends(get_current_active_user)])
async def validate_backup(backup_id: str) -> Dict[str, Any]:
    """Validates the cryptographic integrity of a backup file."""
    result = BackupService.validate_backup(backup_id)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error", "Backup integrity validation failed."))
    return result


@router.post("/{backup_id}/restore", dependencies=[Depends(get_current_active_user)])
async def restore_backup(
    backup_id: str,
    payload: BackupRestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Restores database state from a validated backup. Requires explicit confirm=True."""
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation required.")
    try:
        return await BackupService.restore_backup(
            backup_id=backup_id,
            confirm=payload.confirm,
            db=db,
            user=current_user,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
