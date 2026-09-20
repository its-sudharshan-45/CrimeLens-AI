"""
backend/app/schemas/ai.py
=========================
Pydantic Schemas for CrimeLens AI Deep Learning API Endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timezone


class CrimePredictionRequest(BaseModel):
    """Payload for real-time crime domain classification."""
    city: str = Field(..., description="City name")
    crime_description: str = Field(..., description="Crime description code")
    victim_age: int = Field(..., ge=0, le=120, description="Victim age")
    victim_gender: str = Field(..., description="Victim gender M/F")
    weapon_used: Optional[str] = Field(default="Unknown", description="Weapon used")
    date_of_occurrence: str = Field(..., description="Date of occurrence dd-mm-yyyy HH:MM")
    time_of_occurrence: str = Field(..., description="Time of occurrence dd-mm-yyyy HH:MM")
    date_reported: Optional[str] = Field(default=None, description="Date reported dd-mm-yyyy HH:MM")
    case_closed: Optional[str] = Field(default="No", description="Whether case is closed")
    crime_code: Optional[int] = Field(default=100, description="Crime code number")

    model_config = ConfigDict(from_attributes=True)


class CrimePredictionResponse(BaseModel):
    """Response payload for crime domain classification."""
    prediction_id: Optional[str] = Field(default=None, description="Prediction UUID")
    predicted_domain: str = Field(..., description="Predicted crime domain")
    domain_code: int = Field(..., description="Domain class index")
    confidence_score: float = Field(..., description="Top-1 confidence score")
    probabilities: Dict[str, float] = Field(..., description="Per-class probabilities")
    model_name: str = Field(..., description="Model class name")
    model_version: str = Field(..., description="Model version string")
    execution_time_ms: int = Field(..., description="Inference latency in ms")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ForecastRequest(BaseModel):
    """Payload for multi-horizon sequence forecasting."""
    horizon: int = Field(default=7, description="Forecast horizon in days (7, 30, or 90)")
    recent_sequence: Optional[List[float]] = Field(default=None, description="Optional 30-day historical daily counts")

    model_config = ConfigDict(from_attributes=True)


class ForecastResponse(BaseModel):
    """Response payload for time series forecasting."""
    horizon: int = Field(..., description="Forecast horizon in days")
    forecast_dates: List[str] = Field(..., description="ISO date strings for forecast window")
    predicted_counts: List[float] = Field(..., description="Predicted daily crime counts")
    total_projected_incidents: float = Field(..., description="Sum of predicted counts")
    model_name: str = Field(..., description="Forecaster model class name")
    model_version: str = Field(..., description="Model version string")
    execution_time_ms: int = Field(..., description="Inference latency in ms")

    model_config = ConfigDict(from_attributes=True)


class EmbeddingRequest(BaseModel):
    """Payload for dense vector embedding generation."""
    sample_record: CrimePredictionRequest

    model_config = ConfigDict(from_attributes=True)


class EmbeddingResponse(BaseModel):
    """Response payload for 64-dimensional dense embeddings."""
    embedding_vector: List[float] = Field(..., description="Dense embedding vector")
    embedding_dim: int = Field(default=64, description="Embedding dimension")
    l2_norm: float = Field(default=1.0, description="L2 norm of the embedding")
    model_name: str = Field(default="CrimeEmbeddingNetwork", description="Embedding model name")

    model_config = ConfigDict(from_attributes=True)


class FeatureAttribution(BaseModel):
    feature_name: str
    attribution_score: float


class ExplainabilityRequest(BaseModel):
    """Payload for Captum XAI feature attribution."""
    sample_record: CrimePredictionRequest
    target_class: Optional[int] = Field(default=0, description="Target class index for attribution")

    model_config = ConfigDict(from_attributes=True)


class ExplainabilityResponse(BaseModel):
    """Response payload for feature attribution & sensitivity."""
    predicted_domain: str
    confidence_score: float
    top_contributing_features: List[FeatureAttribution]
    saliency_scores: List[FeatureAttribution]
    model_name: str = Field(default="FTTransformerClassifier")
    method: str = Field(default="Captum Integrated Gradients & Saliency")

    model_config = ConfigDict(from_attributes=True)


class BatchPredictionRequest(BaseModel):
    """Payload for bulk batch inference."""
    records: List[CrimePredictionRequest]

    model_config = ConfigDict(from_attributes=True)


class BatchPredictionResponse(BaseModel):
    """Response payload for bulk batch inference."""
    total_records: int
    predictions: List[CrimePredictionResponse]
    batch_execution_time_ms: int

    model_config = ConfigDict(from_attributes=True)


class ModelHealthResponse(BaseModel):
    """AI Subsystem health probe response."""
    status: str = Field(default="ok", description="Health status string")
    device: str = Field(..., description="Torch device (cpu or cuda)")
    models_loaded: Dict[str, bool] = Field(..., description="Map of model names to load status")
    warmup_complete: bool = Field(default=True)


class ModelMetadataResponse(BaseModel):
    """Metadata response for model version management."""
    version: str = Field(..., description="Model version string")
    framework: str = Field(..., description="Framework version string")
    flagship_model: str = Field(..., description="Primary classifier model name")
    forecaster_model: str = Field(..., description="Forecaster model name")
    embedding_dim: int = Field(default=64, description="Embedding dimension")
    dataset_rows: int = Field(default=40160, description="Training dataset row count")
    dataset_hash_md5: str = Field(..., description="MD5 hash of dataset file")
    saved_at: Optional[str] = None
