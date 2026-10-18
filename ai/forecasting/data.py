"""
ai/forecasting/data.py
======================
Dataset construction for the CrimeLens AI GRU crime-count forecaster.

Dataset facts (verified against ``Dataset/crime_dataset_india.csv``)
-------------------------------------------------------------------
* 40,160 rows x 14 columns.
* ``Date of Occurrence`` is stored as **MM-DD-YYYY HH:MM** (US ordering).
* Exactly **24 incidents per calendar day** for every complete day between
  2020-01-01 and 2024-07-30.  The final day (2024-07-31) is an incomplete
  8-row stub and is dropped.
* Because the national daily total is constant, a national ``total_crimes``
  target is degenerate (this is why the historical GRU forecast was flat).
  City-level and crime-type-level daily counts *do* vary, so we build one
  continuous daily count series per **scope** (a city or a crime description).

No value in this module is fabricated: every series is aggregated directly from
the raw CSV and the calendar is zero-filled so the daily frequency is honest.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Paths & constants ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "Dataset" / "crime_dataset_india.csv"

# Chronological boundaries.  ``DATE_END`` is the last *complete* day.
DATE_START = "2020-01-01"
DATE_END = "2024-07-30"
TRAIN_START, TRAIN_END = "2020-01-01", "2022-12-31"
VAL_START, VAL_END = "2023-01-01", "2023-12-31"
TEST_START, TEST_END = "2024-01-01", "2024-07-30"

# Supported forecasting scopes.
SCOPE_TYPES = ("city", "crime_type")

# Input window and forecast horizon (30-day lookback, 7-day horizon).
SEQ_LEN = 30
FORECAST_HORIZON = 7

# Ordered model input features.
FORECAST_FEATURE_COLUMNS = [
    "count_z",       # per-scope z-scored daily count (train-fitted statistics)
    "sin_weekday",
    "cos_weekday",
    "is_weekend",
    "sin_month",
    "cos_month",
]


@dataclass
class ScopeSeries:
    """A single scope's continuous daily count series."""

    key: str                       # e.g. "city:Delhi" / "crime_type:BURGLARY"
    scope_type: str                # "city" | "crime_type"
    display_name: str              # "Delhi" / "BURGLARY"
    dates: pd.DatetimeIndex
    counts: np.ndarray             # float64, aligned to ``dates``
    mean: float = 0.0              # train-only mean (filled by fit_scope_stats)
    std: float = 1.0               # train-only std  (filled by fit_scope_stats)
    metadata: dict = field(default_factory=dict)


def load_raw_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> pd.DataFrame:
    """Load and validate the raw incident CSV.

    Dates are parsed with the correct MM-DD-YYYY ordering (``dayfirst=False``).
    Rows with an unparseable occurrence date or a missing City / Crime
    Description are dropped and counted.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)
    required = {"Date of Occurrence", "City", "Crime Description"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")

    before = len(df)
    df["date"] = pd.to_datetime(df["Date of Occurrence"], errors="coerce", dayfirst=False)
    df = df.dropna(subset=["date", "City", "Crime Description"]).copy()
    df["date"] = df["date"].dt.normalize()
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped %d rows with unparseable/missing key fields.", dropped)

    # Drop the incomplete final calendar day (fewer than the modal daily count).
    per_day = df.groupby("date").size()
    modal = int(per_day.mode().iloc[0])
    incomplete = per_day[per_day < modal]
    if len(incomplete):
        cutoff = incomplete.index.max()
        df = df[df["date"] < cutoff].copy()
        logger.info("Dropped incomplete trailing day(s) up to %s.", cutoff.date())

    df = df[(df["date"] >= pd.Timestamp(DATE_START)) & (df["date"] <= pd.Timestamp(DATE_END))]
    logger.info("Loaded %d validated incident rows (%s -> %s).", len(df), df["date"].min().date(), df["date"].max().date())
    return df


def _calendar_index() -> pd.DatetimeIndex:
    """Complete, gap-free daily calendar index for the dataset window."""
    return pd.date_range(DATE_START, DATE_END, freq="D")


def build_scope_series(df: pd.DataFrame, scope_type: str) -> dict[str, ScopeSeries]:
    """Aggregate the raw incidents into one continuous daily series per scope."""
    if scope_type not in SCOPE_TYPES:
        raise ValueError(f"Unsupported scope_type '{scope_type}'. Expected one of {SCOPE_TYPES}")

    column = "City" if scope_type == "city" else "Crime Description"
    calendar = _calendar_index()
    per_scope: dict[str, ScopeSeries] = {}

    for value, group in df.groupby(column):
        counts = group.groupby("date").size().reindex(calendar, fill_value=0).astype("float64")
        per_scope[f"{scope_type}:{value}"] = ScopeSeries(
            key=f"{scope_type}:{value}",
            scope_type=scope_type,
            display_name=str(value),
            dates=calendar,
            counts=counts.to_numpy(dtype="float64"),
        )

    logger.info("Built %d '%s' scope series.", len(per_scope), scope_type)
    return per_scope


def fit_scope_stats(series: ScopeSeries) -> None:
    """Fit per-scope mean/std on the **training** window only (no leakage)."""
    mask = (series.dates >= pd.Timestamp(TRAIN_START)) & (series.dates <= pd.Timestamp(TRAIN_END))
    train_counts = series.counts[mask]
    series.mean = float(np.mean(train_counts))
    std = float(np.std(train_counts))
    series.std = std if std > 1e-8 else 1.0
    series.metadata = {
        "train_mean": round(series.mean, 6),
        "train_std": round(series.std, 6),
        "train_min": float(np.min(train_counts)),
        "train_max": float(np.max(train_counts)),
        "n_train_days": int(mask.sum()),
    }


def calendar_features(dates: pd.DatetimeIndex) -> np.ndarray:
    """Date-derived cyclical features (zero leakage, deterministic)."""
    weekday = dates.dayofweek.to_numpy().astype("float64")
    month = dates.month.to_numpy().astype("float64")
    return np.column_stack(
        [
            np.sin(2 * np.pi * weekday / 7.0),
            np.cos(2 * np.pi * weekday / 7.0),
            (weekday >= 5).astype("float64"),
            np.sin(2 * np.pi * month / 12.0),
            np.cos(2 * np.pi * month / 12.0),
        ]
    ).astype("float32")


def scope_feature_matrix(series: ScopeSeries) -> np.ndarray:
    """Full (T, F) feature matrix for a scope using its train-fitted statistics."""
    count_z = (series.counts - series.mean) / series.std
    return np.column_stack([count_z, calendar_features(series.dates)]).astype("float32")


@dataclass
class ForecastDataset:
    """Windowed, leakage-free tensors plus provenance metadata for training."""

    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    scope_index: dict[str, np.ndarray]   # split -> int array mapping window -> scope key
    scope_keys: list[str]
    metadata: dict


def _windows(features: np.ndarray, scope_key: str, seq_len: int, horizon: int):
    """Sliding windows over a single scope's feature matrix."""
    n = len(features)
    xs, ys = [], []
    for i in range(n - seq_len - horizon + 1):
        xs.append(features[i : i + seq_len])
        # target = scale-free z-count of the *next* ``horizon`` days (feature 0)
        ys.append(features[i + seq_len : i + seq_len + horizon, 0])
    X = np.asarray(xs, dtype="float32")
    y = np.asarray(ys, dtype="float32")
    return X, y


def _split_slices(dates: pd.DatetimeIndex, lo: str, hi: str) -> slice | None:
    mask = (dates >= pd.Timestamp(lo)) & (dates <= pd.Timestamp(hi))
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return None
    return slice(int(idx[0]), int(idx[-1]) + 1)


def build_dataset(
    scopes: dict[str, ScopeSeries],
    seq_len: int = SEQ_LEN,
    horizon: int = FORECAST_HORIZON,
) -> ForecastDataset:
    """Build pooled train/val/test window tensors for all scopes.

    * Scalers are fitted on training data only (``fit_scope_stats`` must be
      called before this function).
    * Validation and test windows are given a context tail from the preceding
      split so every prediction uses only past observations.
    """
    train_X, train_y, val_X, val_y, test_X, test_y = [], [], [], [], [], []
    train_s, val_s, test_s = [], [], []

    for key, series in scopes.items():
        feats = scope_feature_matrix(series)
        d = series.dates
        tr = _split_slices(d, TRAIN_START, TRAIN_END)
        va = _split_slices(d, VAL_START, VAL_END)
        te = _split_slices(d, TEST_START, TEST_END)

        tr_X, tr_y = _windows(feats[tr], key, seq_len, horizon)
        if len(tr_X):
            train_X.append(tr_X)
            train_y.append(tr_y)
            train_s.append(np.full(len(tr_X), key, dtype=object))

        # Validation: prepend the last ``seq_len`` training days as context.
        val_ctx = np.concatenate([feats[tr][-seq_len:], feats[va]])
        va_X, va_y = _windows(val_ctx, key, seq_len, horizon)
        if len(va_X):
            val_X.append(va_X)
            val_y.append(va_y)
            val_s.append(np.full(len(va_X), key, dtype=object))

        # Test: prepend the last ``seq_len`` validation days as context.
        test_ctx = np.concatenate([feats[va][-seq_len:], feats[te]])
        te_X, te_y = _windows(test_ctx, key, seq_len, horizon)
        if len(te_X):
            test_X.append(te_X)
            test_y.append(te_y)
            test_s.append(np.full(len(te_X), key, dtype=object))

    def _cat(parts):
        return np.concatenate(parts) if parts else np.empty((0, seq_len, len(FORECAST_FEATURE_COLUMNS)), dtype="float32")

    metadata = {
        "seq_len": seq_len,
        "forecast_horizon": horizon,
        "n_features": len(FORECAST_FEATURE_COLUMNS),
        "feature_columns": list(FORECAST_FEATURE_COLUMNS),
        "scope_types": list(SCOPE_TYPES),
        "n_scopes": len(scopes),
        "train_dates": [TRAIN_START, TRAIN_END],
        "val_dates": [VAL_START, VAL_END],
        "test_dates": [TEST_START, TEST_END],
        "train_windows": int(sum(len(x) for x in train_X)),
        "val_windows": int(sum(len(x) for x in val_X)),
        "test_windows": int(sum(len(x) for x in test_X)),
    }
    logger.info(
        "Dataset built: %d train / %d val / %d test windows over %d scopes.",
        metadata["train_windows"], metadata["val_windows"], metadata["test_windows"], len(scopes),
    )

    return ForecastDataset(
        X_train=_cat(train_X), y_train=_cat(train_y),
        X_val=_cat(val_X), y_val=_cat(val_y),
        X_test=_cat(test_X), y_test=_cat(test_y),
        scope_index={
            "train": np.concatenate(train_s) if train_s else np.empty(0, dtype=object),
            "val": np.concatenate(val_s) if val_s else np.empty(0, dtype=object),
            "test": np.concatenate(test_s) if test_s else np.empty(0, dtype=object),
        },
        scope_keys=list(scopes.keys()),
        metadata=metadata,
    )


def build_all_scope_series(df: pd.DataFrame) -> dict[str, ScopeSeries]:
    """Build and fit every supported scope (all cities + all crime types)."""
    scopes: dict[str, ScopeSeries] = {}
    for scope_type in SCOPE_TYPES:
        scopes.update(build_scope_series(df, scope_type))
    for series in scopes.values():
        fit_scope_stats(series)
    return scopes
