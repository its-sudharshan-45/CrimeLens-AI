"""
ai/inference/temporal_predictor.py
==================================
Standalone Inference Engine for Temporal Forecasters in CrimeLens AI (Phase 3).

Provides:
  - TemporalCrimePredictor class for loading checkpoints and running forecasts
  - Validation of input dimensions (30 x 13) and numerical sanity
  - Inverse scaling to real incident counts
  - Honest empirical prediction intervals based on validation residuals
  - Ethical disclaimer regarding probabilistic crime activity estimation
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
import numpy as np
import torch

from ai.models.temporal.lstm import CrimeLSTMForecaster
from ai.models.temporal.gru import CrimeGRUForecaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TemporalPredictor")

ETHICAL_DISCLAIMER = (
    "The model forecasts historical crime activity patterns and provides "
    "probability-based temporal risk estimates to support early-stage resource "
    "planning and investigation. It does not predict individual crimes, exact locations, "
    "or specific perpetrators."
)


class TemporalCrimePredictor:
    """
    Production-clean inference predictor for 7-day crime activity forecasting.
    """

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        model_type: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        # Default to GRU (best performing in Phase 3 benchmark) or LSTM if available
        if checkpoint_path is None:
            default_gru = os.path.join("ai/models/temporal", "gru_best.pt")
            default_lstm = os.path.join("ai/models/temporal", "lstm_best.pt")
            if os.path.exists(default_gru):
                checkpoint_path = default_gru
            elif os.path.exists(default_lstm):
                checkpoint_path = default_lstm
            else:
                raise FileNotFoundError("No trained temporal checkpoint found in ai/models/temporal/.")

        self.checkpoint_path = checkpoint_path
        self._load_model(model_type)

    def _load_model(self, requested_type: Optional[str] = None) -> None:
        """Load checkpoint and instantiate architecture."""
        if not os.path.exists(self.checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found at: {self.checkpoint_path}")

        ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.model_type = requested_type or ckpt.get("model_type", "GRU")
        cfg = ckpt.get("config", {})

        input_size = cfg.get("input_size", 13)
        hidden_size = cfg.get("hidden_size", 64)
        num_layers = cfg.get("num_layers", 2)
        forecast_horizon = cfg.get("forecast_horizon", 7)
        dropout = cfg.get("dropout", 0.2)

        if self.model_type.upper() == "GRU":
            self.model = CrimeGRUForecaster(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                forecast_horizon=forecast_horizon,
                dropout=dropout,
            )
        elif self.model_type.upper() == "LSTM":
            self.model = CrimeLSTMForecaster(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                forecast_horizon=forecast_horizon,
                dropout=dropout,
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")

        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device).eval()

        self.feature_columns = ckpt.get("feature_columns", [])
        self.scaler_data_min = ckpt.get("scaler_data_min", [])
        self.scaler_data_max = ckpt.get("scaler_data_max", [])
        self.seq_len = cfg.get("seq_len", 30)
        self.forecast_horizon = forecast_horizon
        self.best_val_loss = ckpt.get("best_val_loss", 0.0)

        # Residual std for 95% prediction interval (computed from validation loss)
        self.residual_std = float(np.sqrt(max(self.best_val_loss, 1e-6)))

        logger.info(f"Loaded {self.model_type} Forecaster from {self.checkpoint_path} on {self.device}")

    def inverse_scale_target(self, y_scaled: np.ndarray) -> np.ndarray:
        """Inverse scale target array back to raw incident counts."""
        if len(self.scaler_data_min) > 0 and len(self.scaler_data_max) > 0:
            d_min = float(self.scaler_data_min[0])
            d_max = float(self.scaler_data_max[0])
        else:
            d_min = 24.0
            d_max = 24.0

        if d_max == d_min:
            return y_scaled + d_min
        scale = 1.0 / (d_max - d_min)
        min_val = -d_min * scale
        return (y_scaled - min_val) / scale

    def predict(
        self,
        sequence: Union[np.ndarray, torch.Tensor],
        return_uncertainty: bool = True,
    ) -> Dict[str, Any]:
        """
        Run inference on a single 30-day sequence or batch of sequences.

        Args:
            sequence: Array of shape (30, 13) or (batch_size, 30, 13)
            return_uncertainty: Whether to include empirical prediction intervals

        Returns:
            Dictionary containing 7-day predictions with uncertainty bounds
        """
        if isinstance(sequence, np.ndarray):
            x_arr = sequence.copy()
        elif isinstance(sequence, torch.Tensor):
            x_arr = sequence.detach().cpu().numpy()
        else:
            raise TypeError(f"Expected numpy.ndarray or torch.Tensor, got {type(sequence)}")

        # Validate dimensions
        is_single = False
        if x_arr.ndim == 2:
            if x_arr.shape != (self.seq_len, len(self.feature_columns) or 13):
                raise ValueError(
                    f"Expected input shape ({self.seq_len}, 13), got {x_arr.shape}"
                )
            x_arr = np.expand_dims(x_arr, axis=0)  # (1, 30, 13)
            is_single = True
        elif x_arr.ndim == 3:
            if x_arr.shape[1:] != (self.seq_len, len(self.feature_columns) or 13):
                raise ValueError(
                    f"Expected input shape (batch_size, {self.seq_len}, 13), got {x_arr.shape}"
                )
        else:
            raise ValueError(f"Expected 2D or 3D input tensor, got shape {x_arr.shape}")

        # Check for NaN / Inf
        if not np.all(np.isfinite(x_arr)):
            raise ValueError("Input sequence contains NaN or Inf values.")

        # Forward pass
        x_tensor = torch.from_numpy(x_arr.astype(np.float32)).to(self.device)
        with torch.no_grad():
            preds_scaled = self.model(x_tensor).cpu().numpy()  # (B, 7)

        # Rescale
        preds_real = self.inverse_scale_target(preds_scaled)

        # 95% Prediction Interval: ± 1.96 * residual_std
        margin = 1.96 * self.residual_std if return_uncertainty else 0.0

        if is_single:
            daily_preds = []
            single_preds = preds_real[0]
            for day in range(self.forecast_horizon):
                count = float(single_preds[day])
                entry: Dict[str, Any] = {
                    "day": day + 1,
                    "predicted_crime_count": round(max(0.0, count), 2),
                }
                if return_uncertainty:
                    entry["lower_bound_95"] = round(max(0.0, count - margin), 2)
                    entry["upper_bound_95"] = round(count + margin, 2)
                daily_preds.append(entry)

            return {
                "model_name": self.model_type,
                "forecast_horizon_days": self.forecast_horizon,
                "predictions": daily_preds,
                "uncertainty_method": (
                    "Empirical validation residual standard deviation (95% prediction interval)"
                    if return_uncertainty
                    else "None"
                ),
                "disclaimer": ETHICAL_DISCLAIMER,
            }
        else:
            batch_results = []
            for b in range(preds_real.shape[0]):
                daily_preds = []
                for day in range(self.forecast_horizon):
                    count = float(preds_real[b, day])
                    entry = {
                        "day": day + 1,
                        "predicted_crime_count": round(max(0.0, count), 2),
                    }
                    if return_uncertainty:
                        entry["lower_bound_95"] = round(max(0.0, count - margin), 2)
                        entry["upper_bound_95"] = round(count + margin, 2)
                    daily_preds.append(entry)
                batch_results.append(daily_preds)

            return {
                "model_name": self.model_type,
                "batch_size": preds_real.shape[0],
                "forecast_horizon_days": self.forecast_horizon,
                "batch_predictions": batch_results,
                "uncertainty_method": "Empirical validation residual standard deviation",
                "disclaimer": ETHICAL_DISCLAIMER,
            }


def run_sample_inference() -> None:
    """CLI test: load sample test sequence and execute forecast."""
    logger.info("Running standalone inference test with sample sequence...")
    test_npz_path = "datasets/processed/temporal_sequences/test_sequences.npz"
    if not os.path.exists(test_npz_path):
        raise FileNotFoundError(f"Missing test sequence file: {test_npz_path}")

    test_data = np.load(test_npz_path)
    sample_seq = test_data["X"][0]  # Shape: (30, 13)
    sample_target = test_data["y"][0]

    predictor = TemporalCrimePredictor()
    result = predictor.predict(sample_seq, return_uncertainty=True)

    print("\n" + "=" * 60)
    print("STANDALONE TEMPORAL PREDICTOR INFERENCE OUTPUT")
    print("=" * 60)
    print(f"Model: {result['model_name']}")
    print(f"Horizon: {result['forecast_horizon_days']} Days")
    print("-" * 60)
    print(f"{'Day':<6} | {'Predicted Crimes':<18} | {'95% Prediction Interval'}")
    print("-" * 60)
    for p in result["predictions"]:
        interval = f"[{p.get('lower_bound_95', '-')} - {p.get('upper_bound_95', '-')}]"
        print(f"Day +{p['day']:<2} | {p['predicted_crime_count']:<18.2f} | {interval}")
    print("-" * 60)
    print(f"Uncertainty: {result['uncertainty_method']}")
    print(f"Disclaimer: {result['disclaimer']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_sample_inference()
