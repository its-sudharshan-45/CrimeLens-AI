"""
ai/models/hotspot
=================
City-level spatio-temporal aggregation helpers for CrimeLens AI.

NOTE (2026-10-16): The 2D-CNN forecaster (CNNHotspotForecaster) was removed.
The crime dataset is structured tabular data (29 cities x 8 aggregate
channels), not images. Conv2d across alphabetically-ordered cities assumed
false spatial locality. City-level tensors from
ai.preprocessing.hotspot_dataset remain available as generic tabular
analytics artifacts for future non-convolutional models.
See backups/cnn_removal_2026-10-16/ for quarantined CNN sources.
"""

__all__: list = []
