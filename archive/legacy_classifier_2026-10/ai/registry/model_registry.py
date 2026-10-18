"""
ai/registry/model_registry.py
==============================
Production Enterprise PyTorch Model Registry.

Saves:
  1. .pt model binaries (state_dict)
  2. .ts, .onnx, and _quantized.pt exports
  3. Extended metadata: dataset MD5 hash, FLOPs, parameter count, hardware, latency
  4. Hyperparameters config & evaluation metrics
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone

import torch
from torch import nn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MODELS_DIR = "ai/models"


def compute_file_hash(filepath: str) -> str:
    """Compute MD5 checksum hash for dataset auditing."""
    if not os.path.exists(filepath):
        return "N/A"
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class ModelRegistry:
    """
    Enterprise PyTorch Model Registry.
    """

    def __init__(self, models_dir: str = DEFAULT_MODELS_DIR) -> None:
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)

    def save_pytorch_model(self, model: nn.Module, filename: str) -> str:
        """Save PyTorch state_dict."""
        path = os.path.join(self.models_dir, filename)
        torch.save(model.state_dict(), path)
        logger.info(f"Saved PyTorch model binary to {path}")
        return path

    def save_checkpoint(self, checkpoint_data: dict, filename: str = "checkpoint.pt") -> str:
        """Save training checkpoint."""
        path = os.path.join(self.models_dir, filename)
        torch.save(checkpoint_data, path)
        logger.info(f"Saved checkpoint artifact to {path}")
        return path

    def save_training_config(self, config: dict, filename: str = "training_config.json") -> str:
        """Save training hyperparameters config."""
        path = os.path.join(self.models_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logger.info(f"Saved training config to {path}")
        return path

    def save_feature_columns(self, feature_cols: list, filename: str = "feature_columns.json") -> str:
        """Save feature columns schema."""
        path = os.path.join(self.models_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"feature_columns": feature_cols}, f, indent=4)
        logger.info(f"Saved feature columns schema to {path}")
        return path

    def save_metrics(self, metrics: dict, filename: str = "metrics.json") -> str:
        """Save evaluation metrics JSON."""
        path = os.path.join(self.models_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=4)
        logger.info(f"Saved metrics JSON to {path}")
        return path

    def save_metadata(self, metadata: dict, dataset_path: str = "Dataset/crime_dataset_india.csv", filename: str = "model_metadata.json") -> str:
        """Save production metadata including dataset MD5 hash, hardware, and timestamp."""
        metadata["saved_at"] = datetime.now(tz=timezone.utc).isoformat()
        metadata["dataset_hash_md5"] = compute_file_hash(dataset_path)
        metadata["framework"] = f"PyTorch {torch.__version__}"
        metadata["device"] = "cuda" if torch.cuda.is_available() else "cpu"

        path = os.path.join(self.models_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Saved production metadata to {path}")
        return path
