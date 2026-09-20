import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from app.core.enums.prediction_type import PredictionType

if TYPE_CHECKING:
    from .crime_report import CrimeReport


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


JSONType = JSON().with_variant(JSONB, "postgresql")

class Prediction(BaseModel):
    __tablename__ = "predictions"

    prediction_label: Mapped[str] = mapped_column(String(255), nullable=False)
    prediction_type: Mapped[PredictionType] = mapped_column(SQLEnum(PredictionType), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    prediction_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    
    explanation: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    raw_output: Mapped[dict] = mapped_column(JSONType, nullable=False)

    # Foreign Keys
    report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("crime_reports.id"), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    report: Mapped[Optional["CrimeReport"]] = relationship("CrimeReport", back_populates="predictions")
