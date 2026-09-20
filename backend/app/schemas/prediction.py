from datetime import datetime
from typing import List, Optional
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


# ─── Phase 5: Deep Learning Prediction API Schemas ─────────────────────────

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


class HotspotItem(BaseModel):
    rank: int = Field(..., description="Rank in order of descending risk")
    city: str = Field(..., description="City name")
    predicted_crimes: float = Field(..., description="Predicted crime activity over forecast period")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Normalized relative risk score [0.0 - 1.0]")
    risk_level: str = Field(..., description="Risk tier: Low, Medium, High")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Empirical confidence/quality indicator")


class HotspotPredictionResponse(BaseModel):
    success: bool = True
    prediction_type: str = "city_hotspot"
    forecast_horizon_days: int = 7
    total_cities_evaluated: Optional[int] = 29
    filter_crime_type: Optional[str] = "All"
    hotspots: List[HotspotItem]
    confidence_metric: Optional[str] = None
    disclaimer: str


class TemporalRiskRequest(BaseModel):
    city: str = Field(..., min_length=2, description="Target city for temporal risk context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "Delhi"
            }
        }
    )


class TemporalForecastDay(BaseModel):
    day: int = Field(..., ge=1, le=7, description="Forecast day index (+1 to +7)")
    predicted_crimes: float = Field(..., description="Predicted crime incident count")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Estimated prediction confidence")
    lower_bound_95: Optional[float] = Field(None, description="Lower bound of 95% empirical prediction interval")
    upper_bound_95: Optional[float] = Field(None, description="Upper bound of 95% empirical prediction interval")


class HistoricalDay(BaseModel):
    day_label: str
    crime_count: float


class TemporalRiskResponse(BaseModel):
    success: bool = True
    prediction_type: str = "temporal_forecast"
    prediction_scope: str = Field(
        ...,
        description="Explicit scope of the model forecast (national aggregate with city-context tracking)"
    )
    target_city: Optional[str] = None
    forecast_horizon_days: int = 7
    forecast: List[TemporalForecastDay]
    historical_context: Optional[List[HistoricalDay]] = None
    uncertainty_method: Optional[str] = None
    disclaimer: str


class InvestigationLeadRequest(BaseModel):
    city: str = Field(..., min_length=2, description="Target city to generate investigative priorities for")
    crime_type: Optional[str] = Field(default="All", description="Focus crime type or 'All'")
    risk_level: Optional[str] = Field(default=None, description="Optional target risk level")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "Delhi",
                "crime_type": "All"
            }
        }
    )


class InvestigationLead(BaseModel):
    priority: int = Field(..., ge=1, description="Ranked priority (1 = highest)")
    category: str = Field(..., description="Investigative category (e.g., CCTV Review, Historical Case Review)")
    description: str = Field(..., description="Specific investigative recommendation")
    reason: str = Field(..., description="Pattern-based reason explaining why this recommendation was generated")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Pattern match confidence score")


class InvestigationLeadResponse(BaseModel):
    success: bool = True
    prediction_type: str = "investigation_leads"
    city: Optional[str] = None
    crime_type: Optional[str] = "All"
    risk_assessment: Optional[str] = None
    leads: List[InvestigationLead]
    disclaimer: str
