"""
backend/app/ai/forecast_service.py
==================================
Singleton service that loads the CrimeLens AI GRU crime-count forecaster and
serves seven-day forecasts for a selected scope (city or crime type).

This replaces the previous multi-model ``ModelService`` / ``ModelLoader`` pair.
Only one model is exposed: ``CrimeGRUForecaster``.  The service never refits
preprocessing on a request — it reuses the artifacts written by
``ai.forecasting.train``.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from ai.forecasting.predict import CrimeForecastPredictor, DISCLAIMER, DEFAULT_REGISTRY_DIR

logger = logging.getLogger("crimelens.ai.forecast_service")


class ForecastService:
    """Thread-safe singleton owning the single GRU forecasting model."""

    _instance: Optional["ForecastService"] = None
    _lock = threading.Lock()

    def __init__(self, registry_dir: str | Path | None = None) -> None:
        self.registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR)
        self.is_loaded = False
        self.predictor: Optional[CrimeForecastPredictor] = None
        self.load_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ForecastService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def load(self) -> bool:
        """Load the model once. Never raises — failures are surfaced via ``load_error``."""
        with self._lock:
            if self.is_loaded:
                return True
            checkpoint = self.registry_dir / "gru_forecaster.pt"
            if not checkpoint.exists():
                self.load_error = (
                    f"Forecaster checkpoint not found at {checkpoint}. "
                    "Run `python -m ai.forecasting.train` to create it."
                )
                logger.warning(self.load_error)
                return False
            try:
                self.predictor = CrimeForecastPredictor(self.registry_dir)
                self.is_loaded = True
                self.load_error = None
                logger.info("CrimeGRUForecaster loaded from %s", self.registry_dir)
            except Exception as exc:  # noqa: BLE001
                self.load_error = f"Failed to load CrimeGRUForecaster: {exc}"
                logger.exception(self.load_error)
                self.predictor = None
                self.is_loaded = False
            return self.is_loaded

    # ── scope helpers ────────────────────────────────────────────────────────
    def available_scopes(self) -> List[Dict[str, str]]:
        if not self.is_loaded and not self.load():
            return []
        assert self.predictor is not None
        return self.predictor.available_scopes()

    def resolve_scope_key(self, scope_type: str, scope_value: str) -> Optional[str]:
        """Case-insensitively resolve a scope_type/value pair to a stored scope key."""
        if not self.is_loaded and not self.load():
            return None
        assert self.predictor is not None
        want_type = scope_type.strip().lower()
        want_value = scope_value.strip().lower()
        for scope in self.predictor.available_scopes():
            if scope["scope_type"].lower() == want_type and scope["display_name"].strip().lower() == want_value:
                return scope["key"]
        return None

    # ── inference ────────────────────────────────────────────────────────────
    def forecast(self, scope_type: str, scope_value: str) -> Dict[str, Any]:
        if not self.is_loaded and not self.load():
            raise RuntimeError(self.load_error or "Forecaster is not available.")
        assert self.predictor is not None
        scope_key = self.resolve_scope_key(scope_type, scope_value)
        if scope_key is None:
            raise KeyError(
                f"Unsupported {scope_type} '{scope_value}'. Call GET /api/v1/ai/scopes for valid values."
            )
        return self.predictor.forecast(scope_key)

    def model_metadata(self) -> Dict[str, Any]:
        if not self.is_loaded and not self.load():
            raise RuntimeError(self.load_error or "Forecaster is not available.")
        meta_path = self.registry_dir / "model_metadata.json"
        if meta_path.exists():
            import json

            with open(meta_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        assert self.predictor is not None
        return {
            "version": self.registry_dir.name,
            "primary_model": "CrimeGRUForecaster",
            "seq_len": self.predictor.seq_len,
            "forecast_horizon": self.predictor.forecast_horizon,
        }

    def health(self) -> Dict[str, Any]:
        loaded = self.is_loaded or self.load()
        device = str(getattr(self.predictor, "device", "cpu")) if self.predictor else "cpu"
        n_scopes = len(self.predictor.available_scopes()) if self.predictor else 0
        return {
            "status": "ok" if loaded else "unavailable",
            "model_name": "CrimeGRUForecaster",
            "loaded": loaded,
            "device": device,
            "registry_dir": str(self.registry_dir),
            "n_scopes": n_scopes,
            "error": self.load_error,
        }


def get_forecast_service() -> ForecastService:
    return ForecastService.get_instance()


__all__ = ["ForecastService", "get_forecast_service", "DISCLAIMER", "PROJECT_ROOT"]
