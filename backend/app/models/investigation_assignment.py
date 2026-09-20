from typing import Optional, TYPE_CHECKING
import uuid
from datetime import datetime, timezone
from sqlalchemy import Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .investigation import Investigation
    from .user import User

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class InvestigationAssignment(BaseModel):
    __tablename__ = "investigation_assignments"

    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    investigator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    unassigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Relationships
    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="assignments")
    investigator: Mapped["User"] = relationship("User", foreign_keys=[investigator_id])
    assigner: Mapped["User"] = relationship("User", foreign_keys=[assigned_by])
