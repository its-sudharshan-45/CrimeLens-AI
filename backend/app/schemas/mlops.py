from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ModelVersionInfo(BaseModel):
    model_name: str
    version: str
    training_date: Optional[str] = None
    dataset_hash: str = "N/A"
    dataset_version: Optional[str] = None
    framework_version: str
    accuracy_metrics: dict[str, float] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    status: Literal["Active", "Archived"]
    artifact_path: Optional[str] = None


class ModelListResponse(BaseModel):
    models: list[ModelVersionInfo]
    count: int


class ModelSwitchRequest(BaseModel):
    version: str
    rollback: bool = False


class AnalyticsSummary(BaseModel):
    total_predictions: int
    predictions_today: int
    predictions_this_month: int
    average_confidence: float
    average_inference_latency_ms: float
    most_predicted_crime_domain: Optional[str] = None
    human_review_count: int
    low_confidence_count: int


class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummary
    prediction_distribution: dict[str, int]
    model_usage: list[dict[str, Any]]
    top_confidence_predictions: list[dict[str, Any]]
    low_confidence_predictions: list[dict[str, Any]]
    daily_prediction_trend: list[dict[str, Any]]
    monthly_prediction_trend: list[dict[str, Any]]
    charts: dict[str, Any]


class DriftComponent(BaseModel):
    score: float
    level: Literal["LOW", "MEDIUM", "HIGH"]
    affected_features: list[str] = Field(default_factory=list)


class DriftStatusResponse(BaseModel):
    drift_score: float
    overall_level: Literal["LOW", "MEDIUM", "HIGH"]
    feature_drift: DriftComponent
    confidence_drift: dict[str, Any]
    prediction_distribution_drift: dict[str, Any]
    sample_size: int
    warnings: list[str]
    timestamp: datetime


class DriftReportResponse(BaseModel):
    drift_score: float
    drift_level: Literal["LOW", "MEDIUM", "HIGH"]
    drift_type: list[str]
    affected_features: list[str]
    recommendation: str
    warnings: list[str]
    timestamp: datetime
    details: dict[str, Any]


class SystemStatusResponse(BaseModel):
    api_status: str
    database_status: str
    database_detail: str
    supabase_status: str
    supabase_detail: str
    model_status: str
    model_errors: list[str]
    registry_status: str
    registry_detail: str
    active_version: Optional[str] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    uptime_seconds: float
    project_root: str
