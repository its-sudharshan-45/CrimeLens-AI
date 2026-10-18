"""
ai/evaluation/temporal_evaluator.py
===================================
Comprehensive Evaluation & Benchmarking for Temporal Forecasters (Phase 3).

Computes:
  - Global MAE, RMSE, safe MAPE, sMAPE, and R^2 on original incident count scale
  - Per-day forecast horizon metrics (Day +1 to Day +7)
  - Side-by-side comparison table: LSTM vs GRU vs N-BEATS baseline
  - Evaluation plots saved to datasets/processed/plots/
"""

import os
import json
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

from ai.models.temporal.lstm import CrimeLSTMForecaster
from ai.models.temporal.gru import CrimeGRUForecaster
from ai.models.nbeats_forecaster import NBEATSForecaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TemporalEvaluator")


def inverse_transform_target(
    y_scaled: np.ndarray,
    data_min: float = 24.0,
    data_max: float = 24.0,
) -> np.ndarray:
    """
    Inverse transform scaled target back to original daily crime counts.
    Mirrors sklearn MinMaxScaler(feature_range=(0, 1)) behavior:
      When data_min == data_max, scale_ = 1.0, min_ = -data_min.
      Thus unscaled = scaled + data_min.
    """
    if data_max == data_min:
        return y_scaled + data_min
    scale = 1.0 / (data_max - data_min)
    min_val = -data_min * scale
    return (y_scaled - min_val) / scale


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """
    Compute regression metrics between true and predicted crime counts.
    Includes safe division guards for MAPE.
    """
    error = y_pred - y_true
    abs_error = np.abs(error)
    sq_error = error ** 2

    mae = float(np.mean(abs_error))
    rmse = float(np.sqrt(np.mean(sq_error)))

    # Safe MAPE: avoid division by zero
    safe_denom = np.where(np.abs(y_true) < 1e-5, 1.0, np.abs(y_true))
    mape = float(np.mean(abs_error / safe_denom) * 100.0)

    # Symmetric MAPE (sMAPE)
    smape_denom = np.abs(y_true) + np.abs(y_pred) + 1e-5
    smape = float(np.mean(2.0 * abs_error / smape_denom) * 100.0)

    # R-squared
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    ss_res = np.sum(sq_error)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-8 else 0.0

    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "MAPE": round(mape, 2),
        "sMAPE": round(smape, 2),
        "R2": round(r2, 4),
    }


def calculate_per_day_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, Any]]:
    """Compute metrics individually for each forecast horizon day (Day +1 to Day +7)."""
    horizon = y_true.shape[1]
    per_day: Dict[str, Dict[str, Any]] = {}
    for day in range(horizon):
        day_key = f"Day +{day + 1}"
        per_day[day_key] = calculate_metrics(y_true[:, day], y_pred[:, day])
    return per_day


def generate_evaluation_plots(
    y_test_real: np.ndarray,
    predictions: Dict[str, np.ndarray],
    histories: Dict[str, Dict[str, list]],
    per_day_results: Dict[str, Dict[str, Dict[str, Any]]],
    output_dir: str = "datasets/processed/plots",
) -> None:
    """Generate and save visual evaluation plots."""
    os.makedirs(output_dir, exist_ok=True)

    # -----------------------------------------------------------
    # Plot 1: Actual vs Predicted (Day +1 forecast across test sequence)
    # -----------------------------------------------------------
    plt.figure(figsize=(12, 6))
    time_idx = np.arange(len(y_test_real))
    plt.plot(time_idx, y_test_real[:, 0], label="Actual Crime Count (Day +1)", color="#1e293b", linewidth=2.0)

    colors = {"LSTM": "#2563eb", "GRU": "#16a34a", "N-BEATS": "#d97706"}
    for model_name, preds in predictions.items():
        plt.plot(
            time_idx,
            preds[:, 0],
            label=f"{model_name} Predicted",
            color=colors.get(model_name, "#9333ea"),
            linestyle="--",
            alpha=0.85,
        )

    plt.title("Actual vs Predicted Crime Activity (Out-of-Sample Test Split: Jan–Jul 2024)", fontsize=13, fontweight="bold")
    plt.xlabel("Test Sample Window Index", fontsize=11)
    plt.ylabel("Daily Incident Count", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend()
    plot1_path = os.path.join(output_dir, "actual_vs_predicted.png")
    plt.tight_layout()
    plt.savefig(plot1_path, dpi=150)
    plt.close()
    logger.info(f"Saved Plot 1: {plot1_path}")

    # -----------------------------------------------------------
    # Plot 2: Training vs Validation Loss Curves
    # -----------------------------------------------------------
    plt.figure(figsize=(10, 5))
    for model_name, hist in histories.items():
        if "epoch" in hist and "train_loss" in hist and "val_loss" in hist:
            epochs = hist["epoch"]
            c = colors.get(model_name, "#2563eb")
            plt.plot(epochs, hist["train_loss"], label=f"{model_name} Train Loss", color=c, linestyle=":")
            plt.plot(epochs, hist["val_loss"], label=f"{model_name} Val Loss", color=c, linewidth=2.0)

    plt.title("Temporal Forecaster Training & Validation Loss Across Epochs", fontsize=13, fontweight="bold")
    plt.xlabel("Epoch", fontsize=11)
    plt.ylabel("Loss (Huber Loss)", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend()
    plot2_path = os.path.join(output_dir, "training_validation_loss.png")
    plt.tight_layout()
    plt.savefig(plot2_path, dpi=150)
    plt.close()
    logger.info(f"Saved Plot 2: {plot2_path}")

    # -----------------------------------------------------------
    # Plot 3: Forecast Horizon Error (Day +1 to Day +7 MAE)
    # -----------------------------------------------------------
    plt.figure(figsize=(10, 5))
    days = [f"Day +{d}" for d in range(1, 8)]
    x = np.arange(len(days))
    width = 0.25

    model_names = list(per_day_results.keys())
    for idx, name in enumerate(model_names):
        mae_list = [float(per_day_results[name][f"Day +{d}"]["MAE"]) for d in range(1, 8)]
        offset = (idx - len(model_names) / 2.0 + 0.5) * width
        plt.bar(x + offset, mae_list, width=width, label=name, color=colors.get(name, "#3b82f6"))

    plt.title("Forecast Horizon Error by Day (MAE on Unscaled Crime Counts)", fontsize=13, fontweight="bold")
    plt.xlabel("Forecast Horizon", fontsize=11)
    plt.ylabel("Mean Absolute Error (Incidents)", fontsize=11)
    plt.xticks(x, days)
    plt.grid(True, axis="y", linestyle=":", alpha=0.6)
    plt.legend()
    plot3_path = os.path.join(output_dir, "forecast_horizon_error.png")
    plt.tight_layout()
    plt.savefig(plot3_path, dpi=150)
    plt.close()
    logger.info(f"Saved Plot 3: {plot3_path}")


class TemporalEvaluator:
    """Evaluation manager for LSTM, GRU, and N-BEATS models."""

    def __init__(
        self,
        checkpoint_dir: str = "ai/models/temporal",
        data_dir: str = "datasets/processed/temporal_sequences",
    ) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.data_dir = data_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def evaluate_all(self) -> Dict[str, Any]:
        """Load test data, evaluate LSTM, GRU, and N-BEATS, and produce benchmark report."""
        meta_path = os.path.join(self.data_dir, "sequence_metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        test_npz = np.load(os.path.join(self.data_dir, "test_sequences.npz"))
        X_test = test_npz["X"].astype(np.float32)
        y_test = test_npz["y"].astype(np.float32)

        data_min = float(meta["scaler_data_min"][0])
        data_max = float(meta["scaler_data_max"][0])

        y_test_real = inverse_transform_target(y_test, data_min=data_min, data_max=data_max)

        predictions: Dict[str, np.ndarray] = {}
        histories: Dict[str, Dict[str, list]] = {}
        global_metrics: Dict[str, Dict[str, Any]] = {}
        per_day_results: Dict[str, Dict[str, Dict[str, Any]]] = {}

        # 1. Evaluate LSTM
        lstm_ckpt_path = os.path.join(self.checkpoint_dir, "lstm_best.pt")
        if os.path.exists(lstm_ckpt_path):
            ckpt = torch.load(lstm_ckpt_path, map_location=self.device, weights_only=False)
            cfg = ckpt.get("config", {})
            lstm = CrimeLSTMForecaster(
                input_size=cfg.get("input_size", 13),
                hidden_size=cfg.get("hidden_size", 64),
                num_layers=cfg.get("num_layers", 2),
                forecast_horizon=cfg.get("forecast_horizon", 7),
                dropout=cfg.get("dropout", 0.2),
            )
            lstm.load_state_dict(ckpt["model_state_dict"])
            lstm.to(self.device).eval()

            with torch.no_grad():
                preds_scaled = lstm(torch.from_numpy(X_test).to(self.device)).cpu().numpy()

            preds_real = inverse_transform_target(preds_scaled, data_min=data_min, data_max=data_max)
            predictions["LSTM"] = preds_real
            histories["LSTM"] = ckpt.get("history", {})
            m = calculate_metrics(y_test_real, preds_real)
            m["params"] = ckpt.get("param_count", sum(p.numel() for p in lstm.parameters()))
            m["training_time_sec"] = ckpt.get("training_time_sec", 0.0)
            m["input_type"] = "Multivariate (13 features)"
            global_metrics["LSTM"] = m
            per_day_results["LSTM"] = calculate_per_day_metrics(y_test_real, preds_real)
            logger.info(f"LSTM Test MAE: {m['MAE']:.4f} | RMSE: {m['RMSE']:.4f} | MAPE: {m['MAPE']:.2f}%")

        # 2. Evaluate GRU
        gru_ckpt_path = os.path.join(self.checkpoint_dir, "gru_best.pt")
        if os.path.exists(gru_ckpt_path):
            ckpt = torch.load(gru_ckpt_path, map_location=self.device, weights_only=False)
            cfg = ckpt.get("config", {})
            gru = CrimeGRUForecaster(
                input_size=cfg.get("input_size", 13),
                hidden_size=cfg.get("hidden_size", 64),
                num_layers=cfg.get("num_layers", 2),
                forecast_horizon=cfg.get("forecast_horizon", 7),
                dropout=cfg.get("dropout", 0.2),
            )
            gru.load_state_dict(ckpt["model_state_dict"])
            gru.to(self.device).eval()

            with torch.no_grad():
                preds_scaled = gru(torch.from_numpy(X_test).to(self.device)).cpu().numpy()

            preds_real = inverse_transform_target(preds_scaled, data_min=data_min, data_max=data_max)
            predictions["GRU"] = preds_real
            histories["GRU"] = ckpt.get("history", {})
            m = calculate_metrics(y_test_real, preds_real)
            m["params"] = ckpt.get("param_count", sum(p.numel() for p in gru.parameters()))
            m["training_time_sec"] = ckpt.get("training_time_sec", 0.0)
            m["input_type"] = "Multivariate (13 features)"
            global_metrics["GRU"] = m
            per_day_results["GRU"] = calculate_per_day_metrics(y_test_real, preds_real)
            logger.info(f"GRU Test MAE: {m['MAE']:.4f} | RMSE: {m['RMSE']:.4f} | MAPE: {m['MAPE']:.2f}%")

        # 3. Evaluate N-BEATS Baseline
        nbeats_path = os.path.join("ai/models", "forecast_model.pt")
        if os.path.exists(nbeats_path):
            try:
                nbeats = NBEATSForecaster(input_size=30, forecast_horizon=7)
                nbeats.load_state_dict(torch.load(nbeats_path, map_location=self.device, weights_only=True))
                nbeats.to(self.device).eval()

                # N-BEATS is univariate on total_crimes (index 0)
                x_univariate = torch.from_numpy(X_test[:, :, 0]).to(self.device)
                with torch.no_grad():
                    preds_scaled = nbeats(x_univariate).cpu().numpy()

                preds_real = inverse_transform_target(preds_scaled, data_min=data_min, data_max=data_max)
                predictions["N-BEATS"] = preds_real
                m = calculate_metrics(y_test_real, preds_real)
                m["params"] = sum(p.numel() for p in nbeats.parameters())
                m["training_time_sec"] = "Pre-trained"
                m["input_type"] = "Univariate (total_crimes only)"
                global_metrics["N-BEATS"] = m
                per_day_results["N-BEATS"] = calculate_per_day_metrics(y_test_real, preds_real)
                logger.info(f"N-BEATS Baseline Test MAE: {m['MAE']:.4f} | RMSE: {m['RMSE']:.4f} | MAPE: {m['MAPE']:.2f}%")
            except Exception as e:
                logger.warning(f"Could not evaluate N-BEATS baseline: {e}")

        # Generate plots
        generate_evaluation_plots(
            y_test_real=y_test_real,
            predictions=predictions,
            histories=histories,
            per_day_results=per_day_results,
        )

        # Print Leaderboard
        print("\n" + "=" * 80)
        print("TEMPORAL CRIME FORECASTING BENCHMARK (OUT-OF-SAMPLE TEST SET: 2024)")
        print("=" * 80)
        print(f"{'Model':<10} | {'MAE':<8} | {'RMSE':<8} | {'MAPE (%)':<10} | {'sMAPE (%)':<10} | {'Params':<8} | {'Input Type'}")
        print("-" * 80)
        for name, m in global_metrics.items():
            print(f"{name:<10} | {m['MAE']:<8.4f} | {m['RMSE']:<8.4f} | {m['MAPE']:<10.2f} | {m['sMAPE']:<10.2f} | {m['params']:<8} | {m['input_type']}")
        print("=" * 80)
        print("Note: N-BEATS baseline operates as a univariate model (total_crimes only).")
        print("      LSTM and GRU operate as multivariate models on 13 engineered features.")

        # Per-day report
        print("\nPER-DAY FORECAST ERROR BREAKDOWN (MAE):")
        print("-" * 50)
        print(f"{'Horizon':<10} | " + " | ".join(f"{name:<10}" for name in per_day_results.keys()))
        print("-" * 50)
        for day in range(1, 8):
            d_key = f"Day +{day}"
            row = [f"{d_key:<10}"]
            for name in per_day_results.keys():
                row.append(f"{per_day_results[name][d_key]['MAE']:<10.4f}")
            print(" | ".join(row))
        print("-" * 50)

        # Determine Primary Model
        # Prefer lowest Test MAE; if within 0.05, prefer lower parameter count
        primary_model = "LSTM"
        if "LSTM" in global_metrics and "GRU" in global_metrics:
            if global_metrics["GRU"]["MAE"] <= global_metrics["LSTM"]["MAE"]:
                primary_model = "GRU"
            else:
                primary_model = "LSTM"

        logger.info(f"Recommended Primary Temporal Model: {primary_model}")

        # Save evaluation summary JSON
        results_path = os.path.join(self.checkpoint_dir, "temporal_evaluation_results.json")
        out_summary = {
            "evaluation_date": meta.get("test_dates", []),
            "target": "total_crimes (unscaled incident counts)",
            "primary_model": primary_model,
            "global_metrics": global_metrics,
            "per_day_metrics": per_day_results,
        }
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(out_summary, f, indent=2)

        return out_summary


if __name__ == "__main__":
    evaluator = TemporalEvaluator()
    evaluator.evaluate_all()
