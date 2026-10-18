"""
backend/app/api/v1/predictions.py
=================================
Legacy prediction router for CrimeLens AI.

Endpoints:
  POST /predict/hotspots — DEPRECATED 410 Gone (CNN removed 2026-10-16; tabular data not images)
  GET  /predict/history  — Paginated prediction history from the database
  GET  /predict/stats    — Aggregate prediction observability metrics

Live forecasting now lives at POST /api/v1/ai/forecast (single GRU model).
"""

import uuid
from typing import Annotated, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.prediction import Prediction
from app.schemas.prediction import HotspotPredictionRequest

router = APIRouter()


# ── Prediction History Schema ──────────────────────────────────────────────────
class PredictionHistoryItem(BaseModel):
    id: uuid.UUID
    prediction_label: str
    prediction_type: str
    confidence_score: float
    model_name: str
    model_version: str
    execution_time_ms: int
    created_at: Any  # datetime

    model_config = {"from_attributes": True}


class PredictionHistoryResponse(BaseModel):
    items: List[PredictionHistoryItem]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────────────────────────
# 1. Hotspot Prediction Endpoint — DEPRECATED (CNN removed 2026-10-16)
# ─────────────────────────────────────────────────────────────────────────────
CNN_REMOVAL_DETAIL = (
    "City hotspot CNN model was removed: the crime dataset is structured tabular data, "
    "not images (Conv2d across alphabetically-ordered cities assumed false spatial locality). "
    "Historical HOTSPOT records remain queryable via GET /predict/history. "
    "See backups/cnn_removal_2026-10-16/."
)


@router.post(
    "/hotspots",
    summary="Deprecated: City Crime Hotspots (CNN removed)",
    description=(
        "DEPRECATED (HTTP 410 Gone). The Phase 4 2D-CNN hotspot forecaster was removed "
        "because the dataset is tabular, not images. Historical records remain via /predict/history."
    ),
    status_code=status.HTTP_410_GONE,
)
async def predict_hotspots(
    request: HotspotPredictionRequest,
    http_req: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=CNN_REMOVAL_DETAIL,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Prediction History Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/history",
    response_model=PredictionHistoryResponse,
    summary="Get Prediction History",
    description="Returns paginated list of past prediction records from the database, sorted newest first.",
)
async def get_prediction_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    prediction_type: Optional[str] = Query(default=None, description="Filter by prediction type"),
):
    stmt = select(Prediction)
    if prediction_type:
        stmt = stmt.where(Prediction.prediction_type == prediction_type)

    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(desc(Prediction.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = [
        PredictionHistoryItem(
            id=r.id,
            prediction_label=r.prediction_label,
            prediction_type=r.prediction_type.value if hasattr(r.prediction_type, "value") else str(r.prediction_type),
            confidence_score=r.confidence_score,
            model_name=r.model_name,
            model_version=r.model_version,
            execution_time_ms=r.execution_time_ms or 0,
            created_at=r.created_at,
        )
        for r in records
    ]

    return PredictionHistoryResponse(items=items, total=total, page=page, page_size=page_size)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Prediction Observability & Statistics Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/stats",
    summary="Get Prediction Observability & Aggregate Metrics",
    description="Returns real aggregate metrics computed from persisted prediction records and audit history.",
)
async def get_prediction_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from datetime import datetime, timezone

    from sqlalchemy import func

    total_query = await db.execute(select(func.count(Prediction.id)))
    total_predictions = total_query.scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = await db.execute(select(func.count(Prediction.id)).where(Prediction.created_at >= today_start))
    predictions_today = today_query.scalar() or 0

    avg_latency_query = await db.execute(select(func.avg(Prediction.execution_time_ms)))
    avg_execution_time_ms = round(float(avg_latency_query.scalar() or 0.0), 1)

    model_query = await db.execute(
        select(Prediction.model_name, func.count(Prediction.id)).group_by(Prediction.model_name)
    )
    predictions_by_model = {row[0]: row[1] for row in model_query.all() if row[0]}

    type_query = await db.execute(
        select(Prediction.prediction_type, func.count(Prediction.id)).group_by(Prediction.prediction_type)
    )
    predictions_by_type = {
        (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
        for row in type_query.all()
        if row[0] is not None
    }

    return {
        "total_predictions": total_predictions,
        "predictions_today": predictions_today,
        "avg_execution_time_ms": avg_execution_time_ms,
        "predictions_by_model": predictions_by_model,
        "predictions_by_type": predictions_by_type,
        "active_models": ["CrimeGRUForecaster"],
    }
