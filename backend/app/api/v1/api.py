"""
Central API v1 router.

All versioned routes are registered here so that main.py only needs a
single include_router() call with the /api/v1 prefix.
"""
from fastapi import APIRouter

from app.api.v1 import crime_categories, crime_locations, crime_reports

api_router = APIRouter()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@api_router.get("/health", tags=["Health"])
async def health_check():
    """Quick liveness probe — returns 200 if the API process is running."""
    return {"status": "ok", "message": "CrimeLens AI API is running"}


# ---------------------------------------------------------------------------
# Crime Management Domain  (Phase 4)
# ---------------------------------------------------------------------------
api_router.include_router(
    crime_categories.router,
    prefix="/crime-categories",
    tags=["Crime Categories"],
)
api_router.include_router(
    crime_locations.router,
    prefix="/crime-locations",
    tags=["Crime Locations"],
)
api_router.include_router(
    crime_reports.router,
    prefix="/crime-reports",
    tags=["Crime Reports"],
)

# ---------------------------------------------------------------------------
# Evidence Management (Phase 5.1)
# ---------------------------------------------------------------------------
from app.api.v1 import evidence
api_router.include_router(
    evidence.router,
    prefix="/evidence",
    tags=["Evidence"],
)

# ---------------------------------------------------------------------------
# Investigation Management (Phase 5.2)
# ---------------------------------------------------------------------------
from app.api.v1 import investigations
api_router.include_router(
    investigations.router,
    prefix="/investigations",
    tags=["Investigations"],
)

# ---------------------------------------------------------------------------
# AI Model Serving & Deep Learning Inference (Phase 6.1)
# ---------------------------------------------------------------------------
from app.api.v1 import ai

api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI & Machine Learning"],
)

# ---------------------------------------------------------------------------
# Enterprise MLOps (Phase 6.2)
# ---------------------------------------------------------------------------
from app.api.v1 import mlops

api_router.include_router(
    mlops.router,
    prefix="/mlops",
    tags=["MLOps"],
)

# ---------------------------------------------------------------------------
# Core Predictions & Investigation Assistant (Phase 5)
# ---------------------------------------------------------------------------
from app.api.v1 import predictions

api_router.include_router(
    predictions.router,
    prefix="/predict",
    tags=["Predictions & Forecasting"],
)

# ---------------------------------------------------------------------------
# Enterprise Audit Logs (Phase 7 & 8)
# ---------------------------------------------------------------------------
from app.api.v1 import audit_logs

api_router.include_router(
    audit_logs.router,
    prefix="/audit-logs",
    tags=["Audit Logs"],
)

# ---------------------------------------------------------------------------
# System Health & AI Observability (Phase 9)
# ---------------------------------------------------------------------------
from app.api.v1 import system_health

api_router.include_router(
    system_health.router,
    prefix="/system-health",
    tags=["System Health"],
)

# ---------------------------------------------------------------------------
# Backup & Recovery (Phase 9)
# ---------------------------------------------------------------------------
from app.api.v1 import backup

api_router.include_router(
    backup.router,
    prefix="/backup",
    tags=["Backup & Recovery"],
)


