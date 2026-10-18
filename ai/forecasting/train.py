"""
ai/forecasting/train.py
=======================
One-command training + honest evaluation for the CrimeLens AI GRU forecaster.

Usage
-----
    python -m ai.forecasting.train
    python -m ai.forecasting.train --epochs 60 --version forecast_v1

The pipeline:
  1. Loads the real dataset and builds one continuous daily series per scope
     (all cities + all crime types).
  2. Fits per-scope normalisation statistics on the **training window only**.
  3. Builds pooled 30-day lookback / 7-day horizon windows with chronological
     train / validation / test splits (test is never used for tuning).
  4. Trains ONE PyTorch GRU with reproducible seeds and early stopping.
  5. Evaluates on the held-out test split, reporting MAE / RMSE / WAPE / sMAPE
     plus a persistence baseline.
  6. Saves the checkpoint, scope series, scope statistics, feature schema,
     configuration, metrics, evaluation results and plots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from ai.forecasting import data as fdata
from ai.forecasting import evaluate as feval
from ai.models.temporal.gru import CrimeGRUForecaster

DEFAULT_OUTPUT_DIR = fdata.PROJECT_ROOT / "ai" / "registry" / "forecast_v1"


def seed_everything(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def dataset_hash(path: str | Path = fdata.DEFAULT_DATASET_PATH) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _scope_stat_vectors(scopes, scope_index):
    """Return per-window mean/std arrays aligned to ``scope_index``."""
    mean = np.array([scopes[k].mean for k in scope_index], dtype="float64")
    std = np.array([scopes[k].std for k in scope_index], dtype="float64")
    return mean, std


def _inverse(z: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """Invert z-scored forecasts to real counts; clip at zero."""
    mean = mean.reshape(-1, 1)
    std = std.reshape(-1, 1)
    return np.clip(z * std + mean, 0.0, None)


def train_forecaster(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    epochs: int = 60,
    batch_size: int = 128,
    lr: float = 1e-3,
    patience: int = 10,
    seed: int = 42,
    device: str | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    (output_dir / "plots").mkdir(parents=True, exist_ok=True)
    seed_everything(seed)
    torch_device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

    print("=" * 72)
    print("CrimeLens AI — GRU crime-count forecaster training")
    print("=" * 72)

    # 1-2. Data → scopes → train-only statistics
    raw = fdata.load_raw_dataset()
    scopes = fdata.build_all_scope_series(raw)
    ds = fdata.build_dataset(scopes)
    print(f"Scopes: {ds.metadata['n_scopes']} | windows train/val/test: "
          f"{ds.metadata['train_windows']}/{ds.metadata['val_windows']}/{ds.metadata['test_windows']}")

    # 3. Tensors
    Xtr = torch.from_numpy(ds.X_train)
    ytr = torch.from_numpy(ds.y_train)
    Xva = torch.from_numpy(ds.X_val)
    yva = torch.from_numpy(ds.y_val)
    Xte = torch.from_numpy(ds.X_test)
    yte = torch.from_numpy(ds.y_test)

    train_loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(Xtr, ytr), batch_size=batch_size, shuffle=True
    )
    val_loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(Xva, yva), batch_size=batch_size, shuffle=False
    )

    # 4. Model + optimiser
    model = CrimeGRUForecaster(
        input_size=ds.metadata["n_features"],
        hidden_size=64,
        num_layers=2,
        forecast_horizon=ds.metadata["forecast_horizon"],
        dropout=0.2,
    ).to(torch_device)
    criterion = nn.HuberLoss(delta=1.0)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimiser, mode="min", factor=0.5, patience=3, min_lr=1e-5)

    history = {"epoch": [], "train_loss": [], "val_loss": [], "learning_rate": []}
    best_val, best_epoch, best_state, wait = float("inf"), 0, None, 0
    started = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        running, seen = 0.0, 0
        for bx, by in train_loader:
            bx, by = bx.to(torch_device), by.to(torch_device)
            optimiser.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            running += loss.item() * bx.size(0)
            seen += bx.size(0)
        train_loss = running / max(seen, 1)

        model.eval()
        vrun, vseen = 0.0, 0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(torch_device), by.to(torch_device)
                vrun += criterion(model(bx), by).item() * bx.size(0)
                vseen += bx.size(0)
        val_loss = vrun / max(vseen, 1)
        scheduler.step(val_loss)

        history["epoch"].append(epoch)
        history["train_loss"].append(round(train_loss, 6))
        history["val_loss"].append(round(val_loss, 6))
        history["learning_rate"].append(optimiser.param_groups[0]["lr"])

        marker = ""
        if val_loss < best_val - 1e-6:
            best_val, best_epoch, wait = val_loss, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            marker = " [best]"
        else:
            wait += 1
        print(f"epoch {epoch:02d}/{epochs}  train={train_loss:.6f}  val={val_loss:.6f}{marker}")
        if wait >= patience:
            print(f"early stopping at epoch {epoch} (no val improvement for {patience} epochs)")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    training_time = round(time.time() - started, 2)

    # 5. Held-out evaluation (test split is touched only here)
    model.eval()
    with torch.no_grad():
        test_pred_z = model(Xte.to(torch_device)).cpu().numpy()

    mean_v, std_v = _scope_stat_vectors(scopes, ds.scope_index["test"])
    y_true = _inverse(yte.numpy(), mean_v, std_v)
    y_pred = _inverse(test_pred_z, mean_v, std_v)

    # Persistence baseline: repeat each window's last observed count.
    last_z = ds.X_test[:, -1, 0]
    last_count = np.clip(last_z * std_v + mean_v, 0.0, None)
    y_persist = feval.persistence_forecast(last_count, ds.metadata["forecast_horizon"])

    metrics = {
        "model": feval.regression_metrics(y_true.ravel(), y_pred.ravel()),
        "persistence_baseline": feval.regression_metrics(y_true.ravel(), y_persist.ravel()),
    }
    metrics["model_beats_baseline_MAE"] = metrics["model"]["MAE"] < metrics["persistence_baseline"]["MAE"]
    per_horizon = {
        "model": feval.per_horizon_metrics(y_true, y_pred),
        "persistence_baseline": feval.per_horizon_metrics(y_true, y_persist),
    }
    per_scope = feval.per_scope_metrics(y_true, y_pred, ds.scope_index["test"], ds.scope_keys)

    print("-" * 72)
    print(f"TEST  model      MAE={metrics['model']['MAE']:.4f}  RMSE={metrics['model']['RMSE']:.4f}  "
          f"WAPE={metrics['model']['WAPE']:.4f}  R2={metrics['model']['R2']:.4f}")
    print(f"TEST  persistence MAE={metrics['persistence_baseline']['MAE']:.4f}  "
          f"RMSE={metrics['persistence_baseline']['RMSE']:.4f}  WAPE={metrics['persistence_baseline']['WAPE']:.4f}")
    print("-" * 72)

    # 6. Persist artifacts
    d_hash = dataset_hash()
    config = {
        "model_type": "GRU",
        "input_size": ds.metadata["n_features"],
        "hidden_size": 64,
        "num_layers": 2,
        "dropout": 0.2,
        "seq_len": ds.metadata["seq_len"],
        "forecast_horizon": ds.metadata["forecast_horizon"],
        "feature_columns": ds.metadata["feature_columns"],
    }
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "config": config,
        "feature_columns": ds.metadata["feature_columns"],
        "seq_len": ds.metadata["seq_len"],
        "forecast_horizon": ds.metadata["forecast_horizon"],
        "scope_stats": {k: {"mean": s.mean, "std": s.std, **s.metadata} for k, s in scopes.items()},
        "dataset_hash_md5": d_hash,
        "seed": seed,
        "best_epoch": best_epoch,
        "best_val_loss": float(best_val),
        "training_time_sec": training_time,
        "history": history,
        "splits": {"train": ds.metadata["train_dates"], "val": ds.metadata["val_dates"], "test": ds.metadata["test_dates"]},
    }
    torch.save(checkpoint, output_dir / "gru_forecaster.pt")

    # Scope series (needed for real inference: history + backtest) -----------------
    scope_series_payload = {
        "dates": [d.date().isoformat() for d in next(iter(scopes.values())).dates],
        "scopes": {
            k: {"scope_type": s.scope_type, "display_name": s.display_name, "counts": [round(float(c), 4) for c in s.counts]}
            for k, s in scopes.items()
        },
    }
    with open(output_dir / "scope_series.json", "w", encoding="utf-8") as fh:
        json.dump(scope_series_payload, fh)

    with open(output_dir / "scope_stats.json", "w", encoding="utf-8") as fh:
        json.dump({k: {"mean": s.mean, "std": s.std, **s.metadata} for k, s in scopes.items()}, fh, indent=2)

    with open(output_dir / "feature_columns.json", "w", encoding="utf-8") as fh:
        json.dump({"feature_columns": ds.metadata["feature_columns"], "n_features": ds.metadata["n_features"]}, fh, indent=2)

    with open(output_dir / "forecast_config.json", "w", encoding="utf-8") as fh:
        json.dump({**config, "seed": seed, "batch_size": batch_size, "lr": lr, "patience": patience,
                   "epochs_requested": epochs, "best_epoch": best_epoch}, fh, indent=2)

    with open(output_dir / "metrics.json", "w", encoding="utf-8") as fh:
        json.dump({"test": metrics, "per_horizon": per_horizon}, fh, indent=2)

    evaluation_results = {
        "model_name": "CrimeGRUForecaster",
        "model_version": output_dir.name,
        "evaluation_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "dataset_path": str(fdata.DEFAULT_DATASET_PATH),
        "dataset_hash_md5": d_hash,
        "splits": checkpoint["splits"],
        "seq_len": ds.metadata["seq_len"],
        "forecast_horizon": ds.metadata["forecast_horizon"],
        "n_scopes": ds.metadata["n_scopes"],
        "test_windows": ds.metadata["test_windows"],
        "metrics": metrics,
        "per_horizon": per_horizon,
        "per_scope": per_scope,
        "honest_note": (
            "The dataset is synthetic and balanced; city/type daily counts show no "
            "measurable autocorrelation, so the GRU is expected to perform close to "
            "the persistence baseline. Metrics are computed on the untouched test split."
        ),
    }
    with open(output_dir / "evaluation_results.json", "w", encoding="utf-8") as fh:
        json.dump(evaluation_results, fh, indent=2)

    metadata = {
        "version": output_dir.name,
        "primary_model": "CrimeGRUForecaster",
        "framework": f"PyTorch {torch.__version__}",
        "python": platform.python_version(),
        "device": str(torch_device),
        "seed": seed,
        "seq_len": ds.metadata["seq_len"],
        "forecast_horizon": ds.metadata["forecast_horizon"],
        "n_features": ds.metadata["n_features"],
        "n_scopes": ds.metadata["n_scopes"],
        "dataset_rows": len(raw),
        "dataset_hash_md5": d_hash,
        "best_epoch": best_epoch,
        "best_val_loss": float(best_val),
        "training_time_sec": training_time,
        "test_mae": metrics["model"]["MAE"],
        "test_rmse": metrics["model"]["RMSE"],
        "test_wape": metrics["model"]["WAPE"],
        "persistence_mae": metrics["persistence_baseline"]["MAE"],
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(output_dir / "model_metadata.json", "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    _save_plots(output_dir, history, y_true, y_pred, per_horizon)

    print(f"Artifacts written to {output_dir}")
    return {"metrics": metrics, "evaluation": evaluation_results, "metadata": metadata, "output_dir": str(output_dir)}


def _save_plots(output_dir: Path, history, y_true, y_pred, per_horizon) -> None:
    """Save real evaluation plots (best-effort; never fatal)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001 - plotting is optional, never fatal
        print(f"plotting skipped: {exc}")
        return

    try:
        plt.figure(figsize=(7, 4))
        plt.plot(history["epoch"], history["train_loss"], label="train")
        plt.plot(history["epoch"], history["val_loss"], label="validation")
        plt.xlabel("epoch")
        plt.ylabel("Huber loss")
        plt.legend()
        plt.title("Training / validation loss")
        plt.tight_layout()
        plt.savefig(output_dir / "plots" / "training_validation_loss.png", dpi=110)
        plt.close()

        plt.figure(figsize=(7, 4))
        n = min(500, y_true.shape[0])
        plt.plot(y_true.ravel()[:n], label="actual", alpha=0.8)
        plt.plot(y_pred.ravel()[:n], label="predicted", alpha=0.8)
        plt.xlabel("test observation")
        plt.ylabel("daily crime count")
        plt.legend()
        plt.title("Actual vs predicted (first 500 held-out observations)")
        plt.tight_layout()
        plt.savefig(output_dir / "plots" / "actual_vs_predicted.png", dpi=110)
        plt.close()

        steps = [f"Day +{i+1}" for i in range(len(per_horizon["model"]))]
        mae_model = [per_horizon["model"][s]["MAE"] for s in steps]
        mae_base = [per_horizon["persistence_baseline"][s]["MAE"] for s in steps]
        plt.figure(figsize=(7, 4))
        plt.plot(steps, mae_model, marker="o", label="GRU")
        plt.plot(steps, mae_base, marker="s", label="persistence")
        plt.xlabel("forecast step")
        plt.ylabel("MAE")
        plt.legend()
        plt.title("Forecast-horizon error")
        plt.tight_layout()
        plt.savefig(output_dir / "plots" / "forecast_horizon_error.png", dpi=110)
        plt.close()
        print("plots saved to", output_dir / "plots")
    except Exception as exc:  # noqa: BLE001 - best-effort plots, never fail the run
        print(f"plot generation failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the CrimeLens AI GRU crime-count forecaster.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()
    train_forecaster(
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
        seed=args.seed,
        device=args.device,
    )


if __name__ == "__main__":
    main()
