import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .audit_log import AuditLog
    from .crime_report import CrimeReport
    from .evidence import Evidence
    from .investigation import Investigation

class User(BaseModel):
    __tablename__ = "users"

    supabase_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    badge_number: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, index=True, nullable=True
    )
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    reported_crimes: Mapped[List["CrimeReport"]] = relationship(
        "CrimeReport", back_populates="reporter"
    )
    uploaded_evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="uploader"
    )
    investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation", back_populates="investigator"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )
