"""
backend/app/schemas/ai.py
=========================
Pydantic schemas for the CrimeLens AI forecasting API.

Only one model is exposed: ``CrimeGRUForecaster`` (7-day crime-count forecast per
scope).  The previous classification / N-BEATS / embedding schemas were removed
with their endpoints.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScopeInfo(BaseModel):
    """A selectable forecasting scope (a city or a crime type)."""

    key: str = Field(..., description="Stored scope key, e.g. 'city:Delhi'")
    scope_type: Literal["city", "crime_type"]
    display_name: str


class ScopeListResponse(BaseModel):
    scopes: List[ScopeInfo]
    count: int


class ForecastRequest(BaseModel):
    """Request a 7-day forecast for a supported scope."""

    scope_type: Literal["city", "crime_type"] = Field(..., description="'city' or 'crime_type'")
    scope_value: str = Field(..., min_length=1, description="City name or crime description, e.g. 'Delhi' or 'BURGLARY'")

    model_config = ConfigDict(
        json_schema_extra={"example": {"scope_type": "city", "scope_value": "Delhi"}}
    )


class HistoricalPoint(BaseModel):
    date: str
    count: float


class ForecastDay(BaseModel):
    day: int = Field(..., ge=1, description="Forecast step (1 = next day)")
    date: str = Field(..., description="Calendar date of the forecast")
    predicted_count: float = Field(..., ge=0.0, description="Model-predicted daily crime count")
    lower_bound_95: float = Field(..., ge=0.0)
    upper_bound_95: float = Field(..., ge=0.0)


class ActualVsPredictedPoint(BaseModel):
    date: str
    actual: float
    predicted: float


class ForecastResponse(BaseModel):
    """Full forecast payload: history, seven forecast values, backtest and metrics."""

    success: bool = True
    scope_key: str
    scope_type: str
    scope_display_name: str
    model_name: str = "CrimeGRUForecaster"
    model_version: str
    sequence_length: int
    forecast_horizon_days: int
    last_observed_date: str
    historical: List[HistoricalPoint]
    forecast: List[ForecastDay]
    actual_vs_predicted: List[ActualVsPredictedPoint] = Field(default_factory=list)
    scope_test_metrics: Dict[str, Any] = Field(default_factory=dict)
    test_metrics: Dict[str, Any] = Field(default_factory=dict)
    per_horizon_metrics: Dict[str, Any] = Field(default_factory=dict)
    evaluation_summary: Dict[str, Any] = Field(default_factory=dict)
    uncertainty_method: Optional[str] = None
    disclaimer: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DistrictLocation(BaseModel):
    """A selectable district backed by one city-level model scope."""

    district: str = Field(..., description="Display name shown in the District dropdown")
    city: str = Field(..., description="City value used by the trained model, e.g. 'Delhi'")
    scope_key: str = Field(..., description="Model scope key, e.g. 'city:Delhi'")


class StateLocations(BaseModel):
    state: str
    districts: List[DistrictLocation]


class LocationCatalogResponse(BaseModel):
    """State -> district catalog derived from the dataset and model scopes."""

    states: List[StateLocations]
    district_count: int
    state_count: int


class RiskPredictionRequest(BaseModel):
    """Select a state and district; the backend resolves the model scope."""

    state: str = Field(..., min_length=1, max_length=100, description="Indian state, e.g. 'Delhi'")
    district: str = Field(..., min_length=1, max_length=100, description="District label, e.g. 'New Delhi'")

    @field_validator("state", "district")
    @classmethod
    def strip_and_require(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    model_config = ConfigDict(
        json_schema_extra={"example": {"state": "Delhi", "district": "New Delhi"}}
    )


class RiskPredictionResponse(BaseModel):
    """District risk result derived from a genuine GRU forecast."""

    success: bool = True
    state: str
    district: str
    city: str
    scope_key: str
    risk_percentage: float = Field(..., ge=0.0, le=100.0)
    risk_category: Literal["Low", "Medium", "High"]
    risk_lower_bound: float = Field(..., ge=0.0, le=100.0)
    risk_upper_bound: float = Field(..., ge=0.0, le=100.0)
    risk_method: str
    predicted_daily_average: float = Field(..., ge=0.0)
    predicted_7_day_total: float = Field(..., ge=0.0)
    prediction_interval_95: Dict[str, float]
    peak_predicted_daily_average: float = Field(..., ge=0.0)
    district_rank: Optional[int] = None
    district_count: int = Field(..., ge=0)
    historical_incidents: int = Field(..., ge=0)
    historical_daily_average: float = Field(..., ge=0.0)
    last_observed_date: str
    model_name: str = "CrimeGRUForecaster"
    model_version: str
    model_test_metrics: Dict[str, Any] = Field(default_factory=dict)
    persistence_test_metrics: Dict[str, Any] = Field(default_factory=dict)
    forecast: List[ForecastDay]
    uncertainty_method: Optional[str] = None
    disclaimer: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelHealthResponse(BaseModel):
    status: str
    model_name: str = "CrimeGRUForecaster"
    loaded: bool
    device: str = "cpu"
    registry_dir: Optional[str] = None
    n_scopes: int = 0
    error: Optional[str] = None


class ModelMetadataResponse(BaseModel):
    version: str
    primary_model: str = "CrimeGRUForecaster"
    framework: Optional[str] = None
    device: Optional[str] = None
    seed: Optional[int] = None
    seq_len: Optional[int] = None
    forecast_horizon: Optional[int] = None
    n_features: Optional[int] = None
    n_scopes: Optional[int] = None
    dataset_rows: Optional[int] = None
    dataset_hash_md5: Optional[str] = None
    test_mae: Optional[float] = None
    test_rmse: Optional[float] = None
    test_wape: Optional[float] = None
    persistence_mae: Optional[float] = None
    saved_at: Optional[str] = None
