import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from app.core.enums.investigation_status import InvestigationStatus
from app.core.enums.priority import Priority

if TYPE_CHECKING:
    from .crime_report import CrimeReport
    from .user import User
    from .investigation_assignment import InvestigationAssignment
    from .investigation_note import InvestigationNote
    from .investigation_timeline import InvestigationTimeline

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Investigation(BaseModel):
    __tablename__ = "investigations"

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[InvestigationStatus] = mapped_column(
        SQLEnum(InvestigationStatus),
        default=InvestigationStatus.OPEN,
        nullable=False,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        SQLEnum(Priority), default=Priority.MEDIUM, nullable=False
    )
    
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign Keys
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crime_reports.id"), nullable=False, index=True
    )
    investigator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # Relationships
    report: Mapped["CrimeReport"] = relationship("CrimeReport", back_populates="investigations")
    investigator: Mapped["User"] = relationship("User", back_populates="investigations")
    assignments: Mapped[list["InvestigationAssignment"]] = relationship(
        "InvestigationAssignment",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    notes_list: Mapped[list["InvestigationNote"]] = relationship(
        "InvestigationNote",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    timeline_events: Mapped[list["InvestigationTimeline"]] = relationship(
        "InvestigationTimeline",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
