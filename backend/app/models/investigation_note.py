from typing import Optional, TYPE_CHECKING
import uuid
from sqlalchemy import Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .investigation import Investigation
    from .user import User
    from .evidence import Evidence

class InvestigationNote(BaseModel):
    __tablename__ = "investigation_notes"

    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    note: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("evidence.id"), nullable=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="notes_list")
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id])
    attachment: Mapped[Optional["Evidence"]] = relationship("Evidence", foreign_keys=[attachment_evidence_id])
