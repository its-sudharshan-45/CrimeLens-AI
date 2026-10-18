"""
MLOps feature tests for the single-model (GRU forecaster) registry.

Covers:
  * ModelVersionManager discovery / validation / activation
  * DeploymentValidator startup checks
  * PredictionAnalytics dashboard builders
  * DriftDetector statistics and recommendations
  * MLOps REST endpoints
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.paths import FORECAST_ACTIVE_PATH, REGISTRY_DIR, forecast_registry_dir
from app.main import app
from app.mlops.analytics import PredictionAnalytics
from app.mlops.deployment import DeploymentValidator, SystemMonitor
from app.mlops.drift_detector import DriftDetector, _js_divergence, _level_from_score, _psi
from app.mlops.model_manager import REQUIRED_ARTIFACTS, ModelVersionManager
from app.core.enums.prediction_type import PredictionType
from app.models.prediction import Prediction
from app.services.mlops_service import MLOpsService

FORECAST_DIR = forecast_registry_dir()
ARTIFACTS_PRESENT = all((FORECAST_DIR / name).is_file() for name in REQUIRED_ARTIFACTS)


def _active_version() -> str:
    with open(FORECAST_ACTIVE_PATH, encoding="utf-8") as handle:
        return json.load(handle)["active_version"]


@pytest.fixture
def model_manager() -> ModelVersionManager:
    return ModelVersionManager()


# ─── Model manager ──────────────────────────────────────────────────────────

def test_model_manager_lists_versions(model_manager: ModelVersionManager):
    models = model_manager.list_models()
    assert len(models) >= 1
    versions = {m["version"] for m in models}
    assert model_manager._read_active_version() in versions
    assert models[0]["status"] in {"Active", "Archived"}
    assert "dataset_hash" in models[0]
    assert "framework_version" in models[0]


def test_model_manager_current(model_manager: ModelVersionManager):
    current = model_manager.get_current_model()
    assert current["version"] == model_manager._read_active_version()
    assert current["status"] == "Active"
    assert current["model_name"] == "CrimeGRUForecaster"


def test_model_manager_available_versions_are_forecast_dirs(model_manager: ModelVersionManager):
    versions = model_manager._available_versions()
    assert "forecast_v1" in versions
    assert all(v.startswith("forecast_") for v in versions)


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="forecast artifacts not present")
def test_model_manager_validate_artifacts(model_manager: ModelVersionManager):
    ok, errors = model_manager.validate_model_artifacts(model_manager.default_models_dir)
    assert ok is True
    assert errors == []


def test_model_manager_validate_missing_dir(model_manager: ModelVersionManager):
    ok, errors = model_manager.validate_model_artifacts("/path/that/does/not/exist")
    assert ok is False
    assert errors


def test_model_manager_validate_corrupted_metadata(model_manager: ModelVersionManager, tmp_path):
    models_dir = tmp_path / "forecast_bad"
    models_dir.mkdir()
    for name in REQUIRED_ARTIFACTS:
        (models_dir / name).write_text("{}", encoding="utf-8")
    (models_dir / "model_metadata.json").write_text("{bad json", encoding="utf-8")
    ok, errors = model_manager.validate_model_artifacts(str(models_dir))
    assert ok is False
    assert any("Invalid model_metadata" in err for err in errors)


def test_model_manager_missing_artifact_reported(model_manager: ModelVersionManager, tmp_path):
    models_dir = tmp_path / "forecast_empty"
    models_dir.mkdir()
    ok, errors = model_manager.validate_model_artifacts(str(models_dir))
    assert ok is False
    assert len(errors) == len(REQUIRED_ARTIFACTS)
    assert any("gru_forecaster.pt" in err for err in errors)


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="forecast artifacts not present")
def test_model_manager_switch_same_version(model_manager: ModelVersionManager):
    active = model_manager._read_active_version()
    current = model_manager.switch_version(active)
    assert current["version"] == active


def test_model_manager_switch_invalid_version(model_manager: ModelVersionManager):
    with pytest.raises(ValueError):
        model_manager.switch_version("forecast_does_not_exist")


def test_model_manager_rollback_unsupported(model_manager: ModelVersionManager):
    with pytest.raises(ValueError, match="single model"):
        model_manager.rollback()


def test_model_manager_write_active_version(model_manager: ModelVersionManager, tmp_path):
    manager = ModelVersionManager()
    target = tmp_path / "forecast_active.json"
    with patch.object(manager, "active_version_path", target):
        manager._write_active_version("forecast_v1")
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8"))["active_version"] == "forecast_v1"


# ─── Deployment validator ───────────────────────────────────────────────────

def test_deployment_validator_registry():
    validator = DeploymentValidator()
    ok, msg = validator.validate_registry()
    assert ok is True
    assert "forecast_v1" in msg


@pytest.mark.skipif(not ARTIFACTS_PRESENT, reason="forecast artifacts not present")
def test_deployment_validator_models_ok():
    validator = DeploymentValidator()
    ok, errors = validator.validate_models()
    assert ok is True
    assert errors == []


def test_deployment_validator_missing_registry(tmp_path):
    validator = DeploymentValidator()
    with patch("app.mlops.deployment.forecast_registry_dir", return_value=tmp_path / "missing"):
        ok, msg = validator.validate_registry()
    assert ok is False


def test_deployment_validator_missing_models_dir(tmp_path):
    validator = DeploymentValidator()
    with patch("app.mlops.deployment.forecast_registry_dir", return_value=tmp_path / "missing"):
        ok, errors = validator.validate_models()
    assert ok is False
    assert errors


def test_deployment_preprocessor_artifacts_missing(tmp_path):
    validator = DeploymentValidator()
    with patch("app.mlops.deployment.forecast_registry_dir", return_value=tmp_path / "empty"):
        ok, errors = validator.validate_preprocessor_artifacts()
    assert ok is False
    assert errors


@pytest.mark.asyncio
async def test_deployment_validator_database_missing_url():
    validator = DeploymentValidator()
    with patch("app.mlops.deployment.settings.DATABASE_URL", ""):
        ok, _ = await validator.validate_database()
    assert ok is False


@pytest.mark.asyncio
async def test_deployment_database_exception():
    validator = DeploymentValidator()
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("connection refused"))
    ok, msg = await validator.validate_database(db)
    assert ok is False
    assert "connection refused" in msg


@pytest.mark.asyncio
async def test_deployment_supabase_not_configured():
    validator = DeploymentValidator()
    with patch("app.mlops.deployment.settings.SUPABASE_URL", ""):
        ok, _ = validator.validate_supabase()
    assert ok is False


@pytest.mark.asyncio
async def test_mlops_service_startup_validation():
    service = MLOpsService()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=type("R", (), {"scalar": lambda self: 1})())
    with patch.object(service.validator, "validate_supabase", return_value=(True, "client initialized")):
        result = await service.startup_validation(db)
    assert "checks" in result
    assert "models" in result["checks"]


@pytest.mark.asyncio
async def test_startup_validation_failure_paths():
    validator = DeploymentValidator()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=type("R", (), {"scalar": lambda self: 1})())
    with patch.object(validator, "validate_registry", return_value=(False, "no registry")):
        with patch.object(validator, "validate_models", return_value=(False, ["no models"])):
            with patch.object(validator, "validate_supabase", return_value=(False, "no supabase")):
                result = await validator.run_startup_validation(db)
    assert result.ok is False
    assert result.errors


# ─── Drift detection ────────────────────────────────────────────────────────

def test_drift_stat_helpers():
    assert _level_from_score(0.05, 0.1, 0.25) == "LOW"
    assert _level_from_score(0.15, 0.1, 0.25) == "MEDIUM"
    assert _level_from_score(0.4, 0.1, 0.25) == "HIGH"
    assert _psi([0.1, 0.2, 0.3], [0.1, 0.2, 0.3]) >= 0.0
    assert _js_divergence({"a": 0.5, "b": 0.5}, {"a": 0.5, "b": 0.5}) == 0.0


@pytest.mark.asyncio
async def test_drift_evaluate_with_predictions():
    detector = DriftDetector()
    predictions = [
        Prediction(
            id=uuid4(),
            prediction_label="7-Day Forecast for Delhi (city)",
            prediction_type=PredictionType.TREND,
            confidence_score=0.52,
            model_name="CrimeGRUForecaster",
            model_version="forecast_v1",
            execution_time_ms=12,
            raw_output={"forecast": [1.0, 2.0]},
        )
        for _ in range(10)
    ]
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=type("R", (), {"scalars": lambda self: type("S", (), {"all": lambda self: predictions})()})()
    )
    status = await detector.evaluate(db)
    assert status["overall_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert "drift_score" in status


@pytest.mark.asyncio
async def test_drift_report_no_data_is_low():
    detector = DriftDetector()
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=type("R", (), {"scalars": lambda self: type("S", (), {"all": lambda self: []})()})()
    )
    report = await detector.report(db)
    assert report["drift_level"] == "LOW"
    assert report["drift_type"] == ["None"]


def test_drift_detector_missing_baseline(tmp_path):
    with patch("os.path.isfile", return_value=False):
        baseline = DriftDetector(training_stats_path=str(tmp_path / "missing.json"))._load_baseline()
    assert baseline == {}


@pytest.mark.asyncio
async def test_drift_high_level_recommendation():
    detector = DriftDetector()
    with patch.object(
        detector,
        "evaluate",
        return_value={
            "drift_score": 0.9,
            "overall_level": "HIGH",
            "feature_drift": {"level": "HIGH", "affected_features": ["count"]},
            "confidence_drift": {"level": "LOW"},
            "prediction_distribution_drift": {"level": "LOW"},
            "warnings": ["Feature drift"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ):
        report = await detector.report(AsyncMock())
    assert report["drift_level"] == "HIGH"
    assert "retraining" in report["recommendation"].lower()


@pytest.mark.asyncio
async def test_drift_medium_recommendation():
    detector = DriftDetector()
    with patch.object(
        detector,
        "evaluate",
        return_value={
            "drift_score": 0.2,
            "overall_level": "MEDIUM",
            "feature_drift": {"level": "MEDIUM", "affected_features": ["count"]},
            "confidence_drift": {"level": "LOW"},
            "prediction_distribution_drift": {"level": "LOW"},
            "warnings": ["Feature drift detected (MEDIUM)"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ):
        report = await detector.report(AsyncMock())
    assert report["drift_level"] == "MEDIUM"
    assert "review" in report["recommendation"].lower()


# ─── Analytics ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_dashboard_empty_db():
    analytics = PredictionAnalytics()
    db = AsyncMock()

    async def fake_execute(_stmt):
        result = MagicMock()
        result.scalar.return_value = 0
        result.all.return_value = []
        return result

    db.execute = fake_execute
    dashboard = await analytics.build_dashboard(db)
    assert dashboard["summary"]["total_predictions"] == 0
    assert "charts" in dashboard


# ─── System monitor ─────────────────────────────────────────────────────────

def test_system_monitor_uptime():
    assert SystemMonitor().uptime_seconds() >= 0


def test_system_monitor_memory_and_cpu():
    monitor = SystemMonitor()
    assert monitor.memory_usage_mb() is None or monitor.memory_usage_mb() > 0
    assert monitor.cpu_usage_percent() is None or monitor.cpu_usage_percent() >= 0


@pytest.mark.asyncio
async def test_system_monitor_system_status():
    status = await SystemMonitor().system_status(db=None)
    assert status["api_status"] == "ok"
    assert status["uptime_seconds"] >= 0
    assert status["active_version"] == _active_version()


# ─── MLOps REST endpoints ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mlops_api_models_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_resp = await client.get("/api/v1/mlops/models")
        assert list_resp.status_code == 200
        assert list_resp.json()["count"] >= 1

        current_resp = await client.get("/api/v1/mlops/models/current")
        assert current_resp.status_code == 200
        assert current_resp.json()["version"] == _active_version()


@pytest.mark.asyncio
async def test_mlops_api_switch_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mlops/models/switch",
            json={"version": "does-not-exist", "rollback": False},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_mlops_api_analytics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/mlops/analytics")
        assert response.status_code == 200
        body = response.json()
        assert "summary" in body
        assert "charts" in body


@pytest.mark.asyncio
async def test_mlops_api_analytics_internal_error():
    with patch(
        "app.services.mlops_service.MLOpsService.analytics_dashboard",
        side_effect=RuntimeError("boom"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/mlops/analytics")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_mlops_api_drift_and_system():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        drift_resp = await client.get("/api/v1/mlops/drift")
        assert drift_resp.status_code == 200
        assert drift_resp.json()["overall_level"] in {"LOW", "MEDIUM", "HIGH"}

        report_resp = await client.get("/api/v1/mlops/drift/report")
        assert report_resp.status_code == 200
        assert "recommendation" in report_resp.json()

        system_resp = await client.get("/api/v1/mlops/system")
        assert system_resp.status_code == 200
        assert system_resp.json()["api_status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint_enriched():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "models" in body
    assert "registry" in body


def test_registry_dir_constant_is_project_registry():
    assert REGISTRY_DIR.name == "registry"
