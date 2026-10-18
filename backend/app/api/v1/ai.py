"""
backend/app/api/v1/ai.py
========================
FastAPI router exposing the single CrimeLens AI forecasting model.

Endpoints:
  POST /api/v1/ai/forecast — 7-day GRU crime-count forecast for a scope (city or crime type)
  GET  /api/v1/ai/scopes   — list supported forecasting scopes
  GET  /api/v1/ai/models   — active model version & metadata
  GET  /api/v1/ai/health   — forecasting subsystem health
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.forecast_service import get_forecast_service
from app.core.enums.prediction_type import PredictionType
from app.db.session import get_db
from app.schemas.ai import (
    ForecastRequest,
    ForecastResponse,
    ModelHealthResponse,
    ModelMetadataResponse,
    ScopeListResponse,
)
from app.services.prediction_log import log_prediction

router = APIRouter()


@router.post(
    "/forecast",
    response_model=ForecastResponse,
    summary="7-Day Crime-Count Forecast (GRU)",
    description=(
        "Forecasts daily crime counts for the next seven days for a selected city or crime type "
        "using the single CrimeGRUForecaster model. Includes historical counts, an honest "
        "held-out backtest and evaluation metrics."
    ),
)
async def forecast_crime(
    request: ForecastRequest,
    http_req: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = get_forecast_service()
    try:
        result = service.forecast(request.scope_type, request.scope_value)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast failed: {exc}",
        ) from exc

    avg_predicted = (
        sum(d["predicted_count"] for d in result["forecast"]) / len(result["forecast"])
        if result.get("forecast")
        else 0.0
    )
    await log_prediction(
        db,
        action="PREDICTION_FORECAST",
        prediction_type=PredictionType.TREND,
        label=f"7-Day Forecast for {result['scope_display_name']} ({result['scope_type']})",
        model_name=result["model_name"],
        model_version=result["model_version"],
        confidence=round(float(avg_predicted), 4),
        execution_time_ms=0,
        raw_output={"scope_key": result["scope_key"], "forecast": result["forecast"]},
        audit_details={
            "endpoint": "/api/v1/ai/forecast",
            "scope_type": result["scope_type"],
            "scope_value": result["scope_display_name"],
            "horizon_days": result["forecast_horizon_days"],
        },
        client_ip=http_req.client.host if http_req.client else None,
        user_agent=http_req.headers.get("user-agent"),
    )
    return result


@router.get(
    "/scopes",
    response_model=ScopeListResponse,
    summary="List Supported Forecasting Scopes",
    description="Returns every supported city and crime-type scope for the forecasting model.",
)
async def list_scopes(
    scope_type: Annotated[str | None, Query(description="Optional filter: 'city' or 'crime_type'")] = None,
):
    scopes = get_forecast_service().available_scopes()
    if scope_type:
        scopes = [s for s in scopes if s["scope_type"] == scope_type]
    return ScopeListResponse(scopes=scopes, count=len(scopes))


@router.get(
    "/models",
    response_model=ModelMetadataResponse,
    summary="Active Model Metadata & Version Information",
    description="Returns the active GRU forecaster version, dataset hash, architecture and held-out metrics.",
)
async def get_model_metadata():
    try:
        meta = get_forecast_service().model_metadata()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ModelMetadataResponse(**meta)


@router.get(
    "/health",
    response_model=ModelHealthResponse,
    summary="Forecasting Subsystem Health",
    description="Reports whether the GRU forecaster is loaded and how many scopes it serves.",
)
async def get_health_status():
    return get_forecast_service().health()
