import logging
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.config import settings
from app.db.supabase import supabase_client

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, supabase: Client = supabase_client):
        self.supabase = supabase
        self.bucket_name = settings.STORAGE_BUCKET_NAME

    def _generate_path(self, crime_report_id: UUID, filename: str) -> str:
        """Generates the folder structure: {crime_report_id}/{filename}"""
        return f"{crime_report_id}/{filename}"

    def upload_file(
        self,
        file_content: bytes,
        crime_report_id: UUID,
        filename: str,
        content_type: str,
    ) -> str:
        """
        Uploads a file to Supabase Storage and returns the storage path.
        """
        path = self._generate_path(crime_report_id, filename)
        try:
            self.supabase.storage.from_(self.bucket_name).upload(
                file=file_content,
                path=path,
                file_options={"content-type": content_type},
            )
            logger.info(f"Successfully uploaded file to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to upload file {filename} to storage: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Storage upload failed."
            ) from e

    def delete_file(self, path: str) -> bool:
        """
        Deletes a file from Supabase Storage.
        """
        try:
            res = self.supabase.storage.from_(self.bucket_name).remove([path])
            if not res:
                logger.warning(
                    f"File at {path} might not exist or failed to delete."
                )
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {path} from storage: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Storage deletion failed."
            ) from e

    def generate_signed_url(self, path: str) -> str:
        """
        Generates a temporary signed URL for securely downloading the evidence.
        """
        try:
            res = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path, 
                settings.SIGNED_URL_EXPIRATION_SECONDS
            )
            signed_url = res.get('signedURL') or res.get('signedUrl')
            if not signed_url:
                raise ValueError("No signed URL returned from Supabase.")
            return signed_url
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to retrieve securely signed download URL."
            ) from e

# Reusable instance
storage_service = StorageService()
