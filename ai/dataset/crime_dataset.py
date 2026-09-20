"""
ai/dataset/crime_dataset.py
===========================
PyTorch Dataset and DataModule abstractions for CrimeLens AI.
Supports tabular features as well as chronological sequence forecasting datasets.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CrimeDataset(Dataset):
    """
    PyTorch Dataset for CrimeLens tabular features and targets.
    Converts feature matrices and targets into torch FloatTensors and LongTensors.
    """

    def __init__(self, X: Any, y_class: Optional[Any] = None, y_reg: Optional[Any] = None) -> None:
        if isinstance(X, pd.DataFrame):
            self.X = torch.tensor(X.values, dtype=torch.float32)
        elif isinstance(X, np.ndarray):
            self.X = torch.tensor(X, dtype=torch.float32)
        else:
            self.X = X.float()

        self.y_class = torch.tensor(y_class, dtype=torch.long) if y_class is not None else None
        self.y_reg = torch.tensor(y_reg, dtype=torch.float32) if y_reg is not None else None

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        item = {"x": self.X[idx]}
        if self.y_class is not None:
            item["y_class"] = self.y_class[idx]
        if self.y_reg is not None:
            item["y_reg"] = self.y_reg[idx]
        return item


class CrimeSequenceDataset(Dataset):
    """
    PyTorch Dataset for Time-Series Forecasting.
    Can be initialized with pre-computed sliding window sequence arrays (X_seq, y_target)
    OR directly with a 1D continuous time series.
    """

    def __init__(
        self,
        time_series: Optional[np.ndarray] = None,
        seq_len: int = 30,
        forecast_horizon: int = 7,
        X_seq: Optional[np.ndarray] = None,
        y_target: Optional[np.ndarray] = None,
    ) -> None:
        self.seq_len = seq_len
        self.forecast_horizon = forecast_horizon

        if X_seq is not None and y_target is not None:
            self.X = torch.tensor(X_seq, dtype=torch.float32)
            if self.X.dim() == 2:
                self.X = self.X.unsqueeze(-1)
            self.y = torch.tensor(y_target, dtype=torch.float32)
        elif time_series is not None:
            ts_tensor = torch.tensor(time_series, dtype=torch.float32)
            total_len = len(ts_tensor)
            samples_x = []
            samples_y = []
            for i in range(total_len - seq_len - forecast_horizon + 1):
                x = ts_tensor[i : i + seq_len].unsqueeze(-1)
                y = ts_tensor[i + seq_len : i + seq_len + forecast_horizon]
                samples_x.append(x)
                samples_y.append(y)
            self.X = torch.stack(samples_x) if samples_x else torch.empty(0)
            self.y = torch.stack(samples_y) if samples_y else torch.empty(0)
        else:
            raise ValueError("Either (X_seq, y_target) or time_series must be provided.")

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {"x_seq": self.X[idx], "y_target": self.y[idx]}


class CrimeDataModule:
    """
    PyTorch DataModule managing train, validation, and test DataLoaders
    for both tabular classifiers and chronological sequence forecasters.
    """

    def __init__(self, batch_size: int = 64, num_workers: int = 0, pin_memory: bool = False) -> None:
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.pin_memory = pin_memory

    def get_dataloaders(
        self, X_train: Any, y_train: Any, X_val: Any, y_val: Any, X_test: Any, y_test: Any
    ) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """Build PyTorch DataLoaders for train, val, and test tabular splits."""
        train_dataset = CrimeDataset(X_train, y_class=y_train)
        val_dataset = CrimeDataset(X_val, y_class=y_val)
        test_dataset = CrimeDataset(X_test, y_class=y_test)

        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
        )
        test_loader = DataLoader(
            test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
        )

        logger.info(
            f"Tabular DataLoaders created: Train ({len(train_loader)} batches), Val ({len(val_loader)} batches), Test ({len(test_loader)} batches)"
        )
        return train_loader, val_loader, test_loader

    def get_chronological_sequence_dataloaders(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        X_test: Optional[np.ndarray] = None,
        y_test: Optional[np.ndarray] = None,
    ) -> Tuple[DataLoader, DataLoader, Optional[DataLoader]]:
        """
        Build PyTorch DataLoaders from pre-split chronological sequence arrays.
        Zero data leakage guaranteed.
        """
        train_ds = CrimeSequenceDataset(X_seq=X_train, y_target=y_train)
        val_ds = CrimeSequenceDataset(X_seq=X_val, y_target=y_val)

        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size, shuffle=False)

        test_loader = None
        if X_test is not None and y_test is not None:
            test_ds = CrimeSequenceDataset(X_seq=X_test, y_target=y_test)
            test_loader = DataLoader(test_ds, batch_size=self.batch_size, shuffle=False)

        logger.info(
            f"Chronological Sequence DataLoaders created: Train ({len(train_loader)} batches), Val ({len(val_loader)} batches)"
        )
        return train_loader, val_loader, test_loader

    # Backward compatibility method
    def get_sequence_dataloaders(
        self, time_series: np.ndarray, seq_len: int = 14, forecast_horizon: int = 7
    ) -> Tuple[DataLoader, DataLoader]:
        """Chronological train/val sequence DataLoaders without random split leakage."""
        val_size = max(1, int(len(time_series) * 0.2))
        train_series = time_series[:-val_size]
        val_series = time_series[-val_size - seq_len :]

        train_ds = CrimeSequenceDataset(train_series, seq_len=seq_len, forecast_horizon=forecast_horizon)
        val_ds = CrimeSequenceDataset(val_series, seq_len=seq_len, forecast_horizon=forecast_horizon)

        train_loader = DataLoader(train_ds, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=self.batch_size, shuffle=False)

        return train_loader, val_loader
