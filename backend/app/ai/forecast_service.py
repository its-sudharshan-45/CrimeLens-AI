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

from ai.forecasting.locations import build_location_catalog, resolve_location
from ai.forecasting.predict import CrimeForecastPredictor, DISCLAIMER, DEFAULT_REGISTRY_DIR

logger = logging.getLogger("crimelens.ai.forecast_service")

# A district's risk score is its model-predicted average daily incident count as
# a percentage of the highest predicted district average in the same run.  The
# score is a relative intensity index, not a probability of victimisation.
RISK_HIGH_THRESHOLD = 70.0
RISK_MEDIUM_THRESHOLD = 40.0


def risk_category(score: float) -> str:
    if score >= RISK_HIGH_THRESHOLD:
        return "High"
    if score >= RISK_MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


class ForecastService:
    """Thread-safe singleton owning the single GRU forecasting model."""

    _instance: Optional["ForecastService"] = None
    _lock = threading.Lock()

    def __init__(self, registry_dir: str | Path | None = None) -> None:
        self.registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR)
        self.is_loaded = False
        self.predictor: Optional[CrimeForecastPredictor] = None
        self.load_error: Optional[str] = None
        self._risk_cache_lock = threading.Lock()
        self._district_rankings_cache: Optional[List[Dict[str, Any]]] = None

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

    # ── district risk helpers ────────────────────────────────────────────────
    def _city_scopes(self) -> List[Dict[str, str]]:
        assert self.predictor is not None
        return [scope for scope in self.predictor.available_scopes() if scope["scope_type"] == "city"]

    def location_catalog(self) -> List[Dict[str, Any]]:
        """Return every State/UT and district, annotated with model coverage.

        All officially recognised districts are listed.  Districts without a
        dedicated dataset city scope point at a real representative scope and
        are marked ``coverage="proxy"`` so the UI can label them honestly.
        """
        if not self.is_loaded and not self.load():
            raise RuntimeError(self.load_error or "Forecaster is not available.")
        cities = {scope["display_name"] for scope in self._city_scopes()}
        return build_location_catalog(cities)

    def _district_rankings(self) -> List[Dict[str, Any]]:
        """Average predicted daily count for every district, highest first.

        The ranking is computed once per loaded model with ``predict_horizon``
        (no hard-coded values, no random numbers) and cached for the process.
        """
        with self._risk_cache_lock:
            if self._district_rankings_cache is not None:
                return self._district_rankings_cache

            assert self.predictor is not None
            rows: List[Dict[str, Any]] = []
            for scope in self._city_scopes():
                predictions = self.predictor.predict_horizon(scope["key"])
                average = sum(predictions) / len(predictions) if predictions else 0.0
                rows.append(
                    {
                        "scope_key": scope["key"],
                        "city": scope["display_name"],
                        "average_predicted_daily": round(float(average), 6),
                    }
                )
            rows.sort(key=lambda row: row["average_predicted_daily"], reverse=True)
            self._district_rankings_cache = rows
            return rows

    def predict_district_risk(self, state: str, district: str) -> Dict[str, Any]:
        """Predict district risk from the trained GRU forecast.

        The GRU forecast gives seven daily incident counts.  The risk percentage
        is a transparent relative index: the district's predicted daily average
        divided by the highest predicted daily average across all 29 dataset
        scopes.  No value is hard-coded or sampled randomly.

        Districts outside the 29 dataset cities are still selectable.  They use
        the representative scope recorded in ``STATE_PROXY_CITY`` and the reply
        sets ``model_coverage="proxy"`` so the estimate is never presented as a
        direct dataset observation.
        """
        if not self.is_loaded and not self.load():
            raise RuntimeError(self.load_error or "Forecaster is not available.")

        cities = {scope["display_name"] for scope in self._city_scopes()}
        location = resolve_location(state, district, cities)
        if location is None:
            raise KeyError(
                f"Unsupported state/district '{state}' / '{district}'. "
                "Call GET /api/v1/ai/locations for valid values."
            )

        scope_key = location["scope_key"]
        result = self.forecast("city", location["city"])
        predictions = result["forecast"]
        if not predictions:
            raise ValueError("The model returned an empty forecast.")

        horizon = len(predictions)
        average_daily = sum(day["predicted_count"] for day in predictions) / horizon
        total_7_day = sum(day["predicted_count"] for day in predictions)
        lower_daily = sum(day["lower_bound_95"] for day in predictions) / horizon
        upper_daily = sum(day["upper_bound_95"] for day in predictions) / horizon

        rankings = self._district_rankings()
        peak = rankings[0]["average_predicted_daily"] if rankings else 0.0
        if peak <= 0:
            risk_percentage = 0.0
            risk_lower = 0.0
            risk_upper = 0.0
        else:
            risk_percentage = min(100.0, 100.0 * average_daily / peak)
            risk_lower = min(100.0, 100.0 * lower_daily / peak)
            risk_upper = min(100.0, 100.0 * upper_daily / peak)

        rank = next(
            (index + 1 for index, row in enumerate(rankings) if row["scope_key"] == scope_key),
            None,
        )
        history = self.predictor.historical_summary(scope_key)
        model_metrics = result.get("test_metrics", {}) or {}
        model_scores = model_metrics.get("model", {}) or {}
        baseline_scores = model_metrics.get("persistence_baseline", {}) or {}

        coverage = location["coverage"]
        risk_method = (
            "Relative Crime Risk Index: the model-predicted average daily incident "
            "count for this district as a percentage of the highest predicted "
            "district average across all supported districts. It is a relative "
            "intensity index, not a probability of crime."
        )
        if coverage == "proxy":
            risk_method += (
                f" This district has no dedicated dataset city scope; the index uses "
                f"the model scope for {location['city']} as a representative proxy."
            )

        return {
            "success": True,
            "state": location["state"],
            "district": location["district"],
            "city": location["city"],
            "scope_key": scope_key,
            "model_coverage": coverage,
            "proxy_city": location["city"] if coverage == "proxy" else None,
            "risk_percentage": round(risk_percentage, 1),
            "risk_category": risk_category(risk_percentage),
            "risk_lower_bound": round(risk_lower, 1),
            "risk_upper_bound": round(risk_upper, 1),
            "risk_method": risk_method,
            "predicted_daily_average": round(float(average_daily), 2),
            "predicted_7_day_total": round(float(total_7_day), 2),
            "prediction_interval_95": {
                "daily_lower": round(float(lower_daily), 2),
                "daily_upper": round(float(upper_daily), 2),
            },
            "peak_predicted_daily_average": round(float(peak), 2),
            "district_rank": rank,
            "district_count": len(rankings),
            "historical_incidents": history["total_incidents"],
            "historical_daily_average": history["daily_average"],
            "last_observed_date": result["last_observed_date"],
            "model_name": result["model_name"],
            "model_version": result["model_version"],
            "model_test_metrics": model_scores,
            "persistence_test_metrics": baseline_scores,
            "forecast": predictions,
            "uncertainty_method": result["uncertainty_method"],
            "disclaimer": DISCLAIMER,
        }

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
