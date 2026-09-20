"""
ai/models/nbeats_forecaster.py
================================
N-BEATS: Neural Basis Expansion Analysis for Interpretable Time Series Forecasting.

Reference: Oreshkin et al. (2019) "N-BEATS: Neural basis expansion analysis
           for interpretable time series forecasting"

Architecture:
    Generic + Trend + Seasonality Stacks
    Each Stack:  N Blocks with Basis Expansion (theta projection)
                 Residual backcast subtracted for next block
    Final Forecast: Sum of all block forecasts

Supports multi-horizon forecasting: 7-day, 30-day, 90-day.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple


class NBEATSBlock(nn.Module):
    """
    N-BEATS building block: FC layers with shared theta for backcast/forecast basis expansion.
    """

    def __init__(
        self,
        input_size: int,
        theta_size: int,
        fc_hidden: int = 256,
        n_layers: int = 4,
    ) -> None:
        super().__init__()
        layers = [nn.Linear(input_size, fc_hidden), nn.ReLU()]
        for _ in range(n_layers - 1):
            layers += [nn.Linear(fc_hidden, fc_hidden), nn.ReLU()]
        self.fc_stack = nn.Sequential(*layers)
        self.backcast_linear = nn.Linear(fc_hidden, theta_size)
        self.forecast_linear = nn.Linear(fc_hidden, theta_size)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.fc_stack(x)
        backcast_theta = self.backcast_linear(h)
        forecast_theta = self.forecast_linear(h)
        return backcast_theta, forecast_theta


class NBEATSGenericStack(nn.Module):
    """Generic N-BEATS stack: learns arbitrary basis functions."""

    def __init__(self, input_size: int, forecast_horizon: int, n_blocks: int = 3, fc_hidden: int = 256) -> None:
        super().__init__()
        theta_size = input_size + forecast_horizon
        self.blocks = nn.ModuleList([
            NBEATSBlock(input_size, theta_size, fc_hidden)
            for _ in range(n_blocks)
        ])
        self.input_size = input_size
        self.forecast_horizon = forecast_horizon

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        residual = x
        forecast = torch.zeros(x.size(0), self.forecast_horizon, device=x.device)
        for block in self.blocks:
            theta_back, theta_fore = block(residual)
            backcast = theta_back[:, :self.input_size]
            fore = theta_fore[:, :self.forecast_horizon]
            residual = residual - backcast
            forecast = forecast + fore
        return residual, forecast


class NBEATSTrendStack(nn.Module):
    """Trend N-BEATS stack: polynomial basis for trend extraction."""

    def __init__(self, input_size: int, forecast_horizon: int, n_blocks: int = 3, poly_degree: int = 3) -> None:
        super().__init__()
        theta_size = 2 * (poly_degree + 1)
        self.blocks = nn.ModuleList([
            NBEATSBlock(input_size, theta_size, fc_hidden=256)
            for _ in range(n_blocks)
        ])
        self.input_size = input_size
        self.forecast_horizon = forecast_horizon
        self.poly_degree = poly_degree
        # Precompute polynomial basis matrices
        self._register_basis()

    def _register_basis(self) -> None:
        p = self.poly_degree + 1
        t_back = torch.arange(self.input_size).float() / self.input_size
        t_fore = torch.arange(self.forecast_horizon).float() / self.forecast_horizon
        T_back = torch.stack([t_back ** i for i in range(p)], dim=0)  # (p, input_size)
        T_fore = torch.stack([t_fore ** i for i in range(p)], dim=0)  # (p, forecast_horizon)
        self.register_buffer("T_back", T_back)
        self.register_buffer("T_fore", T_fore)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        residual = x
        forecast = torch.zeros(x.size(0), self.forecast_horizon, device=x.device)
        p = self.poly_degree + 1
        for block in self.blocks:
            theta_back, theta_fore = block(residual)
            # (B, p) @ (p, T) → (B, T)
            backcast = (theta_back[:, :p] @ self.T_back)
            fore = (theta_fore[:, :p] @ self.T_fore)
            residual = residual - backcast
            forecast = forecast + fore
        return residual, forecast


class NBEATSSeasonalityStack(nn.Module):
    """Seasonality N-BEATS stack: Fourier basis for seasonal extraction."""

    def __init__(self, input_size: int, forecast_horizon: int, n_blocks: int = 3, harmonics: int = 4) -> None:
        super().__init__()
        theta_size = 4 * harmonics
        self.blocks = nn.ModuleList([
            NBEATSBlock(input_size, theta_size, fc_hidden=256)
            for _ in range(n_blocks)
        ])
        self.input_size = input_size
        self.forecast_horizon = forecast_horizon
        self.harmonics = harmonics
        self._register_basis()

    def _register_basis(self) -> None:
        h = self.harmonics
        t_back = torch.arange(self.input_size).float() / self.input_size
        t_fore = torch.arange(self.forecast_horizon).float() / self.forecast_horizon
        freqs = torch.arange(1, h + 1).float()
        # (2h, T)
        S_back = torch.cat([
            torch.stack([torch.cos(2 * np.pi * k * t_back) for k in freqs]),
            torch.stack([torch.sin(2 * np.pi * k * t_back) for k in freqs])
        ], dim=0)
        S_fore = torch.cat([
            torch.stack([torch.cos(2 * np.pi * k * t_fore) for k in freqs]),
            torch.stack([torch.sin(2 * np.pi * k * t_fore) for k in freqs])
        ], dim=0)
        self.register_buffer("S_back", S_back)
        self.register_buffer("S_fore", S_fore)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        residual = x
        forecast = torch.zeros(x.size(0), self.forecast_horizon, device=x.device)
        n = 2 * self.harmonics
        for block in self.blocks:
            theta_back, theta_fore = block(residual)
            backcast = (theta_back[:, :n] @ self.S_back)
            fore = (theta_fore[:, :n] @ self.S_fore)
            residual = residual - backcast
            forecast = forecast + fore
        return residual, forecast


class NBEATSForecaster(nn.Module):
    """
    N-BEATS Multi-Horizon Forecaster for crime incident time series.
    Combines Generic + Trend + Seasonality stacks for interpretable forecasting.
    Supports multi-horizon forecasting: 7-day, 30-day, 90-day.

    Args:
        input_size:       Lookback window length (sequence input size).
        forecast_horizon: Number of future steps to predict.
        n_stacks:         Number of stacks per type (default: 1 each type).
        n_blocks:         Number of blocks per stack.
        fc_hidden:        Hidden units in each block FC layer.
    """

    def __init__(
        self,
        input_size: int = 30,
        forecast_horizon: int = 7,
        n_blocks: int = 3,
        fc_hidden: int = 256,
    ) -> None:
        super().__init__()
        self.input_size = input_size
        self.forecast_horizon = forecast_horizon

        self.generic_stack = NBEATSGenericStack(input_size, forecast_horizon, n_blocks, fc_hidden)
        self.trend_stack = NBEATSTrendStack(input_size, forecast_horizon, n_blocks)
        self.seasonality_stack = NBEATSSeasonalityStack(input_size, forecast_horizon, n_blocks)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, input_size) or (batch_size, input_size, 1) — time series lookback window
        Returns:
            forecast: (batch_size, forecast_horizon)
        """
        if x.dim() == 3:
            x = x.squeeze(-1)  # (B, input_size)

        residual, forecast_generic = self.generic_stack(x)
        residual, forecast_trend = self.trend_stack(residual)
        _, forecast_seasonal = self.seasonality_stack(residual)

        forecast = forecast_generic + forecast_trend + forecast_seasonal
        return forecast
