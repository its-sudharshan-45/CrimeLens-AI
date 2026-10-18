"""
ai/models/mlp_classifier.py
============================
Enhanced Residual MLP Classifier with GELU, LayerNorm, and skip connections.
Used as a secondary model in the Ensemble Classifier.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    """Residual feedforward block with GELU activation and LayerNorm."""

    def __init__(self, d_in: int, d_out: int, dropout: float = 0.2) -> None:
        super().__init__()
        self.linear1 = nn.Linear(d_in, d_out)
        self.linear2 = nn.Linear(d_out, d_out)
        self.norm1 = nn.LayerNorm(d_out)
        self.norm2 = nn.LayerNorm(d_out)
        self.dropout = nn.Dropout(dropout)
        # Projection for residual if dimensions differ
        self.proj = nn.Linear(d_in, d_out) if d_in != d_out else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.proj(x)
        out = F.gelu(self.norm1(self.linear1(x)))
        out = self.dropout(out)
        out = self.norm2(self.linear2(out))
        return F.gelu(out + residual)


class CrimeMLPClassifier(nn.Module):
    """
    Enhanced Residual MLP Classifier for tabular crime classification.
    Uses GELU activations, LayerNorm, residual connections, and dropout.
    Serves as secondary model in the EnsembleClassifier.

    Architecture:
        Input(d_in) → ResidualBlock(256) → ResidualBlock(128) → ResidualBlock(64) → Output(num_classes)
    """

    def __init__(self, input_dim: int, num_classes: int = 4, dropout_rate: float = 0.2) -> None:
        super().__init__()
        self.input_norm = nn.LayerNorm(input_dim)
        self.block1 = ResidualBlock(input_dim, 256, dropout=dropout_rate)
        self.block2 = ResidualBlock(256, 128, dropout=dropout_rate)
        self.block3 = ResidualBlock(128, 64, dropout=dropout_rate * 0.5)
        self.output = nn.Linear(64, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.input_norm(x)
        out = self.block1(out)
        out = self.block2(out)
        out = self.block3(out)
        return self.output(out)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Returns softmax class probabilities."""
        self.eval()
        with torch.no_grad():
            return F.softmax(self.forward(x), dim=-1)
