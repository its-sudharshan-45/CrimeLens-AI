"""
ai/tests/test_forecasting.py
============================
Automated tests for the single CrimeLens AI model: the GRU crime-count
forecaster and its data / evaluation / inference pipeline.

Coverage:
  1.  Raw dataset loads with the correct MM-DD-YYYY date parsing.
  2.  Per-scope daily series are gap-free and aggregate real incident counts.
  3.  Per-scope normalisation statistics are fitted on the TRAIN window only
      (no leakage into validation/test).
  4.  Calendar features are bounded and deterministic.
  5.  Chronological windows never look ahead and val/test reuse prior context.
  6.  Regression metrics match independently computed values.
  7.  The persistence baseline repeats the last observation.
  8.  The GRU forward pass produces a (batch, horizon) forecast.
  9.  The end-to-end predictor serves a genuine, honest forecast (skipped if the
      trained checkpoint is absent).

No test fabricates metrics or presents synthetic numbers as model performance.
"""

import os
import sys

import numpy as np
import pytest
import torch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.forecasting import data as fdata
from ai.forecasting import evaluate as feval
from ai.models.temporal.gru import CrimeGRUForecaster

RAW_DATASET_PATH = os.path.join(PROJECT_ROOT, "Dataset", "crime_dataset_india.csv")
FORECAST_CKPT = os.path.join(PROJECT_ROOT, "ai", "registry", "forecast_v1", "gru_forecaster.pt")


@pytest.fixture(scope="module")
def raw_df():
    if not os.path.exists(RAW_DATASET_PATH):
        pytest.skip("raw dataset missing")
    return fdata.load_raw_dataset()


@pytest.fixture(scope="module")
def scopes(raw_df):
    return fdata.build_all_scope_series(raw_df)


# =====================================================================
# 1. DATASET LOADING & DATE PARSING
# =====================================================================

def test_raw_dataset_shape_and_date_range(raw_df):
    assert len(raw_df) > 0
    assert raw_df["date"].min().strftime("%Y-%m-%d") == fdata.DATE_START
    assert raw_df["date"].max().strftime("%Y-%m-%d") == fdata.DATE_END
    # MM-DD-YYYY parsing: the dataset starts on 2020-01-01 (a leap-compatible year).
    assert raw_df["date"].dt.year.min() == 2020


def test_date_parsing_is_not_dayfirst():
    """A known MM-DD-YYYY string must parse to the US ordering, not day-first."""
    parsed = fdata.pd.to_datetime("01-02-2020 13:00", errors="coerce", dayfirst=False)
    assert parsed.month == 1 and parsed.day == 2


# =====================================================================
# 2. SCOPE SERIES
# =====================================================================

def test_scope_series_are_gap_free(scopes):
    expected_days = len(fdata.pd.date_range(fdata.DATE_START, fdata.DATE_END, freq="D"))
    assert len(scopes) >= 40  # ~29 cities + ~21 crime types
    for key, series in scopes.items():
        assert len(series.counts) == expected_days, key
        assert np.all(series.counts >= 0)
        assert series.counts.dtype == np.float64


def test_scope_series_sum_matches_totals(raw_df, scopes):
    """Summing all city series must equal the full incident count."""
    city_keys = [k for k in scopes if k.startswith("city:")]
    total = sum(scopes[k].counts.sum() for k in city_keys)
    assert int(total) == len(raw_df)


# =====================================================================
# 3. LEAKAGE-FREE NORMALISATION STATISTICS
# =====================================================================

def test_scope_stats_fit_on_train_window_only(scopes):
    series = scopes["city:Delhi"]
    train_mask = (series.dates >= fdata.pd.Timestamp(fdata.TRAIN_START)) & (
        series.dates <= fdata.pd.Timestamp(fdata.TRAIN_END)
    )
    assert series.mean == pytest.approx(float(np.mean(series.counts[train_mask])))
    # The full-series mean differs (proves test/val data was not used).
    assert series.mean != pytest.approx(float(np.mean(series.counts)))
    assert series.metadata["n_train_days"] == int(train_mask.sum())


# =====================================================================
# 4. CALENDAR FEATURES
# =====================================================================

def test_calendar_features_bounds_and_determinism():
    dates = fdata.pd.date_range("2024-01-01", periods=60, freq="D")
    feats = fdata.calendar_features(dates)
    assert feats.shape == (60, len(fdata.FORECAST_FEATURE_COLUMNS) - 1)
    assert np.all(feats[:, [0, 1, 3, 4]] >= -1.0001)
    assert np.all(feats[:, [0, 1, 3, 4]] <= 1.0001)
    assert set(np.unique(feats[:, 2]).tolist()) <= {0.0, 1.0}
    np.testing.assert_array_equal(feats, fdata.calendar_features(dates))


# =====================================================================
# 5. WINDOWING & SPLITS (NO LEAKAGE)
# =====================================================================

def test_windows_are_shape_correct_and_aligned(scopes):
    series = scopes["city:Mumbai"]
    feats = fdata.scope_feature_matrix(series)
    X, y = fdata._windows(feats, series.key, fdata.SEQ_LEN, fdata.FORECAST_HORIZON)
    assert X.shape[1:] == (fdata.SEQ_LEN, len(fdata.FORECAST_FEATURE_COLUMNS))
    assert y.shape[1] == fdata.FORECAST_HORIZON
    # The first target is the z-count exactly one step after the first window.
    assert y[0, 0] == pytest.approx(feats[fdata.SEQ_LEN, 0])
    # Targets are the *future* count feature; no window contains its own target.
    assert X[0, -1, 0] == pytest.approx(feats[fdata.SEQ_LEN - 1, 0])


def test_build_dataset_split_counts_and_features(scopes):
    ds = fdata.build_dataset(scopes)
    assert ds.X_train.shape[2] == len(fdata.FORECAST_FEATURE_COLUMNS)
    assert ds.metadata["train_windows"] > 0
    assert ds.metadata["val_windows"] > 0
    assert ds.metadata["test_windows"] > 0
    assert len(ds.scope_index["test"]) == len(ds.X_test)
    assert set(ds.metadata["train_dates"]) == {fdata.TRAIN_START, fdata.TRAIN_END}
    # Validation/test must be strictly after training.
    assert fdata.VAL_START > fdata.TRAIN_END
    assert fdata.TEST_START > fdata.VAL_END


# =====================================================================
# 6. METRICS CORRECTNESS
# =====================================================================

def test_regression_metrics_match_reference_values():
    actual = np.array([10.0, 20.0, 30.0])
    predicted = np.array([12.0, 18.0, 33.0])
    m = feval.regression_metrics(actual, predicted)

    assert m["MAE"] == pytest.approx(7.0 / 3.0, abs=1e-3)
    assert m["RMSE"] == pytest.approx(np.sqrt(17.0 / 3.0), abs=1e-3)
    assert m["WAPE"] == pytest.approx(7.0 / 60.0, abs=1e-3)
    assert m["R2"] == pytest.approx(1.0 - 17.0 / 200.0, abs=1e-3)
    assert m["n_observations"] == 3


def test_smape_handles_zero_actual():
    assert np.isnan(feval.smape(np.array([0.0]), np.array([0.0])))
    assert feval.smape(np.array([0.0, 10.0]), np.array([0.0, 10.0])) == pytest.approx(0.0)


# =====================================================================
# 7. PERSISTENCE BASELINE
# =====================================================================

def test_persistence_repeats_last_observation():
    last = np.array([5.0, 8.0])
    out = feval.persistence_forecast(last, 3)
    assert out.shape == (2, 3)
    np.testing.assert_array_equal(out, [[5.0, 5.0, 5.0], [8.0, 8.0, 8.0]])


# =====================================================================
# 8. GRU FORWARD PASS
# =====================================================================

def test_gru_forward_shape():
    model = CrimeGRUForecaster(
        input_size=len(fdata.FORECAST_FEATURE_COLUMNS),
        hidden_size=32,
        num_layers=1,
        forecast_horizon=fdata.FORECAST_HORIZON,
    )
    model.eval()
    x = torch.randn(4, fdata.SEQ_LEN, len(fdata.FORECAST_FEATURE_COLUMNS))
    with torch.no_grad():
        out = model(x)
    assert out.shape == (4, fdata.FORECAST_HORIZON)
    assert torch.all(torch.isfinite(out))


# =====================================================================
# 9. END-TO-END PREDICTOR (real artifacts)
# =====================================================================

@pytest.mark.skipif(not os.path.exists(FORECAST_CKPT), reason="trained forecaster checkpoint missing")
def test_predictor_serves_genuine_forecast():
    from ai.forecasting.predict import CrimeForecastPredictor

    predictor = CrimeForecastPredictor()
    scopes_meta = predictor.available_scopes()
    assert len(scopes_meta) >= 40

    city = next(s for s in scopes_meta if s["scope_type"] == "city")
    result = predictor.forecast(city["key"])

    assert len(result["forecast"]) == fdata.FORECAST_HORIZON
    assert len(result["historical"]) > 0
    # Forecast dates strictly follow the last observed date.
    assert result["forecast"][0]["date"] > result["last_observed_date"]
    # Uncertainty bounds bracket the point estimate.
    for day in result["forecast"]:
        assert day["lower_bound_95"] <= day["predicted_count"] <= day["upper_bound_95"]

    # The backtest covers the held-out test window and reports honest metrics.
    assert len(result["actual_vs_predicted"]) > 0
    assert "MAE" in result["test_metrics"]["model"]
    assert "MAE" in result["test_metrics"]["persistence_baseline"]
    assert len(result["disclaimer"]) > 0


@pytest.mark.skipif(not os.path.exists(FORECAST_CKPT), reason="trained forecaster checkpoint missing")
def test_saved_metrics_are_internally_consistent():
    import json

    with open(os.path.join(PROJECT_ROOT, "ai", "registry", "forecast_v1", "metrics.json"), encoding="utf-8") as fh:
        metrics = json.load(fh)
    model = metrics["test"]["model"]
    baseline = metrics["test"]["persistence_baseline"]
    for m in (model, baseline):
        assert m["MAE"] > 0
        assert m["RMSE"] >= m["MAE"]  # RMSE is always >= MAE for the same errors
        assert 0 <= m["WAPE"] <= 1.5
        assert m["n_observations"] > 0
