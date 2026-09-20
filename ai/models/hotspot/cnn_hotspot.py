"""
ai/models/hotspot/cnn_hotspot.py
==================================
CNN City-Level Crime Hotspot Forecaster for CrimeLens AI (Phase 4).

Architecture:
    Input: (batch_size, 8_features, 30_days, 29_cities)
       ↓  [treat 8 feature channels as CNN input channels,
           30 days as height, 29 cities as width]
    Conv2d(8, 32, kernel=(3,3), padding=1) + BatchNorm + ReLU
       ↓
    MaxPool2d(kernel=(2,1))  [downsample temporal axis, keep city axis]
       ↓
    Conv2d(32, 64, kernel=(3,3), padding=1) + BatchNorm + ReLU
       ↓
    AdaptiveAvgPool2d((1, 29))  [collapse temporal axis, keep 29 cities]
       ↓
    Reshape to (B, 64 * 29)
       ↓
    Dropout(0.2)
       ↓
    Linear(64 * 29, 128) + ReLU
       ↓
    Dropout(0.2)
       ↓
    Linear(128, 29)  [one value per city]
       ↓
    Output: (batch_size, 29)

Each output represents predicted total crime activity for the next 7 days
for a given city, enabling city-level risk ranking.
"""

from typing import Optional
import torch
import torch.nn as nn


class CNNHotspotForecaster(nn.Module):
    """
    CNN-based city-level crime hotspot forecaster.

    The model takes a sliding window of multi-city, multi-feature daily
    crime statistics and predicts the next-period crime activity for each
    of the 29 cities.

    Args:
        n_cities:          Number of cities (default: 29).
        n_features:        Number of feature channels per city (default: 8).
        window_size:       Historical lookback window in days (default: 30).
        conv_filters_1:    Filters in the first conv layer (default: 32).
        conv_filters_2:    Filters in the second conv layer (default: 64).
        fc_hidden:         Hidden units in the fully-connected head (default: 128).
        dropout:           Dropout rate (default: 0.2).
    """

    def __init__(
        self,
        n_cities: int = 29,
        n_features: int = 8,
        window_size: int = 30,
        conv_filters_1: int = 32,
        conv_filters_2: int = 64,
        fc_hidden: int = 128,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.n_cities = n_cities
        self.n_features = n_features
        self.window_size = window_size
        self.conv_filters_1 = conv_filters_1
        self.conv_filters_2 = conv_filters_2
        self.fc_hidden = fc_hidden
        self.dropout_rate = dropout

        # Convolutional backbone
        self.conv1 = nn.Sequential(
            nn.Conv2d(n_features, conv_filters_1, kernel_size=(3, 3), padding=(1, 1)),
            nn.BatchNorm2d(conv_filters_1),
            nn.ReLU(inplace=True),
        )
        # Pool along temporal axis only (height=days), preserve city axis (width=cities)
        self.pool1 = nn.MaxPool2d(kernel_size=(2, 1))

        self.conv2 = nn.Sequential(
            nn.Conv2d(conv_filters_1, conv_filters_2, kernel_size=(3, 3), padding=(1, 1)),
            nn.BatchNorm2d(conv_filters_2),
            nn.ReLU(inplace=True),
        )
        # Collapse temporal axis entirely, keep full city resolution
        self.adaptive_pool = nn.AdaptiveAvgPool2d((1, n_cities))

        # Fully connected head
        fc_input_dim = conv_filters_2 * n_cities
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(fc_input_dim, fc_hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(fc_hidden, n_cities),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (batch_size, window_size, n_cities, n_features)
               or (batch_size, n_features, window_size, n_cities) if pre-permuted.

        Returns:
            Tensor of shape (batch_size, n_cities) — one predicted crime value per city.
        """
        # Expect x: (B, window_size, n_cities, n_features)
        # Permute to (B, n_features, window_size, n_cities) for Conv2d [NCHW]
        if x.dim() == 4 and x.shape[-1] == self.n_features:
            x = x.permute(0, 3, 1, 2)  # (B, F, T, C)

        # Convolutional feature extraction
        x = self.conv1(x)       # (B, 32, T, C)
        x = self.pool1(x)       # (B, 32, T//2, C)
        x = self.conv2(x)       # (B, 64, T//2, C)
        x = self.adaptive_pool(x)  # (B, 64, 1, 29)

        # Flatten: (B, 64 * 29)
        x = x.flatten(1)

        # Fully connected head: (B, 29)
        x = self.head(x)
        return x

    def get_config(self) -> dict:
        """Return model architecture configuration."""
        return {
            "model_type": "CNNHotspotForecaster",
            "n_cities": self.n_cities,
            "n_features": self.n_features,
            "window_size": self.window_size,
            "conv_filters_1": self.conv_filters_1,
            "conv_filters_2": self.conv_filters_2,
            "fc_hidden": self.fc_hidden,
            "dropout": self.dropout_rate,
        }
