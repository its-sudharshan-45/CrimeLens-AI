"""
ai/training/temporal_trainer.py
================================
Training Engine for Temporal Forecasters (LSTM and GRU) in CrimeLens AI (Phase 3).

Features:
  - Reproducible random seed control (Python, NumPy, PyTorch)
  - Automatic GPU / CPU device selection
  - Configurable loss (HuberLoss / SmoothL1 or MSELoss)
  - Optimizer: Adam with configurable learning rate
  - Learning rate scheduler: ReduceLROnPlateau
  - Early stopping with best weights restoration
  - Saves full reproduction checkpoints to ai/models/temporal/
  - Generates comprehensive training metadata
"""
# cspell:words cudnn

import os
import sys
import json
import time
import random
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ai.models.temporal.lstm import CrimeLSTMForecaster
from ai.models.temporal.gru import CrimeGRUForecaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TemporalTrainer")


def seed_everything(seed: int = 42) -> None:
    """Set random seeds for full reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    logger.info(f"Random seed set to {seed}")


def load_temporal_datasets(
    data_dir: str = "datasets/processed/temporal_sequences",
) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
    """
    Load pre-split Phase 2 temporal sequence datasets and metadata.
    """
    meta_path = os.path.join(data_dir, "sequence_metadata.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Missing sequence metadata at: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    train_npz = np.load(os.path.join(data_dir, "train_sequences.npz"))
    val_npz = np.load(os.path.join(data_dir, "val_sequences.npz"))
    test_npz = np.load(os.path.join(data_dir, "test_sequences.npz"))

    datasets = {
        "X_train": train_npz["X"].astype(np.float32),
        "y_train": train_npz["y"].astype(np.float32),
        "X_val": val_npz["X"].astype(np.float32),
        "y_val": val_npz["y"].astype(np.float32),
        "X_test": test_npz["X"].astype(np.float32),
        "y_test": test_npz["y"].astype(np.float32),
    }

    # Verify expected shapes
    assert datasets["X_train"].shape == (1060, 30, 13), f"Unexpected X_train shape: {datasets['X_train'].shape}"
    assert datasets["y_train"].shape == (1060, 7), f"Unexpected y_train shape: {datasets['y_train'].shape}"
    assert datasets["X_val"].shape == (359, 30, 13), f"Unexpected X_val shape: {datasets['X_val'].shape}"
    assert datasets["y_val"].shape == (359, 7), f"Unexpected y_val shape: {datasets['y_val'].shape}"
    assert datasets["X_test"].shape == (207, 30, 13), f"Unexpected X_test shape: {datasets['X_test'].shape}"
    assert datasets["y_test"].shape == (207, 7), f"Unexpected y_test shape: {datasets['y_test'].shape}"

    return datasets, metadata


def create_dataloaders(
    datasets: Dict[str, np.ndarray],
    batch_size: int = 32,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """Create PyTorch DataLoaders for train, validation, and test splits."""
    train_ds = TensorDataset(torch.from_numpy(datasets["X_train"]), torch.from_numpy(datasets["y_train"]))
    val_ds = TensorDataset(torch.from_numpy(datasets["X_val"]), torch.from_numpy(datasets["y_val"]))
    test_ds = TensorDataset(torch.from_numpy(datasets["X_test"]), torch.from_numpy(datasets["y_test"]))

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader


class TemporalTrainer:
    """
    Production-clean training manager for LSTM/GRU forecasters.
    """

    def __init__(
        self,
        device: Optional[str] = None,
        save_dir: str = "ai/models/temporal",
    ) -> None:
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        logger.info(f"Initialized TemporalTrainer on device: {self.device}")

    def train_model(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        metadata: Dict[str, Any],
        model_name: str = "LSTM",
        epochs: int = 35,
        lr: float = 1e-3,
        patience: int = 10,
        loss_type: str = "HuberLoss",
    ) -> Dict[str, Any]:
        """
        Train a temporal forecaster with early stopping and learning rate scheduling.
        """
        model = model.to(self.device)

        if "huber" in loss_type.lower():
            criterion: nn.Module = nn.HuberLoss(delta=1.0)
        else:
            criterion = nn.MSELoss()

        optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=3, min_lr=1e-5
        )

        history: Dict[str, list] = {
            "epoch": [],
            "train_loss": [],
            "val_loss": [],
            "learning_rate": [],
        }

        best_val_loss = float("inf")
        best_epoch = 0
        best_state_dict: Optional[Dict[str, torch.Tensor]] = None
        patience_counter = 0

        logger.info(f"--- Starting Training for {model_name} ({epochs} epochs max, patience={patience}) ---")
        start_time = time.time()

        for epoch in range(1, epochs + 1):
            # Training pass
            model.train()
            train_running_loss = 0.0
            train_samples = 0

            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                optimizer.zero_grad()
                preds = model(batch_x)
                loss = criterion(preds, batch_y)
                loss.backward()

                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

                train_running_loss += loss.item() * batch_x.size(0)
                train_samples += batch_x.size(0)

            epoch_train_loss = train_running_loss / train_samples

            # Validation pass
            model.eval()
            val_running_loss = 0.0
            val_samples = 0

            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x = batch_x.to(self.device)
                    batch_y = batch_y.to(self.device)

                    preds = model(batch_x)
                    loss = criterion(preds, batch_y)

                    val_running_loss += loss.item() * batch_x.size(0)
                    val_samples += batch_x.size(0)

            epoch_val_loss = val_running_loss / val_samples
            current_lr = optimizer.param_groups[0]["lr"]

            # Step scheduler
            scheduler.step(epoch_val_loss)

            history["epoch"].append(epoch)
            history["train_loss"].append(epoch_train_loss)
            history["val_loss"].append(epoch_val_loss)
            history["learning_rate"].append(current_lr)

            # Check improvement
            is_best = epoch_val_loss < (best_val_loss - 1e-5)
            marker = ""
            if is_best:
                best_val_loss = epoch_val_loss
                best_epoch = epoch
                best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
                marker = " [BEST]"
            else:
                patience_counter += 1

            logger.info(
                f"[{model_name}] Epoch {epoch:02d}/{epochs} | "
                f"Train Loss ({loss_type}): {epoch_train_loss:.6f} | "
                f"Val Loss: {epoch_val_loss:.6f} | "
                f"LR: {current_lr:.6f}{marker}"
            )

            if patience_counter >= patience:
                logger.info(f"[{model_name}] Early stopping triggered at epoch {epoch} (patience={patience}).")
                break

        training_time = round(time.time() - start_time, 2)
        logger.info(f"[{model_name}] Training finished in {training_time}s. Best Epoch: {best_epoch} (Val Loss: {best_val_loss:.6f})")

        # Restore best weights
        if best_state_dict is not None:
            model.load_state_dict(best_state_dict)

        # Save checkpoint
        checkpoint_name = f"{model_name.lower()}_best.pt"
        checkpoint_path = os.path.join(self.save_dir, checkpoint_name)

        get_cfg = getattr(model, "get_config", None)
        model_config = get_cfg() if callable(get_cfg) else {}

        checkpoint_data = {
            "model_state_dict": model.state_dict(),
            "model_type": model_name,
            "config": model_config,
            "feature_columns": metadata.get("feature_columns", []),
            "scaler_data_min": metadata.get("scaler_data_min", []),
            "scaler_data_max": metadata.get("scaler_data_max", []),
            "train_dates": metadata.get("train_dates", []),
            "val_dates": metadata.get("val_dates", []),
            "test_dates": metadata.get("test_dates", []),
            "best_epoch": best_epoch,
            "best_val_loss": float(best_val_loss),
            "loss_function": loss_type,
            "history": history,
            "training_time_sec": training_time,
            "param_count": sum(p.numel() for p in model.parameters()),
        }

        torch.save(checkpoint_data, checkpoint_path)
        logger.info(f"[{model_name}] Saved best checkpoint to: {checkpoint_path}")

        return {
            "model": model,
            "checkpoint_path": checkpoint_path,
            "best_epoch": best_epoch,
            "best_val_loss": best_val_loss,
            "training_time_sec": training_time,
            "history": history,
            "param_count": checkpoint_data["param_count"],
        }


def run_training_pipeline() -> Dict[str, Any]:
    """
    Main training execution function.
    Loads data, trains LSTM and GRU, and writes metadata.
    """
    seed_everything(42)

    logger.info("=" * 60)
    logger.info("CrimeLens AI — Phase 3 Temporal Model Training")
    logger.info("=" * 60)

    datasets, metadata = load_temporal_datasets()
    logger.info(f"Loaded datasets from sequence_metadata.json:")
    logger.info(f"  Train: {datasets['X_train'].shape} -> {datasets['y_train'].shape}")
    logger.info(f"  Val:   {datasets['X_val'].shape} -> {datasets['y_val'].shape}")
    logger.info(f"  Test:  {datasets['X_test'].shape} -> {datasets['y_test'].shape}")
    logger.info(f"  Feature count: {metadata['n_features']}")
    logger.info(f"  Features: {metadata['feature_columns']}")

    train_loader, val_loader, test_loader = create_dataloaders(datasets, batch_size=32)

    trainer = TemporalTrainer()

    # 1. Train Model A: LSTM
    lstm_model = CrimeLSTMForecaster(
        input_size=13,
        hidden_size=64,
        num_layers=2,
        forecast_horizon=7,
        dropout=0.2,
    )
    lstm_results = trainer.train_model(
        model=lstm_model,
        train_loader=train_loader,
        val_loader=val_loader,
        metadata=metadata,
        model_name="LSTM",
        epochs=35,
        lr=0.001,
        patience=10,
        loss_type="HuberLoss",
    )

    # 2. Train Model B: GRU
    gru_model = CrimeGRUForecaster(
        input_size=13,
        hidden_size=64,
        num_layers=2,
        forecast_horizon=7,
        dropout=0.2,
    )
    gru_results = trainer.train_model(
        model=gru_model,
        train_loader=train_loader,
        val_loader=val_loader,
        metadata=metadata,
        model_name="GRU",
        epochs=35,
        lr=0.001,
        patience=10,
        loss_type="HuberLoss",
    )

    # 3. Write model metadata JSON
    combined_metadata = {
        "project": "CrimeLens AI - Phase 3 Temporal Forecasting",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "random_seed": 42,
        "input_features": metadata["feature_columns"],
        "n_features": 13,
        "sequence_length": 30,
        "forecast_horizon": 7,
        "date_ranges": {
            "train": metadata["train_dates"],
            "validation": metadata["val_dates"],
            "test": metadata["test_dates"],
        },
        "models": {
            "LSTM": {
                "checkpoint": lstm_results["checkpoint_path"],
                "best_epoch": lstm_results["best_epoch"],
                "best_val_loss": lstm_results["best_val_loss"],
                "training_time_sec": lstm_results["training_time_sec"],
                "parameters": lstm_results["param_count"],
                "hidden_size": 64,
                "num_layers": 2,
                "dropout": 0.2,
            },
            "GRU": {
                "checkpoint": gru_results["checkpoint_path"],
                "best_epoch": gru_results["best_epoch"],
                "best_val_loss": gru_results["best_val_loss"],
                "training_time_sec": gru_results["training_time_sec"],
                "parameters": gru_results["param_count"],
                "hidden_size": 64,
                "num_layers": 2,
                "dropout": 0.2,
            },
        },
    }

    meta_out_path = os.path.join(trainer.save_dir, "model_metadata.json")
    with open(meta_out_path, "w", encoding="utf-8") as f:
        json.dump(combined_metadata, f, indent=2)

    logger.info(f"Model metadata written to: {meta_out_path}")
    logger.info("Training pipeline complete.")

    return {
        "lstm": lstm_results,
        "gru": gru_results,
        "metadata": combined_metadata,
    }


if __name__ == "__main__":
    run_training_pipeline()
