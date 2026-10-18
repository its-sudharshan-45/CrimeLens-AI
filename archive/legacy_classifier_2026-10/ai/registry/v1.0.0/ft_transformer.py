"""
ai/models/ft_transformer.py
============================
Feature Tokenizer + Transformer (FT-Transformer) for Tabular Classification.

Reference: Gorishniy et al. (2021) "Revisiting Deep Learning Models for Tabular Data"
Architecture:
    Numerical Feature Tokenization (Linear embedding per feature)
    CLS Token Prepended
    Multi-Head Self-Attention × N Transformer Blocks
    LayerNorm + FFN with GELU
    CLS Token → MLP Classification Head
    Crime Domain Prediction
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, cast


class FeatureTokenizer(nn.Module):
    """
    Projects each scalar numerical feature to a d_token-dimensional embedding.
    Each feature gets its own independent linear projection + bias.
    """

    def __init__(self, n_features: int, d_token: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.empty(n_features, d_token))
        self.bias = nn.Parameter(torch.empty(n_features, d_token))
        nn.init.kaiming_uniform_(self.weight, a=5 ** 0.5)
        nn.init.zeros_(self.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, n_features)
        Returns:
            tokens: (batch_size, n_features, d_token)
        """
        return x.unsqueeze(-1) * self.weight.unsqueeze(0) + self.bias.unsqueeze(0)


class TransformerBlock(nn.Module):
    """
    Single Transformer encoder block: Multi-Head Self-Attention + LayerNorm + FFN.
    Pre-LN (Layer Norm before attention) for training stability.
    """

    def __init__(self, d_token: int, n_heads: int, ffn_dropout: float = 0.1, attn_dropout: float = 0.1) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(d_token)
        self.attn = nn.MultiheadAttention(
            embed_dim=d_token, num_heads=n_heads,
            dropout=attn_dropout, batch_first=True
        )
        self.norm2 = nn.LayerNorm(d_token)
        self.ffn = nn.Sequential(
            nn.Linear(d_token, d_token * 4),
            nn.GELU(),
            nn.Dropout(ffn_dropout),
            nn.Linear(d_token * 4, d_token),
            nn.Dropout(ffn_dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_len, d_token)
        Returns:
            x: (batch_size, seq_len, d_token)
        """
        normed = self.norm1(x)
        attn_out, _ = self.attn(normed, normed, normed)
        x = x + attn_out
        x = x + self.ffn(self.norm2(x))
        return x


class FTTransformerClassifier(nn.Module):
    """
    FT-Transformer: Production-grade tabular deep learning classifier.
    SOTA for numerical tabular data (Gorishniy et al., 2021).

    Args:
        input_dim:   Number of input numerical features.
        num_classes: Number of output target classes.
        d_token:     Embedding dimensionality per feature token (default: 64).
        n_heads:     Number of attention heads (default: 8).
        n_layers:    Number of Transformer blocks (default: 3).
        ffn_dropout: FFN dropout rate.
        attn_dropout: Attention dropout rate.
    """

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        d_token: int = 32,
        n_heads: int = 4,
        n_layers: int = 2,
        ffn_dropout: float = 0.1,
        attn_dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.d_token = d_token

        # Feature tokenizer: project each scalar feature to d_token dims
        self.feature_tokenizer = FeatureTokenizer(n_features=input_dim, d_token=d_token)

        # Learnable CLS token prepended to the sequence
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_token))
        nn.init.trunc_normal_(self.cls_token, std=0.02)

        # Transformer encoder blocks
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(d_token=d_token, n_heads=n_heads, ffn_dropout=ffn_dropout, attn_dropout=attn_dropout)
            for _ in range(n_layers)
        ])

        # Final classification head applied to CLS token
        self.head_norm = nn.LayerNorm(d_token)
        self.classifier = nn.Sequential(
            nn.Linear(d_token, d_token),
            nn.GELU(),
            nn.Dropout(ffn_dropout),
            nn.Linear(d_token, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, input_dim) — raw numerical features
        Returns:
            logits: (batch_size, num_classes)
        """
        # Tokenize features → (B, n_features, d_token)
        tokens = self.feature_tokenizer(x)

        # Prepend CLS token → (B, 1 + n_features, d_token)
        cls = self.cls_token.expand(x.size(0), -1, -1)
        tokens = torch.cat([cls, tokens], dim=1)

        # Pass through Transformer blocks
        for block in self.transformer_blocks:
            tokens = block(tokens)

        # Extract CLS token representation → (B, d_token)
        cls_repr = self.head_norm(tokens[:, 0, :])
        logits = self.classifier(cls_repr)
        return logits

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Returns softmax class probabilities."""
        self.eval()
        with torch.no_grad():
            return F.softmax(self.forward(x), dim=-1)

    def get_attention_weights(self, x: torch.Tensor) -> list:
        """Extract attention weight matrices from all blocks (for XAI visualization)."""
        self.eval()
        with torch.no_grad():
            tokens = self.feature_tokenizer(x)
            cls = self.cls_token.expand(x.size(0), -1, -1)
            tokens = torch.cat([cls, tokens], dim=1)
            attn_weights = []
            for block in self.transformer_blocks:
                tb = cast(TransformerBlock, block)
                normed = tb.norm1(tokens)
                _, weights = tb.attn(normed, normed, normed, need_weights=True)
                if weights is not None:
                    attn_weights.append(weights.detach().cpu())
                tokens = tb(tokens)
        return attn_weights
