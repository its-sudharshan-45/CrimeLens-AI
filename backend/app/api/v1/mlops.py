"""
Enterprise MLOps API routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.mlops import (
    AnalyticsResponse,
    DriftReportResponse,
    DriftStatusResponse,
    ModelListResponse,
    ModelSwitchRequest,
    ModelVersionInfo,
    SystemStatusResponse,
)
from app.services.mlops_service import MLOpsService

router = APIRouter()
mlops_service = MLOpsService()


@router.get("/models", response_model=ModelListResponse, summary="List registered model versions")
async def list_models() -> ModelListResponse:
    return mlops_service.list_models()


@router.get("/models/current", response_model=ModelVersionInfo, summary="Get active model version")
async def current_model() -> ModelVersionInfo:
    return mlops_service.current_model()


@router.post("/models/switch", response_model=ModelVersionInfo, summary="Switch or rollback model version")
async def switch_model(request: ModelSwitchRequest) -> ModelVersionInfo:
    try:
        return mlops_service.switch_model(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/analytics", response_model=AnalyticsResponse, summary="Prediction analytics dashboard")
async def analytics(db: Annotated[AsyncSession, Depends(get_db)]) -> AnalyticsResponse:
    try:
        return await mlops_service.analytics_dashboard(db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics generation failed: {exc}",
        ) from exc


@router.get("/drift", response_model=DriftStatusResponse, summary="Live drift monitoring status")
async def drift_status(db: Annotated[AsyncSession, Depends(get_db)]) -> DriftStatusResponse:
    return await mlops_service.drift_status(db)


@router.get("/drift/report", response_model=DriftReportResponse, summary="Detailed drift report")
async def drift_report(db: Annotated[AsyncSession, Depends(get_db)]) -> DriftReportResponse:
    return await mlops_service.drift_report(db)


@router.get("/system", response_model=SystemStatusResponse, summary="Production system status")
async def system_status(db: Annotated[AsyncSession, Depends(get_db)]) -> SystemStatusResponse:
    return await mlops_service.system_status(db)
