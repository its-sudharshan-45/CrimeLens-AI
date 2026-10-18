"""
ai/models/ensemble_classifier.py
==================================
Soft-Voting Ensemble Classifier combining FT-Transformer + Enhanced MLP.
Temperature-scaled probability averaging for improved calibration.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Optional


class EnsembleClassifier(nn.Module):
    """
    Production-grade Soft-Voting Ensemble Classifier.
    Combines predictions from FT-Transformer and Enhanced MLP via weighted
    temperature-scaled probability averaging.

    Args:
        models:      List of PyTorch classification models (nn.Module).
        weights:     Optional list of floats specifying model weights.
                     If None, equal weighting is used.
        temperature: Temperature scalar for probability calibration (default: 1.0).
    """

    def __init__(
        self,
        models: List[nn.Module],
        weights: Optional[List[float]] = None,
        temperature: float = 1.0,
    ) -> None:
        super().__init__()
        self.models = nn.ModuleList(models)
        self.temperature = temperature

        if weights is None:
            weights = [1.0 / len(models)] * len(models)
        total = sum(weights)
        self.weights = [w / total for w in weights]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Weighted soft-voting over all member models.
        Args:
            x: (batch_size, input_dim)
        Returns:
            ensemble_logits: (batch_size, num_classes) — log-scaled ensemble probabilities
        """
        ensemble_proba = None
        for model, weight in zip(self.models, self.weights):
            logits = model(x)
            proba = F.softmax(logits / self.temperature, dim=-1)
            if ensemble_proba is None:
                ensemble_proba = weight * proba
            else:
                ensemble_proba = ensemble_proba + weight * proba
        if ensemble_proba is None:
            raise ValueError("No models in ensemble.")
        # Return log-probabilities as pseudo-logits for consistent loss computation
        return torch.log(ensemble_proba + 1e-9)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Returns averaged class probability tensor."""
        self.eval()
        with torch.no_grad():
            log_proba = self.forward(x)
            return torch.exp(log_proba)

    def set_eval_all(self) -> None:
        """Put all member models into eval mode."""
        for model in self.models:
            model.eval()
