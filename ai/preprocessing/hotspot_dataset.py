"""
ai/preprocessing/hotspot_dataset.py
===================================
City-level spatio-temporal dataset generator for CNN Hotspot prediction.

Geographic Scope & Limitation:
-----------------------------
The Indian Crime dataset contains incidents attributed to 29 Indian cities.
It does NOT contain coordinates (latitude/longitude), wards, street addresses,
or police precinct GPS locations. In adherence to project guidelines, NO artificial
coordinates are fabricated. Instead, city-level spatial tensors are constructed across
the 29 cities over discrete time periods (daily/weekly), producing CNN-compatible
tensors of shape (Time_Steps, 29_Cities, Feature_Channels).
"""

import json
import logging
import os
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Canonical list of 29 cities in alphabetical order
ALL_29_CITIES = sorted([
    "Agra", "Ahmedabad", "Bangalore", "Bhopal", "Chennai", "Delhi",
    "Faridabad", "Ghaziabad", "Hyderabad", "Indore", "Jaipur", "Kalyan",
    "Kanpur", "Kolkata", "Lucknow", "Ludhiana", "Meerut", "Mumbai",
    "Nagpur", "Nashik", "Patna", "Pune", "Rajkot", "Srinagar",
    "Surat", "Thane", "Varanasi", "Vasai", "Visakhapatnam"
])

FEATURE_CHANNELS = [
    "total_crimes",
    "violent_crimes",
    "other_crimes",
    "fire_accidents",
    "traffic_fatalities",
    "avg_police_deployed",
    "case_closure_rate",
    "avg_victim_age",
]


def generate_city_hotspot_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray, Dict[str, Any]]:
    """
    Construct continuous daily city-level hotspot features and 3D CNN tensor.

    Returns:
    - df_hotspot: pd.DataFrame with columns [date, city, ...8 channels]
    - tensor: np.ndarray of shape (num_days, 29_cities, 8_channels)
    - metadata: dictionary containing tensor dimensions, channel names, and geographic documentation
    """
    df = df.copy()
    if "Date of Occurrence" not in df.columns:
        raise ValueError("Missing 'Date of Occurrence' column for hotspot feature generation.")

    df["date"] = pd.to_datetime(df["Date of Occurrence"]).dt.date
    city_col = "City" if "City" in df.columns else "city"

    # Define channel helpers
    df["is_violent"] = (df["Crime Domain"] == "Violent Crime").astype(int) if "Crime Domain" in df.columns else 0
    df["is_other"] = (df["Crime Domain"] == "Other Crime").astype(int) if "Crime Domain" in df.columns else 0
    df["is_fire"] = (df["Crime Domain"] == "Fire Accident").astype(int) if "Crime Domain" in df.columns else 0
    df["is_traffic"] = (df["Crime Domain"] == "Traffic Fatality").astype(int) if "Crime Domain" in df.columns else 0
    df["is_closed"] = (df["Case Closed"] == "Yes").astype(int) if "Case Closed" in df.columns else 0
    police_col = "Police Deployed" if "Police Deployed" in df.columns else None
    age_col = "Victim Age" if "Victim Age" in df.columns else None

    # Group by (date, city)
    grp = df.groupby(["date", city_col])
    agg_dict = {
        "Report Number": "count",
        "is_violent": "sum",
        "is_other": "sum",
        "is_fire": "sum",
        "is_traffic": "sum",
        "is_closed": "mean",
    }
    if police_col:
        agg_dict[police_col] = "mean"
    if age_col:
        agg_dict[age_col] = "mean"

    agg_df = grp.agg(agg_dict).reset_index()

    rename_map = {
        "Report Number": "total_crimes",
        "is_violent": "violent_crimes",
        "is_other": "other_crimes",
        "is_fire": "fire_accidents",
        "is_traffic": "traffic_fatalities",
        "is_closed": "case_closure_rate",
        city_col: "city",
    }
    if police_col:
        rename_map[police_col] = "avg_police_deployed"
    if age_col:
        rename_map[age_col] = "avg_victim_age"

    agg_df = agg_df.rename(columns=rename_map)

    # Ensure all dates from min to max date are represented across all 29 cities
    min_date = df["date"].min()
    max_date = df["date"].max()
    all_dates = pd.date_range(start=min_date, end=max_date, freq="D").date

    grid_index = pd.MultiIndex.from_product([all_dates, ALL_29_CITIES], names=["date", "city"])
    grid_df = pd.DataFrame(index=grid_index).reset_index()

    full_hotspot = pd.merge(grid_df, agg_df, on=["date", "city"], how="left")
    full_hotspot["total_crimes"] = full_hotspot["total_crimes"].fillna(0).astype(float)
    full_hotspot["violent_crimes"] = full_hotspot["violent_crimes"].fillna(0).astype(float)
    full_hotspot["other_crimes"] = full_hotspot["other_crimes"].fillna(0).astype(float)
    full_hotspot["fire_accidents"] = full_hotspot["fire_accidents"].fillna(0).astype(float)
    full_hotspot["traffic_fatalities"] = full_hotspot["traffic_fatalities"].fillna(0).astype(float)
    full_hotspot["avg_police_deployed"] = full_hotspot["avg_police_deployed"].fillna(0).astype(float)
    full_hotspot["case_closure_rate"] = full_hotspot["case_closure_rate"].fillna(0).astype(float)
    full_hotspot["avg_victim_age"] = full_hotspot["avg_victim_age"].fillna(0).astype(float)

    full_hotspot = full_hotspot.sort_values(by=["date", "city"]).reset_index(drop=True)

    # Construct 3D tensor: (T_days, 29_cities, 8_channels)
    num_days = len(all_dates)
    num_cities = len(ALL_29_CITIES)
    num_channels = len(FEATURE_CHANNELS)

    tensor = np.zeros((num_days, num_cities, num_channels), dtype=np.float32)

    for c_idx, ch_name in enumerate(FEATURE_CHANNELS):
        pivoted = full_hotspot.pivot(index="date", columns="city", values=ch_name)
        # Ensure column ordering matches ALL_29_CITIES
        pivoted = pivoted.reindex(columns=ALL_29_CITIES, fill_value=0.0)
        tensor[:, :, c_idx] = pivoted.values

    metadata = {
        "geographic_resolution": "City-level",
        "geographic_limitation": "The dataset contains only city names across 29 Indian municipalities. No GPS coordinates or sub-city wards are fabricated.",
        "cities": ALL_29_CITIES,
        "city_count": num_cities,
        "feature_channels": FEATURE_CHANNELS,
        "channel_count": num_channels,
        "start_date": str(min_date),
        "end_date": str(max_date),
        "time_periods_count": num_days,
        "tensor_shape": [num_days, num_cities, num_channels],
    }

    return full_hotspot, tensor, metadata


def save_hotspot_data(
    df_hotspot: pd.DataFrame,
    tensor: np.ndarray,
    metadata: Dict[str, Any],
    output_csv: str = "datasets/processed/hotspot_features.csv",
    output_npz: str = "datasets/processed/hotspot_tensor.npz",
    output_meta: str = "datasets/processed/hotspot_metadata.json",
) -> None:
    """Export hotspot feature artifacts."""
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_hotspot.to_csv(output_csv, index=False)
    np.savez_compressed(output_npz, hotspot_tensor=tensor)
    with open(output_meta, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"Saved hotspot dataset: {output_csv}, tensor shape: {tensor.shape}")
