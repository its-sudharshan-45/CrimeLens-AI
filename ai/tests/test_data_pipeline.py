"""
ai/tests/test_data_pipeline.py
==============================
Comprehensive Automated Test Suite for Phase 2:
- Data loading & column schemas
- Cleaning, duplicate removal, date parsing, missing values
- Temporal, cyclical, and categorical feature validation
- Chronological train / validation / test splits without leakage
- Sliding window sequence generation and target alignment
- Hotspot spatial tensor validation
- Preprocessor artifact loading and persistence
"""

import json
import os
import numpy as np
import pandas as pd
import pytest

from ai.dataset.dataset_analysis import analyze_dataset
from ai.preprocessing.preprocessor import CrimeDataPreprocessor, CITY_TO_STATE
from ai.preprocessing.feature_engineering import FeatureEngineer, assign_time_of_day, assign_season
from ai.preprocessing.temporal_sequences import (
    aggregate_temporal_crimes,
    build_continuous_daily_series,
    build_multivariate_daily_series,
    create_sliding_window_sequences,
    TemporalSequencePipeline,
    MULTIVARIATE_FEATURE_COLS,
    TARGET_COL,
    TRAIN_START_DATE,
    TRAIN_END_DATE,
    VAL_START_DATE,
    VAL_END_DATE,
    TEST_START_DATE,
    TEST_END_DATE,
)
from ai.preprocessing.hotspot_dataset import generate_city_hotspot_features, ALL_29_CITIES, FEATURE_CHANNELS
from ai.preprocessing.class_imbalance import analyze_class_imbalance

RAW_DATASET_PATH = "Dataset/crime_dataset_india.csv"
EXPECTED_COLUMNS = [
    "Report Number",
    "Date Reported",
    "Date of Occurrence",
    "Time of Occurrence",
    "City",
    "Crime Code",
    "Crime Description",
    "Victim Age",
    "Victim Gender",
    "Weapon Used",
    "Crime Domain",
    "Police Deployed",
    "Case Closed",
    "Date Case Closed",
]


# =====================================================================
# 1. DATA LOADING TESTS
# =====================================================================

def test_raw_dataset_exists_and_loads():
    """Verify raw dataset exists and loads with expected columns and rows."""
    assert os.path.exists(RAW_DATASET_PATH), f"Raw dataset not found at {RAW_DATASET_PATH}"
    df = pd.read_csv(RAW_DATASET_PATH)
    assert len(df) == 40160, f"Expected 40,160 rows, got {len(df)}"
    for col in EXPECTED_COLUMNS:
        assert col in df.columns, f"Missing required column: {col}"


def test_dataset_analysis_summary():
    """Verify dataset analysis profiling function produces valid report."""
    summary = analyze_dataset(RAW_DATASET_PATH, save_summary=False)
    assert summary["row_count"] == 40160
    assert summary["column_count"] == 14
    assert summary["cities"]["count"] == 29
    assert summary["crime_domains"]["count"] == 4
    assert summary["crime_categories"]["count"] == 21
    assert summary["duplicate_rows"] == 0


# =====================================================================
# 2. DATA CLEANING & PARSING TESTS
# =====================================================================

def test_duplicate_handling():
    """Verify duplicate handling identifies and handles duplicates safely."""
    p = CrimeDataPreprocessor()
    df_raw = pd.read_csv(RAW_DATASET_PATH)
    # Inject 5 artificial duplicate rows to test removal
    df_with_duplicates = pd.concat([df_raw, df_raw.head(5)], ignore_index=True)
    assert len(df_with_duplicates) == 40165
    df_cleaned = p.handle_duplicates(df_with_duplicates)
    assert len(df_cleaned) == 40160
    assert p.cleaning_stats["duplicates"]["duplicates_found"] == 5


def test_date_parsing_without_nat_loss():
    """Verify that multi-format date parsing achieves ZERO unparseable dates."""
    p = CrimeDataPreprocessor()
    df_raw = pd.read_csv(RAW_DATASET_PATH)
    df_clean = p.clean_dataset(df_raw)

    # Date Reported: %d-%m-%Y %H:%M
    assert df_clean["Date Reported"].isnull().sum() == 0
    # Date of Occurrence: %m-%d-%Y %H:%M
    assert df_clean["Date of Occurrence"].isnull().sum() == 0
    # Time of Occurrence: %d-%m-%Y %H:%M
    assert df_clean["Time of Occurrence"].isnull().sum() == 0

    # Reporting lag must be non-negative
    assert (df_clean["Reporting_Lag_Hours"] < 0).sum() == 0
    # Date Case Closed missing must match Case Closed == 'No'
    unclosed_count = (df_clean["Case Closed"] == "No").sum()
    assert df_clean["Date Case Closed"].isnull().sum() == unclosed_count


def test_missing_value_semantics():
    """Verify missing values are handled according to domain semantics."""
    p = CrimeDataPreprocessor()
    df_raw = pd.read_csv(RAW_DATASET_PATH)
    df_clean = p.clean_missing_values(df_raw)

    assert df_clean["Weapon Used"].isnull().sum() == 0
    assert (df_clean["Weapon Used"] == "Unknown").sum() == df_raw["Weapon Used"].isnull().sum()


def test_numeric_validation():
    """Verify numeric features are bounded within realistic domains."""
    p = CrimeDataPreprocessor()
    df_raw = pd.read_csv(RAW_DATASET_PATH)
    df_clean = p.validate_numerics(df_raw)

    assert df_clean["Victim Age"].min() >= 0
    assert df_clean["Victim Age"].max() <= 120
    assert df_clean["Police Deployed"].min() >= 1
    assert (df_clean["Crime Code"] < 0).sum() == 0


# =====================================================================
# 3. FEATURE ENGINEERING TESTS
# =====================================================================

def test_temporal_feature_ranges():
    """Verify that temporal features fall within valid calendar/clock ranges."""
    p = CrimeDataPreprocessor()
    fe = FeatureEngineer()
    df_clean = p.clean_dataset(pd.read_csv(RAW_DATASET_PATH))
    df_feats = fe.extract_temporal_features(df_clean)

    assert df_feats["Year"].between(2020, 2024).all()
    assert df_feats["Month"].between(1, 12).all()
    assert df_feats["Day"].between(1, 31).all()
    assert df_feats["Hour"].between(0, 23).all()
    assert df_feats["Day_of_Week"].between(0, 6).all()
    assert df_feats["Quarter"].between(1, 4).all()
    assert df_feats["Is_Weekend"].isin([0, 1]).all()
    assert df_feats["Week_of_Year"].between(1, 53).all()


def test_time_of_day_and_season_categories():
    """Verify that 24 hours and 12 months map correctly to categories."""
    for h in [22, 23, 0, 1, 2, 3, 4, 5]:
        assert assign_time_of_day(h) == "Night"
    for h in range(6, 12):
        assert assign_time_of_day(h) == "Morning"
    for h in range(12, 17):
        assert assign_time_of_day(h) == "Afternoon"
    for h in range(17, 22):
        assert assign_time_of_day(h) == "Evening"

    for m in [12, 1, 2]:
        assert assign_season(m) == "Winter"
    for m in [3, 4, 5]:
        assert assign_season(m) == "Summer"
    for m in [6, 7, 8, 9]:
        assert assign_season(m) == "Monsoon"
    for m in [10, 11]:
        assert assign_season(m) == "Post-Monsoon"


def test_cyclical_feature_ranges():
    """Verify cyclical sin/cos features are bounded within [-1.0, 1.0]."""
    p = CrimeDataPreprocessor()
    fe = FeatureEngineer()
    df_clean = p.clean_dataset(pd.read_csv(RAW_DATASET_PATH))
    df_feats = fe.extract_cyclical_features(fe.extract_temporal_features(df_clean))

    for col in ["sin_month", "cos_month", "sin_hour", "cos_hour", "sin_weekday", "cos_weekday"]:
        assert df_feats[col].min() >= -1.0001
        assert df_feats[col].max() <= 1.0001


# =====================================================================
# 4. CHRONOLOGICAL SPLIT & LEAKAGE PREVENTION TESTS
# =====================================================================

def test_chronological_splits_strictly_ordered():
    """
    Verify chronological splitting:
    Train < Val < Test with ZERO date overlap.
    """
    p = CrimeDataPreprocessor()
    df_clean = p.clean_dataset(pd.read_csv(RAW_DATASET_PATH))
    daily_series = build_continuous_daily_series(df_clean)

    pipe = TemporalSequencePipeline(
        train_dates=(TRAIN_START_DATE, TRAIN_END_DATE),
        val_dates=(VAL_START_DATE, VAL_END_DATE),
        test_dates=(TEST_START_DATE, TEST_END_DATE),
    )
    train_df, val_df, test_df = pipe.split_chronological(daily_series)

    # 1. Verify date order
    assert train_df["date"].max() < val_df["date"].min(), "Train overlaps with Validation!"
    assert val_df["date"].max() < test_df["date"].min(), "Validation overlaps with Test!"

    # 2. Verify date boundaries
    assert str(train_df["date"].min())[:10] == TRAIN_START_DATE
    assert str(train_df["date"].max())[:10] == TRAIN_END_DATE
    assert str(val_df["date"].min())[:10] == VAL_START_DATE
    assert str(val_df["date"].max())[:10] == VAL_END_DATE
    assert str(test_df["date"].min())[:10] == TEST_START_DATE
    assert str(test_df["date"].max())[:10] == TEST_END_DATE


def test_leakage_prevention_on_feature_stats():
    """
    Verify that feature engineering historical stats fit ONLY on training split
    and do not leak validation/test data.
    """
    p = CrimeDataPreprocessor()
    df_clean = p.clean_dataset(pd.read_csv(RAW_DATASET_PATH))
    dt_series = pd.to_datetime(df_clean["Date of Occurrence"])
    train_mask = (dt_series >= pd.Timestamp(TRAIN_START_DATE)) & (dt_series <= pd.Timestamp(TRAIN_END_DATE))

    fe = FeatureEngineer()
    # Fit only on training set
    fe.fit_aggregated_statistics(df_clean[train_mask])

    # Delhi frequency in training set vs full set
    train_delhi_count = (df_clean[train_mask]["City"] == "Delhi").sum()
    full_delhi_count = (df_clean["City"] == "Delhi").sum()

    assert fe.city_freq_map.get("Delhi") == train_delhi_count
    assert fe.city_freq_map.get("Delhi") < full_delhi_count, "Data leakage! Full dataset count was used."


# =====================================================================
# 5. TIME-SERIES SEQUENCE TESTS
# =====================================================================

def test_sliding_window_sequence_generation():
    """Verify correct sequence lengths, target alignment, and no lookahead leakage.
    Tests both 1D (univariate) and 2D (multivariate) input.
    """
    # --- Univariate 1D input ---
    dummy_series = np.arange(100, dtype=np.float32)
    seq_len = 30
    horizon = 7

    X, y = create_sliding_window_sequences(dummy_series, seq_len=seq_len, forecast_horizon=horizon)

    expected_samples = 100 - seq_len - horizon + 1  # 64
    assert len(X) == expected_samples
    assert len(y) == expected_samples
    assert X.shape == (expected_samples, seq_len, 1), f"Unexpected X shape: {X.shape}"
    assert y.shape == (expected_samples, horizon), f"Unexpected y shape: {y.shape}"

    # Verify first sample alignment: X is [0..29], y is [30..36]
    np.testing.assert_array_equal(X[0].squeeze(-1), np.arange(0, 30))
    np.testing.assert_array_equal(y[0], np.arange(30, 37))

    # Verify last sample alignment: X is [63..92], y is [93..99]
    np.testing.assert_array_equal(X[-1].squeeze(-1), np.arange(63, 93))
    np.testing.assert_array_equal(y[-1], np.arange(93, 100))

    # --- Multivariate 2D input (T, F) ---
    n_features = 5
    dummy_mv = np.random.rand(100, n_features).astype(np.float32)
    X_mv, y_mv = create_sliding_window_sequences(dummy_mv, seq_len=seq_len, forecast_horizon=horizon)
    assert X_mv.shape == (expected_samples, seq_len, n_features), f"Unexpected mv X shape: {X_mv.shape}"
    assert y_mv.shape == (expected_samples, horizon), f"Unexpected mv y shape: {y_mv.shape}"
    # y_mv should be the first feature column values, NOT any other column
    np.testing.assert_array_almost_equal(y_mv[0], dummy_mv[seq_len:seq_len + horizon, 0])


def test_pipeline_sequence_shapes_and_scaling():
    """Verify TemporalSequencePipeline produces valid MULTIVARIATE scaled sequence arrays."""
    p = CrimeDataPreprocessor()
    df_clean = p.clean_dataset(pd.read_csv(RAW_DATASET_PATH))

    # Build multivariate daily series
    mv_series = build_multivariate_daily_series(df_clean)

    pipe = TemporalSequencePipeline(seq_len=30, forecast_horizon=7)
    seq_data = pipe.fit_and_generate_multivariate_sequences(
        mv_series, feature_cols=MULTIVARIATE_FEATURE_COLS, target_col=TARGET_COL
    )

    # Shape assertions
    n_features = len(MULTIVARIATE_FEATURE_COLS)
    assert seq_data["X_train"].shape[1] == 30, f"seq_len mismatch: {seq_data['X_train'].shape[1]}"
    assert seq_data["X_train"].shape[2] == n_features, (
        f"Expected {n_features} features, got {seq_data['X_train'].shape[2]}"
    )
    assert seq_data["y_train"].shape[1] == 7
    assert seq_data["X_val"].shape[1] == 30
    assert seq_data["X_val"].shape[2] == n_features
    assert seq_data["y_val"].shape[1] == 7
    assert seq_data["X_test"].shape[1] == 30
    assert seq_data["X_test"].shape[2] == n_features
    assert seq_data["y_test"].shape[1] == 7

    # Metadata assertions
    assert pipe.is_fitted
    assert seq_data["metadata"]["mode"] == "multivariate"
    assert seq_data["metadata"]["n_features"] == n_features
    assert seq_data["metadata"]["target_column"] == TARGET_COL
    assert seq_data["metadata"]["feature_columns"][0] == TARGET_COL

    # Scaler bounds: verify scaler was fitted with correct dimension
    assert len(seq_data["metadata"]["scaler_data_min"]) == n_features
    assert len(seq_data["metadata"]["scaler_data_max"]) == n_features
    # All scaled maxima should be positive
    assert all(v > 0.0 for v in seq_data["metadata"]["scaler_data_max"])


# =====================================================================
# 6. HOTSPOT & CLASS IMBALANCE TESTS
# =====================================================================

def test_hotspot_spatial_tensor():
    """Verify city-level hotspot tensor shape and channels."""
    p = CrimeDataPreprocessor()
    df_clean = p.clean_dataset(pd.read_csv(RAW_DATASET_PATH))
    hotspot_df, tensor, meta = generate_city_hotspot_features(df_clean)

    assert tensor.shape == (1674, 29, 8)
    assert meta["city_count"] == 29
    assert meta["channel_count"] == 8
    assert meta["feature_channels"] == FEATURE_CHANNELS
    assert meta["cities"] == ALL_29_CITIES
    assert "geographic_limitation" in meta


def test_class_imbalance_weights():
    """Verify class weights are properly computed and inversely proportional to frequency."""
    df_raw = pd.read_csv(RAW_DATASET_PATH)
    report = analyze_class_imbalance(df_raw)

    weights = report["domain_class_weights"]
    # Less frequent classes must have higher weight
    assert weights["Traffic Fatality"] > weights["Fire Accident"]
    assert weights["Fire Accident"] > weights["Violent Crime"]
    assert weights["Violent Crime"] > weights["Other Crime"]
