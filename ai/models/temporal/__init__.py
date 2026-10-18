"""
ai/models/temporal/__init__.py
==============================
The single temporal deep-learning model used by CrimeLens AI: a GRU
crime-count forecaster. Historical LSTM/N-BEATS research code now lives under
``archive/legacy_classifier_2026-10/``.
"""

from ai.models.temporal.gru import CrimeGRUForecaster

__all__ = ["CrimeGRUForecaster"]
