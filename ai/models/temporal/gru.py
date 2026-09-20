"""
ai/models/temporal/gru.py
==========================
Standard GRU Time Series Forecaster for CrimeLens AI (Phase 3).

Architecture:
    Input: (batch_size, seq_len=30, input_size=13)
       ↓
    GRU(input_size=13, hidden_size=64, num_layers=2, dropout=0.2, batch_first=True)
       ↓
    Dropout(0.2)
       ↓
    Dense / Linear(64, 7)
       ↓
    Output: (batch_size, forecast_horizon=7)

Designed for academic comparison against the LSTM model with equivalent capacity.
"""

from typing import Optional
import torch
import torch.nn as nn


class CrimeGRUForecaster(nn.Module):
    """
    Standard GRU multi-step crime count forecaster.

    Args:
        input_size: Number of input features per time step (default: 13).
        hidden_size: GRU hidden state dimension (default: 64).
        num_layers: Number of stacked GRU layers (default: 2).
        forecast_horizon: Number of future days to forecast (default: 7).
        dropout: Dropout rate between layers and before dense head (default: 0.2).
    """

    def __init__(
        self,
        input_size: int = 13,
        hidden_size: int = 64,
        num_layers: int = 2,
        forecast_horizon: int = 7,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.forecast_horizon = forecast_horizon
        self.dropout_rate = dropout

        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, forecast_horizon)

    def forward(
        self,
        x: torch.Tensor,
        hx: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Tensor of shape (batch_size, seq_len, input_size) or (batch_size, seq_len)
            hx: Optional initial hidden state

        Returns:
            forecast: Tensor of shape (batch_size, forecast_horizon)
        """
        if x.dim() == 2:
            x = x.unsqueeze(-1)

        # out: (batch_size, seq_len, hidden_size)
        out, _ = self.gru(x, hx)

        # Take last time-step representation
        last_step = out[:, -1, :]  # (batch_size, hidden_size)
        dropped = self.dropout(last_step)
        forecast = self.fc(dropped)  # (batch_size, forecast_horizon)
        return forecast

    def get_config(self) -> dict:
        """Return model architecture configuration dictionary."""
        return {
            "model_type": "GRU",
            "input_size": self.input_size,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "forecast_horizon": self.forecast_horizon,
            "dropout": self.dropout_rate,
        }
