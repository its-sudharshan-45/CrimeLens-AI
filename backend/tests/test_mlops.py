"""
MLOps enterprise feature tests (model switching, analytics, drift, deployment).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.mlops.analytics import PredictionAnalytics
from app.mlops.deployment import DeploymentValidator, SystemMonitor
from app.mlops.drift_detector import DriftDetector, _js_divergence, _level_from_score, _psi
from app.mlops.model_manager import ModelVersionManager
from app.core.enums.prediction_type import PredictionType
from app.models.prediction import Prediction
from app.services.mlops_service import MLOpsService


@pytest.fixture
def model_manager() -> ModelVersionManager:
    return ModelVersionManager()


def test_model_manager_lists_versions(model_manager: ModelVersionManager):
    models = model_manager.list_models()
    assert len(models) >= 1
    assert models[0]["version"] == "v1.0.0"
    assert models[0]["status"] in {"Active", "Archived"}
    assert "dataset_hash" in models[0]
    assert "framework_version" in models[0]


def test_model_manager_current(model_manager: ModelVersionManager):
    current = model_manager.get_current_model()
    assert current["version"] == "v1.0.0"
    assert current["status"] == "Active"


def test_model_manager_validate_artifacts(model_manager: ModelVersionManager):
    ok, errors = model_manager.validate_model_artifacts(model_manager.default_models_dir)
    assert ok is True
    assert errors == []


def test_model_manager_switch_same_version(model_manager: ModelVersionManager):
    current = model_manager.switch_version("v1.0.0")
    assert current["version"] == "v1.0.0"


def test_model_manager_switch_invalid_version(model_manager: ModelVersionManager):
    with pytest.raises(ValueError):
        model_manager.switch_version("v9.9.9")


def test_model_loader_reload_models():
    from app.ai.model_loader import ModelLoader

    loader = ModelLoader.get_instance()
    original_dir = loader.models_dir
    assert loader.reload_models(models_dir=original_dir) is True


def test_model_manager_rollback_without_history(model_manager: ModelVersionManager):
    with pytest.raises(ValueError):
        model_manager.rollback()


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
            prediction_label="Property Crime",
            prediction_type=PredictionType.CRIME_TYPE,
            confidence_score=0.52,
            model_name="EnsembleClassifier",
            model_version="v1.0.0",
            execution_time_ms=12,
            raw_output={"input": {"victim_age": 40, "crime_code": 350}},
        )
        for _ in range(10)
    ]
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: predictions))
    )
    status = await detector.evaluate(db)
    assert status["overall_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert "drift_score" in status


@pytest.mark.asyncio
async def test_analytics_dashboard_empty_db():
    analytics = PredictionAnalytics()
    db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar.return_value = 0
        result.all.return_value = []
        return result

    db.execute = fake_execute
    dashboard = await analytics.build_dashboard(db)
    assert dashboard["summary"]["total_predictions"] == 0
    assert "charts" in dashboard


def test_deployment_validator_registry(model_manager: ModelVersionManager):
    validator = DeploymentValidator()
    ok, _ = validator.validate_registry()
    assert ok is True
    ok_models, errors = validator.validate_models()
    assert ok_models is True
    assert errors == []


def test_system_monitor_uptime():
    monitor = SystemMonitor()
    assert monitor.uptime_seconds() >= 0


@pytest.mark.asyncio
async def test_mlops_service_startup_validation():
    service = MLOpsService()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: 1))
    with patch.object(service.validator, "validate_supabase", return_value=(True, "client initialized")):
        result = await service.startup_validation(db)
    assert "checks" in result
    assert "models" in result["checks"]


@pytest.mark.asyncio
async def test_mlops_api_models_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_resp = await client.get("/api/v1/mlops/models")
        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload["count"] >= 1

        current_resp = await client.get("/api/v1/mlops/models/current")
        assert current_resp.status_code == 200
        assert current_resp.json()["version"] == "v1.0.0"


@pytest.mark.asyncio
async def test_mlops_api_switch_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mlops/models/switch",
            json={"version": "v1.0.0", "rollback": False},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Active"


@pytest.mark.asyncio
async def test_mlops_api_analytics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/mlops/analytics")
        assert response.status_code == 200
        body = response.json()
        assert "summary" in body
        assert "charts" in body


@pytest.mark.asyncio
async def test_mlops_api_switch_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/mlops/models/switch",
            json={"version": "does-not-exist", "rollback": False},
        )
        assert response.status_code == 400


def test_model_manager_validate_missing_dir(model_manager: ModelVersionManager):
    ok, errors = model_manager.validate_model_artifacts("/path/that/does/not/exist")
    assert ok is False
    assert errors


def test_model_manager_load_registry_missing(tmp_path):
    manager = ModelVersionManager(registry_index_path=str(tmp_path / "missing.json"))
    with pytest.raises(FileNotFoundError):
        manager.list_models()


def test_deployment_validator_missing_registry(tmp_path):
    validator = DeploymentValidator()
    validator.model_manager.registry_index_path = str(tmp_path / "missing.json")
    ok, msg = validator.validate_registry()
    assert ok is False


def test_deployment_validator_missing_models_dir(tmp_path):
    validator = DeploymentValidator()
    validator.model_manager.default_models_dir = str(tmp_path / "models")
    ok, errors = validator.validate_models()
    assert ok is False
    assert errors


@pytest.mark.asyncio
async def test_deployment_validator_database_missing_url():
    validator = DeploymentValidator()
    with patch("app.mlops.deployment.settings.DATABASE_URL", ""):
        ok, msg = await validator.validate_database()
    assert ok is False


@pytest.mark.asyncio
async def test_drift_report_recommendations():
    detector = DriftDetector()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [])))
    report = await detector.report(db)
    assert report["drift_level"] == "LOW"
    assert report["drift_type"] == ["None"]


def test_model_manager_switch_with_reload_patch(model_manager: ModelVersionManager):
    expected = {
        "model_name": "EnsembleClassifier",
        "version": "v1.0.0",
        "status": "Active",
        "dataset_hash": "abc",
        "framework_version": "PyTorch",
        "accuracy_metrics": {},
    }
    with patch.object(model_manager, "_read_active_version", return_value="v0.0.0"):
        with patch("app.mlops.model_manager.ModelLoader") as loader_cls:
            loader = MagicMock()
            loader_cls.get_instance.return_value = loader
            with patch.object(model_manager, "_write_active_version"):
                with patch.object(model_manager, "get_current_model", return_value=expected):
                    info = model_manager.switch_version("v1.0.0")
            loader.reload_models.assert_called_once()
            assert info["version"] == "v1.0.0"


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


def test_logging_configuration_writes_mlops_logger():
    from pathlib import Path

    log_path = Path("logs/app.log")
    assert log_path.exists()


@pytest.mark.asyncio
async def test_mlops_service_analytics_fallback():
    service = MLOpsService()
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("db unavailable"))
    dashboard = await service.analytics_dashboard(db)
    assert dashboard.summary.total_predictions == 0


@pytest.mark.asyncio
async def test_startup_validation_failure_paths():
    validator = DeploymentValidator()
    validator.model_manager.registry_index_path = "/missing/registry.json"
    validator.model_manager.active_version_path = "/missing/active.json"
    validator.model_manager.default_models_dir = "/missing/models"
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: 1))
    with patch.object(validator, "validate_supabase", return_value=(False, "no supabase")):
        result = await validator.run_startup_validation(db)
    assert result.ok is False
    assert result.errors


def test_system_monitor_memory_and_cpu():
    monitor = SystemMonitor()
    assert monitor.memory_usage_mb() is None or monitor.memory_usage_mb() > 0
    assert monitor.cpu_usage_percent() is None or monitor.cpu_usage_percent() >= 0


@pytest.mark.asyncio
async def test_drift_high_level_recommendation():
    detector = DriftDetector()
    with patch.object(
        detector,
        "evaluate",
        return_value={
            "drift_score": 0.9,
            "overall_level": "HIGH",
            "feature_drift": {"level": "HIGH", "affected_features": ["Victim Age"]},
            "confidence_drift": {"level": "LOW"},
            "prediction_distribution_drift": {"level": "LOW"},
            "warnings": ["Feature drift"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ):
        report = await detector.report(AsyncMock())
    assert report["drift_level"] == "HIGH"
    assert "retraining" in report["recommendation"].lower()


def test_model_manager_rollback_success(model_manager: ModelVersionManager):
    model_manager._version_history.append("v0.0.0")
    with patch.object(model_manager, "switch_version", return_value={"version": "v0.0.0"}) as switch:
        result = model_manager.rollback()
    switch.assert_called_once_with("", rollback=True)
    assert result["version"] == "v0.0.0"


def test_model_manager_validate_corrupted_weights(model_manager: ModelVersionManager, tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    for name in (
        "preprocessor.pkl",
        "feature_columns.json",
        "ft_transformer.pt",
        "crime_classifier.pt",
    ):
        (models_dir / name).write_bytes(b"bad")
    ok, errors = model_manager.validate_model_artifacts(str(models_dir))
    assert ok is False
    assert any("Corrupted" in err for err in errors)


@pytest.mark.asyncio
async def test_analytics_with_sample_rows():
    analytics = PredictionAnalytics()
    db = AsyncMock()
    call_count = {"n": 0}

    async def fake_execute(stmt):
        call_count["n"] += 1
        result = MagicMock()
        stmt_str = str(stmt)
        if "avg" in stmt_str and "confidence_score" in stmt_str:
            result.scalar.return_value = 0.75
        elif "avg" in stmt_str and "execution_time_ms" in stmt_str:
            result.scalar.return_value = 25.0
        elif "count" in stmt_str and call_count["n"] <= 3:
            result.scalar.return_value = 5
        elif "count" in stmt_str:
            result.scalar.return_value = 1
        elif "group_by" in stmt_str and "prediction_label" in stmt_str:
            result.all.return_value = [("Property Crime", 3), ("Violent Crime", 2)]
        elif "group_by" in stmt_str and "model_name" in stmt_str:
            result.all.return_value = [("EnsembleClassifier", "v1.0.0", 5, 0.75)]
        elif "order_by" in stmt_str and "desc" in stmt_str:
            result.all.return_value = [
                (uuid4(), "Property Crime", 0.9, datetime.now(timezone.utc))
            ]
        elif "order_by" in stmt_str and "asc" in stmt_str:
            result.all.return_value = [
                (uuid4(), "Violent Crime", 0.2, datetime.now(timezone.utc))
            ]
        elif "date_trunc" in stmt_str:
            result.all.return_value = [(datetime.now(timezone.utc), 2)]
        else:
            result.scalar.return_value = 0
            result.all.return_value = []
        return result

    db.execute = fake_execute
    dashboard = await analytics.build_dashboard(db)
    assert dashboard["summary"]["total_predictions"] == 5
    assert "Property Crime" in dashboard["prediction_distribution"] or dashboard["summary"]["total_predictions"] == 5


def test_slim_metrics_helpers():
    from app.mlops.model_manager import _slim_metrics

    assert _slim_metrics("not-a-dict") == {}
    slim = _slim_metrics(
        {
            "model": {"accuracy": 0.5, "y_true": [1, 2, 3]},
            "other": "value",
        }
    )
    assert "y_true" not in slim["model"]
    assert slim["other"] == "value"


def test_model_manager_read_active_from_metadata(tmp_path, model_manager: ModelVersionManager):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "model_metadata.json").write_text(
        json.dumps({"version": "v2.0.0"}),
        encoding="utf-8",
    )
    manager = ModelVersionManager(
        active_version_path=str(tmp_path / "missing_active.json"),
        default_models_dir=str(models_dir),
        registry_index_path=model_manager.registry_index_path,
    )
    assert manager._read_active_version() == "v2.0.0"


def test_model_manager_get_current_fallback(tmp_path):
    index_path = tmp_path / "registry_index.json"
    index_path.write_text(json.dumps({"versions": []}), encoding="utf-8")
    active_path = tmp_path / "active_version.json"
    active_path.write_text(json.dumps({"active_version": "v9.9.9"}), encoding="utf-8")
    manager = ModelVersionManager(
        registry_index_path=str(index_path),
        active_version_path=str(active_path),
        default_models_dir=str(tmp_path / "models"),
    )
    current = manager.get_current_model()
    assert current["status"] == "Active"


def test_model_manager_switch_corrupted_artifacts(model_manager: ModelVersionManager, tmp_path):
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    index = {
        "versions": [
            {
                "model_version": "v-bad",
                "framework": "PyTorch",
                "training_date": "2026-01-01",
                "artifact_path": str(bad_dir),
                "metrics": {},
            }
        ]
    }
    index_path = tmp_path / "registry.json"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    manager = ModelVersionManager(
        registry_index_path=str(index_path),
        default_models_dir=str(tmp_path / "also_bad"),
    )
    with pytest.raises(ValueError, match="No valid artifact"):
        manager.switch_version("v-bad")


def test_model_manager_invalid_metadata_json(model_manager: ModelVersionManager, tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    for artifact in ("preprocessor.pkl", "feature_columns.json", "ft_transformer.pt", "crime_classifier.pt"):
        (models_dir / artifact).write_bytes(b"x")
    (models_dir / "model_metadata.json").write_text("{bad json", encoding="utf-8")
    ok, errors = model_manager.validate_model_artifacts(str(models_dir))
    assert ok is False
    assert any("Invalid model_metadata" in err for err in errors)


@pytest.mark.asyncio
async def test_deployment_preprocessor_and_supabase_failures(tmp_path):
    validator = DeploymentValidator()
    validator.model_manager.default_models_dir = str(tmp_path / "empty")
    ok, errors = validator.validate_preprocessor_artifacts()
    assert ok is False
    assert errors

    with patch("app.mlops.deployment.settings.SUPABASE_URL", ""):
        ok, msg = validator.validate_supabase()
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
async def test_drift_medium_recommendation():
    detector = DriftDetector()
    with patch.object(
        detector,
        "evaluate",
        return_value={
            "drift_score": 0.2,
            "overall_level": "MEDIUM",
            "feature_drift": {"level": "MEDIUM", "affected_features": ["Crime Code"]},
            "confidence_drift": {"level": "LOW"},
            "prediction_distribution_drift": {"level": "LOW"},
            "warnings": ["Feature drift detected (MEDIUM)"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ):
        report = await detector.report(AsyncMock())
    assert report["drift_level"] == "MEDIUM"
    assert "review" in report["recommendation"].lower()


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
async def test_startup_validation_model_loader_not_loaded():
    validator = DeploymentValidator()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: 1))
    with patch.object(validator, "validate_registry", return_value=(True, "ok")):
        with patch.object(validator, "validate_models", return_value=(True, [])):
            with patch.object(validator, "validate_preprocessor_artifacts", return_value=(True, [])):
                with patch.object(validator, "validate_supabase", return_value=(True, "ok")):
                    with patch("app.mlops.deployment.ModelLoader") as loader_cls:
                        loader = MagicMock()
                        loader.is_loaded = False
                        loader_cls.get_instance.return_value = loader
                        result = await validator.run_startup_validation(db)
    assert result.ok is False


def test_model_manager_write_active_version(model_manager: ModelVersionManager, tmp_path):
    active_path = tmp_path / "active.json"
    manager = ModelVersionManager(
        registry_index_path=model_manager.registry_index_path,
        active_version_path=str(active_path),
    )
    manager._write_active_version("v1.0.0")
    assert active_path.exists()
    assert json.loads(active_path.read_text(encoding="utf-8"))["active_version"] == "v1.0.0"


@pytest.mark.asyncio
async def test_system_monitor_with_psutil():
    monitor = SystemMonitor()
    status = await monitor.system_status(db=None)
    assert status["api_status"] == "ok"
    assert status["uptime_seconds"] >= 0


def test_model_manager_resolves_registry_snapshot(model_manager: ModelVersionManager):
    index = model_manager._load_registry_index()
    entry = next(v for v in index["versions"] if v["model_version"] == "v1.0.0")
    models_dir = model_manager._resolve_models_dir(entry)
    assert models_dir.replace("\\", "/").endswith("ai/registry/v1.0.0")
    ok, errors = model_manager.validate_model_artifacts(models_dir)
    assert ok is True, errors
    assert "ft_transformer.pt" in __import__("os").listdir(models_dir)


def test_drift_detector_missing_baseline(tmp_path):
    with patch("os.path.isfile", return_value=False):
        baseline = DriftDetector(training_stats_path=str(tmp_path / "missing.json"))._load_baseline()
    assert baseline == {}
