"""
ai/forecasting
==============
Single, beginner-friendly GRU crime-count forecasting package for CrimeLens AI.

This package replaces the previous multi-model temporal stack (LSTM + GRU +
N-BEATS) with exactly one model, one training pipeline, one evaluation pipeline
and one inference implementation.

Public surface:
    data.build_scope_series          -> per-scope continuous daily count series
    data.FORECAST_FEATURE_COLUMNS    -> ordered model input features
    train.train_forecaster           -> trains + evaluates + saves artifacts
    predict.CrimeForecastPredictor   -> loads artifacts and produces forecasts
"""

from ai.forecasting.data import (
    FORECAST_FEATURE_COLUMNS,
    SCOPE_TYPES,
    build_dataset,
    load_raw_dataset,
)

__all__ = [
    "FORECAST_FEATURE_COLUMNS",
    "SCOPE_TYPES",
    "build_dataset",
    "load_raw_dataset",
]
