import hashlib
import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums.evidence_type import EvidenceType
from app.models.audit_log import AuditLog
from app.models.evidence import Evidence
from app.repositories.evidence_repository import EvidenceRepository
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

class EvidenceService:
    def __init__(self, repository: EvidenceRepository):
        self.repository = repository

    def _determine_evidence_type(self, mime_type: str) -> EvidenceType:
        if mime_type.startswith("image/"):
            return EvidenceType.IMAGE
        if mime_type.startswith("video/"):
            return EvidenceType.VIDEO
        if mime_type == "application/pdf":
            return EvidenceType.DOCUMENT
        if mime_type.startswith("audio/"):
            return EvidenceType.AUDIO
        return EvidenceType.OTHER

    def _validate_file(self, filename: str, mime_type: str, file_size: int):
        # 1. Reject unknown or empty MIME types
        if not mime_type or mime_type == "application/octet-stream":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unknown MIME types are not allowed."
            )

        # 2. Validate Allowed MIME types
        if mime_type not in settings.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Unsupported file type. Allowed types: "
                    f"{', '.join(settings.ALLOWED_MIME_TYPES)}"
                ),
            )
            
        # 3. Maximum file size validation
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_mb}MB."
            )
            
        # 4. Prevent directory traversal
        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename."
            )
            
        # 5. Reject Executable files, Scripts, Archives based on extension
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        rejected_extensions = {
            # Executables & Scripts
            "exe", "sh", "bat", "cmd", "js", "php", "py", "vbs", "msi",
            # Archives
            "zip", "rar", "tar", "gz", "7z", "bz2"
        }
        if ext in rejected_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Executable files, scripts, and archives are strictly prohibited."
            )

    async def _log_audit(
        self,
        db: AsyncSession,
        action: str,
        entity_id: UUID,
        report_id: UUID,
        user_id: UUID,
        ip_address: str,
        user_agent: str,
        details: Optional[dict] = None,
    ):
        log_details = details or {}
        log_details["crime_report_id"] = str(report_id)
        
        audit = AuditLog(
            action=action,
            entity_type="EVIDENCE",
            entity_id=entity_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=log_details
        )
        db.add(audit)

    async def upload_evidence(
        self,
        db: AsyncSession,
        file_content: bytes,
        filename: str,
        content_type: str,
        file_size: int,
        report_id: UUID,
        uploader_id: UUID,
        ip_address: str,
        user_agent: str,
        description: Optional[str] = None
    ) -> Evidence:
        """Uploads evidence, saves to db, and logs audit."""
        self._validate_file(filename, content_type, file_size)

        evidence_type = self._determine_evidence_type(content_type)
        file_extension = filename.split(".")[-1].lower() if "." in filename else None
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # 1. Upload to Storage
        storage_path = storage_service.upload_file(
            file_content, report_id, filename, content_type
        )

        try:
            # 2. Persist to DB
            evidence = await self.repository.create(
                report_id=report_id,
                uploaded_by=uploader_id,
                file_name=filename,
                file_type=evidence_type,
                mime_type=content_type,
                file_size=file_size,
                file_url=storage_path,  # Use signed URLs on demand
                storage_path=storage_path,
                bucket_name=settings.STORAGE_BUCKET_NAME,
                checksum=checksum,
                file_extension=file_extension,
                description=description
            )
            
            # 3. Create Audit Log
            await self._log_audit(
                db=db,
                action="UPLOAD",
                entity_id=evidence.id,
                report_id=evidence.report_id,
                user_id=uploader_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"filename": filename, "size": file_size},
            )
            
            await db.commit()
            return evidence
        except Exception as e:
            await db.rollback()
            # Compensating transaction to remove orphaned storage file
            storage_service.delete_file(storage_path)
            logger.error(
                f"Failed to persist evidence to DB, rolled back storage: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail="Database transaction failed during upload.",
            ) from e

    async def generate_download_url(
        self,
        db: AsyncSession,
        evidence_id: UUID,
        user_id: UUID,
        ip_address: str,
        user_agent: str,
    ) -> str:
        """Retrieves a secure signed URL for downloading evidence."""
        evidence = await self.repository.get_by_id_with_relations(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")

        signed_url = storage_service.generate_signed_url(evidence.storage_path)
        
        await self._log_audit(
            db=db,
            action="GENERATE_DOWNLOAD_URL",
            entity_id=evidence.id,
            report_id=evidence.report_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()
        return signed_url

    async def delete_evidence(
        self,
        db: AsyncSession,
        evidence_id: UUID,
        user_id: UUID,
        ip_address: str,
        user_agent: str,
    ):
        """Soft deletes evidence from database and removes from storage."""
        evidence = await self.repository.get_by_id_with_relations(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
        
        await self.repository.soft_delete(evidence)
        
        # We will also delete it from storage for security and space saving, 
        # though the database record remains soft-deleted.
        storage_service.delete_file(evidence.storage_path)

        await self._log_audit(
            db=db,
            action="DELETE",
            entity_id=evidence.id,
            report_id=evidence.report_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()
        return True

    async def update_evidence(
        self,
        db: AsyncSession,
        evidence_id: UUID,
        user_id: UUID,
        ip_address: str,
        user_agent: str,
        update_data: dict,
    ) -> Evidence:
        """Updates metadata of the evidence."""
        evidence = await self.repository.get_by_id_with_relations(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
            
        evidence = await self.repository.update(evidence, update_data)
        
        await self._log_audit(
            db=db,
            action="UPDATE",
            entity_id=evidence.id,
            report_id=evidence.report_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=update_data,
        )
        await db.commit()
        return evidence
