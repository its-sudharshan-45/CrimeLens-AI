from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums.prediction_type import PredictionType

# ─── Database Entity Schemas (Phase 4 / Core) ──────────────────────────────

class PredictionBase(BaseModel):
    prediction_label: str
    prediction_type: PredictionType
    confidence_score: float
    model_name: str
    model_version: str
    execution_time_ms: int
    explanation: Optional[str] = None
    raw_output: dict
    report_id: Optional[UUID] = None

class PredictionCreate(PredictionBase):
    pass

class PredictionUpdate(BaseModel):
    prediction_label: Optional[str] = None
    confidence_score: Optional[float] = None
    explanation: Optional[str] = None

class PredictionResponse(PredictionBase):
    id: UUID
    prediction_time: datetime
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


# ─── Phase 5: Deprecated Hotspot request schema ────────────────────────────
# NOTE (2026-10-16): The CNN hotspot producer was removed (tabular data, not
# images). This request schema is retained only so the deprecated
# POST /predict/hotspots endpoint still validates its payload before returning
# HTTP 410 Gone. Historical HOTSPOT records remain queryable via /predict/history.

class HotspotPredictionRequest(BaseModel):
    top_n: int = Field(
        default=5,
        ge=1,
        le=29,
        description="Number of top risk cities to return (1 to 29)"
    )
    crime_type: Optional[str] = Field(
        default="All",
        description="Optional filter for crime category"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "top_n": 5,
                "crime_type": "All"
            }
        }
    )
