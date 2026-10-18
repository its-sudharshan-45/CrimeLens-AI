"""
ai/forecasting/predict.py
=========================
Inference for the CrimeLens AI GRU crime-count forecaster.

Loads the artifacts produced by ``ai.forecasting.train`` exactly once and serves
seven-day forecasts for any supported scope (city or crime type).  The same
class is used by the CLI and by the FastAPI backend, so training and serving use
identical preprocessing and never refit statistics on a request.

The class also produces an honest **rolling one-step-ahead backtest** over the
held-out test window for the requested scope (actual vs model-predicted counts),
which the frontend plots directly.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from ai.forecasting import data as fdata
from ai.models.temporal.gru import CrimeGRUForecaster

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_DIR = fdata.PROJECT_ROOT / "ai" / "registry" / "forecast_v1"

DISCLAIMER = (
    "Seven-day crime-count forecasts are statistical estimates derived from historical "
    "daily incident totals for the selected scope. They are not guarantees that a crime "
    "will occur and must not be used to predict or profile individuals. The source dataset "
    "is synthetic and its daily counts carry little temporal signal, so forecast skill is "
    "close to a naive persistence baseline; treat values as indicative only."
)


class CrimeForecastPredictor:
    """Load a forecast bundle and produce scope-level seven-day forecasts."""

    def __init__(self, registry_dir: str | Path | None = None, device: str | None = None) -> None:
        self.registry_dir = Path(registry_dir or DEFAULT_REGISTRY_DIR)
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self._backtest_cache: dict[str, list[dict[str, Any]]] = {}

        ckpt_path = self.registry_dir / "gru_forecaster.pt"
        if not ckpt_path.exists():
            raise FileNotFoundError(
                f"Forecaster checkpoint not found at {ckpt_path}. Run `python -m ai.forecasting.train` first."
            )
        self.checkpoint = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        cfg = self.checkpoint.get("config", {})

        self.seq_len = int(self.checkpoint.get("seq_len", fdata.SEQ_LEN))
        self.forecast_horizon = int(self.checkpoint.get("forecast_horizon", fdata.FORECAST_HORIZON))
        self.feature_columns = self.checkpoint.get("feature_columns", list(fdata.FORECAST_FEATURE_COLUMNS))

        self.model = CrimeGRUForecaster(
            input_size=cfg.get("input_size", len(self.feature_columns)),
            hidden_size=cfg.get("hidden_size", 64),
            num_layers=cfg.get("num_layers", 2),
            forecast_horizon=self.forecast_horizon,
            dropout=cfg.get("dropout", 0.2),
        )
        self.model.load_state_dict(self.checkpoint["model_state_dict"])
        self.model.to(self.device).eval()

        self.scope_stats: dict[str, dict[str, float]] = self.checkpoint.get("scope_stats", {})
        self._load_series()
        self._load_evaluation()
        # Honest empirical residual scale: test RMSE (falls back to 1.0).
        self.residual_sigma = float(self._metrics.get("test", {}).get("model", {}).get("RMSE", 1.0) or 1.0)
        logger.info("CrimeForecastPredictor ready: %d scopes, seq_len=%d, horizon=%d",
                    len(self.scope_series), self.seq_len, self.forecast_horizon)

    # ── loading ──────────────────────────────────────────────────────────────
    def _load_series(self) -> None:
        path = self.registry_dir / "scope_series.json"
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        self.dates = pd.to_datetime(payload["dates"])
        self.scope_series: dict[str, dict[str, Any]] = payload["scopes"]

    def _load_evaluation(self) -> None:
        self._metrics: dict[str, Any] = {}
        self._evaluation: dict[str, Any] = {}
        mpath = self.registry_dir / "metrics.json"
        epath = self.registry_dir / "evaluation_results.json"
        if mpath.exists():
            with open(mpath, "r", encoding="utf-8") as fh:
                self._metrics = json.load(fh)
        if epath.exists():
            with open(epath, "r", encoding="utf-8") as fh:
                self._evaluation = json.load(fh)

    # ── public API ───────────────────────────────────────────────────────────
    def available_scopes(self) -> list[dict[str, str]]:
        return [
            {"key": key, "scope_type": meta["scope_type"], "display_name": meta["display_name"]}
            for key, meta in self.scope_series.items()
        ]

    def scope_exists(self, scope_key: str) -> bool:
        return scope_key in self.scope_series

    def _counts(self, scope_key: str) -> np.ndarray:
        return np.asarray(self.scope_series[scope_key]["counts"], dtype="float64")

    def _stats(self, scope_key: str) -> tuple[float, float]:
        stats = self.scope_stats.get(scope_key, {})
        return float(stats.get("mean", 0.0)), float(stats.get("std", 1.0) or 1.0)

    def _features(self, scope_key: str) -> np.ndarray:
        mean, std = self._stats(scope_key)
        counts = self._counts(scope_key)
        return np.column_stack([(counts - mean) / std, fdata.calendar_features(self.dates)]).astype("float32")

    # ── inference ────────────────────────────────────────────────────────────
    def backtest(self, scope_key: str) -> list[dict[str, Any]]:
        """Rolling one-step-ahead actual vs predicted over the held-out test window."""
        if scope_key in self._backtest_cache:
            return self._backtest_cache[scope_key]

        feats = self._features(scope_key)
        counts = self._counts(scope_key)
        mean, std = self._stats(scope_key)
        test_mask = (self.dates >= pd.Timestamp(fdata.TEST_START)) & (self.dates <= pd.Timestamp(fdata.TEST_END))
        idx = np.flatnonzero(test_mask)

        windows, targets = [], []
        for i in idx:
            if i - self.seq_len < 0:
                continue
            windows.append(feats[i - self.seq_len : i])
            targets.append(i)
        if not windows:
            self._backtest_cache[scope_key] = []
            return []

        x = torch.from_numpy(np.asarray(windows, dtype="float32")).to(self.device)
        with torch.no_grad():
            pred_z = self.model(x).cpu().numpy()[:, 0]  # step-1 prediction per day
        pred = np.clip(pred_z * std + mean, 0.0, None)

        rows = [
            {"date": self.dates[t].date().isoformat(),
             "actual": round(float(counts[t]), 4),
             "predicted": round(float(p), 4)}
            for t, p in zip(targets, pred)
        ]
        self._backtest_cache[scope_key] = rows
        return rows

    def forecast(self, scope_key: str, history_days: int = 30) -> dict[str, Any]:
        if not self.scope_exists(scope_key):
            raise KeyError(f"Unsupported scope '{scope_key}'.")

        meta = self.scope_series[scope_key]
        counts = self._counts(scope_key)
        mean, std = self._stats(scope_key)
        feats = self._features(scope_key)

        if len(feats) < self.seq_len:
            raise ValueError(f"Scope '{scope_key}' has insufficient history ({len(feats)} < {self.seq_len}).")

        x = torch.from_numpy(feats[-self.seq_len :][None, :, :]).to(self.device)
        with torch.no_grad():
            pred_z = self.model(x).cpu().numpy()[0]
        pred = np.clip(pred_z * std + mean, 0.0, None)

        last_date = self.dates[-1]
        margin = 1.96 * self.residual_sigma
        forecast_days = []
        for step in range(self.forecast_horizon):
            value = float(pred[step])
            forecast_days.append({
                "day": step + 1,
                "date": (last_date + pd.Timedelta(days=step + 1)).date().isoformat(),
                "predicted_count": round(value, 2),
                "lower_bound_95": round(max(0.0, value - margin), 2),
                "upper_bound_95": round(value + margin, 2),
            })

        history = [
            {"date": self.dates[i].date().isoformat(), "count": round(float(counts[i]), 2)}
            for i in range(max(0, len(counts) - history_days), len(counts))
        ]

        backtest = self.backtest(scope_key)
        actual = np.array([r["actual"] for r in backtest], dtype="float64")
        predicted = np.array([r["predicted"] for r in backtest], dtype="float64")
        if len(actual):
            from ai.forecasting.evaluate import regression_metrics
            scope_test_metrics = regression_metrics(actual, predicted)
        else:
            scope_test_metrics = {}

        return {
            "success": True,
            "scope_key": scope_key,
            "scope_type": meta["scope_type"],
            "scope_display_name": meta["display_name"],
            "model_name": "CrimeGRUForecaster",
            "model_version": self.registry_dir.name,
            "sequence_length": self.seq_len,
            "forecast_horizon_days": self.forecast_horizon,
            "last_observed_date": last_date.date().isoformat(),
            "historical": history,
            "forecast": forecast_days,
            "actual_vs_predicted": backtest,
            "scope_test_metrics": scope_test_metrics,
            "test_metrics": self._metrics.get("test", {}),
            "per_horizon_metrics": self._metrics.get("per_horizon", {}),
            "evaluation_summary": {
                "dataset_hash_md5": self._evaluation.get("dataset_hash_md5"),
                "splits": self._evaluation.get("splits"),
                "test_windows": self._evaluation.get("test_windows"),
                "n_scopes": self._evaluation.get("n_scopes"),
                "evaluation_date": self._evaluation.get("evaluation_date"),
                "honest_note": self._evaluation.get("honest_note"),
            },
            "uncertainty_method": "±1.96 × held-out test RMSE (empirical 95% interval)",
            "disclaimer": DISCLAIMER,
        }


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run a sample GRU forecast for one scope.")
    parser.add_argument("--scope", default="city:Delhi", help="Scope key, e.g. city:Delhi or crime_type:BURGLARY")
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY_DIR))
    parser.add_argument("--list-scopes", action="store_true", help="Print every supported scope and exit")
    args = parser.parse_args()

    predictor = CrimeForecastPredictor(args.registry_dir)

    if args.list_scopes:
        for scope in sorted(predictor.available_scopes(), key=lambda s: s["key"]):
            print(f"{scope['key']:<32} {scope['display_name']}")
        return

    if not predictor.scope_exists(args.scope):
        print(f"Unknown scope '{args.scope}'.")
        print("Use --list-scopes to see all valid keys, e.g. city:Delhi or crime_type:BURGLARY.")
        raise SystemExit(2)

    result = predictor.forecast(args.scope)
    print(f"\nScope: {result['scope_display_name']} ({result['scope_type']})")
    print(f"Last observed: {result['last_observed_date']} | model: {result['model_name']} {result['model_version']}")
    print("-" * 64)
    for f in result["forecast"]:
        print(f"Day +{f['day']}  {f['date']}  {f['predicted_count']:>6.2f}  "
              f"[{f['lower_bound_95']:.2f}, {f['upper_bound_95']:.2f}]")
    print("-" * 64)
    print("Test metrics:", json.dumps(result["test_metrics"], indent=2))


if __name__ == "__main__":
    _main()
