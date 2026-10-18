"""
ai/evaluation/evaluator.py
==========================
Comprehensive Evaluation Metrics Component for PyTorch Deep Learning Models.

Classification Metrics:
  - Accuracy, Precision, Recall, F1-Score (weighted & macro)
  - ROC-AUC (multiclass OVR)
  - PR-AUC (Precision-Recall Area Under Curve)
  - Cohen's Kappa
  - Matthews Correlation Coefficient (MCC)
  - Confusion Matrix

Forecasting Metrics:
  - RMSE, MAE, MAPE
  - SMAPE (Symmetric Mean Absolute Percentage Error)
  - R² Score (Coefficient of Determination)
"""

import logging
from typing import List, Optional

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    auc,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def compute_smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Symmetric Mean Absolute Percentage Error (SMAPE)."""
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    diff = np.abs(y_true - y_pred)
    with np.errstate(divide="ignore", invalid="ignore"):
        smape = np.where(denom == 0, 0.0, diff / denom)
    return float(np.mean(smape) * 100.0)


def compute_multiclass_pr_auc(y_true: np.ndarray, y_proba: np.ndarray, num_classes: int) -> float:
    """Compute micro-averaged Precision-Recall AUC for multiclass."""
    y_true_onehot = np.eye(num_classes)[y_true]
    pr_aucs = []
    for c in range(num_classes):
        precision_c, recall_c, _ = precision_recall_curve(y_true_onehot[:, c], y_proba[:, c])
        pr_aucs.append(auc(recall_c, precision_c))
    return float(np.mean(pr_aucs))


class DeepLearningEvaluator:
    """
    Comprehensive PyTorch Evaluation Suite.
    Calculates Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, Cohen Kappa, MCC,
    RMSE, MAE, MAPE, SMAPE, R².
    """

    @staticmethod
    def evaluate_classifier(
        model: torch.nn.Module,
        test_loader: torch.utils.data.DataLoader,
        device: str = "cpu",
        model_name: str = "PyTorchClassifier",
        class_names: Optional[List[str]] = None,
    ) -> dict:
        """Evaluate a classification model on a held-out loader.

        Metrics are computed directly from the raw predictions and probabilities
        produced on the provided loader — never from rounded display values. When
        ``class_names`` is supplied, the confusion matrix and per-class report use
        that explicit, stable class order.

        Undefined metrics (e.g. ROC-AUC when a class is absent from the split) are
        reported as ``float("nan")`` rather than silently coerced.
        """
        model = model.to(device)
        model.eval()

        all_preds, all_targets, all_probas = [], [], []

        with torch.no_grad():
            for batch in test_loader:
                x = batch["x"].to(device)
                y = batch["y_class"].to(device)

                logits = model(x)
                probas = torch.softmax(logits, dim=-1)
                preds = torch.argmax(probas, dim=-1)

                all_preds.extend(preds.cpu().numpy())
                all_targets.extend(y.cpu().numpy())
                all_probas.extend(probas.cpu().numpy())

        y_true = np.array(all_targets)
        y_pred = np.array(all_preds)
        y_proba = np.array(all_probas)
        num_classes = y_proba.shape[1]
        labels = list(range(num_classes))
        if class_names is not None and len(class_names) != num_classes:
            logger.warning("class_names length != num_classes; falling back to integer labels.")
            class_names = None

        acc = accuracy_score(y_true, y_pred)
        bal_acc = balanced_accuracy_score(y_true, y_pred)
        prec_w = precision_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)  # type: ignore
        rec_w = recall_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)  # type: ignore
        f1_w = f1_score(y_true, y_pred, average="weighted", zero_division=0, labels=labels)  # type: ignore
        prec_m = precision_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)  # type: ignore
        rec_m = recall_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)  # type: ignore
        f1_m = f1_score(y_true, y_pred, average="macro", zero_division=0, labels=labels)  # type: ignore
        kappa = cohen_kappa_score(y_true, y_pred, labels=labels)
        mcc = matthews_corrcoef(y_true, y_pred)
        cm = confusion_matrix(y_true, y_pred, labels=labels)

        per_class_p = precision_score(y_true, y_pred, average=None, zero_division=0, labels=labels)  # type: ignore
        per_class_r = recall_score(y_true, y_pred, average=None, zero_division=0, labels=labels)  # type: ignore
        per_class_f = f1_score(y_true, y_pred, average=None, zero_division=0, labels=labels)  # type: ignore
        supports = np.bincount(y_true, minlength=num_classes)[:num_classes]

        per_class = []
        for c in range(num_classes):
            per_class.append({
                "class_index": c,
                "class_name": class_names[c] if class_names else str(c),
                "precision": round(float(per_class_p[c]), 4),
                "recall": round(float(per_class_r[c]), 4),
                "f1_score": round(float(per_class_f[c]), 4),
                "support": int(supports[c]),
            })

        # Multiclass log loss (uses true probabilities; undefined if labels missing)
        try:
            ll = float(log_loss(y_true, y_proba, labels=labels))
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Could not calculate log loss: {e}")
            ll = float("nan")

        # ROC AUC & PR AUC (only mathematically valid with >=2 classes present)
        roc_auc, pr_auc = float("nan"), float("nan")
        try:
            if len(np.unique(y_true)) > 1:
                roc_auc = float(roc_auc_score(y_true, y_proba, multi_class="ovr", average="weighted", labels=labels))
                pr_auc = compute_multiclass_pr_auc(y_true, y_proba, num_classes)
        except Exception as e:
            logger.warning(f"Could not calculate ROC/PR AUC: {e}")

        metrics = {
            "model_name": model_name,
            "accuracy": round(float(acc), 4),
            "balanced_accuracy": round(float(bal_acc), 4),
            "precision": round(float(prec_w), 4),
            "recall": round(float(rec_w), 4),
            "f1_score": round(float(f1_w), 4),
            "precision_macro": round(float(prec_m), 4),
            "recall_macro": round(float(rec_m), 4),
            "f1_macro": round(float(f1_m), 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "log_loss": round(ll, 4),
            "cohen_kappa": round(float(kappa), 4),
            "mcc": round(float(mcc), 4),
            "n_samples": int(len(y_true)),
            "class_labels": class_names if class_names else [str(c) for c in labels],
            "per_class": per_class,
            "confusion_matrix": cm.tolist(),
            "y_true": y_true.tolist(),
            "y_pred": y_pred.tolist(),
            "y_proba": y_proba.tolist(),
        }

        logger.info(
            f"[{model_name}] Acc: {acc:.4f} | BalAcc: {bal_acc:.4f} | Prec(w): {prec_w:.4f} | "
            f"Rec(w): {rec_w:.4f} | F1(w): {f1_w:.4f} | F1(macro): {f1_m:.4f} | "
            f"ROC-AUC: {roc_auc:.4f} | PR-AUC: {pr_auc:.4f} | LogLoss: {ll:.4f} | "
            f"Kappa: {kappa:.4f} | MCC: {mcc:.4f}"
        )
        return metrics

    @staticmethod
    def evaluate_forecaster(
        model: torch.nn.Module,
        test_loader: torch.utils.data.DataLoader,
        device: str = "cpu",
        model_name: str = "PyTorchForecaster",
    ) -> dict:
        """Evaluate forecasting model on sequence test set."""
        model = model.to(device)
        model.eval()

        all_preds, all_targets = [], []

        with torch.no_grad():
            for batch in test_loader:
                x_seq = batch["x_seq"].to(device)
                y_target = batch["y_target"].to(device)

                preds = model(x_seq)
                all_preds.append(preds.cpu().numpy())
                all_targets.append(y_target.cpu().numpy())

        y_true = np.vstack(all_targets)
        y_pred = np.vstack(all_preds)

        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = float(np.sqrt(mse))
        r2 = r2_score(y_true, y_pred)
        smape = compute_smape(y_true, y_pred)

        try:
            mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1.0))) * 100.0)
        except Exception:
            mape = 0.0

        metrics = {
            "model_name": model_name,
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "mape_pct": round(mape, 2),
            "smape_pct": round(smape, 2),
            "r2_score": round(r2, 4),
        }

        logger.info(f"[{model_name}] MAE: {mae:.4f} | RMSE: {rmse:.4f} | SMAPE: {smape:.2f}% | R²: {r2:.4f}")
        return metrics
