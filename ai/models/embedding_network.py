"""
ai/models/embedding_network.py
==============================
Contrastive Learning Dense Embedding Network.

Architecture:
    Encoder (Linear → LayerNorm → GELU → Linear)
          ↓
    Projection Head (128-dim intermediate)
          ↓
    Contrastive / Triplet Loss Training
          ↓
    L2 Normalized Dense Embedding Space (E in R^64)

Generated embeddings enable:
    - Similar crime incident retrieval
    - Vector Database storage (pgvector / Supabase / Faiss)
    - Semantic similarity search
    - RAG context retrieval (Phase 7 ready)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class CrimeEmbeddingNetwork(nn.Module):
    """
    Production-grade Dense Embedding Network trained via Contrastive / Triplet Loss.
    Produces 64-dimensional L2-normalized dense embeddings (E in R^64).

    Args:
        input_dim:     Input feature dimension.
        proj_dim:      Projection head dimension (default: 128).
        embedding_dim: Final normalized embedding dimension (default: 64).
    """

    def __init__(
        self,
        input_dim: int,
        proj_dim: int = 128,
        embedding_dim: int = 64,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.embedding_dim = embedding_dim

        # Encoder backbone
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.GELU(),
        )

        # Projection head (used during contrastive training)
        self.projection_head = nn.Sequential(
            nn.Linear(128, proj_dim),
            nn.GELU(),
            nn.Linear(proj_dim, embedding_dim),
        )

    def forward(self, x: torch.Tensor, return_projection: bool = False) -> torch.Tensor:
        """
        Args:
            x: (batch_size, input_dim)
            return_projection: If True, returns unnormalized projection head output for loss.
        Returns:
            l2_normalized_embedding: (batch_size, embedding_dim)
        """
        feat = self.encoder(x)
        proj = self.projection_head(feat)
        if return_projection:
            return proj
        return F.normalize(proj, p=2, dim=-1)

    def get_embedding(self, x: torch.Tensor) -> torch.Tensor:
        """Extract L2-normalized dense embedding vector (E in R^64)."""
        self.eval()
        with torch.no_grad():
            return self.forward(x, return_projection=False)
