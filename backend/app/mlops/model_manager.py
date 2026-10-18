"""
backend/app/mlops/model_manager.py
==================================
Single-model version management for the CrimeLens AI GRU forecaster.

The project ships exactly one deep-learning model. Forecast versions live under
``ai/registry/<version>/`` (e.g. ``forecast_v1``) and the active version is
recorded in ``ai/registry/forecast_active.json``.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.paths import (
    FORECAST_ACTIVE_PATH,
    REGISTRY_DIR,
    forecast_registry_dir,
    read_active_forecast_version,
)

logger = logging.getLogger("crimelens.mlops")

REQUIRED_ARTIFACTS = (
    "gru_forecaster.pt",
    "feature_columns.json",
    "model_metadata.json",
    "scope_series.json",
)


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class ModelVersionManager:
    """Discovers, validates and activates forecast model versions."""

    _lock = threading.Lock()

    def __init__(self) -> None:
        self.registry_dir = REGISTRY_DIR
        self.registry_index_path = REGISTRY_DIR / "forecast_index.json"
        self.active_version_path = FORECAST_ACTIVE_PATH
        self.default_models_dir = forecast_registry_dir()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _read_active_version(self) -> str:
        return read_active_forecast_version()

    def _write_active_version(self, version: str) -> None:
        self.active_version_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"active_version": version, "updated_at": datetime.now(timezone.utc).isoformat()}
        with open(self.active_version_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        logger.info("Active forecast version set to %s", version)

    def _available_versions(self) -> list[str]:
        if not self.registry_dir.is_dir():
            return []
        return sorted(
            p.name for p in self.registry_dir.iterdir()
            if p.is_dir() and p.name.startswith("forecast_")
        )

    def validate_model_artifacts(self, models_dir: str | Path) -> tuple[bool, list[str]]:
        """Ensure the required forecast artifacts exist and the metadata is valid JSON."""
        models_dir = Path(models_dir)
        errors: list[str] = []
        if not models_dir.is_dir():
            return False, [f"Forecast directory missing: {models_dir}"]
        for artifact in REQUIRED_ARTIFACTS:
            if not (models_dir / artifact).is_file():
                errors.append(f"Missing artifact: {artifact}")
        meta = models_dir / "model_metadata.json"
        if meta.is_file():
            try:
                _read_json(meta)
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid model_metadata.json: {exc}")
        return len(errors) == 0, errors

    def _info_for_version(self, version: str) -> dict[str, Any]:
        models_dir = forecast_registry_dir(version)
        meta_path = models_dir / "model_metadata.json"
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                meta = _read_json(meta_path)
            except json.JSONDecodeError:
                meta = {}

        regression_metrics = {
            k: float(meta[k])
            for k in ("test_mae", "test_rmse", "test_wape", "persistence_mae")
            if meta.get(k) is not None
        }
        active = self._read_active_version()
        return {
            "model_name": meta.get("primary_model", "CrimeGRUForecaster"),
            "version": version,
            "training_date": meta.get("saved_at"),
            "dataset_hash": meta.get("dataset_hash_md5", "N/A"),
            "dataset_version": None,
            "framework_version": meta.get("framework", "PyTorch"),
            "accuracy_metrics": {
                "MAE": regression_metrics.get("test_mae"),
                "RMSE": regression_metrics.get("test_rmse"),
                "WAPE": regression_metrics.get("test_wape"),
            } if "test_mae" in regression_metrics else {},
            "metrics": regression_metrics,
            "status": "Active" if version == active else "Archived",
            "artifact_path": str(models_dir),
        }

    # ── public API ───────────────────────────────────────────────────────────
    def list_models(self) -> list[dict[str, Any]]:
        versions = self._available_versions()
        if not versions:
            return [self.get_current_model()]
        return [self._info_for_version(v) for v in versions]

    def get_current_model(self) -> dict[str, Any]:
        return self._info_for_version(self._read_active_version())

    def switch_version(self, target_version: str, rollback: bool = False) -> dict[str, Any]:
        del rollback  # single-model registry: no historical rollback targets
        with self._lock:
            if target_version not in self._available_versions():
                raise ValueError(f"Forecast version '{target_version}' is not registered.")
            ok, errors = self.validate_model_artifacts(forecast_registry_dir(target_version))
            if not ok:
                raise ValueError(f"Cannot switch to {target_version}: {'; '.join(errors)}")
            self._write_active_version(target_version)
            try:
                from app.ai.forecast_service import get_forecast_service
                import ai.forecasting.predict as fp

                service = get_forecast_service()
                service.registry_dir = forecast_registry_dir(target_version)
                service.predictor = fp.CrimeForecastPredictor(service.registry_dir)
                service.is_loaded = True
                service.load_error = None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Model switch reload failed: %s", exc)
            return self.get_current_model()

    def rollback(self) -> dict[str, Any]:
        raise ValueError("Rollback is unavailable: the project ships a single model version.")
