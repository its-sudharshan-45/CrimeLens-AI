"""
ai/preprocessing/run_pipeline.py
================================
Master execution script for Phase 2: Dataset & Preprocessing Pipeline Rebuild.

Executes the full pipeline:
1. Dataset Loading & Validation
2. Cleaning & Multi-Format Datetime Parsing
3. Temporal & Cyclical Feature Engineering
4. Leakage-Free Historical Aggregated Statistics Fitting (Train Split Only)
5. Temporal Crime Aggregation (Daily City & Crime Type)
6. 30-Day Sequence Generation (Train / Val / Test)
7. City-Level Spatio-Temporal CNN Hotspot Tensor Construction
8. Class Imbalance Analysis & Balanced Loss Weight Computation
9. Saving All Processed Datasets & Metadata
10. Formatted Data Quality Report
"""

import json
import logging
import os
import shutil
import sys
from typing import Any, Dict

import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.dataset.dataset_analysis import analyze_dataset
from ai.preprocessing.class_imbalance import analyze_class_imbalance, save_imbalance_report
from ai.preprocessing.feature_engineering import FeatureEngineer
from ai.preprocessing.hotspot_dataset import generate_city_hotspot_features, save_hotspot_data
from ai.preprocessing.preprocessor import CrimeDataPreprocessor
from ai.preprocessing.temporal_sequences import (
    MULTIVARIATE_FEATURE_COLS,
    TARGET_COL,
    TEST_END_DATE,
    TEST_START_DATE,
    TRAIN_END_DATE,
    TRAIN_START_DATE,
    VAL_END_DATE,
    VAL_START_DATE,
    TemporalSequencePipeline,
    aggregate_temporal_crimes,
    build_continuous_daily_series,
    build_multivariate_daily_series,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

RAW_DATASET_SOURCE = os.path.join(PROJECT_ROOT, "Dataset", "crime_dataset_india.csv")
RAW_DATASET_DEST = os.path.join(PROJECT_ROOT, "datasets", "raw", "crime_dataset_india.csv")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "datasets", "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "ai", "models")


def run_pipeline() -> Dict[str, Any]:
    """Execute the complete Phase 2 Data Pipeline."""
    logger.info("Starting CrimeLens AI Phase 2 Data Pipeline...")

    os.makedirs(os.path.dirname(RAW_DATASET_DEST), exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    # 1. Mirror raw dataset to datasets/raw/ if not already present
    if os.path.exists(RAW_DATASET_SOURCE) and not os.path.exists(RAW_DATASET_DEST):
        shutil.copyfile(RAW_DATASET_SOURCE, RAW_DATASET_DEST)
        logger.info(f"Copied raw dataset to {RAW_DATASET_DEST}")

    dataset_path = RAW_DATASET_DEST if os.path.exists(RAW_DATASET_DEST) else RAW_DATASET_SOURCE
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Raw crime dataset not found at {dataset_path}")

    # ---------------------------------------------------------
    # STEP 1: Dataset Inspection & Validation
    # ---------------------------------------------------------
    logger.info(">>> STEP 1: DATASET INSPECTION & VALIDATION <<<")
    summary = analyze_dataset(
        dataset_path=dataset_path,
        output_path=os.path.join(PROJECT_ROOT, "ai", "artifacts", "dataset_summary.json"),
        save_summary=True,
    )
    df_raw = pd.read_csv(dataset_path)
    records_before = len(df_raw)

    # ---------------------------------------------------------
    # STEP 2: Data Cleaning & Multi-Format Datetime Parsing
    # ---------------------------------------------------------
    logger.info(">>> STEP 2: CLEANING & DATETIME PARSING <<<")
    preprocessor = CrimeDataPreprocessor()
    df_clean = preprocessor.clean_dataset(df_raw)
    records_after = len(df_clean)
    duplicates_removed = records_before - records_after

    # Save cleaned dataset
    cleaned_csv_path = os.path.join(PROCESSED_DIR, "crime_cleaned.csv")
    df_clean.to_csv(cleaned_csv_path, index=False)
    logger.info(f"Saved cleaned dataset to {cleaned_csv_path}")

    # ---------------------------------------------------------
    # STEP 3: Temporal & Cyclical Feature Engineering
    # ---------------------------------------------------------
    logger.info(">>> STEP 3: TEMPORAL FEATURE ENGINEERING <<<")
    # Identify training split mask to prevent data leakage during statistics fitting
    dt_series = pd.to_datetime(df_clean["Date of Occurrence"])
    train_mask = (dt_series >= pd.Timestamp(TRAIN_START_DATE)) & (dt_series <= pd.Timestamp(TRAIN_END_DATE))
    df_train_only = df_clean[train_mask].copy()

    # Fit feature engineer stats STRICTLY on training records
    feature_engineer = FeatureEngineer()
    feature_engineer.fit_aggregated_statistics(feature_engineer.extract_cyclical_features(feature_engineer.extract_temporal_features(df_train_only)))

    # Apply to full dataset
    df_features = feature_engineer.transform(df_clean, is_train=False)

    # Fit and transform encoders on training data
    preprocessor.fit_encoders(df_clean[train_mask])
    df_features_encoded = preprocessor.transform_encoders(df_features)

    # Attach stats to preprocessor for inference engine compatibility
    preprocessor.city_stats = feature_engineer.city_stats
    preprocessor.state_stats = feature_engineer.state_stats

    # Save preprocessor artifact
    preprocessor.save(os.path.join(PROCESSED_DIR, "preprocessor.pkl"))
    preprocessor.save(os.path.join(MODELS_DIR, "preprocessor.pkl"))

    # Extract feature matrix schema
    _, _, feature_cols = feature_engineer.get_feature_matrix(df_features_encoded)
    schema_payload = {
        "feature_columns": feature_cols,
        "input_dim": len(feature_cols),
        "target_column": "Crime Domain_encoded",
        "domain_classes": list(preprocessor.label_encoders["Crime Domain"].classes_) if "Crime Domain" in preprocessor.label_encoders else [],
        "description_classes": list(preprocessor.label_encoders["Crime Description"].classes_) if "Crime Description" in preprocessor.label_encoders else [],
    }
    with open(os.path.join(PROCESSED_DIR, "feature_columns.json"), "w", encoding="utf-8") as f:
        json.dump(schema_payload, f, indent=4)
    with open(os.path.join(MODELS_DIR, "feature_columns.json"), "w", encoding="utf-8") as f:
        json.dump(schema_payload, f, indent=4)

    # Save features dataset
    features_csv_path = os.path.join(PROCESSED_DIR, "crime_features.csv")
    df_features_encoded.to_csv(features_csv_path, index=False)
    logger.info(f"Saved feature dataset to {features_csv_path}")

    # ---------------------------------------------------------
    # STEP 4: Temporal Aggregation
    # ---------------------------------------------------------
    logger.info(">>> STEP 4: TEMPORAL AGGREGATION <<<")
    detailed_agg, city_agg = aggregate_temporal_crimes(df_clean)
    agg_csv_path = os.path.join(PROCESSED_DIR, "temporal_aggregated.csv")
    detailed_agg.to_csv(agg_csv_path, index=False)
    logger.info(f"Saved temporal aggregation to {agg_csv_path} ({len(detailed_agg)} records)")

    # ---------------------------------------------------------
    # STEP 5: Chronological Sequences Generation (Multivariate)
    # ---------------------------------------------------------
    logger.info(">>> STEP 5: TIME-SERIES SEQUENCES GENERATION (MULTIVARIATE) <<<")

    # Build univariate series for report counts only
    daily_series = build_continuous_daily_series(
        df_clean, start_date=TRAIN_START_DATE, end_date=TEST_END_DATE
    )

    # Build rich multivariate feature series: 8 crime + 5 cyclical = 13 features
    multivariate_series = build_multivariate_daily_series(
        df_clean, start_date=TRAIN_START_DATE, end_date=TEST_END_DATE
    )
    logger.info(f"Multivariate series shape: {multivariate_series.shape}, features: {MULTIVARIATE_FEATURE_COLS}")

    seq_pipeline = TemporalSequencePipeline(
        seq_len=30,
        forecast_horizon=7,
        train_dates=(TRAIN_START_DATE, TRAIN_END_DATE),
        val_dates=(VAL_START_DATE, VAL_END_DATE),
        test_dates=(TEST_START_DATE, TEST_END_DATE),
    )
    # Generate multivariate sequences: X=(N, 30, 13), y=(N, 7)
    seq_data = seq_pipeline.fit_and_generate_multivariate_sequences(
        multivariate_series,
        feature_cols=MULTIVARIATE_FEATURE_COLS,
        target_col=TARGET_COL,
    )
    seq_output_dir = os.path.join(PROCESSED_DIR, "temporal_sequences")
    seq_pipeline.save_sequences(seq_data, output_dir=seq_output_dir)

    # Save chronological split metadata
    split_meta_path = os.path.join(PROCESSED_DIR, "split_metadata.json")
    with open(split_meta_path, "w", encoding="utf-8") as f:
        json.dump(seq_data["metadata"], f, indent=4)

    # ---------------------------------------------------------
    # STEP 6: CNN Hotspot Dataset
    # ---------------------------------------------------------
    logger.info(">>> STEP 6: CNN HOTSPOT DATASET <<<")
    hotspot_df, hotspot_tensor, hotspot_meta = generate_city_hotspot_features(df_clean)
    save_hotspot_data(
        df_hotspot=hotspot_df,
        tensor=hotspot_tensor,
        metadata=hotspot_meta,
        output_csv=os.path.join(PROCESSED_DIR, "hotspot_features.csv"),
        output_npz=os.path.join(PROCESSED_DIR, "hotspot_tensor.npz"),
        output_meta=os.path.join(PROCESSED_DIR, "hotspot_metadata.json"),
    )

    # ---------------------------------------------------------
    # STEP 7: Class Imbalance & Loss Weights
    # ---------------------------------------------------------
    logger.info(">>> STEP 7: CLASS IMBALANCE ANALYSIS <<<")
    imbalance_report = analyze_class_imbalance(df_clean)
    save_imbalance_report(
        imbalance_report,
        output_path=os.path.join(PROCESSED_DIR, "class_weights.json"),
    )

    # ---------------------------------------------------------
    # STEP 8: Print Data Quality Report (Section 17 Specification)
    # ---------------------------------------------------------
    date_min = str(df_clean["Date of Occurrence"].min())[:10]
    date_max = str(df_clean["Date of Occurrence"].max())[:10]
    num_cities = df_clean["City"].nunique()
    num_categories = df_clean["Crime Description"].nunique()
    num_domains = df_clean["Crime Domain"].nunique()

    missing_weapon = df_raw["Weapon Used"].isnull().sum()
    missing_closure = df_raw["Date Case Closed"].isnull().sum()
    missing_other = int(df_raw.drop(columns=["Weapon Used", "Date Case Closed"]).isnull().sum().sum())

    report_text = f"""
==================================================
CrimeLens AI - Phase 2 Data Pipeline
==================================================

Records:
Before cleaning:       {records_before}
Duplicates removed:       {duplicates_removed}
After cleaning:        {records_after}

Date range:
{date_min} -> {date_max}

Cities:                    {num_cities}
Crime categories:          {num_categories}
Crime domains:              {num_domains}

Missing values:
Weapon Used:               {missing_weapon} (filled with 'Unknown')
Case Closed:               {missing_closure} (unresolved preserved as NaT)
Other:                     {missing_other}

Features generated:
[OK] year
[OK] month
[OK] day
[OK] hour
[OK] day_of_week
[OK] is_weekend
[OK] season
[OK] time_of_day

Temporal split:
Train:       {TRAIN_START_DATE} -> {TRAIN_END_DATE} ({seq_data['metadata']['train_samples']} steps)
Validation:  {VAL_START_DATE} -> {VAL_END_DATE} ({seq_data['metadata']['val_samples']} steps)
Test:        {TEST_START_DATE} -> {TEST_END_DATE} ({seq_data['metadata']['test_samples']} steps)

Temporal sequences:
Sequence length: {seq_data['metadata']['seq_len']}
Input features:  {seq_data['metadata']['n_features']} (multivariate)
Train shape:     {seq_data['metadata']['train_shape']}
Validation shape:{seq_data['metadata']['val_shape']}
Test shape:      {seq_data['metadata']['test_shape']}
Training sequences: {seq_data['metadata']['train_samples']}
Validation sequences: {seq_data['metadata']['val_samples']}
Testing sequences: {seq_data['metadata']['test_samples']}

Hotspot dataset:
Cities: {hotspot_meta['city_count']}
Time periods: {hotspot_meta['time_periods_count']}
Tensor shape: {hotspot_meta['tensor_shape']}

Status: SUCCESS
==================================================
"""
    try:
        print(report_text)
    except UnicodeEncodeError:
        print(report_text.encode("ascii", errors="replace").decode("ascii"))

    return {
        "status": "SUCCESS",
        "records_before": records_before,
        "records_after": records_after,
        "duplicates_removed": duplicates_removed,
        "date_range": (date_min, date_max),
        "cities": num_cities,
        "crime_categories": num_categories,
        "crime_domains": num_domains,
        "seq_metadata": seq_data["metadata"],
        "hotspot_metadata": hotspot_meta,
    }


if __name__ == "__main__":
    run_pipeline()
