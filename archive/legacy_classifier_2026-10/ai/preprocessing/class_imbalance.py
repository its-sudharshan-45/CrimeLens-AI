"""
ai/preprocessing/class_imbalance.py
===================================
Class imbalance analysis and loss-weight calculation for CrimeLens AI.
Analyzes category, domain, geographic, and temporal distributions to prepare
balanced class weights for downstream model training without synthetic distortion.
"""

import json
import logging
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.utils.class_weight import compute_class_weight

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def analyze_class_imbalance(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Perform comprehensive class distribution and imbalance analysis:
    - Overall domain and category distributions
    - City-level distribution and spatial skew
    - Temporal distribution across years and seasons
    - Calculate balanced class weights for training loss functions
    """
    df = df.copy()
    total_records = len(df)

    # 1. Crime Domain Distribution & Balanced Weights
    domain_counts = df["Crime Domain"].value_counts().to_dict() if "Crime Domain" in df.columns else {}
    domain_weights = {}
    if domain_counts:
        classes = np.array(list(domain_counts.keys()))
        y = df["Crime Domain"].values
        computed_weights = compute_class_weight(class_weight="balanced", classes=classes, y=y)
        domain_weights = {str(cls): float(round(w, 4)) for cls, w in zip(classes, computed_weights)}

    domain_summary = {
        cls: {
            "count": int(count),
            "percentage": round(count / total_records * 100, 2),
            "balanced_weight": domain_weights.get(cls, 1.0),
        }
        for cls, count in domain_counts.items()
    }

    # 2. Crime Description (Category) Distribution & Balanced Weights
    category_counts = df["Crime Description"].value_counts().to_dict() if "Crime Description" in df.columns else {}
    category_weights = {}
    if category_counts:
        cat_classes = np.array(list(category_counts.keys()))
        y_cat = df["Crime Description"].values
        computed_cat_weights = compute_class_weight(class_weight="balanced", classes=cat_classes, y=y_cat)
        category_weights = {str(cls): float(round(w, 4)) for cls, w in zip(cat_classes, computed_cat_weights)}

    category_summary = {
        cls: {
            "count": int(count),
            "percentage": round(count / total_records * 100, 2),
            "balanced_weight": category_weights.get(cls, 1.0),
        }
        for cls, count in category_counts.items()
    }

    # 3. Identify Rare Categories (Threshold: < 5% of dataset)
    rare_domains = [cls for cls, info in domain_summary.items() if info["percentage"] < 5.0]
    rare_categories = [cls for cls, info in category_summary.items() if info["percentage"] < 4.0]

    # 4. City-level Distribution
    city_counts = df["City"].value_counts().to_dict() if "City" in df.columns else {}
    city_summary = {
        city: {
            "count": int(count),
            "percentage": round(count / total_records * 100, 2),
        }
        for city, count in city_counts.items()
    }

    # 5. Temporal Distribution
    temporal_summary: Dict[str, Any] = {}
    if "Date of Occurrence" in df.columns:
        dt = pd.to_datetime(df["Date of Occurrence"])
        yearly = dt.dt.year.value_counts().sort_index().to_dict()
        monthly = dt.dt.month.value_counts().sort_index().to_dict()
        temporal_summary["by_year"] = {int(k): int(v) for k, v in yearly.items()}
        temporal_summary["by_month"] = {int(k): int(v) for k, v in monthly.items()}

    # 6. Combined Report
    imbalance_report = {
        "total_records": total_records,
        "crime_domain_imbalance": domain_summary,
        "domain_class_weights": domain_weights,
        "crime_category_imbalance": category_summary,
        "category_class_weights": category_weights,
        "rare_domains": rare_domains,
        "rare_categories": rare_categories,
        "city_distribution": city_summary,
        "temporal_distribution": temporal_summary,
        "recommendation": (
            "Do NOT blindly oversample temporal sequence data as it causes lookahead distortion. "
            "Instead, use provided balanced_weights directly in CrossEntropyLoss(weight=weights) "
            "or FocalLoss for domain and category classification."
        ),
    }

    return imbalance_report


def save_imbalance_report(
    report: Dict[str, Any],
    output_path: str = "datasets/processed/class_weights.json",
) -> None:
    """Save class weights and imbalance analysis to JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    logger.info(f"Class imbalance report and weights saved to {output_path}")
