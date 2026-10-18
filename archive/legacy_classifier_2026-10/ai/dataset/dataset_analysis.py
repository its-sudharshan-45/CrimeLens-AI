"""
ai/dataset/dataset_analysis.py
==============================
Dataset Analysis & Data Profiling component for CrimeLens AI.
Inspects dataset dimensions, data types, missing values, duplicates, date ranges,
class distributions, city distributions, numeric validity, and outlier profiles.
"""

import json
import logging
import os
from typing import Any, Dict

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATASET_PATH = r"Dataset/crime_dataset_india.csv"
OUTPUT_SUMMARY_PATH = r"ai/artifacts/dataset_summary.json"


def detect_outliers_iqr(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    """Detect outliers using Interquartile Range (IQR) for numerical features."""
    if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
        return {}
    s = df[col].dropna()
    if len(s) == 0:
        return {}
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = s[(s < lower_bound) | (s > upper_bound)]
    return {
        "column": col,
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "iqr": round(iqr, 4),
        "lower_bound": round(lower_bound, 4),
        "upper_bound": round(upper_bound, 4),
        "outlier_count": len(outliers),
        "outlier_percentage": round(len(outliers) / len(df) * 100, 2),
    }


def analyze_dataset(
    dataset_path: str = DEFAULT_DATASET_PATH,
    output_path: str = OUTPUT_SUMMARY_PATH,
    save_summary: bool = True,
) -> Dict[str, Any]:
    """
    Phase 2 Dataset Validation and Profiling.
    Inspects and reports all metrics specified in Phase 2 Requirements.
    """
    logger.info(f"Inspecting dataset from: {dataset_path}")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file not found at: {dataset_path}")

    df = pd.read_csv(dataset_path)
    rows, cols = df.shape
    logger.info(f"Dataset loaded successfully. Rows: {rows}, Columns: {cols}")

    # 1. Missing values & Duplicates
    missing_vals = {col: int(val) for col, val in df.isnull().sum().to_dict().items()}
    duplicates_count = int(df.duplicated().sum())
    data_types = {col: str(dtype) for col, dtype in df.dtypes.items()}

    # 2. Date validations with format awareness
    date_summary: Dict[str, Any] = {}
    date_configs = [
        ("Date Reported", "%d-%m-%Y %H:%M"),
        ("Date of Occurrence", "%m-%d-%Y %H:%M"),
        ("Time of Occurrence", "%d-%m-%Y %H:%M"),
        ("Date Case Closed", "%d-%m-%Y %H:%M"),
    ]
    for col_name, fmt in date_configs:
        if col_name in df.columns:
            parsed = pd.to_datetime(df[col_name], format=fmt, errors="coerce")
            non_null = df[col_name].notnull().sum()
            parsed_count = parsed.notnull().sum()
            unparsed_count = non_null - parsed_count
            date_summary[col_name] = {
                "format": fmt,
                "total_non_null": non_null,
                "successfully_parsed": parsed_count,
                "unparseable": unparsed_count,
                "min_date": str(parsed.min()) if parsed.notnull().any() else None,
                "max_date": str(parsed.max()) if parsed.notnull().any() else None,
            }

    # 3. Numeric validity
    numeric_summary: Dict[str, Any] = {}
    for num_col in ["Victim Age", "Crime Code", "Police Deployed"]:
        if num_col in df.columns:
            s = df[num_col].dropna()
            numeric_summary[num_col] = {
                "min": s.min(),
                "max": s.max(),
                "mean": round(s.mean(), 2),
                "std": round(s.std(), 2),
                "negative_count": (s < 0).sum(),
                "null_count": df[num_col].isnull().sum(),
            }

    # 4. Distributions
    city_dist = df["City"].value_counts().to_dict() if "City" in df.columns else {}
    domain_dist = df["Crime Domain"].value_counts().to_dict() if "Crime Domain" in df.columns else {}
    category_dist = df["Crime Description"].value_counts().to_dict() if "Crime Description" in df.columns else {}
    closure_dist = df["Case Closed"].value_counts().to_dict() if "Case Closed" in df.columns else {}
    weapon_dist = df["Weapon Used"].value_counts(dropna=False).to_dict() if "Weapon Used" in df.columns else {}
    weapon_dist = {str(k): int(v) for k, v in weapon_dist.items()}

    # 5. Outlier Detection
    num_cols = df.select_dtypes(include="number").columns.tolist()
    outlier_summary = {col: detect_outliers_iqr(df, col) for col in num_cols}

    summary_report: Dict[str, Any] = {
        "dataset_path": dataset_path,
        "row_count": rows,
        "column_count": cols,
        "columns": list(df.columns),
        "data_types": data_types,
        "missing_values": missing_vals,
        "duplicate_rows": duplicates_count,
        "date_validation": date_summary,
        "numeric_validation": numeric_summary,
        "cities": {
            "count": len(city_dist),
            "distribution": city_dist,
        },
        "crime_domains": {
            "count": len(domain_dist),
            "distribution": domain_dist,
        },
        "crime_categories": {
            "count": len(category_dist),
            "distribution": category_dist,
        },
        "case_closure": closure_dist,
        "weapon_used": weapon_dist,
        "outlier_summary": outlier_summary,
    }

    if save_summary:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                summary_report,
                f,
                indent=4,
                default=lambda o: int(o) if isinstance(o, np.integer) else (float(o) if isinstance(o, np.floating) else str(o)),
            )
        logger.info(f"Dataset summary exported to {output_path}")

    return summary_report


if __name__ == "__main__":
    report = analyze_dataset()
    print("\n==========================================")
    print("DATASET VALIDATION SUMMARY")
    print("==========================================")
    print(f"Total Records:      {report['row_count']}")
    print(f"Total Columns:      {report['column_count']}")
    print(f"Exact Duplicates:   {report['duplicate_rows']}")
    print(f"Cities:             {report['cities']['count']}")
    print(f"Crime Domains:      {report['crime_domains']['count']}")
    print(f"Crime Categories:   {report['crime_categories']['count']}")
    print("==========================================")
