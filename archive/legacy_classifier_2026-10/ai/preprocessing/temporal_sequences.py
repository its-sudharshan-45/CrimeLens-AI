"""
ai/preprocessing/temporal_sequences.py
======================================
Temporal aggregation, sequence generation, and chronological split utilities.
Implements zero-leakage sliding window sequences for LSTM/GRU forecasting models.

Supports both:
  - Univariate 1D sequences (legacy, backward-compatible)
  - Multivariate sequences using all available daily crime features (Phase 3+)
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Strict Chronological Date Boundaries
TRAIN_START_DATE = "2020-01-01"
TRAIN_END_DATE = "2022-12-31"

VAL_START_DATE = "2023-01-01"
VAL_END_DATE = "2023-12-31"

TEST_START_DATE = "2024-01-01"
TEST_END_DATE = "2024-07-31"

# All 13 features used in multivariate LSTM/GRU input sequences.
# 8 from daily national crime aggregation + 5 derived calendar cyclical features.
MULTIVARIATE_FEATURE_COLS = [
    # Crime counts by domain (national daily totals)
    "total_crimes",
    "violent_crimes",
    "other_crimes",
    "fire_accidents",
    "traffic_fatalities",
    # Operations features
    "avg_police_deployed",
    "case_closure_rate",
    "avg_victim_age",
    # Temporal cyclical features (derived from date, zero leakage)
    "sin_month",
    "cos_month",
    "sin_weekday",
    "cos_weekday",
    "is_weekend",
]

# Target column for forecasting: next-N-day national total crimes
TARGET_COL = "total_crimes"


def aggregate_temporal_crimes(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate clean temporal aggregated datasets:
    1. Detailed daily count by (date, city, crime_type, crime_count).
    2. City daily total count (date, city, total_crimes).
    """
    df = df.copy()

    if "Date of Occurrence" in df.columns:
        dt = pd.to_datetime(df["Date of Occurrence"])
        df["date"] = dt.dt.date
    else:
        raise ValueError("Missing 'Date of Occurrence' column for temporal aggregation.")

    city_col = "City" if "City" in df.columns else "city"
    crime_col = "Crime Description" if "Crime Description" in df.columns else "Crime Type"

    detailed_agg = (
        df.groupby(["date", city_col, crime_col], as_index=False)
        .size()
        .rename(columns={city_col: "city", crime_col: "crime_type", "size": "crime_count"})
    )
    detailed_agg["date"] = pd.to_datetime(detailed_agg["date"])
    detailed_agg = detailed_agg.sort_values(by=["date", "city", "crime_type"]).reset_index(drop=True)

    city_daily_agg = (
        df.groupby(["date", city_col], as_index=False)
        .size()
        .rename(columns={city_col: "city", "size": "crime_count"})
    )
    city_daily_agg["date"] = pd.to_datetime(city_daily_agg["date"])
    city_daily_agg = city_daily_agg.sort_values(by=["date", "city"]).reset_index(drop=True)

    return detailed_agg, city_daily_agg


def build_continuous_daily_series(
    df: pd.DataFrame,
    start_date: str = TRAIN_START_DATE,
    end_date: str = TEST_END_DATE,
) -> pd.DataFrame:
    """
    Construct a complete, unbroken daily calendar time series across all dates.
    Fills zero counts for dates with no recorded incidents.
    """
    df = df.copy()
    if "Date of Occurrence" in df.columns:
        df["date"] = pd.to_datetime(df["Date of Occurrence"]).dt.date
    daily_counts = df.groupby("date").size().reset_index(name="incident_count")
    daily_counts["date"] = pd.to_datetime(daily_counts["date"])

    full_date_idx = pd.date_range(start=start_date, end=end_date, freq="D")
    full_df = pd.DataFrame({"date": full_date_idx})
    merged = pd.merge(full_df, daily_counts, on="date", how="left").fillna({"incident_count": 0})
    merged["incident_count"] = merged["incident_count"].astype(float)
    return merged.sort_values("date").reset_index(drop=True)


def build_multivariate_daily_series(
    df: pd.DataFrame,
    start_date: str = TRAIN_START_DATE,
    end_date: str = TEST_END_DATE,
) -> pd.DataFrame:
    """
    Build a multivariate daily feature dataframe for LSTM/GRU temporal forecasting.

    Aggregates the following national-level daily features from raw incident data:
      - total_crimes: count of all incidents
      - violent_crimes: count of Violent Crime domain incidents
      - other_crimes: count of Other Crime domain incidents
      - fire_accidents: count of Fire Accident domain incidents
      - traffic_fatalities: count of Traffic Fatality domain incidents
      - avg_police_deployed: mean police units deployed per incident
      - case_closure_rate: fraction of cases marked closed
      - avg_victim_age: mean victim age

    Then derives calendar-based cyclical features (zero leakage, purely date-derived):
      - sin_month, cos_month, sin_weekday, cos_weekday, is_weekend

    Zero-fills days with no incidents.

    Returns pd.DataFrame with columns:
      [date, total_crimes, violent_crimes, ..., sin_month, ..., is_weekend]
    sorted ascending with no calendar gaps.
    """
    df = df.copy()

    if "Date of Occurrence" not in df.columns:
        raise ValueError("Missing 'Date of Occurrence' column for multivariate daily series.")

    df["date"] = pd.to_datetime(df["Date of Occurrence"]).dt.date

    df["is_violent"] = (df["Crime Domain"] == "Violent Crime").astype(int) if "Crime Domain" in df.columns else 0
    df["is_other"] = (df["Crime Domain"] == "Other Crime").astype(int) if "Crime Domain" in df.columns else 0
    df["is_fire"] = (df["Crime Domain"] == "Fire Accident").astype(int) if "Crime Domain" in df.columns else 0
    df["is_traffic"] = (df["Crime Domain"] == "Traffic Fatality").astype(int) if "Crime Domain" in df.columns else 0
    df["is_closed"] = (df["Case Closed"] == "Yes").astype(int) if "Case Closed" in df.columns else 0

    agg_dict: Dict[str, Any] = {
        "Report Number": "count",
        "is_violent": "sum",
        "is_other": "sum",
        "is_fire": "sum",
        "is_traffic": "sum",
        "is_closed": "mean",
    }
    if "Police Deployed" in df.columns:
        agg_dict["Police Deployed"] = "mean"
    if "Victim Age" in df.columns:
        agg_dict["Victim Age"] = "mean"

    daily_agg = df.groupby("date").agg(agg_dict).reset_index()
    daily_agg = daily_agg.rename(columns={
        "Report Number": "total_crimes",
        "is_violent": "violent_crimes",
        "is_other": "other_crimes",
        "is_fire": "fire_accidents",
        "is_traffic": "traffic_fatalities",
        "is_closed": "case_closure_rate",
        "Police Deployed": "avg_police_deployed",
        "Victim Age": "avg_victim_age",
    })
    daily_agg["date"] = pd.to_datetime(daily_agg["date"])

    # Build full calendar index and merge (zero-fill missing days)
    full_date_idx = pd.date_range(start=start_date, end=end_date, freq="D")
    full_df = pd.DataFrame({"date": full_date_idx})
    merged = pd.merge(full_df, daily_agg, on="date", how="left")

    for col in ["total_crimes", "violent_crimes", "other_crimes", "fire_accidents", "traffic_fatalities"]:
        merged[col] = merged[col].fillna(0.0).astype(float)
    merged["avg_police_deployed"] = merged["avg_police_deployed"].fillna(0.0).astype(float)
    merged["case_closure_rate"] = merged["case_closure_rate"].fillna(0.0).astype(float)
    merged["avg_victim_age"] = merged["avg_victim_age"].fillna(0.0).astype(float)

    # Calendar cyclical features — purely date-derived, zero leakage
    merged["sin_month"] = np.sin(2 * np.pi * merged["date"].dt.month / 12.0)
    merged["cos_month"] = np.cos(2 * np.pi * merged["date"].dt.month / 12.0)
    merged["sin_weekday"] = np.sin(2 * np.pi * merged["date"].dt.dayofweek / 7.0)
    merged["cos_weekday"] = np.cos(2 * np.pi * merged["date"].dt.dayofweek / 7.0)
    merged["is_weekend"] = merged["date"].dt.dayofweek.isin([5, 6]).astype(float)

    merged = merged.sort_values("date").reset_index(drop=True)
    logger.info(
        f"Multivariate daily series built: {len(merged)} days, "
        f"{len(MULTIVARIATE_FEATURE_COLS)} features, "
        f"range: {merged['date'].min().date()} -> {merged['date'].max().date()}"
    )
    return merged


def create_sliding_window_sequences(
    series: np.ndarray,
    seq_len: int = 30,
    forecast_horizon: int = 1,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Reusable sliding window sequence generation utility.

    Accepts either a 1D array (univariate) or a 2D array (T_timesteps, N_features).

    Returns:
      X_seq:    shape (N_samples, seq_len, n_features)
      y_target: shape (N_samples, forecast_horizon)
                Target is always the FIRST feature column (index 0), i.e. total_crimes.
    """
    if series.ndim == 1:
        series = series.reshape(-1, 1)

    total_len = len(series)
    if total_len < seq_len + forecast_horizon:
        raise ValueError(
            f"Series length {total_len} < seq_len + forecast_horizon ({seq_len + forecast_horizon})"
        )

    X_list: List[np.ndarray] = []
    y_list: List[np.ndarray] = []

    for i in range(total_len - seq_len - forecast_horizon + 1):
        x_window = series[i: i + seq_len, :]
        y_window = series[i + seq_len: i + seq_len + forecast_horizon, 0]
        X_list.append(x_window)
        y_list.append(y_window)

    X_arr = np.array(X_list, dtype=np.float32)   # (N, seq_len, n_features)
    y_arr = np.array(y_list, dtype=np.float32)    # (N, forecast_horizon)

    if forecast_horizon == 1:
        y_arr = y_arr.squeeze(-1)

    return X_arr, y_arr


class TemporalSequencePipeline:
    """
    Manages chronological splitting, scaling without data leakage,
    and sequence generation across train, validation, and test splits.

    Supports both univariate (legacy) and multivariate feature sequences.
    """

    def __init__(
        self,
        seq_len: int = 30,
        forecast_horizon: int = 7,
        train_dates: Tuple[str, str] = (TRAIN_START_DATE, TRAIN_END_DATE),
        val_dates: Tuple[str, str] = (VAL_START_DATE, VAL_END_DATE),
        test_dates: Tuple[str, str] = (TEST_START_DATE, TEST_END_DATE),
    ) -> None:
        self.seq_len = seq_len
        self.forecast_horizon = forecast_horizon
        self.train_dates = train_dates
        self.val_dates = val_dates
        self.test_dates = test_dates
        self.scaler = MinMaxScaler(feature_range=(0.0, 1.0))
        self.is_fitted = False
        self.split_metadata: Dict[str, Any] = {}

    def split_chronological(
        self, df: pd.DataFrame, date_col: str = "date"
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split a dataframe chronologically using verified boundaries.
        Guarantees: max(train) < min(val) and max(val) < min(test).
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        train_mask = (df[date_col] >= self.train_dates[0]) & (df[date_col] <= self.train_dates[1])
        val_mask = (df[date_col] >= self.val_dates[0]) & (df[date_col] <= self.val_dates[1])
        test_mask = (df[date_col] >= self.test_dates[0]) & (df[date_col] <= self.test_dates[1])

        df_train = df[train_mask].sort_values(date_col).reset_index(drop=True)
        df_val = df[val_mask].sort_values(date_col).reset_index(drop=True)
        df_test = df[test_mask].sort_values(date_col).reset_index(drop=True)

        logger.info(
            f"Chronological split: Train={len(df_train)}, Val={len(df_val)}, Test={len(df_test)}"
        )
        return df_train, df_val, df_test

    def fit_and_generate_sequences(
        self,
        daily_series_df: pd.DataFrame,
        value_col: str = "incident_count",
    ) -> Dict[str, Any]:
        """
        Fit scaler strictly on training slice and generate leakage-free sequence tensors.
        UNIVARIATE mode: uses a single value column (legacy / backward-compatible).
        """
        train_df, val_df, test_df = self.split_chronological(daily_series_df, date_col="date")

        train_vals = train_df[[value_col]].values
        self.scaler = MinMaxScaler(feature_range=(0.0, 1.0))
        self.scaler.fit(train_vals)
        self.is_fitted = True

        scaled_train = self.scaler.transform(train_vals).flatten()
        scaled_val = self.scaler.transform(val_df[[value_col]].values).flatten()
        scaled_test = self.scaler.transform(test_df[[value_col]].values).flatten()

        val_with_context = np.concatenate([scaled_train[-self.seq_len:], scaled_val])
        test_with_context = np.concatenate([scaled_val[-self.seq_len:], scaled_test])

        X_train, y_train = create_sliding_window_sequences(
            scaled_train, seq_len=self.seq_len, forecast_horizon=self.forecast_horizon
        )
        X_val, y_val = create_sliding_window_sequences(
            val_with_context, seq_len=self.seq_len, forecast_horizon=self.forecast_horizon
        )
        X_test, y_test = create_sliding_window_sequences(
            test_with_context, seq_len=self.seq_len, forecast_horizon=self.forecast_horizon
        )

        metadata = {
            "mode": "univariate",
            "seq_len": self.seq_len,
            "forecast_horizon": self.forecast_horizon,
            "n_features": 1,
            "feature_columns": [value_col],
            "target_column": value_col,
            "train_dates": list(self.train_dates),
            "val_dates": list(self.val_dates),
            "test_dates": list(self.test_dates),
            "train_samples": int(len(X_train)),
            "val_samples": int(len(X_val)),
            "test_samples": int(len(X_test)),
            "train_shape": list(X_train.shape),
            "val_shape": list(X_val.shape),
            "test_shape": list(X_test.shape),
            "scaler_min": float(self.scaler.data_min_[0]),
            "scaler_max": float(self.scaler.data_max_[0]),
        }
        self.split_metadata = metadata

        return {
            "X_train": X_train, "y_train": y_train,
            "X_val": X_val, "y_val": y_val,
            "X_test": X_test, "y_test": y_test,
            "metadata": metadata,
        }

    def fit_and_generate_multivariate_sequences(
        self,
        multivariate_df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        target_col: str = TARGET_COL,
    ) -> Dict[str, Any]:
        """
        Fit per-feature MinMaxScaler ONLY on training partition and generate
        leakage-free MULTIVARIATE sequence tensors.

        Args:
          multivariate_df: DataFrame with 'date' column + feature columns.
          feature_cols:    List of feature column names to use.
                           Defaults to MULTIVARIATE_FEATURE_COLS (13 features).
          target_col:      Column to predict (placed at feature index 0).

        Output sequences:
          X shape: (N_samples, seq_len, n_features)
          y shape: (N_samples, forecast_horizon)
              y values are the next forecast_horizon values of target_col (scaled).
        """
        if feature_cols is None:
            feature_cols = MULTIVARIATE_FEATURE_COLS

        # Place target_col at index 0 (required by create_sliding_window_sequences)
        ordered_cols = [target_col] + [c for c in feature_cols if c != target_col]
        missing = [c for c in ordered_cols if c not in multivariate_df.columns]
        if missing:
            logger.warning(f"Skipping missing columns: {missing}")
            ordered_cols = [c for c in ordered_cols if c in multivariate_df.columns]

        n_features = len(ordered_cols)
        logger.info(f"Multivariate pipeline: {n_features} features -> {ordered_cols}")

        train_df, val_df, test_df = self.split_chronological(multivariate_df, date_col="date")

        # Fit scaler ONLY on training data
        train_arr = train_df[ordered_cols].values.astype(np.float32)
        self.scaler = MinMaxScaler(feature_range=(0.0, 1.0))
        self.scaler.fit(train_arr)
        self.is_fitted = True

        # Scale all splits with the training-fitted scaler
        scaled_train = self.scaler.transform(train_arr)
        scaled_val = self.scaler.transform(val_df[ordered_cols].values.astype(np.float32))
        scaled_test = self.scaler.transform(test_df[ordered_cols].values.astype(np.float32))

        # Prepend context windows for val/test sequences (no future leakage)
        val_with_context = np.concatenate([scaled_train[-self.seq_len:], scaled_val], axis=0)
        test_with_context = np.concatenate([scaled_val[-self.seq_len:], scaled_test], axis=0)

        # Generate sliding window sequences
        X_train, y_train = create_sliding_window_sequences(
            scaled_train, seq_len=self.seq_len, forecast_horizon=self.forecast_horizon
        )
        X_val, y_val = create_sliding_window_sequences(
            val_with_context, seq_len=self.seq_len, forecast_horizon=self.forecast_horizon
        )
        X_test, y_test = create_sliding_window_sequences(
            test_with_context, seq_len=self.seq_len, forecast_horizon=self.forecast_horizon
        )

        metadata = {
            "mode": "multivariate",
            "seq_len": self.seq_len,
            "forecast_horizon": self.forecast_horizon,
            "n_features": n_features,
            "feature_columns": ordered_cols,
            "target_column": target_col,
            "train_dates": list(self.train_dates),
            "val_dates": list(self.val_dates),
            "test_dates": list(self.test_dates),
            "train_samples": int(len(X_train)),
            "val_samples": int(len(X_val)),
            "test_samples": int(len(X_test)),
            "train_shape": list(X_train.shape),
            "val_shape": list(X_val.shape),
            "test_shape": list(X_test.shape),
            "scaler_data_min": self.scaler.data_min_.tolist(),
            "scaler_data_max": self.scaler.data_max_.tolist(),
        }
        self.split_metadata = metadata

        logger.info(
            f"Multivariate sequences generated:\n"
            f"  X_train: {X_train.shape}, y_train: {y_train.shape}\n"
            f"  X_val:   {X_val.shape}, y_val:   {y_val.shape}\n"
            f"  X_test:  {X_test.shape}, y_test:  {y_test.shape}"
        )

        return {
            "X_train": X_train, "y_train": y_train,
            "X_val": X_val, "y_val": y_val,
            "X_test": X_test, "y_test": y_test,
            "metadata": metadata,
        }

    def save_sequences(
        self,
        sequence_data: Dict[str, Any],
        output_dir: str = "datasets/processed/temporal_sequences",
    ) -> None:
        """Save sequence arrays and metadata to disk."""
        os.makedirs(output_dir, exist_ok=True)
        np.savez_compressed(
            os.path.join(output_dir, "train_sequences.npz"),
            X=sequence_data["X_train"],
            y=sequence_data["y_train"],
        )
        np.savez_compressed(
            os.path.join(output_dir, "val_sequences.npz"),
            X=sequence_data["X_val"],
            y=sequence_data["y_val"],
        )
        np.savez_compressed(
            os.path.join(output_dir, "test_sequences.npz"),
            X=sequence_data["X_test"],
            y=sequence_data["y_test"],
        )
        with open(os.path.join(output_dir, "sequence_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(sequence_data["metadata"], f, indent=4)
        logger.info(f"Saved temporal sequences and metadata to {output_dir}")
