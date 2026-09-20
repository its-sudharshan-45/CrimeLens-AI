"""
ai/preprocessing/preprocessor.py
================================
Core Data Cleaning & Preprocessing Pipeline for CrimeLens AI.
Handles multi-format datetime parsing, duplicate identification, categorical encoding,
state mapping, numeric validation, and leakage-safe preprocessing.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Complete Indian City to State mapping for all 29 cities in the dataset
CITY_TO_STATE: Dict[str, str] = {
    "Delhi": "Delhi",
    "Mumbai": "Maharashtra",
    "Bangalore": "Karnataka",
    "Hyderabad": "Telangana",
    "Kolkata": "West Bengal",
    "Chennai": "Tamil Nadu",
    "Pune": "Maharashtra",
    "Ahmedabad": "Gujarat",
    "Jaipur": "Rajasthan",
    "Lucknow": "Uttar Pradesh",
    "Kanpur": "Uttar Pradesh",
    "Surat": "Gujarat",
    "Nagpur": "Maharashtra",
    "Agra": "Uttar Pradesh",
    "Ludhiana": "Punjab",
    "Visakhapatnam": "Andhra Pradesh",
    "Thane": "Maharashtra",
    "Ghaziabad": "Uttar Pradesh",
    "Indore": "Madhya Pradesh",
    "Patna": "Bihar",
    "Bhopal": "Madhya Pradesh",
    "Meerut": "Uttar Pradesh",
    "Srinagar": "Jammu & Kashmir",
    "Nashik": "Maharashtra",
    "Vasai": "Maharashtra",
    "Varanasi": "Uttar Pradesh",
    "Kalyan": "Maharashtra",
    "Faridabad": "Haryana",
    "Rajkot": "Gujarat",
    # Additional fallbacks
    "Amritsar": "Punjab",
    "Coimbatore": "Tamil Nadu",
    "Vadodara": "Gujarat",
}

# Explicit date formats per column based on verified dataset inspection
DATETIME_COLUMN_FORMATS: Dict[str, str] = {
    "Date Reported": "%d-%m-%Y %H:%M",
    "Date of Occurrence": "%m-%d-%Y %H:%M",
    "Time of Occurrence": "%d-%m-%Y %H:%M",
    "Date Case Closed": "%d-%m-%Y %H:%M",
}


class CrimeDataPreprocessor:
    """
    Preprocessing pipeline for CrimeLens AI dataset.
    Handles duplicate removal, multi-format datetime parsing, missing value handling,
    state mapping, categorical encoding, numeric validation, and transformation.
    """

    def __init__(self) -> None:
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.category_mappings: Dict[str, Dict[str, int]] = {}
        self.scaler = StandardScaler()
        self.feature_columns: List[str] = []
        self.is_fitted: bool = False
        self.city_stats: Dict[str, Any] = {}
        self.state_stats: Dict[str, Any] = {}
        self.cleaning_stats: Dict[str, Any] = {}

    def __setstate__(self, state: Dict[str, Any]) -> None:
        """Handle unpickling of legacy or saved checkpoint instances safely."""
        self.__dict__.update(state)
        if "cleaning_stats" not in self.__dict__ or self.cleaning_stats is None:
            self.cleaning_stats = {}
        if "city_stats" not in self.__dict__ or self.city_stats is None:
            self.city_stats = {}
        if "state_stats" not in self.__dict__ or self.state_stats is None:
            self.state_stats = {}

    def handle_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify and remove genuine duplicate records."""
        if not hasattr(self, "cleaning_stats") or self.cleaning_stats is None:
            self.cleaning_stats = {}
        records_before = len(df)
        duplicates_found = int(df.duplicated().sum())
        df_cleaned = df.drop_duplicates().copy()
        records_after = len(df_cleaned)

        self.cleaning_stats["duplicates"] = {
            "records_before": records_before,
            "duplicates_found": duplicates_found,
            "records_after": records_after,
        }
        if duplicates_found > 0:
            logger.info(f"Dropped {duplicates_found} duplicate records ({records_before} -> {records_after}).")
        return df_cleaned

    def clean_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing values according to semantic meaning:
        - Weapon Used: missing -> 'Unknown'
        - Date Case Closed: preserved as NaT for unresolved cases (Case Closed == 'No').
        """
        df = df.copy()
        missing_before = {col: df[col].isnull().sum() for col in df.columns}

        if "Weapon Used" in df.columns:
            df["Weapon Used"] = df["Weapon Used"].fillna("Unknown")

        if "Victim Gender" in df.columns:
            df["Victim Gender"] = df["Victim Gender"].fillna("Unknown")

        missing_after = {col: df[col].isnull().sum() for col in df.columns}
        self.cleaning_stats["missing_values"] = {
            "before": missing_before,
            "after": missing_after,
        }
        return df

    def validate_numerics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate numeric columns (Victim Age, Police Deployed, Crime Code)."""
        df = df.copy()
        if "Victim Age" in df.columns:
            df["Victim Age"] = pd.to_numeric(df["Victim Age"], errors="coerce").fillna(df["Victim Age"].median()).clip(lower=0, upper=120)

        if "Police Deployed" in df.columns:
            df["Police Deployed"] = pd.to_numeric(df["Police Deployed"], errors="coerce").fillna(1).clip(lower=1)

        if "Crime Code" in df.columns:
            df["Crime Code"] = pd.to_numeric(df["Crime Code"], errors="coerce").fillna(0).astype(int)

        return df

    def map_states(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map city names to their corresponding Indian state."""
        df = df.copy()
        if "City" in df.columns:
            df["State"] = df["City"].map(lambda c: CITY_TO_STATE.get(str(c).strip(), "Other State"))
        return df

    def parse_datetime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parse string datetime columns into pandas Datetime objects using verified formats.
        Calculates Reporting_Lag_Hours and Resolution_Days safely.
        """
        df = df.copy()

        for col, fmt in DATETIME_COLUMN_FORMATS.items():
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format=fmt, errors="coerce")

        # Reporting Lag in Hours (Date Reported - Date of Occurrence)
        if "Date Reported" in df.columns and "Date of Occurrence" in df.columns:
            diff_rep = df["Date Reported"] - df["Date of Occurrence"]
            # Total seconds / 3600.0, safely clipped at >= 0
            df["Reporting_Lag_Hours"] = (diff_rep.dt.total_seconds() / 3600.0).fillna(0.0).clip(lower=0.0)  # type: ignore

        # Resolution Days for closed cases
        if "Date Case Closed" in df.columns and "Date of Occurrence" in df.columns:
            diff_cls = df["Date Case Closed"] - df["Date of Occurrence"]
            # Negative 1.0 signifies open/unresolved cases
            df["Resolution_Days"] = (diff_cls.dt.total_seconds() / 86400.0).fillna(-1.0)  # type: ignore

        return df

    def fit_encoders(self, df: pd.DataFrame) -> None:
        """
        Fit label encoders for categorical features.
        Stores category mappings explicitly for neural network embedding indexing.
        """
        cat_cols = [
            "City",
            "State",
            "Victim Gender",
            "Weapon Used",
            "Crime Domain",
            "Crime Description",
            "Case Closed",
        ]

        for col in cat_cols:
            if col in df.columns:
                le = LabelEncoder()
                values = df[col].astype(str).unique()
                le.fit(values)
                self.label_encoders[col] = le
                self.category_mappings[col] = {category: idx for idx, category in enumerate(le.classes_)}

    def transform_encoders(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform categorical features using fitted LabelEncoders.
        Handles unseen categories gracefully using known fallback classes.
        """
        df = df.copy()
        for col, le in self.label_encoders.items():
            if col in df.columns:
                known_classes = set(le.classes_)
                fallback_val = le.classes_[0]
                col_values = df[col].astype(str).map(
                    lambda s, _kc=known_classes, _fb=fallback_val: s if s in _kc else _fb
                )
                df[f"{col}_encoded"] = le.transform(col_values)  # type: ignore
        return df

    def clean_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform full data cleaning stage (duplicates, missing, numerics, states, dates)."""
        df_unique = self.handle_duplicates(df)
        df_clean = self.clean_missing_values(df_unique)
        df_num = self.validate_numerics(df_clean)
        df_state = self.map_states(df_num)
        df_dt = self.parse_datetime_features(df_state)
        return df_dt

    def fit(self, df: pd.DataFrame) -> "CrimeDataPreprocessor":
        """Fit all preprocessing transformers strictly on provided (e.g. training) data."""
        df_clean = self.clean_dataset(df)
        self.fit_encoders(df_clean)
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply full preprocessing transformation pipeline to any split."""
        if not self.is_fitted:
            self.fit(df)
        df_clean = self.clean_dataset(df)
        df_encoded = self.transform_encoders(df_clean)
        return df_encoded

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit on training data and return transformed dataframe."""
        return self.fit(df).transform(df)

    def save(self, filepath: str = "ai/models/preprocessor.pkl") -> None:
        """Save preprocessor pipeline artifact."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self, filepath)
        logger.info(f"Preprocessor artifact saved to {filepath}")

    @staticmethod
    def load(filepath: str = "ai/models/preprocessor.pkl") -> "CrimeDataPreprocessor":
        """Load preprocessor pipeline artifact."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Preprocessor model file not found at {filepath}")
        return joblib.load(filepath)
