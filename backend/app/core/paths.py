"""
backend/app/core/paths.py
=========================
Canonical filesystem paths shared across the backend.

The project now ships a single deep-learning model (the GRU crime-count
forecaster).  Its artifacts live under ``ai/registry/<version>/`` and the active
version is recorded in ``ai/registry/forecast_active.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = PROJECT_ROOT / "ai" / "registry"
FORECAST_ACTIVE_PATH = REGISTRY_DIR / "forecast_active.json"
DEFAULT_FORECAST_VERSION = "forecast_v1"


def read_active_forecast_version() -> str:
    """Return the active forecast version, defaulting to ``forecast_v1``."""
    try:
        with open(FORECAST_ACTIVE_PATH, "r", encoding="utf-8") as handle:
            version = json.load(handle).get("active_version")
        if version and (REGISTRY_DIR / version).is_dir():
            return str(version)
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_FORECAST_VERSION


def forecast_registry_dir(version: str | None = None) -> Path:
    """Resolve the artifact directory for a forecast version (default: active)."""
    return REGISTRY_DIR / (version or read_active_forecast_version())
