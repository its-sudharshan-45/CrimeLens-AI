from typing import Optional, TYPE_CHECKING
import uuid
from sqlalchemy import Text, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .investigation import Investigation
    from .user import User

class InvestigationTimeline(BaseModel):
    __tablename__ = "investigation_timeline"

    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="timeline_events")
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[performed_by])
