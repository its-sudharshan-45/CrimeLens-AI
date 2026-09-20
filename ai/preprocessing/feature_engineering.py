"""
ai/preprocessing/feature_engineering.py
======================================
Feature engineering component for CrimeLens AI data pipeline.
Generates temporal, cyclical, time-of-day, Indian seasonal, aggregate frequency,
and district/state historical features with strict leakage prevention.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Consistent 24-hour Time-of-Day mapping
# Night: 22:00 - 05:59 (hours 22, 23, 0, 1, 2, 3, 4, 5)
# Morning: 06:00 - 11:59 (hours 6, 7, 8, 9, 10, 11)
# Afternoon: 12:00 - 16:59 (hours 12, 13, 14, 15, 16)
# Evening: 17:00 - 21:59 (hours 17, 18, 19, 20, 21)
def assign_time_of_day(hour: int) -> str:
    """Map 24-hour integer to time-of-day category."""
    if hour in (22, 23, 0, 1, 2, 3, 4, 5):
        return "Night"
    elif 6 <= hour <= 11:
        return "Morning"
    elif 12 <= hour <= 16:
        return "Afternoon"
    else:
        return "Evening"


# Indian Meteorological Department (IMD) Standard Seasonal Groupings
# Winter: Dec, Jan, Feb
# Summer: Mar, Apr, May
# Monsoon: Jun, Jul, Aug, Sep
# Post-Monsoon: Oct, Nov
def assign_season(month: int) -> str:
    """Map calendar month to Indian meteorological season."""
    if month in (12, 1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Summer"
    elif month in (6, 7, 8, 9):
        return "Monsoon"
    else:
        return "Post-Monsoon"


class FeatureEngineer:
    """
    Feature engineering component for CrimeLens AI data pipeline.
    Extracts temporal, cyclical, regional, and domain features without data leakage.
    """

    def __init__(self) -> None:
        self.city_stats: Dict[str, Dict[str, float]] = {}
        self.state_stats: Dict[str, Dict[str, float]] = {}
        self.category_freq_map: Dict[str, int] = {}
        self.city_freq_map: Dict[str, int] = {}
        self.state_freq_map: Dict[str, int] = {}
        self.is_fitted: bool = False

    def extract_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract temporal features from Date of Occurrence and Time of Occurrence:
        year, month, day, day_of_week, hour, week_of_year, quarter, is_weekend,
        time_of_day, and season.
        """
        df = df.copy()

        # Base datetime from Date of Occurrence
        if "Date of Occurrence" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Date of Occurrence"]):
            dt = df["Date of Occurrence"]
        elif "Date of Occurrence" in df.columns:
            dt = pd.to_datetime(df["Date of Occurrence"], errors="coerce")
        else:
            dt = pd.Series(pd.to_datetime("2020-01-01"), index=df.index)

        dt_prop: Any = dt.dt
        # Exact hour from Time of Occurrence if available and valid
        if "Time of Occurrence" in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df["Time of Occurrence"]):
                tm_dt = df["Time of Occurrence"]
            else:
                tm_dt = pd.to_datetime(df["Time of Occurrence"], errors="coerce")
            tm_dt_prop: Any = tm_dt.dt
            # Fall back to dt hour if tm_dt is missing
            hour_series = tm_dt_prop.hour.fillna(dt_prop.hour).fillna(0).astype(int)
        else:
            hour_series = dt_prop.hour.fillna(0).astype(int)

        df["Year"] = dt_prop.year.fillna(2020).astype(int)
        df["Month"] = dt_prop.month.fillna(1).astype(int)
        df["Day"] = dt_prop.day.fillna(1).astype(int)
        df["Day_of_Week"] = dt_prop.dayofweek.fillna(0).astype(int)
        df["Weekday"] = df["Day_of_Week"]  # backward compatibility alias
        df["Hour"] = hour_series
        # ISO week of year (1-53)
        df["Week_of_Year"] = dt_prop.isocalendar().week.fillna(1).astype(int)
        df["Quarter"] = dt_prop.quarter.fillna(1).astype(int)
        df["Is_Weekend"] = df["Day_of_Week"].isin([5, 6]).astype(int)

        # Categorical time buckets
        df["Time_of_Day"] = df["Hour"].map(assign_time_of_day)
        df["Season"] = df["Month"].map(assign_season)

        return df

    def extract_cyclical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract Sine and Cosine cyclical transformations for cyclic features."""
        df = df.copy()
        # Month (1-12)
        df["sin_month"] = np.sin(2 * np.pi * df["Month"] / 12.0)
        df["cos_month"] = np.cos(2 * np.pi * df["Month"] / 12.0)
        # Hour (0-23)
        df["sin_hour"] = np.sin(2 * np.pi * df["Hour"] / 24.0)
        df["cos_hour"] = np.cos(2 * np.pi * df["Hour"] / 24.0)
        # Day of week (0-6)
        df["sin_weekday"] = np.sin(2 * np.pi * df["Day_of_Week"] / 7.0)
        df["cos_weekday"] = np.cos(2 * np.pi * df["Day_of_Week"] / 7.0)
        return df

    def fit_aggregated_statistics(self, df_train: pd.DataFrame) -> None:
        """
        Fit historical frequency maps and city/state summary statistics ONLY on training split.
        Prevents lookahead target/frequency data leakage into validation and test sets.
        """
        if "City" in df_train.columns:
            self.city_freq_map = df_train["City"].value_counts().to_dict()
        if "State" in df_train.columns:
            self.state_freq_map = df_train["State"].value_counts().to_dict()
        if "Crime Description" in df_train.columns:
            self.category_freq_map = df_train["Crime Description"].value_counts().to_dict()

        # City statistics from training set
        if "City" in df_train.columns:
            city_grp = df_train.groupby("City")
            for city, group in city_grp:
                self.city_stats[str(city)] = {
                    "mean_police": group["Police Deployed"].mean() if "Police Deployed" in group.columns else 10.0,
                    "closure_rate": (group["Case Closed"] == "Yes").mean() if "Case Closed" in group.columns else 0.5,
                    "avg_victim_age": group["Victim Age"].mean() if "Victim Age" in group.columns else 44.0,
                }

        # State statistics from training set
        if "State" in df_train.columns:
            state_grp = df_train.groupby("State")
            for state, group in state_grp:
                self.state_stats[str(state)] = {
                    "mean_police": group["Police Deployed"].mean() if "Police Deployed" in group.columns else 10.0,
                    "closure_rate": (group["Case Closed"] == "Yes").mean() if "Case Closed" in group.columns else 0.5,
                    "avg_victim_age": group["Victim Age"].mean() if "Victim Age" in group.columns else 44.0,
                }

        self.is_fitted = True

    def apply_aggregated_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply pre-fitted historical statistics and frequency encodings to any dataframe split."""
        df = df.copy()

        if "City" in df.columns:
            df["City_Crime_Freq"] = df["City"].map(lambda c: self.city_freq_map.get(c, 0)).fillna(0)
            df["City_Mean_Police"] = df["City"].map(lambda c: self.city_stats.get(c, {}).get("mean_police", 10.0))
            df["City_Closure_Rate"] = df["City"].map(lambda c: self.city_stats.get(c, {}).get("closure_rate", 0.5))

        if "State" in df.columns:
            df["State_Crime_Freq"] = df["State"].map(lambda s: self.state_freq_map.get(s, 0)).fillna(0)
            df["State_Mean_Police"] = df["State"].map(lambda s: self.state_stats.get(s, {}).get("mean_police", 10.0))
            df["State_Closure_Rate"] = df["State"].map(lambda s: self.state_stats.get(s, {}).get("closure_rate", 0.5))

        if "Crime Description" in df.columns:
            df["Category_Freq"] = df["Crime Description"].map(lambda cd: self.category_freq_map.get(cd, 0)).fillna(0)

        return df

    def transform(self, df: pd.DataFrame, is_train: bool = True) -> pd.DataFrame:
        """
        Execute full feature engineering pipeline.
        If is_train=True, fits statistics before applying them.
        """
        df_temp = self.extract_temporal_features(df)
        df_cyc = self.extract_cyclical_features(df_temp)

        if is_train or not self.is_fitted:
            self.fit_aggregated_statistics(df_cyc)

        df_feats = self.apply_aggregated_statistics(df_cyc)
        return df_feats

    def get_feature_matrix(self, df: pd.DataFrame, target_type: str = "classification") -> Tuple[pd.DataFrame, Optional[np.ndarray], List[str]]:
        """
        Extract numeric feature matrix X and target array y for modeling.
        target_type options:
        - 'classification' (Crime Domain)
        - 'fine_classification' (Crime Description)
        - 'regression' (Police Deployed)
        """
        feature_cols = [
            "Victim Age",
            "City_encoded",
            "State_encoded",
            "Victim Gender_encoded",
            "Weapon Used_encoded",
            "Year",
            "Month",
            "Day",
            "Day_of_Week",
            "Hour",
            "Week_of_Year",
            "Quarter",
            "Is_Weekend",
            "sin_month",
            "cos_month",
            "sin_hour",
            "cos_hour",
            "sin_weekday",
            "cos_weekday",
            "City_Crime_Freq",
            "State_Crime_Freq",
            "Category_Freq",
            "City_Mean_Police",
            "City_Closure_Rate",
            "State_Mean_Police",
            "State_Closure_Rate",
            "Reporting_Lag_Hours",
        ]

        available_cols = [c for c in feature_cols if c in df.columns]
        X = df[available_cols].copy()

        if target_type == "classification":
            y = np.asarray(df["Crime Domain_encoded"]) if "Crime Domain_encoded" in df.columns else None
        elif target_type == "fine_classification":
            y = np.asarray(df["Crime Description_encoded"]) if "Crime Description_encoded" in df.columns else None
        elif target_type == "regression":
            y = np.asarray(df["Police Deployed"]) if "Police Deployed" in df.columns else None
        else:
            y = None

        return X, y, available_cols
