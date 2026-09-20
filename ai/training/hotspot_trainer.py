"""
ai/training/hotspot_trainer.py
==============================
Training Engine for CNN City-Level Crime Hotspot Forecaster in CrimeLens AI (Phase 4).

Features:
  - Loads Phase 2 spatio-temporal tensor (1674 days, 29 cities, 8 features)
  - Chronological splitting: Train (2020-2022), Val (2023), Test (2024)
  - Sliding-window generation (30 days lookback, 7 days forecast horizon)
  - Feature normalization fit strictly on training slice (zero data leakage)
  - Target scaling fit strictly on train target slice
  - Robust loss function: HuberLoss (Smooth L1) to mitigate crime burst outliers
  - Optimizer: Adam with CosineAnnealingLR or ReduceLROnPlateau
  - Early stopping with best checkpoint restoration
  - Saves best checkpoint to ai/models/hotspot/cnn_hotspot_best.pt
  - Standalone runnable: python -m ai.training.hotspot_trainer
"""
# cspell:words lookback

import os
import sys
import json
import time
import random
import logging
from typing import Dict, Any, Tuple, Optional, List

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ai.models.hotspot.cnn_hotspot import CNNHotspotForecaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HotspotTrainer")

DEFAULT_DATA_DIR = "datasets/processed"
DEFAULT_SAVE_DIR = "ai/models/hotspot"

# Split day counts derived from calendar boundaries:
# Train: 2020-01-01 to 2022-12-31 = 1096 days
# Val:   2023-01-01 to 2023-12-31 = 365 days
# Test:  2024-01-01 to 2024-07-31 = 213 days
TRAIN_DAYS = 1096
VAL_DAYS = 365
TEST_DAYS = 213


def seed_everything(seed: int = 42) -> None:
    """Ensure full reproducibility across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    logger.info(f"Random seed locked to {seed}")


def load_hotspot_tensor_data(
    data_dir: str = DEFAULT_DATA_DIR,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Load Phase 2 hotspot tensor and metadata.
    """
    tensor_path = os.path.join(data_dir, "hotspot_tensor.npz")
    meta_path = os.path.join(data_dir, "hotspot_metadata.json")

    if not os.path.exists(tensor_path):
        raise FileNotFoundError(f"Hotspot tensor file not found: {tensor_path}")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Hotspot metadata file not found: {meta_path}")

    npz = np.load(tensor_path)
    tensor = npz["hotspot_tensor"].astype(np.float32)

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    logger.info(
        f"Loaded hotspot tensor: shape={tensor.shape}, "
        f"cities={metadata.get('city_count')}, "
        f"channels={metadata.get('channel_count')}, "
        f"days={tensor.shape[0]}"
    )
    return tensor, metadata


def build_sliding_windows(
    series: np.ndarray,
    window_size: int = 30,
    forecast_horizon: int = 7,
    target_channel: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate sliding window inputs and future sum targets.

    Args:
        series: Array of shape (T, N_cities, N_features)
        window_size: Lookback days (default: 30)
        forecast_horizon: Forecast horizon days (default: 7)
        target_channel: Feature index to forecast (default: 0 for total_crimes)

    Returns:
        X: (N_samples, window_size, N_cities, N_features)
        y: (N_samples, N_cities) — sum of target_channel over horizon
    """
    T, n_cities, n_features = series.shape
    total_needed = window_size + forecast_horizon
    if T < total_needed:
        raise ValueError(f"Series length {T} is shorter than window {window_size} + horizon {forecast_horizon}")

    n_samples = T - total_needed + 1
    X = np.empty((n_samples, window_size, n_cities, n_features), dtype=np.float32)
    y = np.empty((n_samples, n_cities), dtype=np.float32)

    for i in range(n_samples):
        X[i] = series[i : i + window_size]
        # Sum target feature over future horizon
        y[i] = series[i + window_size : i + window_size + forecast_horizon, :, target_channel].sum(axis=0)

    return X, y


def prepare_hotspot_splits(
    tensor: np.ndarray,
    metadata: Dict[str, Any],
    window_size: int = 30,
    forecast_horizon: int = 7,
) -> Dict[str, Any]:
    """
    Perform chronological split, build sliding windows, and apply leakage-free normalization.
    """
    T_total = tensor.shape[0]
    expected_total = TRAIN_DAYS + VAL_DAYS + TEST_DAYS
    if T_total != expected_total:
        logger.warning(f"Tensor length {T_total} differs from expected {expected_total}; adapting slices.")

    train_slice = tensor[:TRAIN_DAYS]
    val_slice = tensor[TRAIN_DAYS - window_size : TRAIN_DAYS + VAL_DAYS]
    test_slice = tensor[TRAIN_DAYS + VAL_DAYS - window_size : TRAIN_DAYS + VAL_DAYS + TEST_DAYS]

    # Generate raw unscaled windows
    X_train_raw, y_train_raw = build_sliding_windows(train_slice, window_size, forecast_horizon)
    X_val_raw, y_val_raw = build_sliding_windows(val_slice, window_size, forecast_horizon)
    X_test_raw, y_test_raw = build_sliding_windows(test_slice, window_size, forecast_horizon)

    # Compute normalization statistics STRICTLY on train_slice to avoid data leakage
    # Per-channel min and max: shape (8,)
    f_min = train_slice.min(axis=(0, 1)).astype(np.float32)
    f_max = train_slice.max(axis=(0, 1)).astype(np.float32)
    f_denom = np.where((f_max - f_min) == 0, 1.0, f_max - f_min).astype(np.float32)

    # Scale inputs: (X - min) / (max - min)
    X_train_scaled = (X_train_raw - f_min) / f_denom
    X_val_scaled = (X_val_raw - f_min) / f_denom
    X_test_scaled = (X_test_raw - f_min) / f_denom

    # Target scaling: fit strictly on y_train_raw
    y_min = float(y_train_raw.min())
    y_max = float(y_train_raw.max())
    y_denom = (y_max - y_min) if (y_max - y_min) > 0 else 1.0

    y_train_scaled = (y_train_raw - y_min) / y_denom
    y_val_scaled = (y_val_raw - y_min) / y_denom
    y_test_scaled = (y_test_raw - y_min) / y_denom

    scaler_stats = {
        "f_min": f_min.tolist(),
        "f_max": f_max.tolist(),
        "f_denom": f_denom.tolist(),
        "y_min": y_min,
        "y_max": y_max,
        "y_denom": y_denom,
    }

    logger.info(
        f"Generated splits: "
        f"Train={X_train_scaled.shape}, "
        f"Val={X_val_scaled.shape}, "
        f"Test={X_test_scaled.shape}"
    )

    return {
        "X_train_scaled": X_train_scaled,
        "y_train_scaled": y_train_scaled,
        "X_val_scaled": X_val_scaled,
        "y_val_scaled": y_val_scaled,
        "X_test_scaled": X_test_scaled,
        "y_test_scaled": y_test_scaled,
        "X_train_raw": X_train_raw,
        "y_train_raw": y_train_raw,
        "X_val_raw": X_val_raw,
        "y_val_raw": y_val_raw,
        "X_test_raw": X_test_raw,
        "y_test_raw": y_test_raw,
        "scaler_stats": scaler_stats,
    }


def compute_baseline_predictions(
    X_raw: np.ndarray,
    forecast_horizon: int = 7,
) -> np.ndarray:
    """
    Historical average baseline:
    Predict each city's future crime as historical 30-day mean * forecast_horizon.

    Args:
        X_raw: Array of shape (N, window_size, n_cities, n_features)
               where channel 0 is total_crimes.

    Returns:
        Array of shape (N, n_cities) representing predicted crime activity.
    """
    # Channel 0 is total_crimes: shape (N, window_size, n_cities)
    daily_mean = X_raw[:, :, :, 0].mean(axis=1)  # (N, n_cities)
    return daily_mean * forecast_horizon


class HotspotTrainer:
    """
    Training manager for CNNHotspotForecaster.
    """

    def __init__(
        self,
        model: nn.Module,
        criterion: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Optional[Any] = None,
        device: Optional[torch.device] = None,
        patience: int = 10,
    ) -> None:
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device)
        self.criterion = criterion
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.patience = patience

        self.best_val_loss = float("inf")
        self.best_epoch = 0
        self.best_weights: Optional[Dict[str, torch.Tensor]] = None
        self.history: Dict[str, List[float]] = {
            "train_loss": [],
            "val_loss": [],
            "learning_rate": [],
        }

    def train_epoch(self, dataloader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        n_batches = 0

        for X_batch, y_batch in dataloader:
            X_batch = X_batch.to(self.device)
            y_batch = y_batch.to(self.device)

            self.optimizer.zero_grad()
            preds = self.model(X_batch)
            loss = self.criterion(preds, y_batch)
            loss.backward()

            # Gradient clipping to prevent gradient explosion
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(n_batches, 1)

    @torch.no_grad()
    def evaluate(self, dataloader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        n_batches = 0

        for X_batch, y_batch in dataloader:
            X_batch = X_batch.to(self.device)
            y_batch = y_batch.to(self.device)

            preds = self.model(X_batch)
            loss = self.criterion(preds, y_batch)

            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(n_batches, 1)

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        max_epochs: int = 40,
    ) -> Dict[str, Any]:
        epochs_no_improve = 0
        start_time = time.time()

        logger.info(f"Starting training for up to {max_epochs} epochs on device: {self.device}")

        for epoch in range(1, max_epochs + 1):
            train_loss = self.train_epoch(train_loader)
            val_loss = self.evaluate(val_loader)
            current_lr = self.optimizer.param_groups[0]["lr"]

            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_loss)
            self.history["learning_rate"].append(current_lr)

            if self.scheduler is not None:
                if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                    self.scheduler.step(val_loss)
                else:
                    self.scheduler.step()

            if val_loss < self.best_val_loss - 1e-5:
                self.best_val_loss = val_loss
                self.best_epoch = epoch
                self.best_weights = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                epochs_no_improve = 0
                improved_flag = "(*)"
            else:
                epochs_no_improve += 1
                improved_flag = ""

            logger.info(
                f"Epoch [{epoch:02d}/{max_epochs:02d}] "
                f"Train Loss: {train_loss:.6f} | "
                f"Val Loss: {val_loss:.6f} {improved_flag} | "
                f"LR: {current_lr:.6f}"
            )

            if epochs_no_improve >= self.patience:
                logger.info(f"Early stopping triggered at epoch {epoch} (no improvement for {self.patience} epochs).")
                break

        elapsed = time.time() - start_time
        logger.info(
            f"Training finished in {elapsed:.1f}s. "
            f"Best Val Loss: {self.best_val_loss:.6f} at Epoch {self.best_epoch}"
        )

        # Restore best weights
        if self.best_weights is not None:
            self.model.load_state_dict(self.best_weights)

        return {
            "best_epoch": self.best_epoch,
            "best_val_loss": self.best_val_loss,
            "training_time_seconds": round(elapsed, 2),
            "history": self.history,
        }


def run_training_pipeline(
    data_dir: str = DEFAULT_DATA_DIR,
    save_dir: str = DEFAULT_SAVE_DIR,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    max_epochs: int = 40,
    patience: int = 10,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Full Phase 4 training pipeline execution.
    """
    seed_everything(seed)
    os.makedirs(save_dir, exist_ok=True)

    tensor, metadata = load_hotspot_tensor_data(data_dir)
    splits = prepare_hotspot_splits(tensor, metadata, window_size=30, forecast_horizon=7)

    # Create PyTorch DataLoaders
    train_dataset = TensorDataset(
        torch.tensor(splits["X_train_scaled"]),
        torch.tensor(splits["y_train_scaled"]),
    )
    val_dataset = TensorDataset(
        torch.tensor(splits["X_val_scaled"]),
        torch.tensor(splits["y_val_scaled"]),
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # Instantiate CNN model
    model = CNNHotspotForecaster(
        n_cities=metadata.get("city_count", 29),
        n_features=metadata.get("channel_count", 8),
        window_size=30,
        conv_filters_1=32,
        conv_filters_2=64,
        fc_hidden=128,
        dropout=0.2,
    )

    # Use SmoothL1Loss (Huber) for robust gradient updates
    criterion = nn.SmoothL1Loss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=4, min_lr=1e-5
    )

    trainer = HotspotTrainer(
        model=model,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        patience=patience,
    )

    train_results = trainer.fit(train_loader, val_loader, max_epochs=max_epochs)

    # Save best model checkpoint
    checkpoint_path = os.path.join(save_dir, "cnn_hotspot_best.pt")
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "model_config": model.get_config(),
        "input_dimensions": [30, metadata.get("city_count", 29), metadata.get("channel_count", 8)],
        "output_dimensions": [metadata.get("city_count", 29)],
        "window_size": 30,
        "forecast_horizon": 7,
        "cities": metadata["cities"],
        "feature_channels": metadata["feature_channels"],
        "scaler_stats": splits["scaler_stats"],
        "best_epoch": train_results["best_epoch"],
        "best_val_loss": train_results["best_val_loss"],
        "training_time_seconds": train_results["training_time_seconds"],
        "seed": seed,
    }
    torch.save(checkpoint, checkpoint_path)
    logger.info(f"Saved best model checkpoint to: {checkpoint_path}")

    # Save comprehensive metadata json
    meta_out_path = os.path.join(save_dir, "hotspot_metadata.json")
    save_meta = {
        "model_name": "CNNHotspotForecaster",
        "architecture": "CNN2D-AdaptivePool-FC",
        "input_shape": [30, 29, 8],
        "output_shape": [29],
        "window_size": 30,
        "forecast_horizon": 7,
        "feature_columns": metadata["feature_channels"],
        "city_count": metadata["city_count"],
        "cities": metadata["cities"],
        "training_date_range": ["2020-01-01", "2022-12-31"],
        "validation_date_range": ["2023-01-01", "2023-12-31"],
        "test_date_range": ["2024-01-01", "2024-07-31"],
        "loss_function": "SmoothL1Loss (Huber)",
        "optimizer": "Adam",
        "learning_rate": learning_rate,
        "best_epoch": train_results["best_epoch"],
        "best_val_loss": train_results["best_val_loss"],
        "scaler_stats": splits["scaler_stats"],
        "history": train_results["history"],
    }
    with open(meta_out_path, "w", encoding="utf-8") as f:
        json.dump(save_meta, f, indent=4)
    logger.info(f"Saved hotspot model metadata to: {meta_out_path}")

    return {
        "checkpoint_path": checkpoint_path,
        "metadata_path": meta_out_path,
        "train_results": train_results,
        "splits": splits,
        "metadata": metadata,
    }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CrimeLens AI — City-Level Crime Hotspot Forecaster (Phase 4)")
    print("=" * 60)
    res = run_training_pipeline()
    print("\nTraining completed successfully.")
    print(f"Checkpoint saved at: {res['checkpoint_path']}")
    print(f"Metadata saved at:   {res['metadata_path']}")
