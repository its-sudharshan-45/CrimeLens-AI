import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from app.core.enums.crime_status import CrimeStatus
from app.core.enums.priority import Priority

if TYPE_CHECKING:
    from .user import User
    from .crime_category import CrimeCategory
    from .crime_location import CrimeLocation
    from .evidence import Evidence
    from .investigation import Investigation
    from .prediction import Prediction

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class CrimeReport(BaseModel):
    __tablename__ = "crime_reports"

    # Human-readable CR number (e.g., CR-2026-000001)
    crime_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    incident_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    report_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    
    status: Mapped[CrimeStatus] = mapped_column(
        SQLEnum(CrimeStatus), default=CrimeStatus.OPEN, nullable=False
    )
    priority: Mapped[Priority] = mapped_column(
        SQLEnum(Priority), default=Priority.MEDIUM, nullable=False
    )
    
    victim_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    suspect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_loss: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Foreign Keys
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crime_categories.id"), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crime_locations.id"), nullable=False)

    # Relationships
    reporter: Mapped["User"] = relationship("User", back_populates="reported_crimes")
    category: Mapped["CrimeCategory"] = relationship("CrimeCategory", back_populates="reports")
    location: Mapped["CrimeLocation"] = relationship("CrimeLocation", back_populates="reports")
    
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="report", cascade="all, delete-orphan"
    )
    investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation", back_populates="report", cascade="all, delete-orphan"
    )
    predictions: Mapped[List["Prediction"]] = relationship(
        "Prediction", back_populates="report", cascade="all, delete-orphan"
    )
