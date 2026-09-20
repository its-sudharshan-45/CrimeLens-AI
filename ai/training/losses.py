"""
ai/training/losses.py
======================
Production PyTorch Loss Functions:
  1. FocalLoss — Class-imbalanced classification loss
  2. TripletMarginLossWrapper — Triplet loss for embedding space alignment
  3. SupervisedContrastiveLoss — SupCon loss for dense representation learning
"""

import torch
import torch.nn.functional as F
from torch import nn


class FocalLoss(nn.Module):
    """
    Focal Loss for addressing class imbalance in tabular classification.
    Reference: Lin et al. (2017) "Focal Loss for Dense Object Detection"

    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    """

    def __init__(self, alpha: float = 1.0, gamma: float = 2.0, reduction: str = "mean") -> None:
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: (B, C)
            targets: (B,)
        """
        ce_loss = F.cross_entropy(logits, targets, reduction="none")
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * ((1 - pt) ** self.gamma) * ce_loss

        if self.reduction == "mean":
            return focal_loss.mean()
        elif self.reduction == "sum":
            return focal_loss.sum()
        return focal_loss


class TripletLoss(nn.Module):
    """
    Triplet Margin Loss for embedding space metric learning.
    Pull anchor and positive closer, push anchor and negative apart.
    """

    def __init__(self, margin: float = 0.3) -> None:
        super().__init__()
        self.triplet_loss = nn.TripletMarginLoss(margin=margin, p=2)

    def forward(self, anchor: torch.Tensor, positive: torch.Tensor, negative: torch.Tensor) -> torch.Tensor:
        return self.triplet_loss(anchor, positive, negative)


class SupervisedContrastiveLoss(nn.Module):
    """
    Supervised Contrastive Loss (Khosla et al., 2020).
    Pulls embeddings of the same class together, pushes different classes apart.
    """

    def __init__(self, temperature: float = 0.07) -> None:
        super().__init__()
        self.temperature = temperature

    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            features: (B, D) normalized embeddings
            labels: (B,) class labels
        """
        device = features.device
        batch_size = features.shape[0]
        labels = labels.contiguous().view(-1, 1)

        mask = torch.eq(labels, labels.T).float().to(device)

        # Compute similarity matrix
        anchor_dot_contrast = torch.div(torch.matmul(features, features.T), self.temperature)

        # For numerical stability
        logits_max, _ = torch.max(anchor_dot_contrast, dim=1, keepdim=True)
        logits = anchor_dot_contrast - logits_max.detach()

        # Mask out self-contrast
        logits_mask = torch.scatter(
            torch.ones_like(mask),
            1,
            torch.arange(batch_size).view(-1, 1).to(device),
            0
        )
        mask = mask * logits_mask

        # Compute log-softmax
        exp_logits = torch.exp(logits) * logits_mask
        log_prob = logits - torch.log(exp_logits.sum(1, keepdim=True) + 1e-9)

        # Mean of log-likelihood over positive pairs
        mean_log_prob_pos = (mask * log_prob).sum(1) / (mask.sum(1) + 1e-9)

        loss = -mean_log_prob_pos
        return loss.mean()
