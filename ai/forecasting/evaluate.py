"""
ai/forecasting/evaluate.py
==========================
Honest regression metrics for the GRU crime-count forecaster.

All metrics are computed on real, held-out (test) observations.  No value in
this module is hardcoded or randomised.  A **persistence baseline** (repeat the
last observed count for every future day) is reported alongside the model so
readers can judge whether the network adds any skill.
"""

from __future__ import annotations

import numpy as np


def _finite(a: np.ndarray) -> np.ndarray:
    return np.asarray(a, dtype="float64")


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual, predicted = _finite(actual), _finite(predicted)
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual, predicted = _finite(actual), _finite(predicted)
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Weighted absolute percentage error: sum|err| / sum|actual| (0..1+)."""
    actual, predicted = _finite(actual), _finite(predicted)
    denom = np.sum(np.abs(actual))
    if denom <= 1e-8:
        return float("nan")
    return float(np.sum(np.abs(actual - predicted)) / denom)


def smape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Symmetric MAPE as a fraction (0..2); robust when actual values are zero."""
    actual, predicted = _finite(actual), _finite(predicted)
    denom = np.abs(actual) + np.abs(predicted)
    mask = denom > 1e-8
    if not np.any(mask):
        return float("nan")
    return float(np.mean(2.0 * np.abs(predicted[mask] - actual[mask]) / denom[mask]))


def r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual, predicted = _finite(actual), _finite(predicted)
    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    if ss_tot <= 1e-12:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """Bundle the headline metrics into one dictionary."""
    return {
        "MAE": round(mae(actual, predicted), 4),
        "RMSE": round(rmse(actual, predicted), 4),
        "WAPE": round(wape(actual, predicted), 4),
        "sMAPE": round(smape(actual, predicted), 4),
        "R2": round(r2(actual, predicted), 4),
        "n_observations": int(np.size(actual)),
    }


def persistence_forecast(last_observed: np.ndarray, horizon: int) -> np.ndarray:
    """Persistence baseline: repeat the last observed count ``horizon`` times.

    ``last_observed`` is shape (n_windows,) — the final input-window count per
    window; returns shape (n_windows, horizon).
    """
    last = _finite(last_observed).reshape(-1, 1)
    return np.repeat(last, horizon, axis=1)


def per_horizon_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, dict[str, float]]:
    """Metrics broken out by forecast step (Day +1 .. Day +H)."""
    actual = _finite(actual)
    predicted = _finite(predicted)
    horizon = actual.shape[1]
    out: dict[str, dict[str, float]] = {}
    for step in range(horizon):
        out[f"Day +{step + 1}"] = regression_metrics(actual[:, step], predicted[:, step])
    return out


def per_scope_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    scope_index: np.ndarray,
    scope_keys: list[str],
) -> dict[str, dict[str, float]]:
    """Aggregate metrics per scope (all horizon steps pooled)."""
    actual = _finite(actual)
    predicted = _finite(predicted)
    out: dict[str, dict[str, float]] = {}
    for key in scope_keys:
        mask = scope_index == key
        if not np.any(mask):
            continue
        out[key] = regression_metrics(actual[mask].ravel(), predicted[mask].ravel())
    return out
