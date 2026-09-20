"""
Dynamic model version management backed by ai/registry/registry_index.json.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import torch
except (ImportError, OSError):
    torch = None

from app.ai.model_loader import ModelLoader, DEFAULT_MODELS_DIR, PROJECT_ROOT

logger = logging.getLogger("crimelens.mlops")

REGISTRY_DIR = os.path.join(PROJECT_ROOT, "ai", "registry")
REGISTRY_INDEX_PATH = os.path.join(REGISTRY_DIR, "registry_index.json")
ACTIVE_VERSION_PATH = os.path.join(REGISTRY_DIR, "active_version.json")

REQUIRED_ARTIFACTS = (
    "preprocessor.pkl",
    "feature_columns.json",
    "ft_transformer.pt",
    "crime_classifier.pt",
)

METRIC_HEAVY_KEYS = frozenset({"y_true", "y_pred", "confusion_matrix"})


def _slim_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Remove large evaluation arrays from registry metrics for API responses."""
    if not isinstance(metrics, dict):
        return {}
    slim: dict[str, Any] = {}
    for model_name, model_metrics in metrics.items():
        if not isinstance(model_metrics, dict):
            slim[model_name] = model_metrics
            continue
        slim[model_name] = {
            k: v for k, v in model_metrics.items() if k not in METRIC_HEAVY_KEYS
        }
    return slim


class ModelVersionManager:
    """Reads registry index, validates artifacts, and hot-reloads ModelLoader."""

    _lock = threading.Lock()

    def __init__(
        self,
        registry_index_path: str = REGISTRY_INDEX_PATH,
        active_version_path: str = ACTIVE_VERSION_PATH,
        default_models_dir: str = DEFAULT_MODELS_DIR,
    ) -> None:
        self.registry_index_path = registry_index_path
        self.active_version_path = active_version_path
        self.default_models_dir = default_models_dir
        self._version_history: list[str] = []

    def _load_registry_index(self) -> dict[str, Any]:
        if not os.path.exists(self.registry_index_path):
            raise FileNotFoundError(f"Registry index not found: {self.registry_index_path}")
        with open(self.registry_index_path, encoding="utf-8") as handle:
            return json.load(handle)

    def _read_active_version(self) -> str:
        if os.path.exists(self.active_version_path):
            with open(self.active_version_path, encoding="utf-8") as handle:
                data = json.load(handle)
            version = data.get("active_version")
            if version:
                return str(version)
        meta_path = os.path.join(self.default_models_dir, "model_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as handle:
                meta = json.load(handle)
            return str(meta.get("version", "v1.0.0"))
        return "v1.0.0"

    def _write_active_version(self, version: str) -> None:
        os.makedirs(os.path.dirname(self.active_version_path), exist_ok=True)
        payload = {
            "active_version": version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.active_version_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)
        logger.info("Active model version set to %s", version)

    def validate_model_artifacts(self, models_dir: str) -> tuple[bool, list[str]]:
        """Ensure required files exist and PyTorch weights are readable."""
        errors: list[str] = []
        if not os.path.isdir(models_dir):
            return False, [f"Models directory missing: {models_dir}"]

        for artifact in REQUIRED_ARTIFACTS:
            path = os.path.join(models_dir, artifact)
            if not os.path.isfile(path):
                errors.append(f"Missing artifact: {artifact}")

        ft_path = os.path.join(models_dir, "ft_transformer.pt")
        mlp_path = os.path.join(models_dir, "crime_classifier.pt")
        if torch is not None:
            for label, path in (("ft_transformer", ft_path), ("crime_classifier", mlp_path)):
                if os.path.isfile(path):
                    try:
                        torch.load(path, map_location="cpu", weights_only=True)
                    except TypeError:
                        torch.load(path, map_location="cpu")
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"Corrupted {label} weights: {exc}")

        meta_path = os.path.join(models_dir, "model_metadata.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as handle:
                    json.load(handle)
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid model_metadata.json: {exc}")

        return len(errors) == 0, errors

    def _resolve_models_dir(self, version_entry: dict[str, Any]) -> str:
        artifact_path = version_entry.get("artifact_path") or ""
        if artifact_path:
            artifact_path = os.path.normpath(artifact_path)
            if not os.path.isabs(artifact_path):
                artifact_path = os.path.normpath(os.path.join(PROJECT_ROOT, artifact_path))
        if artifact_path and os.path.isdir(artifact_path):
            ok, _ = self.validate_model_artifacts(artifact_path)
            if ok:
                return artifact_path
        ok, _ = self.validate_model_artifacts(self.default_models_dir)
        if ok:
            return self.default_models_dir
        raise FileNotFoundError(
            f"No valid artifact directory for version {version_entry.get('model_version')}"
        )

    def _metadata_for_version(self, version: str, entry: dict[str, Any]) -> dict[str, Any]:
        models_dir = self._resolve_models_dir(entry)
        meta_path = os.path.join(models_dir, "model_metadata.json")
        dataset_hash = "N/A"
        framework_version = entry.get("framework", "PyTorch")
        model_name = "EnsembleClassifier"
        if os.path.isfile(meta_path):
            with open(meta_path, encoding="utf-8") as handle:
                meta = json.load(handle)
            dataset_hash = meta.get("dataset_hash_md5", dataset_hash)
            framework_version = meta.get("framework", framework_version)
            model_name = meta.get("flagship_model", model_name)

        metrics = _slim_metrics(entry.get("metrics", {}))
        accuracy_metrics: dict[str, float] = {}
        for _name, model_metrics in metrics.items():
            if isinstance(model_metrics, dict) and "accuracy" in model_metrics:
                accuracy_metrics["accuracy"] = float(model_metrics["accuracy"])
                break

        active = self._read_active_version()
        status = "Active" if version == active else "Archived"

        return {
            "model_name": model_name,
            "version": version,
            "training_date": entry.get("training_date"),
            "dataset_hash": dataset_hash,
            "dataset_version": entry.get("dataset_version"),
            "framework_version": framework_version,
            "accuracy_metrics": accuracy_metrics,
            "metrics": metrics,
            "status": status,
            "artifact_path": models_dir,
        }

    def list_models(self) -> list[dict[str, Any]]:
        index = self._load_registry_index()
        versions = index.get("versions", [])
        return [
            self._metadata_for_version(entry["model_version"], entry)
            for entry in versions
            if entry.get("model_version")
        ]

    def get_current_model(self) -> dict[str, Any]:
        active = self._read_active_version()
        index = self._load_registry_index()
        for entry in index.get("versions", []):
            if entry.get("model_version") == active:
                return self._metadata_for_version(active, entry)
        loader = ModelLoader.get_instance()
        meta = loader.model_metadata or {}
        return {
            "model_name": meta.get("flagship_model", "EnsembleClassifier"),
            "version": meta.get("version", active),
            "training_date": meta.get("saved_at"),
            "dataset_hash": meta.get("dataset_hash_md5", "N/A"),
            "framework_version": meta.get("framework", f"PyTorch {torch.__version__ if torch is not None else 'N/A'}"),
            "accuracy_metrics": {},
            "status": "Active",
            "artifact_path": loader.models_dir,
        }

    def switch_version(self, target_version: str, rollback: bool = False) -> dict[str, Any]:
        with self._lock:
            index = self._load_registry_index()
            entries = index.get("versions", [])
            entry_map = {e.get("model_version"): e for e in entries if e.get("model_version")}

            if rollback:
                if not self._version_history:
                    raise ValueError("No previous version available for rollback.")
                target_version = self._version_history[-1]

            if target_version not in entry_map:
                raise ValueError(f"Model version '{target_version}' is not registered.")

            current = self._read_active_version()
            if target_version == current and not rollback:
                return self.get_current_model()

            entry = entry_map[target_version]
            try:
                models_dir = self._resolve_models_dir(entry)
            except FileNotFoundError as exc:
                raise ValueError(str(exc)) from exc
            ok, errors = self.validate_model_artifacts(models_dir)
            if not ok:
                raise ValueError(
                    f"Cannot switch to {target_version}: {'; '.join(errors)}"
                )

            loader = ModelLoader.get_instance()
            loader.reload_models(models_dir=models_dir)
            self._version_history.append(current)
            self._write_active_version(target_version)
            logger.info(
                "Model version switch %s -> %s (rollback=%s)",
                current,
                target_version,
                rollback,
            )
            return self.get_current_model()

    def rollback(self) -> dict[str, Any]:
        return self.switch_version("", rollback=True)
