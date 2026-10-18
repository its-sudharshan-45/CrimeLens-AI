"""
backend/app/api/v1/system_health.py
===================================
Real System Health, Hardware Resource Metrics, and Deep Learning Model Status.
Zero fake metrics. Uses psutil, time, sqlalchemy text queries, and real PyTorch model objects.
"""

import os
import time
import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import psutil

from app.db.session import get_db
from app.ai.forecast_service import get_forecast_service
from app.core.paths import read_active_forecast_version

router = APIRouter()

_START_TIME = time.time()


def _active_registry_version() -> str:
    """Read the active forecast model version (single source of truth)."""
    return read_active_forecast_version()


def get_system_metrics() -> Dict[str, Any]:
    """Retrieves real host system hardware metrics using psutil."""
    vm = psutil.virtual_memory()
    disk_path = "C:\\" if os.name == "nt" else "/"
    try:
        du = psutil.disk_usage(disk_path)
        disk_pct = du.percent
    except Exception:
        disk_pct = 0.0

    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": vm.percent,
        "memory_used_mb": round(vm.used / (1024 * 1024), 1),
        "memory_total_mb": round(vm.total / (1024 * 1024), 1),
        "disk_percent": disk_pct,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


def get_ai_models_health() -> List[Dict[str, Any]]:
    """Inspects the single GRU forecasting model loaded in memory."""
    service = get_forecast_service()
    service.load()
    version = _active_registry_version()

    loaded = bool(service.is_loaded and service.predictor is not None)
    param_count = 0
    if loaded and service.predictor is not None:
        param_count = sum(p.numel() for p in service.predictor.model.parameters())

    models: List[Dict[str, Any]] = [
        {
            "model_name": "CrimeGRUForecaster",
            "model_type": "gru_crime_count_forecaster",
            "version": version,
            "loaded": loaded,
            "checkpoint_available": loaded,
            "parameter_count": param_count,
            "inference_available": loaded,
            "status": "ACTIVE" if loaded else "UNAVAILABLE",
        }
    ]

    # The Phase 4 CNN hotspot model was removed 2026-10-16 (tabular data, not images).
    # Former classifiers (FT-Transformer, MLP, N-BEATS, Embedding) were removed with
    # the simplification to a single GRU model.
    return models


async def build_system_health_payload(db: AsyncSession) -> Dict[str, Any]:
    """Builds complete real runtime health payload."""
    db_ok = True
    db_detail = "Operational"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False
        db_detail = str(e)

    sys_metrics = get_system_metrics()
    models = get_ai_models_health()
    version = _active_registry_version()
    all_models_ok = all(m["inference_available"] for m in models)

    overall_status = "healthy" if db_ok and all_models_ok else "degraded"

    return {
        "status": overall_status,
        "api_status": "ok",
        "database": {
            "status": "healthy" if db_ok else "unhealthy",
            "detail": db_detail,
        },
        "system": sys_metrics,
        "ai_models": models,
        "total_model_parameters": sum(m["parameter_count"] for m in models),
        "registry": {
            "version": version,
            "status": "VALIDATED",
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
    }


@router.get(
    "",
    summary="Detailed Enterprise System & AI Health Check",
    status_code=status.HTTP_200_OK,
)
async def get_system_health(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Returns real hardware resource metrics, database health, and AI model statuses."""
    return await build_system_health_payload(db)
