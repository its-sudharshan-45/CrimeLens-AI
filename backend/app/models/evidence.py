import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from app.core.enums.evidence_type import EvidenceType

if TYPE_CHECKING:
    from .crime_report import CrimeReport
    from .user import User

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Evidence(BaseModel):
    __tablename__ = "evidence"

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[EvidenceType] = mapped_column(SQLEnum(EvidenceType), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    bucket_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="evidence"
    )
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    file_extension: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Foreign Keys
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crime_reports.id"), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Relationships
    report: Mapped["CrimeReport"] = relationship("CrimeReport", back_populates="evidence")
    uploader: Mapped["User"] = relationship("User", back_populates="uploaded_evidence")
