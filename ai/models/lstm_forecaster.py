"""
ai/models/lstm_forecaster.py
============================
Bi-Directional LSTM + Multi-Head Attention Time Series Forecaster.
Serves as secondary forecaster in the multi-horizon forecasting ensemble.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class BiLSTMAttentionForecaster(nn.Module):
    """
    Bi-LSTM + Multi-Head Self-Attention sequence forecasting network.
    Uses bi-directional context and multi-head attention to weight temporal states.

    Args:
        input_size:       Number of input features per time step (default: 1).
        hidden_dim:       LSTM hidden state size (default: 64).
        num_layers:       Number of stacked LSTM layers (default: 2).
        forecast_horizon: Number of future time steps to predict (default: 7).
        n_heads:          Number of attention heads (default: 4).
        dropout:          Dropout rate.
    """

    def __init__(
        self,
        input_size: int = 1,
        hidden_dim: int = 64,
        num_layers: int = 2,
        forecast_horizon: int = 7,
        n_heads: int = 4,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.input_size = input_size
        self.hidden_dim = hidden_dim
        self.forecast_horizon = forecast_horizon

        # Bi-directional LSTM
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Multi-Head Attention over temporal states (hidden_dim * 2 for bidirectional)
        self.attn_norm = nn.LayerNorm(hidden_dim * 2)
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim * 2,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True,
        )

        # Dense projection head
        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Linear(64, forecast_horizon),
        )

    def forward(self, x_seq: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x_seq: (batch_size, seq_len, input_size) or (batch_size, seq_len)
        Returns:
            forecast: (batch_size, forecast_horizon)
        """
        if x_seq.dim() == 2:
            x_seq = x_seq.unsqueeze(-1)

        # Bi-LSTM output: (B, seq_len, hidden_dim * 2)
        lstm_out, _ = self.lstm(x_seq)

        # Self-attention over temporal sequence
        normed = self.attn_norm(lstm_out)
        attn_out, _ = self.attention(normed, normed, normed)
        context = lstm_out + attn_out

        # Global average pooling over time steps
        pooled = torch.mean(context, dim=1)  # (B, hidden_dim * 2)

        # Project to forecast horizon
        forecast = self.head(pooled)
        return forecast


# Alias for backward compatibility
CrimeLSTMForecaster = BiLSTMAttentionForecaster
