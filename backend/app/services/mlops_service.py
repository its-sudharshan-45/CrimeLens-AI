"""
MLOps orchestration service layer.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mlops.analytics import PredictionAnalytics
from app.mlops.deployment import DeploymentValidator, SystemMonitor
from app.mlops.drift_detector import DriftDetector
from app.mlops.model_manager import ModelVersionManager
from app.schemas.mlops import (
    AnalyticsResponse,
    AnalyticsSummary,
    DriftReportResponse,
    DriftStatusResponse,
    ModelListResponse,
    ModelSwitchRequest,
    ModelVersionInfo,
    SystemStatusResponse,
)

logger = logging.getLogger("crimelens.mlops")


class MLOpsService:
    def __init__(self) -> None:
        self.model_manager = ModelVersionManager()
        self.analytics = PredictionAnalytics()
        self.drift = DriftDetector()
        self.monitor = SystemMonitor()
        self.validator = DeploymentValidator()

    def list_models(self) -> ModelListResponse:
        models = [ModelVersionInfo(**item) for item in self.model_manager.list_models()]
        return ModelListResponse(models=models, count=len(models))

    def current_model(self) -> ModelVersionInfo:
        return ModelVersionInfo(**self.model_manager.get_current_model())

    def switch_model(self, request: ModelSwitchRequest) -> ModelVersionInfo:
        if request.rollback:
            info = self.model_manager.rollback()
        else:
            info = self.model_manager.switch_version(request.version)
        logger.info("Model switch completed: version=%s", info.get("version"))
        return ModelVersionInfo(**info)

    async def analytics_dashboard(self, db: AsyncSession) -> AnalyticsResponse:
        try:
            payload = await self.analytics.build_dashboard(db)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Analytics dashboard fallback due to DB error: %s", exc)
            payload = self._empty_analytics_payload()
        summary = AnalyticsSummary(**payload["summary"])
        return AnalyticsResponse(summary=summary, **{k: v for k, v in payload.items() if k != "summary"})

    @staticmethod
    def _empty_analytics_payload() -> dict[str, Any]:
        return {
            "summary": {
                "total_predictions": 0,
                "predictions_today": 0,
                "predictions_this_month": 0,
                "average_confidence": 0.0,
                "average_inference_latency_ms": 0.0,
                "most_predicted_crime_domain": None,
                "human_review_count": 0,
                "low_confidence_count": 0,
            },
            "prediction_distribution": {},
            "model_usage": [],
            "top_confidence_predictions": [],
            "low_confidence_predictions": [],
            "daily_prediction_trend": [],
            "monthly_prediction_trend": [],
            "charts": {"domain_pie": [], "daily_line": [], "monthly_line": []},
        }

    async def drift_status(self, db: AsyncSession) -> DriftStatusResponse:
        data = await self.drift.evaluate(db)
        return DriftStatusResponse(**data)

    async def drift_report(self, db: AsyncSession) -> DriftReportResponse:
        data = await self.drift.report(db)
        return DriftReportResponse(**data)

    async def system_status(self, db: AsyncSession) -> SystemStatusResponse:
        data = await self.monitor.system_status(db)
        return SystemStatusResponse(**data)

    async def startup_validation(self, db: AsyncSession | None = None) -> dict[str, Any]:
        result = await self.validator.run_startup_validation(db)
        return {"ok": result.ok, "checks": result.checks, "errors": result.errors}
